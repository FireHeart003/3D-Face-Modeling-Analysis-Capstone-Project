from pathlib import Path


def make_head_only_obj(in_obj_path, out_obj_path, face_mask, group_name="head_only"):
    in_obj_path = Path(in_obj_path)
    out_obj_path = Path(out_obj_path)

    face_mask = set(face_mask)

    vertices = []
    uvs = []
    normals = []
    faces = []
    mtllib_line = None
    current_mtl = None

    with open(in_obj_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("mtllib "):
            if mtllib_line is None:
                mtllib_line = line
        elif line.startswith("usemtl "):
            current_mtl = line.split(maxsplit=1)[1].strip()
        elif line.startswith("v "):
            vertices.append(line)
        elif line.startswith("vt "):
            uvs.append(line)
        elif line.startswith("vn "):
            normals.append(line)
        elif line.startswith("f "):
            faces.append((current_mtl, line))  # store material with face

    selected_faces = [faces[i] for i in face_mask]

    used_v = set()
    used_vt = set()
    used_vn = set()
    parsed_faces = []

    for mtl, face in selected_faces:
        parts = face.strip().split()[1:]
        new_face = []
        for part in parts:
            vals = part.split("/")
            v  = int(vals[0])
            vt = int(vals[1]) if len(vals) > 1 and vals[1] else None
            vn = int(vals[2]) if len(vals) > 2 and vals[2] else None
            used_v.add(v)
            if vt is not None:
                used_vt.add(vt)
            if vn is not None:
                used_vn.add(vn)
            new_face.append((v, vt, vn))
        parsed_faces.append((mtl, new_face))

    v_map  = {old: i+1 for i, old in enumerate(sorted(used_v))}
    vt_map = {old: i+1 for i, old in enumerate(sorted(used_vt))}
    vn_map = {old: i+1 for i, old in enumerate(sorted(used_vn))}

    Path(out_obj_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_obj_path, "w") as out:
        if mtllib_line:
            out.write(mtllib_line)          # ✅ keeps mtllib mesh.mtl

        if group_name:
            out.write(f"g {group_name}\n")

        for old in sorted(used_v):
            out.write(vertices[old-1])
        for old in sorted(used_vt):
            out.write(uvs[old-1])
        for old in sorted(used_vn):
            out.write(normals[old-1])

        last_mtl = None
        for mtl, face in parsed_faces:
            if mtl != last_mtl:
                if mtl:
                    out.write(f"usemtl {mtl}\n")  # ✅ keeps material assignments
                last_mtl = mtl

            line = "f "
            for v, vt, vn in face:
                nv  = v_map[v]
                nvt = vt_map[vt] if vt is not None else ""
                nvn = vn_map[vn] if vn is not None else ""
                if vt is not None and vn is not None:
                    line += f"{nv}/{nvt}/{nvn} "
                elif vt is not None:
                    line += f"{nv}/{nvt} "
                else:
                    line += f"{nv} "
            out.write(line.strip() + "\n")


def build_head_face_mask_by_y(obj_path: str, keep_top_percent: float = 0.10):
    obj_path = Path(obj_path)
    ys = []

    with obj_path.open("r", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    ys.append(float(parts[2]))

    if not ys:
        raise ValueError("No vertices found in OBJ")

    min_y, max_y = min(ys), max(ys)
    cutoff = max_y - keep_top_percent * (max_y - min_y)

    face_mask = []
    face_index = 0

    def parse_vi(tok: str) -> int:
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