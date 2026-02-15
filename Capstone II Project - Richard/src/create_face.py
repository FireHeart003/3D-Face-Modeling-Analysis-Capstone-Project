from pathlib import Path
import json

BASE_DIR = Path("faces")

FOLDERS = [
    "geometry",
    "parameters",
    "textures",
    "measurements",
    "rendering",
    "transforms",
    "experiments",
    "metadata"
]

def get_next_face_id():
    if not BASE_DIR.exists():
        return 1

    ids = [
        int(p.name.split("_")[1])
        for p in BASE_DIR.iterdir()
        if p.is_dir() and p.name.startswith("face_")
    ]
    return max(ids, default=0) + 1


def create_face():
    BASE_DIR.mkdir(exist_ok=True)

    face_id = f"face_{get_next_face_id():03d}"
    face_dir = BASE_DIR / face_id

    # Create folders
    for folder in FOLDERS:
        (face_dir / folder).mkdir(parents=True, exist_ok=True)

    # FaceModel.json
    face_model = {
        "face_id": face_id,

        "geometry": {
            "neutral": None,
            "expression": None,
            "scan": None
        },

        "parameters": {
            "makehuman": {
                "identity": None,
                "expression": None
            },
            "flame": None,
            "arkit": None,
            "eom": None
        },

        "textures": {
            "diffuse": None,
            "specular": None,
            "normal": None,
            "displacement": None,
            "reflectance": None
        },

        "measurements": {
            "landmarks": None,
            "anthropometry": None,
            "expression_metrics": None
        },

        "rendering": {
            "camera": None,
            "lighting": None,
            "settings": None
        },

        "transforms": {
            "mh_to_flame": None,
            "arkit_to_mh": None,
            "eom_to_mh": None
        },

        "experiments": {
            "sampling": None,
            "trajectories": None,
            "reverse_correlation": None
        },

        "metadata": "metadata/meta.json"
    }

    with open(face_dir / "FaceModel.json", "w") as f:
        json.dump(face_model, f, indent=4)

    # metadata/meta.json
    metadata = {
        "identity": {
            "face_id": face_id,
            "label": None,
            "description": None
        },
        "provenance": {
            "source_type": None,
            "source_tool": None,
            "dataset": None,
            "license": None
        },
        "representation": {
            "space": None,
            "topology": None,
            "units": None
        },
        "processing_history": []
    }

    with open(face_dir / "metadata" / "meta.json", "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"✅ Created {face_id}")


if __name__ == "__main__":
    create_face()