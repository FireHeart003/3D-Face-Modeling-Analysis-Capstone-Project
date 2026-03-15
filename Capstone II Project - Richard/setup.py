from setuptools import setup, Extension
import sys
import os
import platform

try:
    import pybind11
    include_dirs = [pybind11.get_include()]
except ImportError:
    include_dirs = []

# Filament paths
project_root = os.path.dirname(__file__)
filament_path = os.path.join(project_root, 'libs', 'filament')
filament_include = os.path.join(filament_path, 'include')

# Use arm64 for Apple Silicon
filament_lib = os.path.join(filament_path, 'lib', 'arm64')

include_dirs.append(filament_include)

# Filament libraries to link (in correct order - dependencies matter!)
libraries = [
    'gltfio',
    'gltfio_core',
    'filament',
    'filamat',
    'backend',
    'bluevk',
    'bluegl',
    'filabridge',
    'filaflat',
    'shaders',        # ← ADD THIS
    'geometry',
    'utils',
    'ibl',
    'image',
    'smol-v',
    'uberzlib',
    'meshoptimizer',
    'dracodec',
]

# macOS frameworks needed by Filament
extra_link_args = ['-stdlib=libc++']
if platform.system() == 'Darwin':
    extra_link_args.extend([
        '-framework', 'Cocoa',
        '-framework', 'Metal',
        '-framework', 'MetalKit',
        '-framework', 'QuartzCore',
        '-framework', 'CoreVideo',
        '-framework', 'IOKit',
        '-framework', 'IOSurface',
    ])

ext_modules = [
    Extension(
        'face_renderer._renderer',
        ['src/face_renderer/_native/test_binding.cpp'],
        include_dirs=include_dirs,
        library_dirs=[filament_lib],
        libraries=libraries,
        language='c++',
        extra_compile_args=['-std=c++17', '-stdlib=libc++'],
        extra_link_args=extra_link_args,
    ),
]

setup(
    name='face_renderer',
    version='0.1',
    ext_modules=ext_modules,
    setup_requires=['pybind11>=2.6.0'],
    install_requires=['pybind11>=2.6.0', 'numpy'],
    packages=['face_renderer'],
    package_dir={'face_renderer': 'src/face_renderer'},
)