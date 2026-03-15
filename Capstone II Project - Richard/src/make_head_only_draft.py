from pathlib import Path


def make_head_only_obj(in_obj_path, out_obj_path, face_mask, group_name="head_only"):
    """
    Export a subset of faces from an OBJ while preserving:
      - mtllib line (material library reference)
      - usemtl assignments (so textures/materials still work)

    face_mask: list[int] of face indices (0-based) among ONLY the 'f ' lines.
    """
    in_obj_path = Path(in_obj_path)
    out_obj_path = Path(out_obj_path)

    face_mask = set(face_mask)  # faster lookup

    vertices = []
    uvs = []
    normals = []

    # We'll store selected faces as: (material_name_or_None, face_line_string)
    selected_faces = []

    mtllib_line = None
    current_mtl = None

    face_index = 0  # counts ONLY 'f ' lines

    # ---- Pass 1: read file, collect v/vt/vn, and collect ONLY selected faces with their usemtl ----
    with in_obj_path.open("r", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if line.startswith("mtllib "):
                # Keep the first mtllib (usually just one)
                if mtllib_line is None:
                    mtllib_line = line

            elif line.startswith("usemtl "):
                current_mtl = line.split(maxsplit=1)[1].strip() if len(line.split()) > 1 else None

            elif line.startswith("v "):
                vertices.append(line + "\n")

            elif line.startswith("vt "):
                uvs.append(line + "\n")

            elif line.startswith("vn "):
                normals.append(line + "\n")

            elif line.startswith("f "):
                if face_index in face_mask:
                    selected_faces.append((current_mtl, line))
                face_index += 1

    if not selected_faces:
        raise ValueError("No faces selected. face_mask may be empty or cutoff too strict.")

    # ---- Pass 2: figure out which v/vt/vn indices are used by selected faces ----
    used_v = set()
    used_vt = set()
    used_vn = set()

    # parsed faces: list of (material, list[(v,vt,vn)])
    parsed_faces = []

    for mtl, face_line in selected_faces:
        parts = face_line.strip().split()[1:]
        tri = []
        for part in parts:
            vals = part.split("/")
            v = int(vals[0]) if vals[0] else None
            vt = int(vals[1]) if len(vals) > 1 and vals[1] else None
            vn = int(vals[2]) if len(vals) > 2 and vals[2] else None

            if v is None:
                continue

            used_v.add(v)
            if vt is not None:
                used_vt.add(vt)
            if vn is not None:
                used_vn.add(vn)

            tri.append((v, vt, vn))

        if tri:
            parsed_faces.append((mtl, tri))

    # Create remap tables: old OBJ indices are 1-based; new should also be 1-based
    v_sorted = sorted(used_v)
    vt_sorted = sorted(used_vt)
    vn_sorted = sorted(used_vn)

    v_map = {old: i + 1 for i, old in enumerate(v_sorted)}
    vt_map = {old: i + 1 for i, old in enumerate(vt_sorted)}
    vn_map = {old: i + 1 for i, old in enumerate(vn_sorted)}

    # ---- Write output OBJ ----
    out_obj_path.parent.mkdir(parents=True, exist_ok=True)

    with out_obj_path.open("w") as out:
        out.write(f"# Generated head-only OBJ from: {in_obj_path.name}\n")
        out.write(f"# Faces kept: {len(parsed_faces)}\n")

        # Preserve mtllib so materials/textures can resolve
        if mtllib_line:
            out.write(mtllib_line + "\n")

        # Optional group name
        if group_name:
            out.write(f"g {group_name}\n")

        # Write only used vertices/uvs/normals
        for old in v_sorted:
            out.write(vertices[old - 1])
        for old in vt_sorted:
            out.write(uvs[old - 1])
        for old in vn_sorted:
            out.write(normals[old - 1])

        # Write faces, inserting usemtl only when it changes
        last_mtl = None
        for mtl, face in parsed_faces:
            if mtl != last_mtl:
                if mtl:
                    out.write(f"usemtl {mtl}\n")
                last_mtl = mtl

            line = "f "
            for v, vt, vn in face:
                nv = v_map[v]
                if vt is not None and vn is not None:
                    line += f"{nv}/{vt_map[vt]}/{vn_map[vn]} "
                elif vt is not None:
                    line += f"{nv}/{vt_map[vt]} "
                elif vn is not None:
                    # This format is v//vn
                    line += f"{nv}//{vn_map[vn]} "
                else:
                    line += f"{nv} "
            out.write(line.rstrip() + "\n")


def build_head_face_mask_by_y(obj_path: str, keep_top_percent: float = 0.22):
    """
    Returns a list of face indices (0-based) to keep among ONLY 'f ' lines.
    keep_top_percent=0.22 means keep faces in the top 22% of the model height.
    """
    obj_path = Path(obj_path)
    ys = []

    # Pass 1: collect vertex Y
    with obj_path.open("r", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    ys.append(float(parts[2]))  # v x y z

    if not ys:
        raise ValueError("No vertices found in OBJ")

    min_y, max_y = min(ys), max(ys)
    cutoff = max_y - keep_top_percent * (max_y - min_y)

    # Pass 2: build face mask
    face_mask = []
    face_index = 0

    def parse_vi(tok: str) -> int:
        # OBJ indices are 1-based; convert to 0-based for ys list
        return int(tok.split("/")[0]) - 1

    with obj_path.open("r", errors="ignore") as f:
        for line in f:
            if line.startswith("f "):
                toks = line.split()[1:]
                vis = [parse_vi(t) for t in toks]
                if all(ys[vi] >= cutoff for vi in vis):
                    face_mask.append(face_index)
                face_index += 1

    return face_mask