#include "renderer.h"
#include <filament/Engine.h>
#include <filament/Renderer.h>
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
#include <gltfio/ResourceLoader.h>
#include <gltfio/TextureProvider.h>
#include <utils/EntityManager.h>
#include <backend/DriverEnums.h>
#include <backend/PixelBufferDescriptor.h>
#include <math/vec3.h>
#include <math/vec4.h>
#include <math/mat4.h>
#include <vector>
#include <fstream>
#include <stdexcept>

using namespace filament;
using namespace filament::math;
using namespace filament::gltfio;

// ── Helper: load a binary file into a vector ──────────────────────────────────
static std::vector<uint8_t> loadBinaryFile(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) return {};
    size_t size = file.tellg();
    file.seekg(0);
    std::vector<uint8_t> data(size);
    file.read(reinterpret_cast<char*>(data.data()), size);
    return data;
}

FaceRenderer::FaceRenderer(int width, int height, const std::string& filamentDistPath)
    : mWidth(width), mHeight(height), mFilamentDistPath(filamentDistPath) {

    // Create engine — uses Metal automatically on Apple Silicon
    mEngine   = Engine::create();
    mRenderer = mEngine->createRenderer();
    mScene    = mEngine->createScene();

    _setupRenderTarget();

    // Create view
    mView = mEngine->createView();
    mView->setScene(mScene);
    mView->setViewport({0, 0, (uint32_t)mWidth, (uint32_t)mHeight});
    mView->setRenderTarget(mRenderTarget);

    // Create camera
    mCameraEntity = utils::EntityManager::get().create();
    mCamera = mEngine->createCamera(mCameraEntity);
    mView->setCamera(mCamera);

    _setupLight();

    // ── Load ubershader package ───────────────────────────────────────────────
    // Search common locations for the uberarchive shader package
    std::vector<std::string> candidates = {
        filamentDistPath + "/bin/assets/uberarchive.bin",
        filamentDistPath + "/bin/uberarchive.bin",
        filamentDistPath + "/assets/uberarchive.bin",
        filamentDistPath + "/bin/assets/materials/uberarchive.bin",
    };

    for (auto& p : candidates) {
        mUbershaderData = loadBinaryFile(p);
        if (!mUbershaderData.empty()) {
            printf("Loaded ubershader from: %s\n", p.c_str());
            break;
        }
    }

    if (!mUbershaderData.empty()) {
        mMaterialProvider = createUbershaderProvider(
            mEngine,
            mUbershaderData.data(),
            mUbershaderData.size()
        );
    } else {
        // Last resort fallback — may cause decompression error on some builds
        printf("WARNING: ubershader package not found, using nullptr fallback\n");
        mMaterialProvider = createUbershaderProvider(mEngine, nullptr, 0);
    }

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
        .usage(Texture::Usage::COLOR_ATTACHMENT | Texture::Usage::SAMPLEABLE)
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
    mAsset->releaseSourceData();
    mScene->addEntities(mAsset->getEntities(), mAsset->getEntityCount());

    // Compute face center from bounding box
    auto bbox = mAsset->getBoundingBox();
    mFaceCenter = (bbox.min + bbox.max) * 0.5f;
}

void FaceRenderer::setCamera(float yaw, float pitch, float radius) {
    float y = yaw   * (float)M_PI / 180.0f;
    float p = pitch * (float)M_PI / 180.0f;

    float3 offset = {
        radius * std::sin(y) * std::cos(p),
        radius * std::sin(p),
        radius * std::cos(y) * std::cos(p)
    };

    float3 eye    = mFaceCenter + offset;
    float3 target = mFaceCenter;
    float3 up     = {0.0f, 1.0f, 0.0f};

    mCamera->lookAt(eye, target, up);
    mCamera->setProjection(
        45.0f,
        (float)mWidth / (float)mHeight,
        0.1f, 10000.0f,
        Camera::Fov::VERTICAL
    );
}

std::vector<uint8_t> FaceRenderer::render() {
    // Render offscreen
    mRenderer->renderStandaloneView(mView);
    mEngine->flushAndWait();

    // Read pixels from GPU → CPU
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