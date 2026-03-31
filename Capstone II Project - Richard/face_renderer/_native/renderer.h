#pragma once
#include <string>
#include <vector>
#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filament/RenderTarget.h>
#include <filament/Texture.h>
#include <filament/Fence.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/FilamentAsset.h>
#include <gltfio/FilamentInstance.h>
#include <gltfio/Animator.h>
#include <gltfio/ResourceLoader.h>
#include <gltfio/TextureProvider.h>
#include <utils/Entity.h>
#include <math/vec3.h>

using namespace filament;
using namespace filament::gltfio;

class FaceRenderer {
public:
    FaceRenderer(int width, int height, const std::string& filamentDistPath);
    ~FaceRenderer();

    void loadModel(const std::string& glbPath);
    void setCamera(float yaw, float pitch, float radius);
    std::vector<uint8_t> render();

private:
    void _setupRenderTarget();
    void _setupLight();
    void _fixMaterials();

    int mWidth, mHeight;
    std::string mFilamentDistPath;
    std::vector<uint8_t> mUbershaderData;

    Engine*             mEngine           = nullptr;
    Renderer*           mRenderer         = nullptr;
    Scene*              mScene            = nullptr;
    View*               mView             = nullptr;
    Camera*             mCamera           = nullptr;
    RenderTarget*       mRenderTarget     = nullptr;
    Texture*            mColorTexture     = nullptr;
    Texture*            mDepthTexture     = nullptr;
    utils::Entity       mCameraEntity;
    utils::Entity       mLight;

    AssetLoader*        mAssetLoader      = nullptr;
    FilamentAsset*      mAsset            = nullptr;
    ResourceLoader*     mResourceLoader   = nullptr;
    TextureProvider*    mTextureProvider  = nullptr;
    MaterialProvider*   mMaterialProvider = nullptr;

    filament::math::float3 mFaceCenter = {0, 0, 0};
    float                  mAutoRadius = 300.0f;
};