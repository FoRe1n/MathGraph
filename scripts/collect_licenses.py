"""Collect distribution metadata notices without changing dependency packages."""
from importlib import metadata
from pathlib import Path
import json
import shutil
import sys


def collect(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    qt_licenses = Path(__file__).resolve().parents[1] / 'graphmath' / 'resources' / 'licenses'
    shutil.copytree(qt_licenses, destination / 'Qt', dirs_exist_ok=True)
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        inventory.append({"name": name, "version": dist.version, "license": dist.metadata.get("License", "See bundled notices")})
        for item in dist.files or []:
            lower = str(item).lower()
            if any(part in lower for part in ["license", "licence", "copying", "notice"]) and not lower.endswith((".py", ".pyc")):
                source = Path(dist.locate_file(item))
                if source.is_file():
                    target = destination / name / str(item).replace("..", "_")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, destination / "PYTHON-LICENSE.txt")
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    collect(sys.argv[1] if len(sys.argv)>1 else "build/licenses")
