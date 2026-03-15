#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "renderer.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_native_renderer, m) {
    py::class_<face::Renderer>(m, "Renderer")
        .def(py::init<int, int>())
        .def("load_model", &face::Renderer::load_model)
        .def("render", [](face::Renderer& r, float yaw, float pitch, float roll) {
            auto buf = r.render(yaw, pitch, roll);

            // Shape: (H, W, 4)
            py::ssize_t h = r.height();
            py::ssize_t w = r.width();

            // Copy into NumPy-owned memory (simplest/robust)
            auto arr = py::array_t<uint8_t>({h, w, 4});
            std::memcpy(arr.mutable_data(), buf.data(), buf.size());
            return arr;
        }, py::arg("yaw") = 0.0f, py::arg("pitch") = 0.0f, py::arg("roll") = 0.0f);
}