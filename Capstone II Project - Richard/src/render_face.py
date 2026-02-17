from pathlib import Path
import torch
import numpy as np
from PIL import Image

from pytorch3d.io import load_objs_as_meshes
from pytorch3d.renderer import (
    MeshRenderer,
    MeshRasterizer,
    SoftPhongShader,
    RasterizationSettings,
    PerspectiveCameras,
    PointLights,
    look_at_view_transform
)


def render_face(
    face_or_path,
    model="makehuman",
    renderable="default",
    out_path="preview.png",
    image_size=512,
    n_frames=1,
    yaw_degrees=0.0,
    pitch_degrees=0.0,
    roll_degrees=0.0,
    radius=None,
    face_center_mode="auto",
    device="cuda"
):

    device = torch.device(device if torch.cuda.is_available() else "cpu")

    from src.face import Face

    if isinstance(face_or_path, str):
        face = Face.load(face_or_path)
        base_dir = Path(face_or_path)
    else:
        face = face_or_path
        base_dir = Path(".")

    rdata = face.data["models"][model]["renderables"][renderable]
    mesh_path = base_dir / rdata["mesh"]

    mesh = load_objs_as_meshes([str(mesh_path)], device=device)

    verts = mesh.verts_packed()
    center = verts.mean(0)

    if radius is None:
        bbox = verts.max(0)[0] - verts.min(0)[0]
        radius = bbox.norm().item() * 1.5

    images = []

    for i in range(n_frames):

        if n_frames > 1:
            yaw = yaw_degrees * (i / (n_frames - 1))
        else:
            yaw = yaw_degrees

        R, T = look_at_view_transform(
            dist=radius,
            elev=pitch_degrees,
            azim=yaw,
            device=device
        )

        cameras = PerspectiveCameras(device=device, R=R, T=T)

        lights = PointLights(
            device=device,
            location=[[0.0, 0.0, radius]]
        )

        raster_settings = RasterizationSettings(
            image_size=image_size,
            blur_radius=0.0,
            faces_per_pixel=1
        )

        renderer = MeshRenderer(
            rasterizer=MeshRasterizer(
                cameras=cameras,
                raster_settings=raster_settings
            ),
            shader=SoftPhongShader(
                device=device,
                cameras=cameras,
                lights=lights
            )
        )

        rendered = renderer(mesh)
        image = rendered[0, ..., :3].detach().cpu().numpy()
        image = (image * 255).astype(np.uint8)

        if n_frames == 1:
            Image.fromarray(image).save(out_path)
        else:
            frame_path = out_path.replace(".png", f"_{i:03d}.png")
            Image.fromarray(image).save(frame_path)

        images.append(image)

    return images