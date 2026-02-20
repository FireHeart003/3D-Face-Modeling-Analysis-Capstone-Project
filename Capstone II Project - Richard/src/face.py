import json
import shutil
import hashlib
from pathlib import Path
from .utilities import read_params

# Hard coded values, need to implment
def parse_mhm(path):
    # return {"identity_param": 0.5}
    return read_params(path)

# Hard coded values, need to implment
def parse_mhpose(path):
    return {"expression_param": 0.8}


class Face:
    # Constructor
    def __init__(self, data=None):
        self.data = data or {
            "models": {
                "makehuman": {
                    "components": {
                        "identity": {"parameters": {}},
                        "expression": {"parameters": {}}
                    },
                    "renderables": {}
                }
            }
        }

    # Alternate constructor that creates a Face object from a MakeHuman identity mhm file
    @classmethod
    def from_makehuman_identity(cls, mhm_path):
        identity_dict = parse_mhm(mhm_path)
        data = {
            "models": {
                "makehuman": {
                    "components": {
                        "identity": {"parameters": identity_dict},
                        "expression": {"parameters": {}}
                    },
                    "renderables": {}
                }
            }
        }
        return cls(data=data)

    # Add a MakeHuman expression to the Face object and updates the expression parameter in the dictionary of self.data
    def add_makehuman_expression(self, mhpose_path):
        expression_dict = parse_mhpose(mhpose_path)
        self.data["models"]["makehuman"]["components"]["expression"]["parameters"] = expression_dict

    # Registers a renderable 3D mesh into a dictionary to be added to self.data object
    def add_renderable(self, model, name, mesh, mtl=None, textures_dir=None):
        renderable = {
            "mesh": mesh,
            "mtl": mtl,
            "textures_dir": textures_dir,
            "manifest": {}
        }
        self.data["models"][model]["renderables"][name] = renderable

    # Saves the Face object data stored into a JSON file with relative paths
    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        models_dir = directory / "models"
        for model_name, model_data in self.data["models"].items():
            model_dir = models_dir / model_name
            renderables = model_data.get("renderables", {})
            for name, rdata in renderables.items():
                rdir = model_dir / "renderables" / name
                rdir.mkdir(parents=True, exist_ok=True)

                mesh_src = Path(rdata["mesh"])
                mesh_dst = rdir / mesh_src.name
                shutil.copy(mesh_src, mesh_dst)
                rdata["mesh"] = str(mesh_dst.relative_to(directory))

                if rdata.get("mtl"):
                    mtl_src = Path(rdata["mtl"])
                    mtl_dst = rdir / mtl_src.name
                    shutil.copy(mtl_src, mtl_dst)
                    rdata["mtl"] = str(mtl_dst.relative_to(directory))

                if rdata.get("textures_dir"):
                    textures_src = Path(rdata["textures_dir"])
                    textures_dst = rdir / "textures"
                    textures_dst.mkdir(exist_ok=True)
                    for file in textures_src.iterdir():
                        shutil.copy(file, textures_dst / file.name)
                    rdata["textures_dir"] = str(textures_dst.relative_to(directory))

        with open(directory / "FaceModel.json", "w") as f:
            json.dump(self.data, f, indent=4)

    # Read a JSON object into a Face object with its data as a dictionary
    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        with open(directory / "FaceModel.json", "r") as f:
            data = json.load(f)
        return cls(data=data)

    # Validate a renderable and stored validation results into the manifest dictionary in rdata
    def validate_renderable(self, model, renderable, base_dir):
        base_dir = Path(base_dir)
        rdata = self.data["models"][model]["renderables"][renderable]

        mesh_path = base_dir / rdata["mesh"]
        if not mesh_path.exists():
            raise ValueError("Mesh file missing")

        vertex_count = 0
        face_count = 0
        uv_present = False
        uv_data = []

        with open(mesh_path, "r") as f:
            for line in f:
                if line.startswith("v "):
                    vertex_count += 1
                elif line.startswith("f "):
                    face_count += 1
                elif line.startswith("vt "):
                    uv_present = True
                    uv_data.append(line.strip())

        if rdata.get("textures_dir") and not uv_present:
            raise ValueError("Textures provided but OBJ has no UVs")

        uv_hash = None
        if uv_present:
            hash_obj = hashlib.sha256()
            for uv in uv_data:
                hash_obj.update(uv.encode())
            uv_hash = hash_obj.hexdigest()

        manifest = {
            "vertex_count": vertex_count,
            "face_count": face_count,
            "uv_present": uv_present,
            "uv_hash": uv_hash
        }

        rdata["manifest"] = manifest

    # Calls validate_renderable() for each renderable
    def validate(self, base_dir=None):
        base_dir = Path(base_dir) if base_dir else Path(".")
        for model_name, model_data in self.data["models"].items():
            for renderable in model_data.get("renderables", {}):
                self.validate_renderable(model_name, renderable, base_dir)