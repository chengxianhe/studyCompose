"""Pinned local assets for the knowledge search embedding model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from fastembed import TextEmbedding
from huggingface_hub import snapshot_download

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_REPOSITORY = "Qdrant/bge-small-zh-v1.5"
MODEL_REVISION = "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59"
MODEL_SHA256 = {
    "config.json": "9088751d39abbf86ec3d19ffca92ad62ad19075f7e59712e6c71217fa125d1d3",
    "model_optimized.onnx": "1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38",
    "special_tokens_map.json": "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
    "tokenizer.json": "48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26",
    "tokenizer_config.json": "e6f3b96db926a37d4039995fbf5ad17de158dfb8f6343d607e4dbaad18d75f5a",
}

_DEFAULT_CACHE = Path(__file__).resolve().parents[2] / ".data" / "models"
_MODEL_DIRECTORY = "models--Qdrant--bge-small-zh-v1.5"


class ModelCacheError(RuntimeError):
    """The pinned model cannot be used safely from the selected cache."""


def cache_directory() -> Path:
    override = os.environ.get("FASTEMBED_CACHE_PATH")
    if not override:
        return _DEFAULT_CACHE
    path = Path(override).expanduser()
    if not path.is_absolute():
        raise ModelCacheError("FASTEMBED_CACHE_PATH 必须是绝对路径")
    return path.resolve()


def snapshot_directory(cache: Path | None = None) -> Path:
    root = cache if cache is not None else cache_directory()
    return root / _MODEL_DIRECTORY / "snapshots" / MODEL_REVISION


def verify_snapshot(snapshot: Path, cache: Path | None = None) -> None:
    root = cache if cache is not None else cache_directory()
    root = root.resolve()
    if not snapshot.is_dir() or not snapshot.resolve().is_relative_to(root):
        raise ModelCacheError("固定修订的模型快照不存在或不在模型缓存内")
    for filename, expected in MODEL_SHA256.items():
        file = snapshot / filename
        try:
            resolved = file.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise ModelCacheError(f"模型文件越过缓存目录：{filename}")
            with resolved.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise ModelCacheError(f"模型文件缺失或不可读：{filename}") from exc
        if actual != expected:
            raise ModelCacheError(f"模型文件摘要不匹配：{filename}")


def ensure_snapshot(*, allow_download: bool) -> Path:
    root = cache_directory()
    snapshot = snapshot_directory(root)
    if snapshot.is_dir():
        verify_snapshot(snapshot, root)
        return snapshot
    if not allow_download:
        raise ModelCacheError("模型尚未预下载；请运行 python -m govplatform.model_cache prepare")
    try:
        downloaded = Path(
            snapshot_download(
                repo_id=MODEL_REPOSITORY,
                revision=MODEL_REVISION,
                allow_patterns=list(MODEL_SHA256),
                cache_dir=str(root),
            )
        )
    except Exception as exc:
        raise ModelCacheError("固定修订的模型下载失败") from exc
    if downloaded.resolve() != snapshot.resolve():
        raise ModelCacheError("下载结果的模型修订与固定修订不一致")
    verify_snapshot(snapshot, root)
    return snapshot


def load_model(*, allow_download: bool) -> TextEmbedding:
    snapshot = ensure_snapshot(allow_download=allow_download)
    return TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=str(cache_directory()),
        specific_model_path=str(snapshot),
        local_files_only=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or verify the pinned local search model")
    parser.add_argument("action", choices=("prepare", "check"))
    args = parser.parse_args()
    try:
        model = load_model(allow_download=args.action == "prepare")
        dimensions = len(next(iter(model.embed(["知识检索离线验收"]))))
        if dimensions != 512:
            raise ModelCacheError("模型输出维度不符合 512 维约定")
    except (ModelCacheError, OSError, ValueError) as exc:
        parser.exit(1, f"模型检查失败：{exc}\n")
    print(
        json.dumps(
            {
                "model": MODEL_NAME,
                "repository": MODEL_REPOSITORY,
                "revision": MODEL_REVISION,
                "cache": str(cache_directory()),
                "dimensions": dimensions,
                "sha256": MODEL_SHA256,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
