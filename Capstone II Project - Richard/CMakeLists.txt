cmake_minimum_required(VERSION 3.18)
project(face_renderer)

set(CMAKE_CXX_STANDARD 17)

# ── Paths ─────────────────────────────────────────────────────────────────────
set(FILAMENT_DIR "${CMAKE_SOURCE_DIR}/filament_dist")

# ── Python + pybind11 ─────────────────────────────────────────────────────────
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Find pybind11 via Python instead of hardcoded path
execute_process(
    COMMAND "${Python3_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
find_package(pybind11 REQUIRED HINTS "${PYBIND11_CMAKE_DIR}")

# ── Filament include dirs ──────────────────────────────────────────────────────
set(FILAMENT_INCLUDE ${FILAMENT_DIR}/include)

# ── Filament libraries ─────────────────────────────────────────────────────────
set(LIB_DIR ${FILAMENT_DIR}/lib/arm64)

# ── Build the Python extension ─────────────────────────────────────────────────
pybind11_add_module(filament_renderer
    face_renderer/_native/renderer.cpp
    face_renderer/_native/bindings.cpp
)

target_include_directories(filament_renderer PRIVATE
    ${FILAMENT_INCLUDE}
)

target_link_libraries(filament_renderer PRIVATE
    ${LIB_DIR}/libfilament.a
    ${LIB_DIR}/libbackend.a
    ${LIB_DIR}/libgltfio_core.a
    ${LIB_DIR}/libgltfio.a
    ${LIB_DIR}/libfilamat.a
    ${LIB_DIR}/libfilabridge.a
    ${LIB_DIR}/libfilaflat.a
    ${LIB_DIR}/libutils.a
    ${LIB_DIR}/libgeometry.a
    ${LIB_DIR}/libshaders.a
    ${LIB_DIR}/libibl.a
    ${LIB_DIR}/libimage.a
    ${LIB_DIR}/libimageio-lite.a
    ${LIB_DIR}/libktxreader.a
    ${LIB_DIR}/libbasis_transcoder.a
    ${LIB_DIR}/libdracodec.a
    ${LIB_DIR}/libzstd.a
    ${LIB_DIR}/libuberzlib.a
    ${LIB_DIR}/libuberarchive.a
    ${LIB_DIR}/libabseil.a
    ${LIB_DIR}/libsmol-v.a
    ${LIB_DIR}/libmeshoptimizer.a
    ${LIB_DIR}/libmikktspace.a
    ${LIB_DIR}/libstb.a
    ${LIB_DIR}/libperfetto.a
    ${LIB_DIR}/libbluevk.a
    ${LIB_DIR}/libbluegl.a
    "-framework Metal"
    "-framework CoreVideo"
    "-framework QuartzCore"
    "-framework Cocoa"
)

set_target_properties(filament_renderer PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/face_renderer"
)