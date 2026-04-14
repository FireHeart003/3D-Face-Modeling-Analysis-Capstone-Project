"""
render_face() — high-level Python API for Filament-based face rendering.

Pipeline:
  Face object / path
    → locate mesh.obj
    → make head-only OBJ  (via cache.py)
    → convert to GLB      (via cache.py)
    → load into FaceRenderer (C++ / Filament)
    → set camera
    → render → numpy RGBA array
    → composite over white → save PNG
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Native extension
# ---------------------------------------------------------------------------
try:
    from face_renderer.filament_renderer import FaceRenderer as _NativeRenderer
    _NATIVE_OK = True
except ImportError:
    _NATIVE_OK = False
    _NativeRenderer = None  # type: ignore

# ---------------------------------------------------------------------------
# Cache (all hashing / conversion logic lives here)
# ---------------------------------------------------------------------------
from face_renderer.cache import get_cached_head_obj, get_cached_glb

# ---------------------------------------------------------------------------
# Renderer singleton — keep one renderer alive to avoid re-init overhead
# ---------------------------------------------------------------------------

_renderer_cache: dict[tuple, "_NativeRenderer"] = {}


def _get_renderer(image_size: int) -> "_NativeRenderer":
    if not _NATIVE_OK:
        raise RuntimeError(
            "Native Filament extension not found. "
            "Build it with: pip install ."
        )
    key = (image_size,)
    if key not in _renderer_cache:
        _renderer_cache[key] = _NativeRenderer(image_size, image_size)
    return _renderer_cache[key]


# ---------------------------------------------------------------------------
# Resolve mesh.obj from a directory path or Face object
# ---------------------------------------------------------------------------

def _resolve_obj_path(face_or_path, model: str, renderable: str) -> Path:
    if isinstance(face_or_path, (str, Path)):
        base = Path(face_or_path)
        if base.suffix.lower() == ".obj":
            return base
        candidate = base / "mesh.obj"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Cannot find mesh.obj in {base}")

    # Duck-type: Face object
    try:
        mesh_path = (
            face_or_path
            .models[model]
            .renderables[renderable]
            .mesh
        )
        return Path(mesh_path)
    except (AttributeError, KeyError, TypeError):
        pass

    try:
        mesh_path = getattr(
            getattr(
                getattr(face_or_path.models, model).renderables, renderable
            ), "mesh"
        )
        return Path(mesh_path)
    except AttributeError:
        pass

    raise ValueError(
        f"Cannot resolve OBJ path from face_or_path={face_or_path!r}. "
        "Pass a directory path or a Face object."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_face(
    face_or_path,
    model: str = "makehuman",
    renderable: str = "default",
    out_path: str = "preview.png",
    image_size: int = 512,
    n_frames: int = 1,
    yaw_degrees: float = 0.0,
    pitch_degrees: float = 0.0,
    radius: float = None,
    keep_top_percent: float = 0.13,
    bg_color: tuple = (255, 255, 255),
) -> Union[list[Path], Path]:
    """
    Render a face mesh using the Filament GPU renderer.

    Parameters
    ----------
    face_or_path : str | Path | Face
        Directory containing mesh.obj, a direct path to mesh.obj,
        or a Face object.
    model : str
        Model name (used when face_or_path is a Face object).
    renderable : str
        Renderable name (used when face_or_path is a Face object).
    out_path : str
        Output PNG path. For n_frames > 1 treated as a directory;
        frames saved as frame_0000.png … frame_NNNN.png.
    image_size : int
        Width and height of the rendered image in pixels.
    n_frames : int
        Number of frames. Yaw distributed 0-360° for turntable.
    yaw_degrees : float
        Camera yaw (horizontal rotation) in degrees.
    pitch_degrees : float
        Camera pitch (vertical tilt) in degrees.
    radius : float | None
        Camera distance. None = auto from bounding box.
    keep_top_percent : float
        Fraction of mesh height kept as head-only.
    bg_color : tuple
        RGB background color for compositing.

    Returns
    -------
    Path | list[Path]
        Path to saved PNG (or list of Paths for n_frames > 1).
    """

    # ── 1. Resolve OBJ path ───────────────────────────────────────────────────
    obj_path = _resolve_obj_path(face_or_path, model, renderable)
    print(f"[render_face] OBJ source: {obj_path}")

    # ── 2. Get cached head-only OBJ ───────────────────────────────────────────
    head_obj = get_cached_head_obj(obj_path, keep_top_percent)
    print(f"[render_face] Head OBJ:   {head_obj}")

    # ── 3. Get cached GLB ─────────────────────────────────────────────────────
    glb_path = get_cached_glb(head_obj)
    print(f"[render_face] GLB:        {glb_path}")

    # ── 4. Set up renderer & load model ───────────────────────────────────────
    renderer = _get_renderer(image_size)
    renderer.load_model(str(glb_path))

    effective_radius = radius if radius is not None else -1.0

    # ── 5. Render ─────────────────────────────────────────────────────────────
    out_path = Path(out_path)

    if n_frames == 1:
        renderer.set_camera(
            yaw=yaw_degrees,
            pitch=pitch_degrees,
            radius=effective_radius,
        )
        raw = renderer.render(image_size, image_size)
        saved = _save_frame(raw, out_path, bg_color)
        print(f"[render_face] Saved → {saved}")
        return saved

    else:
        out_path.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []
        for i in range(n_frames):
            yaw = yaw_degrees + (360.0 / n_frames) * i
            renderer.set_camera(
                yaw=yaw,
                pitch=pitch_degrees,
                radius=effective_radius,
            )
            raw = renderer.render(image_size, image_size)
            frame_path = out_path / f"frame_{i:04d}.png"
            _save_frame(raw, frame_path, bg_color)
            saved_paths.append(frame_path)
            if (i + 1) % 10 == 0 or i == n_frames - 1:
                print(f"[render_face] Rendered {i+1}/{n_frames} frames")
        print(f"[render_face] Turntable saved to {out_path}/")
        return saved_paths


def _save_frame(
    raw: np.ndarray,
    out_path: Path,
    bg_color: tuple = (255, 255, 255),
) -> Path:
    """Composite RGBA render over solid background and save as PNG."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.fromarray(raw, "RGBA")
    background = Image.new("RGBA", img.size, (*bg_color, 255))
    final = Image.alpha_composite(background, img).convert("RGB")
    final.save(str(out_path))
    return out_path