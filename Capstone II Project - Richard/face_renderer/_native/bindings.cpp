#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "renderer.h"

namespace py = pybind11;

PYBIND11_MODULE(filament_renderer, m) {
    m.doc() = "Filament-based face renderer";

    py::class_<FaceRenderer>(m, "FaceRenderer")
        .def(py::init<int, int, std::string>(),
             py::arg("width") = 512,
             py::arg("height") = 512,
             py::arg("filament_dist_path") = "filament_dist")

        .def("load_model", &FaceRenderer::loadModel,
             py::arg("glb_path"))

        .def("set_camera", &FaceRenderer::setCamera,
             py::arg("yaw")    = 0.0f,
             py::arg("pitch")  = 0.0f,
             py::arg("radius") = 300.0f)

        .def("render", [](FaceRenderer& self, int width, int height) {
            auto pixels = self.render();
            return py::array_t<uint8_t>(
                {height, width, 4},
                {width * 4, 4, 1},
                pixels.data()
            );
        }, py::arg("width") = 512, py::arg("height") = 512);
}