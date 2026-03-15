#include "renderer.hpp"

#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filament/SwapChain.h>
#include <filament/Viewport.h>
#include <filament/TransformManager.h>
#include <filament/LightManager.h>
#include <filament/Fence.h>

#include <gltfio/AssetLoader.h>
#include <gltfio/FilamentAsset.h>
#include <gltfio/ResourceLoader.h>
#include <gltfio/TextureProvider.h>

#include <utils/EntityManager.h>

#include <cmath>
#include <fstream>
#include <stdexcept>

using namespace filament;
using namespace gltfio;
using namespace utils;

namespace face {

struct Renderer::Impl {
    Engine* engine = nullptr;
    SwapChain* swapChain = nullptr;
    filament::Renderer* renderer = nullptr;
    Scene* scene = nullptr;
    View* view = nullptr;
    Camera* camera = nullptr;

    // gltf
    AssetLoader* assetLoader = nullptr;
    ResourceLoader* resourceLoader = nullptr;
    FilamentAsset* asset = nullptr;

    Entity cameraEntity;
    Entity lightEntity;

    std::vector<uint8_t> pixelBuffer;

    int width = 0;
    int height = 0;
};

static std::vector<uint8_t> read_file_bytes(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("Failed to open file: " + path);
    f.seekg(0, std::ios::end);
    std::streamsize n = f.tellg();
    f.seekg(0, std::ios::beg);
    std::vector<uint8_t> buf((size_t)n);
    if (!f.read((char*)buf.data(), n)) throw std::runtime_error("Failed to read file: " + path);
    return buf;
}

Renderer::Renderer(int width, int height) {
    m_width = width;
    m_height = height;

    m = new Impl();
    m->width = width;
    m->height = height;

    m->engine = Engine::create();

    // Headless offscreen swapchain (no window)
    m->swapChain = m->engine->createSwapChain((uint32_t)width, (uint32_t)height);

    m->renderer = m->engine->createRenderer();
    m->scene = m->engine->createScene();
    m->view = m->engine->createView();

    // Camera
    auto& em = EntityManager::get();
    m->cameraEntity = em.create();
    m->camera = m->engine->createCamera(m->cameraEntity);

    m->view->setScene(m->scene);
    m->view->setCamera(m->camera);
    m->view->setViewport({0, 0, (uint32_t)width, (uint32_t)height});

    // Simple light so the mesh isn't black
    m->lightEntity = em.create();
    LightManager::Builder(LightManager::Type::DIRECTIONAL)
        .color(1.0f, 1.0f, 1.0f)
        .intensity(100000.0f)
        .direction({0.2f, -1.0f, -0.2f})
        .castShadows(false)
        .build(*m->engine, m->lightEntity);
    m->scene->addEntity(m->lightEntity);

    // glTF loader setup
    static constexpr bool normalizeSkinningWeights = true;
    m->assetLoader = AssetLoader::create({
        .engine = m->engine,
        .materials = nullptr,
        .entities = &EntityManager::get(),
        .transformManager = &m->engine->getTransformManager(),
        .normalizeSkinningWeights = normalizeSkinningWeights,
    });

    // Resource loader handles textures/buffers referenced by glb
    m->resourceLoader = new ResourceLoader({
        .engine = m->engine,
        .normalizeSkinningWeights = normalizeSkinningWeights,
    });

    m->pixelBuffer.resize((size_t)width * (size_t)height * 4);
}

Renderer::~Renderer() {
    destroy();
}

void Renderer::destroy() {
    if (!m) return;

    if (m->asset) {
        // Remove from scene then destroy asset
        m->scene->removeEntities(m->asset->getEntities(), m->asset->getEntityCount());
        m->assetLoader->destroyAsset(m->asset);
        m->asset = nullptr;
    }

    if (m->resourceLoader) {
        delete m->resourceLoader;
        m->resourceLoader = nullptr;
    }
    if (m->assetLoader) {
        AssetLoader::destroy(&m->assetLoader);
    }

    if (m->camera) m->engine->destroyCameraComponent(m->cameraEntity);
    if (m->view) m->engine->destroy(m->view);
    if (m->scene) m->engine->destroy(m->scene);
    if (m->renderer) m->engine->destroy(m->renderer);
    if (m->swapChain) m->engine->destroy(m->swapChain);

    // Entities
    EntityManager::get().destroy(m->lightEntity);
    EntityManager::get().destroy(m->cameraEntity);

    if (m->engine) Engine::destroy(&m->engine);

    delete m;
    m = nullptr;
}

void Renderer::load_model(const std::string& glb_path) {
    if (!m) throw std::runtime_error("Renderer not initialized");

    // Clear previous asset
    if (m->asset) {
        m->scene->removeEntities(m->asset->getEntities(), m->asset->getEntityCount());
        m->assetLoader->destroyAsset(m->asset);
        m->asset = nullptr;
    }

    auto bytes = read_file_bytes(glb_path);
    m->asset = m->assetLoader->createAssetFromBinary(bytes.data(), bytes.size());
    if (!m->asset) throw std::runtime_error("Failed to load GLB asset: " + glb_path);

    // Load resources (textures/buffers)
    m->resourceLoader->loadResources(m->asset);

    // Add renderable entities to scene
    m->scene->addEntities(m->asset->getEntities(), m->asset->getEntityCount());

    // Optional: release source data after upload
    m->asset->releaseSourceData();
}

static float deg2rad(float d) { return d * 3.1415926535f / 180.0f; }

std::vector<uint8_t> Renderer::render(float yaw_deg, float pitch_deg, float roll_deg) {
    if (!m || !m->asset) throw std::runtime_error("Call load_model(glb) before render()");

    // Compute a simple orbit camera around the model’s bounding box center
    const auto box = m->asset->getBoundingBox();
    const auto c = box.center;
    const float r = box.halfExtent.length() * 2.2f + 0.001f; // radius

    float yaw = deg2rad(yaw_deg);
    float pitch = deg2rad(pitch_deg);

    // Camera position in world space
    float x = c.x + r * std::cos(pitch) * std::sin(yaw);
    float y = c.y + r * std::sin(pitch);
    float z = c.z + r * std::cos(pitch) * std::cos(yaw);

    // LookAt
    m->camera->lookAt({x, y, z}, {c.x, c.y, c.z}, {0.0f, 1.0f, 0.0f});

    // Projection
    float aspect = (float)m->width / (float)m->height;
    m->camera->setProjection(45.0f, aspect, 0.01f, 1000.0f, Camera::Fov::VERTICAL);

    // Render
    if (m->renderer->beginFrame(m->swapChain)) {
        m->renderer->render(m->view);
        m->renderer->endFrame();
    }

    // Read pixels back (async callback) + fence wait
    bool done = false;

    PixelBufferDescriptor pbd(
        m->pixelBuffer.data(),
        m->pixelBuffer.size(),
        PixelDataFormat::RGBA,
        PixelDataType::UBYTE,
        [&done](void*, size_t, void*) { done = true; }
    );

    m->renderer->readPixels(
        0, 0, (uint32_t)m->width, (uint32_t)m->height,
        std::move(pbd)
    );

    // Wait until readback completes
    // (Fence ensures GPU finishes; loop ensures callback ran)
    Fence::waitAndDestroy(m->engine->createFence());

    // In practice the callback should be done after the fence,
    // but we guard anyway.
    if (!done) {
        // tiny spin; should be near-instant after fence
        for (int i = 0; i < 1000000 && !done; i++) {}
    }

    return m->pixelBuffer;
}

} // namespace face