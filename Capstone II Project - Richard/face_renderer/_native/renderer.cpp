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

using namespace filament;
using namespace filament::math;
using namespace filament::gltfio;

FaceRenderer::FaceRenderer(int width, int height, const std::string& filamentDistPath)
    : mWidth(width), mHeight(height), mFilamentDistPath(filamentDistPath) {

    mEngine   = Engine::create();
    mRenderer = mEngine->createRenderer();
    mScene    = mEngine->createScene();

    _setupRenderTarget();

    mView = mEngine->createView();
    mView->setScene(mScene);
    mView->setViewport({0, 0, (uint32_t)mWidth, (uint32_t)mHeight});
    mView->setRenderTarget(mRenderTarget);
    mView->setBlendMode(View::BlendMode::TRANSLUCENT);

    mCameraEntity = utils::EntityManager::get().create();
    mCamera = mEngine->createCamera(mCameraEntity);
    mView->setCamera(mCamera);

    _setupLight();

    mMaterialProvider = createUbershaderProvider(
        mEngine,
        UBERARCHIVE_DEFAULT_DATA,
        UBERARCHIVE_DEFAULT_SIZE
    );

    mAssetLoader     = AssetLoader::create({mEngine, mMaterialProvider});
    mResourceLoader  = new ResourceLoader({mEngine});
    mTextureProvider = createStbProvider(mEngine);
    mResourceLoader->addTextureProvider("image/png",  mTextureProvider);
    mResourceLoader->addTextureProvider("image/jpeg", mTextureProvider);
}

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
    mEngine->destroy(mLight);
    mEngine->destroy(mView);
    mEngine->destroy(mScene);
    mEngine->destroy(mRenderer);
    mEngine->destroy(mColorTexture);
    mEngine->destroy(mDepthTexture);
    mEngine->destroy(mRenderTarget);
    Engine::destroy(&mEngine);
}

void FaceRenderer::_setupRenderTarget() {
    mColorTexture = Texture::Builder()
        .width(mWidth).height(mHeight)
        .levels(1)
        .usage(Texture::Usage::COLOR_ATTACHMENT | Texture::Usage::SAMPLEABLE | Texture::Usage::BLIT_SRC)
        .format(Texture::InternalFormat::RGBA8)
        .build(*mEngine);

    mDepthTexture = Texture::Builder()
        .width(mWidth).height(mHeight)
        .levels(1)
        .usage(Texture::Usage::DEPTH_ATTACHMENT)
        .format(Texture::InternalFormat::DEPTH24)
        .build(*mEngine);

    mRenderTarget = RenderTarget::Builder()
        .texture(RenderTarget::AttachmentPoint::COLOR, mColorTexture)
        .texture(RenderTarget::AttachmentPoint::DEPTH, mDepthTexture)
        .build(*mEngine);
}

void FaceRenderer::_setupLight() {
    mLight = utils::EntityManager::get().create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color({1.0f, 1.0f, 1.0f})
        .intensity(100000.0f)
        .direction({0.0f, -1.0f, -1.0f})
        .build(*mEngine, mLight);
    mScene->addEntity(mLight);
}

void FaceRenderer::_fixMaterials() {
    // Filament's ubershader renames all materials to "base_lit_opaque" etc so
    // we cannot match by name here. All alphaMode/doubleSided is baked into the
    // GLB by obj_to_glb.py. We use FilamentInstance::getMaterialInstances()
    // (confirmed in FilamentInstance.h) to iterate and force doubleSided=true
    // on everything as a safe global override.
    FilamentInstance* instance = mAsset->getInstance();
    if (!instance) {
        printf("  [WARN] No FilamentInstance found\n");
        return;
    }

    size_t matCount = instance->getMaterialInstanceCount();
    MaterialInstance* const* materials = instance->getMaterialInstances();

    printf("=== _fixMaterials: %zu material instances ===\n", matCount);
    for (size_t i = 0; i < matCount; i++) {
        if (!materials[i]) continue;
        const char* name = materials[i]->getName();
        printf("  [%zu] '%s'\n", i, name ? name : "(null)");
        // Force double-sided so thin quads (eyebrows, eyelids) are never culled
        materials[i]->setDoubleSided(true);
    }
    printf("=============================================\n");
}

void FaceRenderer::loadModel(const std::string& glbPath) {
    if (mAsset) {
        mScene->removeEntities(mAsset->getEntities(), mAsset->getEntityCount());
        mAssetLoader->destroyAsset(mAsset);
        mAsset = nullptr;
    }

    std::ifstream file(glbPath, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open GLB file: " + glbPath);
    }
    size_t size = file.tellg();
    file.seekg(0);
    std::vector<uint8_t> buffer(size);
    file.read(reinterpret_cast<char*>(buffer.data()), size);

    mAsset = mAssetLoader->createAsset(buffer.data(), buffer.size());
    if (!mAsset) {
        throw std::runtime_error("Failed to load GLB asset: " + glbPath);
    }

    mResourceLoader->loadResources(mAsset);

    // ── Apply GLB scene graph transforms ─────────────────────────────────────
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
    // radius <= 0 → use auto-computed value from bounding box
    float r = (radius > 0.0f) ? radius : mAutoRadius;

    float y = yaw   * (float)M_PI / 180.0f;
    float p = pitch * (float)M_PI / 180.0f;

    float3 offset = {
        r * std::sin(y) * std::cos(p),
        r * std::sin(p),
        r * std::cos(y) * std::cos(p)
    };

    float3 eye    = mFaceCenter + offset;
    float3 target = mFaceCenter;
    float3 up     = {0.0f, 1.0f, 0.0f};

    mCamera->lookAt(eye, target, up);

    // Scale near/far to scene so nothing clips
    float nearPlane = r * 0.01f;
    float farPlane  = r * 10.0f;
    mCamera->setProjection(
        45.0f,
        (float)mWidth / (float)mHeight,
        nearPlane, farPlane,
        Camera::Fov::VERTICAL
    );

    printf("Camera: eye=(%.2f,%.2f,%.2f) radius=%.2f near=%.3f far=%.1f\n",
           eye.x, eye.y, eye.z, r, nearPlane, farPlane);
}

std::vector<uint8_t> FaceRenderer::render() {
    mRenderer->renderStandaloneView(mView);
    mEngine->flushAndWait();

    std::vector<uint8_t> pixels(mWidth * mHeight * 4);

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

    return pixels;
}