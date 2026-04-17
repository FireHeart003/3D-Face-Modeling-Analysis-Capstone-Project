// Import renderer.h and everything needed from Filament Modules
#include "renderer.h"
#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/RenderableManager.h>
#include <filament/MaterialInstance.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filament/RenderTarget.h>
#include <filament/Texture.h>
#include <filament/Fence.h>
#include <filament/Viewport.h>
#include <filament/LightManager.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/FilamentAsset.h>
#include <gltfio/FilamentInstance.h>
#include <gltfio/ResourceLoader.h>
#include <gltfio/TextureProvider.h>
#include <gltfio/Animator.h>
#include <gltfio/materials/uberarchive.h>
#include <utils/EntityManager.h>
#include <backend/DriverEnums.h>
#include <backend/PixelBufferDescriptor.h>
#include <math/vec3.h>
#include <math/vec4.h>
#include <math/mat4.h>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <algorithm>
#include <filament/Skybox.h>

using namespace filament;
using namespace filament::math;
using namespace filament::gltfio;

// Constructor
FaceRenderer::FaceRenderer(int width, int height, const std::string& filamentDistPath)
    : mWidth(width), mHeight(height), mFilamentDistPath(filamentDistPath) {

    // Start up Filament
    mEngine   = Engine::create(); // Create the Filament Engine
    mRenderer = mEngine->createRenderer(); // Create the environment, the drawing
    mScene    = mEngine->createScene(); // Create the scene, the 3D world where object lives in

    // Create a white background(skybox)
    mSkybox = Skybox::Builder()
        .color({1.0f, 1.0f, 1.0f, 1.0f}) // Values are in RGBA format, set to white but default is black
        .build(*mEngine);
    mScene->setSkybox(mSkybox);

    // Set up render target and offscreen texture to render into
    _setupRenderTarget();

    // Create the view for the camera
    mView = mEngine->createView();
    mView->setScene(mScene);
    mView->setViewport({0, 0, (uint32_t)mWidth, (uint32_t)mHeight});
    mView->setRenderTarget(mRenderTarget);
    mView->setBlendMode(View::BlendMode::OPAQUE); // Set to opaque

    // Crteate the camera entity and attach it to the view
    mCameraEntity = utils::EntityManager::get().create(); // Light, camera, meshes are all entities
    mCamera = mEngine->createCamera(mCameraEntity);
    mView->setCamera(mCamera);

    // Sets up lighting
    _setupLight();

    // Filament's built in ubershader that handles all material types
    mMaterialProvider = createUbershaderProvider(
        mEngine,
        UBERARCHIVE_DEFAULT_DATA,
        UBERARCHIVE_DEFAULT_SIZE
    );

    // Set up GLB loading pipeline
    mAssetLoader     = AssetLoader::create({mEngine, mMaterialProvider}); // Loads and parses the GLB file
    mResourceLoader  = new ResourceLoader({mEngine}); // Loads the textures
    mTextureProvider = createStbProvider(mEngine); // Decodes PNG/JPEG images
    mResourceLoader->addTextureProvider("image/png",  mTextureProvider);
    mResourceLoader->addTextureProvider("image/jpeg", mTextureProvider);
}

// Destroys and cleans up everything (Manual cleanup necessary to prevent memory leaks)
FaceRenderer::~FaceRenderer() {
    if (mAsset) {
        mScene->removeEntities(mAsset->getEntities(), mAsset->getEntityCount());
        mAssetLoader->destroyAsset(mAsset);
    }
    delete mResourceLoader;
    mMaterialProvider->destroyMaterials();
    delete mMaterialProvider;
    AssetLoader::destroy(&mAssetLoader);
    mEngine->destroyCameraComponent(mCameraEntity);
    utils::EntityManager::get().destroy(mCameraEntity);
    for (auto& light : mLights) {
        mEngine->destroy(light);
    }

    if (mSkybox) {
        mEngine->destroy(mSkybox);
    }

    mEngine->destroy(mView);
    mEngine->destroy(mScene);
    mEngine->destroy(mRenderer);
    mEngine->destroy(mColorTexture);
    mEngine->destroy(mDepthTexture);
    mEngine->destroy(mRenderTarget);
    Engine::destroy(&mEngine);
}


void FaceRenderer::_setupRenderTarget() {
    // Set up GPU texture to render color
    mColorTexture = Texture::Builder()
        .width(mWidth).height(mHeight)
        .levels(1)
        .usage(Texture::Usage::COLOR_ATTACHMENT | Texture::Usage::SAMPLEABLE | Texture::Usage::BLIT_SRC)
        .format(Texture::InternalFormat::RGBA8)
        .build(*mEngine);

    // Depth texture helps Filament understand the distance of objects from each other and from camera
    mDepthTexture = Texture::Builder()
        .width(mWidth).height(mHeight)
        .levels(1)
        .usage(Texture::Usage::DEPTH_ATTACHMENT)
        .format(Texture::InternalFormat::DEPTH24)
        .build(*mEngine);

    // Combines color and depth textures into one render target
    mRenderTarget = RenderTarget::Builder()
        .texture(RenderTarget::AttachmentPoint::COLOR, mColorTexture)
        .texture(RenderTarget::AttachmentPoint::DEPTH, mDepthTexture)
        .build(*mEngine);
}

void FaceRenderer::_setupLight() {
    // ── 3-point + back fill lighting rig 
    // Key light: front-left, warm, strongest
    mLights[0] = utils::EntityManager::get().create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color({1.0f, 0.98f, 0.95f})
        .intensity(90000.0f)
        .direction({0.4f, -0.6f, -1.0f}) // Adjust direction
        .build(*mEngine, mLights[0]);
    mScene->addEntity(mLights[0]); // Puts light in the scene

    // Fill light: front-right, cooler, softer
    mLights[1] = utils::EntityManager::get().create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color({0.85f, 0.90f, 1.0f})
        .intensity(40000.0f)
        .direction({-0.6f, -0.3f, -0.8f}) // Adjust direction
        .build(*mEngine, mLights[1]);
    mScene->addEntity(mLights[1]); // Puts light in the scene

    // Back/rim light: behind the head, prevents pure-black silhouette
    mLights[2] = utils::EntityManager::get().create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color({0.9f, 0.95f, 1.0f})
        .intensity(50000.0f)
        .direction({0.0f, -0.2f, 1.0f}) // Adjust direction
        .build(*mEngine, mLights[2]);
    mScene->addEntity(mLights[2]); // Puts light in the scene

    // Top light: gentle overhead fill, reduces harsh shadows under brow/nose
    mLights[3] = utils::EntityManager::get().create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color({1.0f, 1.0f, 1.0f})
        .intensity(25000.0f)
        .direction({0.0f, -1.0f, 0.0f}) // Adjust direction
        .build(*mEngine, mLights[3]);
    mScene->addEntity(mLights[3]); // Puts light in the scene
}

void FaceRenderer::_fixMaterials() {
    // Filament's ubershader renames all materials to "base_lit_opaque" etc so
    // we cannot match by name here. All alphaMode/doubleSided is baked into the
    // GLB by obj_to_glb.py. We use FilamentInstance::getMaterialInstances()
    // (confirmed in FilamentInstance.h) to iterate and force doubleSided=true
    // on everything as a safe global override.
    FilamentInstance* instance = mAsset->getInstance(); // Get loaded model instance
    if (!instance) {
        printf("  [WARN] No FilamentInstance found\n");
        return;
    }

    // Grab all the needed material instances
    size_t matCount = instance->getMaterialInstanceCount();
    MaterialInstance* const* materials = instance->getMaterialInstances();


    printf("=== _fixMaterials: %zu material instances ===\n", matCount);
    for (size_t i = 0; i < matCount; i++) {
        if (!materials[i]) continue;
        const char* name = materials[i]->getName();
        printf("  [%zu] '%s'\n", i, name ? name : "(null)");
        // Force material to render on both sides of each polygon
        materials[i]->setDoubleSided(true);
    }
    printf("=============================================\n");
}

void FaceRenderer::loadModel(const std::string& glbPath) {
    // Free memory if a model is already loaded
    if (mAsset) {
        mScene->removeEntities(mAsset->getEntities(), mAsset->getEntityCount());
        mAssetLoader->destroyAsset(mAsset);
        mAsset = nullptr;
    }

    // Load GLB file
    std::ifstream file(glbPath, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open GLB file: " + glbPath);
    }
    size_t size = file.tellg();
    file.seekg(0);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);

    // Parse GLB bytes into Filament asset and load all its textures
    mAsset = mAssetLoader->createAsset(buffer.data(), buffer.size());
    if (!mAsset) {
        throw std::runtime_error("Failed to load GLB asset: " + glbPath);
    }

    mResourceLoader->loadResources(mAsset);

    // Apply GLB scene graph transforms 
    // getAnimator() lives on FilamentInstance, not FilamentAsset.
    // Calling applyAnimation + updateBoneMatrices evaluates the scene graph so
    // sub-meshes (eyes, eyebrows, teeth) land on the face instead of origin.
    FilamentInstance* instance = mAsset->getInstance();
    if (instance) {
        Animator* animator = instance->getAnimator();
        if (animator) {
            if (animator->getAnimationCount() > 0) {
                animator->applyAnimation(0, 0.0f);
            }
            animator->updateBoneMatrices();
            printf("Animator: applied %zu animation(s)\n",
                   animator->getAnimationCount());
        } else {
            printf("Animator: no animator on instance\n");
        }
    } else {
        printf("Animator: no instance found\n");
    }
    mEngine->flushAndWait();

    // Adds all mesh entities to scene
    mAsset->releaseSourceData();
    mScene->addEntities(mAsset->getEntities(), mAsset->getEntityCount());

    _fixMaterials();

    // ── Bounding box + auto-radius ────────────────────────────────────────────
    // Use instance bbox (reflects actual node transforms) if available,
    // fall back to asset bbox.
    filament::Aabb bbox;
    if (instance) {
        bbox = instance->getBoundingBox();
    } else {
        bbox = mAsset->getBoundingBox();
    }

    // Computes face center and how far camera should be
    mFaceCenter = (bbox.min + bbox.max) * 0.5f;
    float3 bboxSize = bbox.max - bbox.min;
    mAutoRadius = std::max({bboxSize.x, bboxSize.y, bboxSize.z}) * 1.5f;

    printf("BBox min=(%.2f,%.2f,%.2f) max=(%.2f,%.2f,%.2f)\n",
           bbox.min.x, bbox.min.y, bbox.min.z,
           bbox.max.x, bbox.max.y, bbox.max.z);
    printf("FaceCenter=(%.2f,%.2f,%.2f)  AutoRadius=%.2f\n",
           mFaceCenter.x, mFaceCenter.y, mFaceCenter.z, mAutoRadius);
}

void FaceRenderer::setCamera(float yaw, float pitch, float radius) {
    float r = (radius > 0.0f) ? radius : mAutoRadius;

    // Convert degrees to radians because C++ trig functions uses radians
    float y = yaw * (float)M_PI / 180.0f;
    float p = pitch * (float)M_PI / 180.0f;

    // Convert yaw, pitch, radius for camera position
    float3 offset = {
        r * std::sin(y) * std::cos(p),
        r * std::sin(p),
        r * std::cos(y) * std::cos(p)
    };


    float3 eye = mFaceCenter + offset;
    float3 target = mFaceCenter;
    float3 up = {0.0f, 1.0f, 0.0f};

    // Points camera at facce center
    mCamera->lookAt(eye, target, up);

    float nearPlane = r * 0.01f;
    float farPlane  = r * 10.0f;

    // Set up perspective projection with correct aspect ratio
    mCamera->setProjection(
        45.0f,
        (float)mWidth / (float)mHeight,
        nearPlane, farPlane,
        Camera::Fov::VERTICAL
    );

    // ── Camera-relative lighting ──────────────────────────────────────────────
    // Inline helpers since filament::math::normalize/cross aren't in scope here.
    auto norm3 = [](float3 v) -> float3 {
        float len = std::sqrt(v.x*v.x + v.y*v.y + v.z*v.z);
        return (len > 0.0f) ? float3{v.x/len, v.y/len, v.z/len} : float3{0,0,1};
    };
    auto cross3 = [](float3 a, float3 b) -> float3 {
        return {a.y*b.z - a.z*b.y,
                a.z*b.x - a.x*b.z,
                a.x*b.y - a.y*b.x};
    };

    // Compute camera-relative lighting
    float3 forward = norm3(target - eye);
    float3 right = norm3(cross3(forward, up));
    float3 cam_up = cross3(right, forward);

    auto& lm = mEngine->getLightManager();

    // Update each light direction relative to camera so lighting always looks good
    float3 key_dir  = norm3(forward - right * 0.4f - cam_up * 0.3f);
    lm.setDirection(lm.getInstance(mLights[0]), {key_dir.x,  key_dir.y,  key_dir.z});

    float3 fill_dir = norm3(forward + right * 0.6f - cam_up * 0.1f);
    lm.setDirection(lm.getInstance(mLights[1]), {fill_dir.x, fill_dir.y, fill_dir.z});

    float3 rim_dir  = norm3(-forward - cam_up * 0.1f);
    lm.setDirection(lm.getInstance(mLights[2]), {rim_dir.x,  rim_dir.y,  rim_dir.z});

    lm.setDirection(lm.getInstance(mLights[3]), {0.0f, -1.0f, 0.0f});

    printf("Camera: eye=(%.2f,%.2f,%.2f) radius=%.2f near=%.3f far=%.1f\n",
           eye.x, eye.y, eye.z, r, nearPlane, farPlane);
}

std::vector<uint8_t> FaceRenderer::render() {
    // Tells Filament to render the scene into offscreen texture and wait for GPU to finish
    mRenderer->renderStandaloneView(mView);
    mEngine->flushAndWait();

    // Allocate CPU buffer big enough for all pixels
    std::vector<uint8_t> pixels(mWidth * mHeight * 4);

    // Copies rendered pixels from GPU memory back to CPU memory
    backend::PixelBufferDescriptor pbd(
        pixels.data(),
        pixels.size(),
        backend::PixelDataFormat::RGBA,
        backend::PixelDataType::UBYTE
    );

    mRenderer->readPixels(
        mRenderTarget,
        0, 0,
        mWidth, mHeight,
        std::move(pbd)
    );

    mEngine->flushAndWait();

    return pixels; // Returns flat byte array that bindings.cpp reshapes into a numpy array
}