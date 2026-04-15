# 3D Face Renderer — Filament GPU Rendering Pipeline

A unified Python framework for 3D face modeling and rendering using Google's Filament engine. This system takes MakeHuman-generated assets and produces high-quality GPU-accelerated face renders via a clean Python API.

**Platform Notice:** This project currently only supports **macOS with Apple Silicon (M1/M2/M3/M4 chips)**. The C++ build system and Filament backend are configured for Metal (Apple's GPU API). Windows and Linux support would require rebuilding Filament for those platforms.

---

## How It Works

The rendering pipeline runs in the following order:

```
mesh.obj
  → head-only OBJ  (Y-axis cutoff, cached)
  → GLB file       (OBJ → GLB conversion, cached)
  → Filament C++ renderer  (GPU render via pybind11 bridge)
  → preview.png / turntable frames
```

---

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- Xcode Command Line Tools

Install Python dependencies:
```bash
pip install -r requirements.txt
```

---

## Installation

Build and install the native C++ extension (required before first run): **Ensure that you are in the directory above the build folder.**
```bash
cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4
```

This compiles the Filament-based `FaceRenderer` C++ class and exposes it to Python via pybind11. You only need to do this once, or after any changes to `renderer.cpp` or `bindings.cpp`. 

---

## Usage

### Quick preview (single image)

```bash
python demo_render.py
```

By default this looks for assets in `tests/assets/makehuman_raw/`. To use a different directory:

```bash
python demo_render.py path/to/your/mesh_folder
```

### Turntable (60-frame 360° rotation)

```bash
python demo_render.py --turntable
```

### All available options

```bash
python demo_render.py [mesh_dir] [options]

Options:
  --size        Image size in pixels (default: 512)
  --yaw         Camera horizontal rotation in degrees (default: 0.0). Degrees > 0 = Rotate left and vice versa 
  --pitch       Camera vertical tilt in degrees (default: 0.0). Degrees > 0 = Tilt head down and vice versa
  --keep-top    Fraction of mesh height to keep as head-only (default: 0.13)
  --frames      Number of turntable frames (default: 60, only used with --turntable)
  --out         Output directory (default: out_face)
  --turntable   Also render a full 360° turntable animation(No params needed, just put "--turntable")
```

### Examples

```bash
# Front-facing render at 1024px
python demo_render.py --size 1024

# Side profile (90° yaw)
python demo_render.py --yaw 90

# Slightly elevated camera angle
python demo_render.py --pitch 15

# Keep more of the head (larger crop)
python demo_render.py --keep-top 0.20

# 60-frame turntable at 512px
python demo_render.py --turntable --frames 60
```

## Output

- **Preview:** `out_face/preview.png` — single front-facing PNG
- **Turntable:** `out_face/turntable/frame_0000.png` … `frame_0059.png`

---

## Caching

Conversion from OBJ → GLB is slow the first time. Results are automatically cached in:

```
~/.cache/face_renderer/
  objs/   ← cached head-only OBJ files
  glbs/   ← cached GLB files
```

Cache keys are based on SHA-256 hashes of the source files, so the cache is automatically invalidated if the mesh changes. Subsequent renders reuse the cached files and are significantly faster.

---

## Project Structure

```
face_renderer/
├── __init__.py           ← exposes render_face()
├── render.py             ← main pipeline orchestration
├── cache.py              ← SHA-256 caching for OBJ and GLB
├── make_head_only.py     ← Y-axis mesh extraction
├── obj_to_glb.py         ← OBJ → GLB conversion with material handling
└── _native/
    ├── renderer.h        ← FaceRenderer class declaration
    ├── renderer.cpp      ← Filament rendering implementation
    └── bindings.cpp      ← pybind11 bridge (C++ → Python)

demo_render.py            ← CLI entry point
tests/
└── assets/
    └── makehuman_raw/    ← place mesh.obj, mesh.mtl, textures/ here
```

---

## Technologies

- **Python** — pipeline orchestration and CLI
- **Filament** (Google) — production-grade GPU rendering engine
- **pybind11** — C++/Python bridge
- **trimesh** — OBJ → GLB conversion
- **pygltflib** — GLB material patching
- **Pillow** — image compositing and PNG export

---

## Accepted Input Format

Your mesh directory must contain:

```
mesh_folder/
├── mesh.obj
├── mesh.mtl
└── textures/
    ├── young_lightskinned_male_diffuse2.png
    ├── brown_eye.png
    ├── eyebrow012.png
    ├── teeth.png
    └── tongue01_diffuse.png
```

This matches the export format from MakeHuman and any required textures for the mesh obj.

## Additional Notes
There is a view_server.py that can be used to render on localhost. You can run it thru the following command:
```
python tests/view_server.py
```
This allows for easy modification of the yaw and pitch of the face render.
