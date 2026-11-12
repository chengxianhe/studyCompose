"""Stable snapshot hashes shared by core governance services and presentation adapters."""

import hashlib

from pydantic import BaseModel


def fingerprint(obj: BaseModel) -> str:
    return hashlib.sha256(obj.model_dump_json().encode()).hexdigest()
