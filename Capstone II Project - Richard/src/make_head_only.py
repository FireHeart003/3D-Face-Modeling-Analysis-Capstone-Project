def make_head_only_obj(in_obj_path, out_obj_path, face_mask):
    vertices = []
    uvs = []
    normals = []
    faces = []

    with open(in_obj_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("v "):
            vertices.append(line)
        elif line.startswith("vt "):
            uvs.append(line)
        elif line.startswith("vn "):
            normals.append(line)
        elif line.startswith("f "):
            faces.append(line)

    selected_faces = [faces[i] for i in face_mask]

    used_v = set()
    used_vt = set()
    used_vn = set()

    parsed_faces = []

    for face in selected_faces:
        parts = face.strip().split()[1:]
        new_face = []
        for part in parts:
            vals = part.split("/")
            v = int(vals[0])
            vt = int(vals[1]) if len(vals) > 1 and vals[1] else None
            vn = int(vals[2]) if len(vals) > 2 and vals[2] else None

            used_v.add(v)
            if vt:
                used_vt.add(vt)
            if vn:
                used_vn.add(vn)

            new_face.append((v, vt, vn))
        parsed_faces.append(new_face)

    v_map = {old: i+1 for i, old in enumerate(sorted(used_v))}
    vt_map = {old: i+1 for i, old in enumerate(sorted(used_vt))}
    vn_map = {old: i+1 for i, old in enumerate(sorted(used_vn))}

    with open(out_obj_path, "w") as out:
        for old in sorted(used_v):
            out.write(vertices[old-1])
        for old in sorted(used_vt):
            out.write(uvs[old-1])
        for old in sorted(used_vn):
            out.write(normals[old-1])

        for face in parsed_faces:
            line = "f "
            for v, vt, vn in face:
                nv = v_map[v]
                nvt = vt_map[vt] if vt else ""
                nvn = vn_map[vn] if vn else ""
                if vt and vn:
                    line += f"{nv}/{nvt}/{nvn} "
                elif vt:
                    line += f"{nv}/{nvt} "
                else:
                    line += f"{nv} "
            out.write(line.strip() + "\n")