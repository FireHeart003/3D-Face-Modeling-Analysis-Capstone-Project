"""
render_face() — high-level Python API for Filament-based face rendering.

Pipeline:
  Face object / path
    → locate mesh.obj
    → make head-only OBJ  (cached per source hash + keep_top_percent)
    → convert to GLB      (cached per head-only OBJ hash)
    → load into FaceRenderer (C++ / Filament)
    → set camera
    → render → numpy RGBA array
    → composite over white → save PNG
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Optional import of the native extension.  We defer the error so the module
# can still be imported (e.g. for documentation) even when the .so isn't built.
# ---------------------------------------------------------------------------
try:
    from face_renderer.filament_renderer import FaceRenderer as _NativeRenderer
    _NATIVE_OK = True
except ImportError:
    _NATIVE_OK = False
    _NativeRenderer = None  # type: ignore

from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y
from face_renderer.obj_to_glb import obj_to_glb

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

_CACHE_DIR = Path(os.environ.get("FACE_RENDERER_CACHE", Path.home() / ".cache" / "face_renderer"))


def _file_sha256(path: Union[str, Path], chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _cached_head_obj(obj_path: Path, keep_top_percent: float) -> Path:
    """
    Return path to a head-only OBJ, building it if not already cached.
    Cache key = sha256(source OBJ) + keep_top_percent.
    """
    src_hash = _file_sha256(obj_path)
    pct_str  = f"{keep_top_percent:.4f}".replace(".", "p")
    cache_key = f"{src_hash[:16]}_{pct_str}"

    head_obj = _CACHE_DIR / "objs" / f"{cache_key}_head.obj"
    if head_obj.exists():
        return head_obj

    head_obj.parent.mkdir(parents=True, exist_ok=True)
    mask = build_head_face_mask_by_y(str(obj_path), keep_top_percent=keep_top_percent)
    make_head_only_obj(str(obj_path), str(head_obj), mask)
    return head_obj


def _cached_glb(head_obj: Path) -> Path:
    """
    Return path to a GLB, converting from the head-only OBJ if not cached.
    Cache key = sha256(head-only OBJ).
    """
    src_hash = _file_sha256(head_obj)
    glb_path = _CACHE_DIR / "glbs" / f"{src_hash[:16]}.glb"
    if glb_path.exists():
        return glb_path

    glb_path.parent.mkdir(parents=True, exist_ok=True)
    obj_to_glb(str(head_obj), str(glb_path))
    return glb_path


# ---------------------------------------------------------------------------
# Renderer singleton — keep one renderer alive to avoid re-init overhead
# ---------------------------------------------------------------------------

_renderer_cache: dict[tuple, "_NativeRenderer"] = {}


def _get_renderer(image_size: int) -> "_NativeRenderer":
    if not _NATIVE_OK:
        raise RuntimeError(
            "Native Filament extension not found. "
            "Build it with: pip install . (or python setup.py build_ext --inplace)"
        )
    key = (image_size,)
    if key not in _renderer_cache:
        _renderer_cache[key] = _NativeRenderer(image_size, image_size)
    return _renderer_cache[key]


# ---------------------------------------------------------------------------
# _resolve_obj_path: locate mesh.obj from a Face object or a directory path
# ---------------------------------------------------------------------------

def _resolve_obj_path(face_or_path, model: str, renderable: str) -> Path:
    """
    Accept:
      • a string/Path pointing to a directory that contains mesh.obj
      • an object with  .models.<model>.renderables.<renderable>.mesh  attribute
        that gives the path to mesh.obj
    """
    if isinstance(face_or_path, (str, Path)):
        base = Path(face_or_path)
        # If user passed the .obj directly
        if base.suffix.lower() == ".obj":
            return base
        # Otherwise look for mesh.obj inside the directory
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

    # Fallback: try attribute-style access
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
        Directory containing mesh.obj (and mesh.mtl / textures/),
        a direct path to mesh.obj, or a Face object.
    model : str
        Model name (used when face_or_path is a Face object).
    renderable : str
        Renderable name (used when face_or_path is a Face object).
    out_path : str
        Output PNG path.  For n_frames > 1 this is treated as a
        directory; frame files are named frame_0000.png … frame_NNNN.png.
    image_size : int
        Width and height of the rendered image in pixels.
    n_frames : int
        Number of frames.  Yaw is evenly distributed 0–360° when
        n_frames > 1 (turntable animation).
    yaw_degrees : float
        Camera yaw offset (horizontal rotation) in degrees.
    pitch_degrees : float
        Camera pitch offset (vertical tilt) in degrees.
    roll_degrees : float
        Reserved for future use (Filament does not support roll natively).
    radius : float | None
        Camera distance.  None → auto-computed from bounding box.
    face_center_mode : str
        "auto" → use bounding-box centre (only supported mode currently).
    device : str
        "gpu" (default) or "cpu" — Filament chooses backend automatically.
    keep_top_percent : float
        Fraction of mesh height kept as "head only" (passed to
        build_head_face_mask_by_y).
    bg_color : tuple
        RGB background colour for compositing, default white.

    Returns
    -------
    Path | list[Path]
        Path to the saved PNG (or list of Paths for n_frames > 1).
    """

    # ── 1. Resolve OBJ path ───────────────────────────────────────────────────
    obj_path = _resolve_obj_path(face_or_path, model, renderable)
    print(f"[render_face] OBJ source: {obj_path}")

    # ── 2. Build / retrieve cached head-only OBJ ──────────────────────────────
    head_obj = _cached_head_obj(obj_path, keep_top_percent)
    print(f"[render_face] Head OBJ:   {head_obj}")

    # ── 3. Convert / retrieve cached GLB ─────────────────────────────────────
    glb_path = _cached_glb(head_obj)
    print(f"[render_face] GLB:        {glb_path}")

    # ── 4. Set up renderer & load model ───────────────────────────────────────
    renderer = _get_renderer(image_size)
    renderer.load_model(str(glb_path))

    effective_radius = radius if radius is not None else -1.0  # -1 → auto

    # ── 5. Render ─────────────────────────────────────────────────────────────
    out_path = Path(out_path)

    if n_frames == 1:
        # Single frame
        renderer.set_camera(
            yaw=yaw_degrees,
            pitch=pitch_degrees,
            radius=effective_radius,
        )
        raw = renderer.render(image_size, image_size)          # (H, W, 4) uint8
        saved = _save_frame(raw, out_path, bg_color)
        print(f"[render_face] Saved → {saved}")
        return saved

    else:
        # Turntable: distribute yaw evenly over 360°
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