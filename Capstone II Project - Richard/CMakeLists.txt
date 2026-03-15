cmake_minimum_required(VERSION 3.20)
project(face_renderer_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- Python + pybind11 ----
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

# Easiest: install pybind11 into venv: pip install pybind11
find_package(pybind11 CONFIG REQUIRED)

# ---- Filament paths ----
# You set this when configuring:
#   -DFILAMENT_OUT=/path/to/filament/out/cmake-release
set(FILAMENT_OUT "" CACHE PATH "Path to filament out/cmake-release")

if(NOT FILAMENT_OUT)
  message(FATAL_ERROR "Set -DFILAMENT_OUT=/path/to/filament/out/cmake-release")
endif()

# Headers are in filament/ and libs in FILAMENT_OUT/filament, gltfio, utils, etc (varies by build)
# We'll point includes to filament source and out include dirs.
# Adjust these if your build layout differs.
set(FILAMENT_SRC "${FILAMENT_OUT}/../..")  # typically .../filament/out/cmake-release/../.. -> filament/
# If this doesn't work in your setup, just set FILAMENT_SRC manually.

include_directories(
  "${FILAMENT_SRC}"
  "${FILAMENT_SRC}/filament/include"
  "${FILAMENT_SRC}/gltfio/include"
  "${FILAMENT_SRC}/utils/include"
  "${FILAMENT_SRC}/math/include"
)

link_directories(
  "${FILAMENT_OUT}/filament"
  "${FILAMENT_OUT}/gltfio"
  "${FILAMENT_OUT}/utils"
)

pybind11_add_module(_native_renderer
  src/face_renderer/_native/bindings.cpp
  src/face_renderer/_native/renderer.cpp
)

# Link Filament libs (names can differ slightly by platform/build).
# If you get link errors, run `ls ${FILAMENT_OUT}/filament` etc and adjust.
target_link_libraries(_native_renderer PRIVATE
  filament
  gltfio
  utils
)

# Install into the Python package directory
install(TARGETS _native_renderer DESTINATION face_renderer)