import trimesh
import shutil
import numpy as np
from pathlib import Path

ASSET_ROOT = Path("tests/assets/makehuman_raw")

# Maps geometry name keywords → material settings.
# Checked in order — first match wins.
_MATERIAL_RULES = [
    {
        "keywords": ["eyebrow"],
        "texture":  "textures/eyebrow012.png",
        "alpha_mode":   "BLEND",   # ← was MASK
        "alpha_cutoff": 0.0,
        "double_sided": True,
    },
    {
        # Eye_brown matches "eye" AND "brown" — one rule covers both
        "keywords": ["eye", "brown"],
        "texture":  "textures/brown_eye.png",
        # BLEND so alpha channel in the texture is respected
        "alpha_mode":   "BLEND",
        "alpha_cutoff": 0.0,
        "double_sided": True,
    },
    {
        "keywords": ["teeth"],
        "texture":  "textures/teeth.png",
        "alpha_mode":   "OPAQUE",
        "alpha_cutoff": 0.0,
        "double_sided": False,
    },
    {
        "keywords": ["tongue"],
        "texture":  "textures/tongue01_diffuse.png",
        "alpha_mode":   "OPAQUE",
        "alpha_cutoff": 0.0,
        "double_sided": False,
    },
]

_SKIN_RULE = {
    "texture":  "textures/young_lightskinned_male_diffuse2.png",
    "alpha_mode":   "OPAQUE",
    "alpha_cutoff": 0.0,
    "double_sided": False,
}


def _rule_for(name_lower: str) -> dict:
    for rule in _MATERIAL_RULES:
        if any(kw in name_lower for kw in rule["keywords"]):
            return rule
    return _SKIN_RULE


def obj_to_glb(obj_path, glb_path, asset_root=None):
    obj_path = Path(obj_path)
    glb_path = Path(glb_path)

    if asset_root is None:
        asset_root = (
            obj_path.parent
            if (obj_path.parent / "mesh.mtl").exists()
            else ASSET_ROOT
        )

    glb_path.parent.mkdir(parents=True, exist_ok=True)
    _copy_assets_to(obj_path, asset_root)

    scene = trimesh.load(str(obj_path), force="scene")

    # Returns the ordered geometry name list so patch can use it
    geom_name_order = _fix_scene_materials(scene, asset_root)

    scene.export(str(glb_path))
    print(f"Converted: {obj_path.name} -> {glb_path.name}")

    # Post-process: hard-set alphaMode/doubleSided in the GLB JSON.
    # Uses name matching first; falls back to insertion-order index if names
    # are None (trimesh bug in some versions).
    _patch_glb_materials(glb_path, geom_name_order)

    return glb_path


# -----------------------------------------------------------------------------
# Step 1: fix trimesh visuals before export
# -----------------------------------------------------------------------------

def _fix_scene_materials(scene, asset_root):
    """Assign correct PBR materials + preserve UVs. Returns ordered name list."""
    from PIL import Image as PILImage

    geom_names = list(scene.geometry.keys())
    print("Geometry names found:", geom_names)

    for name, geom in scene.geometry.items():
        if not hasattr(geom, "visual"):
            continue

        rule = _rule_for(name.lower())
        tex_path = asset_root / rule["texture"]

        if not tex_path.exists():
            print(f"  [WARN] {name}: texture not found at {tex_path}")
            continue

        # Recover UV coordinates robustly
        uv = None
        if hasattr(geom.visual, "uv") and geom.visual.uv is not None:
            uv = geom.visual.uv
            print(f"  {name}: UVs from .uv ({len(uv)} coords) "
                  f"| alpha={rule['alpha_mode']} | ds={rule['double_sided']}")
        elif hasattr(geom.visual, "to_texture"):
            try:
                tv = geom.visual.to_texture()
                if hasattr(tv, "uv") and tv.uv is not None:
                    uv = tv.uv
                    print(f"  {name}: UVs via to_texture() ({len(uv)} coords)")
            except Exception as e:
                print(f"  {name}: to_texture() failed: {e}")

        if uv is None:
            print(f"  [WARN] {name}: no UVs found")
        else:
            # MakeHuman UVs frequently exceed [0,1] (UDIM / atlas overflow).
            # Without clamping, the GLB sampler tiles the texture, producing the
            # checkerboard-of-repeated-heads artifact visible in the render.
            uv_min, uv_max = uv.min(), uv.max()
            if uv_min < 0.0 or uv_max > 1.0:
                print(f"  {name}: clamping UVs from [{uv_min:.3f}, {uv_max:.3f}] → [0, 1]")
                uv = np.clip(uv, 0.0, 1.0)

        img = PILImage.open(str(tex_path)).convert("RGBA")

        mat = trimesh.visual.material.PBRMaterial(
            baseColorTexture=img,
            doubleSided=rule["double_sided"],
            alphaMode=rule["alpha_mode"],
            alphaCutoff=rule["alpha_cutoff"] if rule["alpha_mode"] == "MASK" else None,
        )

        # Stamp the geometry name onto the material object.
        # trimesh copies mat.name into the GLB material JSON when present.
        mat.name = name

        if uv is not None:
            geom.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
        else:
            geom.visual = trimesh.visual.TextureVisuals(material=mat)

    return geom_names


# -----------------------------------------------------------------------------
# Step 2: patch the written GLB so nothing is silently dropped by trimesh
# -----------------------------------------------------------------------------

def _patch_glb_materials(glb_path: Path, geom_name_order: list = None):
    """
    Hard-set alphaMode / doubleSided in the GLB.

    Strategy A (preferred): match by material.name keyword.
    Strategy B (fallback):  trimesh wrote None names → use insertion order.
      The order trimesh writes materials mirrors scene.geometry insertion order,
      which is the geom_name_order list passed in from _fix_scene_materials.
    """
    try:
        import pygltflib
    except ImportError:
        print("  [WARN] pygltflib not installed. Run: pip install pygltflib")
        return

    gltf = pygltflib.GLTF2().load(str(glb_path))
    changed = False

    names_are_none = all(m.name is None for m in gltf.materials)
    if names_are_none:
        print("  [INFO] All GLB material names are None — using index-based patch.")

    for i, mat in enumerate(gltf.materials):
        # Determine which rule applies
        if not names_are_none and mat.name:
            rule = _rule_for(mat.name.lower())
            label = mat.name
        elif geom_name_order and i < len(geom_name_order):
            # Fallback: assume material i corresponds to geometry i
            label = geom_name_order[i]
            rule = _rule_for(label.lower())
        else:
            rule = _SKIN_RULE
            label = f"mat[{i}]"

        new_alpha  = rule["alpha_mode"]
        new_cutoff = rule["alpha_cutoff"] if new_alpha == "MASK" else None
        new_ds     = rule["double_sided"]

        if (mat.alphaMode != new_alpha
                or mat.alphaCutoff != new_cutoff
                or mat.doubleSided != new_ds):
            print(f"  Patching [{i}] '{label}': "
                  f"alphaMode {mat.alphaMode!r}->{new_alpha!r}  "
                  f"doubleSided {mat.doubleSided}->{new_ds}")
            mat.alphaMode   = new_alpha
            mat.alphaCutoff = new_cutoff
            mat.doubleSided = new_ds
            # Also write the name so future runs can use Strategy A
            if mat.name is None:
                mat.name = label
            changed = True

    if changed:
        gltf.save(str(glb_path))
        print(f"  GLB re-saved: {glb_path.name}")
    else:
        print("  GLB materials already correct.")

    # ── Force all texture samplers to CLAMP_TO_EDGE ───────────────────────────
    # glTF wrap constants: 33071 = CLAMP_TO_EDGE, 10497 = REPEAT (default).
    # Without this, any residual out-of-range UV will tile the texture and
    # produce the checkerboard-of-repeated-heads artifact.
    CLAMP_TO_EDGE = 33071
    sampler_changed = False
    for i, sampler in enumerate(gltf.samplers):
        if sampler.wrapS != CLAMP_TO_EDGE or sampler.wrapT != CLAMP_TO_EDGE:
            print(f"  Patching sampler [{i}]: wrapS/T → CLAMP_TO_EDGE")
            sampler.wrapS = CLAMP_TO_EDGE
            sampler.wrapT = CLAMP_TO_EDGE
            sampler_changed = True

    # If there are textures but no explicit samplers, inject one
    if not gltf.samplers and gltf.textures:
        print(f"  Injecting CLAMP_TO_EDGE sampler for {len(gltf.textures)} texture(s)")
        for tex in gltf.textures:
            gltf.samplers.append(pygltflib.Sampler(wrapS=CLAMP_TO_EDGE, wrapT=CLAMP_TO_EDGE))
            tex.sampler = len(gltf.samplers) - 1
        sampler_changed = True

    if sampler_changed:
        gltf.save(str(glb_path))
        print(f"  GLB re-saved with clamped samplers: {glb_path.name}")

    print("\n  Final GLB material state:")
    for i, mat in enumerate(gltf.materials):
        print(f"    [{i}] {str(mat.name):<35s}  "
              f"alphaMode={mat.alphaMode!r:<8s}  "
              f"alphaCutoff={mat.alphaCutoff}  "
              f"doubleSided={mat.doubleSided}")


# -----------------------------------------------------------------------------
# Utility: copy MTL + textures next to the OBJ so trimesh can find them
# -----------------------------------------------------------------------------

def _copy_assets_to(obj_path, asset_root):
    obj_path = Path(obj_path)
    obj_dir  = obj_path.parent

    mtl_name = None
    with open(obj_path) as f:
        for line in f:
            if line.startswith("mtllib "):
                mtl_name = line.split(maxsplit=1)[1].strip()
                break

    if not mtl_name:
        return

    mtl_path = asset_root / mtl_name
    if not mtl_path.exists():
        print(f"MTL not found: {mtl_path}")
        return

    dest_mtl = obj_dir / mtl_name
    if not dest_mtl.exists():
        shutil.copy(mtl_path, dest_mtl)
        print(f"Copied {mtl_name}")

    with open(mtl_path) as f:
        for line in f:
            if line.strip().lower().startswith("map_"):
                tex_name = line.split(maxsplit=1)[1].strip()
                tex_src  = asset_root / tex_name
                tex_dst  = obj_dir / tex_name
                if tex_src.exists() and not tex_dst.exists():
                    tex_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(tex_src, tex_dst)
                    print(f"Copied texture: {tex_name}")