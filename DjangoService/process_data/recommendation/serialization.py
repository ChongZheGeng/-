from __future__ import annotations

import pickle
from pathlib import Path

try:
    import joblib  # type: ignore
except Exception:
    joblib = None


def dump_object(obj, path: Path):
    if joblib is not None:
        joblib.dump(obj, path)
        return
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def load_object(path: Path):
    if joblib is not None:
        return joblib.load(path)
    with open(path, 'rb') as f:
        return pickle.load(f)
