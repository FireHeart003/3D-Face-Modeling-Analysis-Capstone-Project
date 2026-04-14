"""
demo_render_turntable.py
Usage:
    python demo_render_turntable.py [mesh_dir] [--frames N] [--size S]

Renders a 60-frame turntable of the face mesh and saves frames to
out_face/turntable/.  Also saves a single front-facing preview.
"""

import argparse
import sys
import time
from pathlib import Path

from face_renderer import render_face


def main():
    parser = argparse.ArgumentParser(description="Face turntable renderer")
    parser.add_argument(
        "mesh_dir",
        nargs="?",
        default="tests/assets/makehuman_raw",
        help="Directory containing mesh.obj (default: tests/assets/makehuman_raw)",
    )
    parser.add_argument("--frames", type=int, default=60, help="Number of turntable frames")
    parser.add_argument("--size",   type=int, default=512,  help="Image size in pixels")
    parser.add_argument("--pitch",  type=float, default=0.0, help="Camera pitch in degrees")
    parser.add_argument("--out",    default="out_face",      help="Output directory")
    parser.add_argument("--keep-top", type=float, default=0.13, help="Keep top N% of vertices")
    parser.add_argument("--yaw",      type=float, default=0.0, help="Camera yaw in degrees")
    parser.add_argument("--turntable", action="store_true", help="Also render 60-frame turntable")
    args = parser.parse_args()

    mesh_dir = Path(args.mesh_dir)
    out_dir  = Path(args.out)

    if not mesh_dir.exists():
        print(f"ERROR: mesh_dir not found: {mesh_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Single preview ────────────────────────────────────────────────────────
    preview_path = out_dir / "preview.png"
    print(f"\n{'='*60}")
    print(f"Rendering single preview → {preview_path}")
    t0 = time.perf_counter()
    render_face(
        mesh_dir,
        out_path=str(preview_path),
        image_size=args.size,
        yaw_degrees=args.yaw,
        pitch_degrees=args.pitch,
        keep_top_percent=args.keep_top,
    )
    print(f"Preview done in {(time.perf_counter()-t0)*1000:.1f} ms")

    # ── Turntable ─────────────────────────────────────────────────────────────
    if args.turntable:
        turntable_dir = out_dir / "turntable"
        print(f"\nRendering {args.frames}-frame turntable → {turntable_dir}/")
        t0 = time.perf_counter()
        render_face(
            mesh_dir,
            out_path=str(turntable_dir),
            image_size=args.size,
            n_frames=args.frames,
            pitch_degrees=args.pitch,
            keep_top_percent=args.keep_top,
        )
        elapsed = time.perf_counter() - t0
        print(f"Turntable done in {elapsed:.2f} s  ({elapsed/args.frames*1000:.1f} ms/frame)")
        print(f"\n✅ All done. Outputs in {out_dir}/")


if __name__ == "__main__":
    main()