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
            faces.append((current_mtl, line))

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
            out.write(mtllib_line)

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
                    out.write(f"usemtl {mtl}\n")
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


def build_head_face_mask_by_y(obj_path: str, keep_top_percent: float = 0.13):
    from collections import defaultdict, deque
    obj_path = Path(obj_path)
    ys = []
    xs = []
    zs = []

    with obj_path.open("r", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    xs.append(float(parts[1]))
                    ys.append(float(parts[2]))
                    zs.append(float(parts[3]))

    if not ys:
        raise ValueError("No vertices found in OBJ")

    min_y, max_y = min(ys), max(ys)
    cutoff = max_y - keep_top_percent * (max_y - min_y)

    def parse_vi(tok):
        return int(tok.split("/")[0]) - 1

    all_faces = []
    with obj_path.open("r", errors="ignore") as f:
        for line in f:
            if line.startswith("f "):
                toks = line.split()[1:]
                vis = [parse_vi(t) for t in toks]
                all_faces.append(vis)

    candidate_faces = [(fi, vis) for fi, vis in enumerate(all_faces)
                       if all(ys[vi] >= cutoff for vi in vis)]

    if not candidate_faces:
        raise ValueError("No faces above cutoff")

    # Build adjacency via shared vertices
    vert_to_faces = defaultdict(set)
    for fi, vis in candidate_faces:
        for vi in vis:
            vert_to_faces[vi].add(fi)

    face_to_verts = {fi: vis for fi, vis in candidate_faces}
    visited = set()
    components = []

    for fi, _ in candidate_faces:
        if fi in visited:
            continue
        component = set()
        queue = deque([fi])
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            component.add(curr)
            for vi in face_to_verts[curr]:
                for neighbor in vert_to_faces[vi]:
                    if neighbor not in visited:
                        queue.append(neighbor)
        components.append(component)

    print(f"Found {len(components)} components")

    # Find the largest component (main head skin)
    largest = max(components, key=len)

    # Compute centroid of largest component
    largest_verts = set()
    for fi in largest:
        for vi in face_to_verts[fi]:
            largest_verts.add(vi)
    cx = sum(xs[vi] for vi in largest_verts) / len(largest_verts)
    cy = sum(ys[vi] for vi in largest_verts) / len(largest_verts)
    cz = sum(zs[vi] for vi in largest_verts) / len(largest_verts)

    # ── Deduplicate components ────────────────────────────────────────────────
    # Small meshes (eyes, teeth, eyebrows) that straddle the Y cutoff get
    # fragmented into many tiny components of identical size with very similar
    # centroids. We deduplicate by rounding each component's centroid to a grid
    # and keeping only one component per (face_count, grid_cell) bucket.
    kept = set(largest)
    seen_signatures = set()

    for comp in components:
        if comp is largest:
            continue

        comp_verts = set()
        for fi in comp:
            for vi in face_to_verts[fi]:
                comp_verts.add(vi)

        ccx = sum(xs[vi] for vi in comp_verts) / len(comp_verts)
        ccy = sum(ys[vi] for vi in comp_verts) / len(comp_verts)
        ccz = sum(zs[vi] for vi in comp_verts) / len(comp_verts)

        dist = ((ccx-cx)**2 + (ccy-cy)**2 + (ccz-cz)**2) ** 0.5

        if dist >= 50.0:
            print(f"  Dropping component ({len(comp)} faces, dist={dist:.1f}) — too far")
            continue

        # Deduplicate: round centroid to 1-unit grid, bucket by (size, grid_cell)
        grid_res = 1.0
        sig = (
            len(comp),
            round(ccx / grid_res),
            round(ccy / grid_res),
            round(ccz / grid_res),
        )

        if sig in seen_signatures:
            print(f"  Deduplicating component ({len(comp)} faces, dist={dist:.1f}) — duplicate of kept component")
            continue

        seen_signatures.add(sig)
        kept.update(comp)
        print(f"  Keeping component ({len(comp)} faces, dist={dist:.1f})")

    print(f"Total faces kept: {len(kept)}")
    return sorted(kept)