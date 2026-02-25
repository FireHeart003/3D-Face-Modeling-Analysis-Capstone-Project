#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filament/RenderableManager.h>
#include <filament/TransformManager.h>
#include <utils/EntityManager.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/ResourceLoader.h>
#include <backend/PixelBufferDescriptor.h>
#include <string>
#include <vector>
#include <fstream>

namespace py = pybind11;
using namespace filament;
using namespace filament::backend;

class FilamentRenderer {
private:
    Engine* engine = nullptr;
    Renderer* renderer = nullptr;
    Scene* scene = nullptr;
    View* view = nullptr;
    Camera* camera = nullptr;
    gltfio::AssetLoader* assetLoader = nullptr;
    gltfio::ResourceLoader* resourceLoader = nullptr;
    
public:
    FilamentRenderer() {
        // Create Filament engine
        engine = Engine::create(Engine::Backend::DEFAULT);
        renderer = engine->createRenderer();
        scene = engine->createScene();
        view = engine->createView();
        
        // Setup view
        view->setScene(scene);
        
        // Create asset loaders
        assetLoader = gltfio::AssetLoader::create({engine});
        resourceLoader = new gltfio::ResourceLoader({engine});
    }
    
    ~FilamentRenderer() {
        if (assetLoader) gltfio::AssetLoader::destroy(&assetLoader);
        if (resourceLoader) delete resourceLoader;
        if (engine) {
            if (renderer) engine->destroy(renderer);
            if (scene) engine->destroy(scene);
            if (view) engine->destroy(view);
            Engine::destroy(&engine);
        }
    }
    
    py::array_t<uint8_t> render(const std::string& glb_path, int width, int height) {
        // For now, still return black image
        // We'll add actual rendering in the next iteration
        auto result = py::array_t<uint8_t>({height, width, 4});
        auto buf = result.request();
        uint8_t* ptr = static_cast<uint8_t*>(buf.ptr);
        
        for (int i = 0; i < height * width * 4; i += 4) {
            ptr[i] = 0;
            ptr[i+1] = 0;
            ptr[i+2] = 0;
            ptr[i+3] = 255;
        }
        
        return result;
    }
};

PYBIND11_MODULE(_renderer, m) {
    m.doc() = "Filament-based face renderer";
    
    py::class_<FilamentRenderer>(m, "FilamentRenderer")
        .def(py::init<>())
        .def("render", &FilamentRenderer::render,
             "Render a GLB file",
             py::arg("glb_path"),
             py::arg("width") = 512,
             py::arg("height") = 512);
}