from setuptools import setup, Extension
import sys

# Try to import pybind11, but don't fail if it's not available yet
# This file compiles test_binding.cpp
try:
    import pybind11
    include_dirs = [pybind11.get_include()]
except ImportError:
    include_dirs = []

ext_modules = [
    Extension(
        'face_renderer._renderer',
        ['src/face_renderer/_native/test_binding.cpp'],
        include_dirs=include_dirs,
        language='c++',
        extra_compile_args=['-std=c++17'],
    ),
]

setup(
    name='face_renderer',
    version='0.1',
    ext_modules=ext_modules,
    setup_requires=['pybind11>=2.6.0'],
    install_requires=['pybind11>=2.6.0'],
    packages=['face_renderer'],
    package_dir={'face_renderer': 'src/face_renderer'},
)