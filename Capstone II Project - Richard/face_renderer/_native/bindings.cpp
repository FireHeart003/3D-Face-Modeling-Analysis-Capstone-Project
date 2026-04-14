// Imports for pybind11 to alow basic Python binding and other Python to C++ functionalities
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "renderer.h"

namespace py = pybind11;

// This is what will be exposed and imported in our python files(from face_renderer.filament_renderer import FaceRenderer)
PYBIND11_MODULE(filament_renderer, m) {
    m.doc() = "Filament-based face renderer";

    // Exposes the FaceRenderer Class from renderer.h to Python
    py::class_<FaceRenderer>(m, "FaceRenderer")
        .def(py::init<int, int, std::string>(), // Constructor
             py::arg("width") = 512,
             py::arg("height") = 512,
             py::arg("filament_dist_path") = "filament_dist")

        .def("load_model", &FaceRenderer::loadModel, // Loads the model given a path to GLB object
             py::arg("glb_path"))

        .def("set_camera", &FaceRenderer::setCamera, // Sets the camera given the params
             py::arg("yaw")    = 0.0f,
             py::arg("pitch")  = 0.0f,
             py::arg("radius") = 300.0f)

        .def("render", [](FaceRenderer& self, int width, int height) {
            auto pixels = self.render(); // At this stage, FaceRenderer object has been created, GLB file loaded, and camera has been set
            return py::array_t<uint8_t>( // Convert raw bytes to numpy array
                {height, width, 4},
                {width * 4, 4, 1},
                pixels.data()
            );
        }, py::arg("width") = 512, py::arg("height") = 512);
}