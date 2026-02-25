#include <pybind11/pybind11.h>

namespace py = pybind11;

// Simple test function
int add(int a, int b) {
    return a + b;
}

PYBIND11_MODULE(_renderer, m) {
    m.doc() = "Test renderer module";
    m.def("add", &add, "A test function that adds two numbers");
}