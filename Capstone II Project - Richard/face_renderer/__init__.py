"""face_renderer — Filament-based GPU face rendering package."""

# Imports render_face from render.py and makes it avaiable at the package level
from face_renderer.render import render_face

# Export only the render_face function
__all__ = ["render_face"]