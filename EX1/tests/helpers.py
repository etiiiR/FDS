import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_task(number):
    spec = importlib.util.spec_from_file_location(
        f"task{number}", ROOT / f"template/task{number}/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
