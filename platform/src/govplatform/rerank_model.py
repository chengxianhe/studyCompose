"""Pinned, offline-loadable Chinese cross-encoder assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from fastembed.rerank.cross_encoder import TextCrossEncoder
from huggingface_hub import snapshot_download

from govplatform.model_cache import cache_directory

MODEL_NAME = "BAAI/bge-reranker-base"
MODEL_REVISION = "2cfc18c9415c912f9d8155881c133215df768a70"
MODEL_SHA256 = {
    "config.json": "289adf7ada1eb6b4afa7589a48a032d45a076cf2e46dcdb3b4cabc33be14f708",
    "onnx/model.onnx": "15b9a8c3da82eddf263df571281166e00e9308fe19d077084b642ebfcaf06d2b",
    "sentencepiece.bpe.model": "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
    "special_tokens_map.json": "d5469a60db23249c7f8945013d78df30b44b6bf686c6bb4740f4223f77b1b535",
    "tokenizer.json": "9eb652ac4e40cc093272bbbe0f55d521cf67570060227109b5cdc20945a4489e",
    "tokenizer_config.json": "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
}
_MODEL_DIRECTORY = "models--BAAI--bge-reranker-base"


class RerankModelError(RuntimeError):
    """The pinned cross-encoder cannot be loaded from the selected cache."""


def snapshot_directory(cache: Path | None = None) -> Path:
    root = cache if cache is not None else cache_directory()
    return root / _MODEL_DIRECTORY / "snapshots" / MODEL_REVISION


def verify_snapshot(snapshot: Path, cache: Path | None = None) -> None:
    root = (cache if cache is not None else cache_directory()).resolve()
    if not snapshot.is_dir() or not snapshot.resolve().is_relative_to(root):
        raise RerankModelError("固定修订的重排模型快照不存在或不在缓存内")
    for filename, expected in MODEL_SHA256.items():
        file = snapshot / filename
        try:
            resolved = file.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise RerankModelError(f"重排模型文件越过缓存目录：{filename}")
            with resolved.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise RerankModelError(f"重排模型文件缺失或不可读：{filename}") from exc
        if actual != expected:
            raise RerankModelError(f"重排模型文件摘要不匹配：{filename}")


def ensure_snapshot(*, allow_download: bool) -> Path:
    root = cache_directory()
    snapshot = snapshot_directory(root)
    if snapshot.is_dir():
        verify_snapshot(snapshot, root)
        return snapshot
    if not allow_download:
        raise RerankModelError(
            "重排模型尚未预下载；请运行 python -m govplatform.rerank_model prepare"
        )
    try:
        downloaded = Path(
            snapshot_download(
                repo_id=MODEL_NAME,
                revision=MODEL_REVISION,
                allow_patterns=list(MODEL_SHA256),
                cache_dir=str(root),
            )
        )
    except Exception as exc:
        raise RerankModelError("固定修订的重排模型下载失败") from exc
    if downloaded.resolve() != snapshot.resolve():
        raise RerankModelError("重排模型下载结果与固定修订不一致")
    verify_snapshot(snapshot, root)
    return snapshot


def load_model(*, allow_download: bool) -> TextCrossEncoder:
    snapshot = ensure_snapshot(allow_download=allow_download)
    return TextCrossEncoder(
        model_name=MODEL_NAME,
        cache_dir=str(cache_directory()),
        specific_model_path=str(snapshot),
        local_files_only=True,
        threads=4,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or check the pinned local reranker")
    parser.add_argument("action", choices=("prepare", "check"))
    args = parser.parse_args()
    try:
        scores = list(
            load_model(allow_download=args.action == "prepare").rerank(
                "知识库如何检索", ["知识库使用混合检索", "苹果和香蕉是水果"]
            )
        )
        if len(scores) != 2 or not all(math.isfinite(float(score)) for score in scores):
            raise RerankModelError("重排模型输出无效")
    except (RerankModelError, OSError, ValueError) as exc:
        parser.exit(1, f"重排模型检查失败：{exc}\n")
    print(
        json.dumps(
            {
                "model": MODEL_NAME,
                "revision": MODEL_REVISION,
                "cache": str(cache_directory()),
                "sha256": MODEL_SHA256,
                "smoke_scores": scores,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
