from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from govplatform import rerank_model


def _snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = b"synthetic reranker asset"
    monkeypatch.setattr(
        rerank_model, "MODEL_SHA256", {"onnx/model.onnx": hashlib.sha256(data).hexdigest()}
    )
    snapshot = rerank_model.snapshot_directory(tmp_path)
    (snapshot / "onnx").mkdir(parents=True)
    (snapshot / "onnx/model.onnx").write_bytes(data)
    return snapshot


def test_cached_reranker_is_verified_and_never_downloaded_for_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))

    def unexpected_download(**_kwargs: Any) -> None:
        pytest.fail("cached reranker must not be downloaded again")

    monkeypatch.setattr(rerank_model, "snapshot_download", unexpected_download)
    assert rerank_model.ensure_snapshot(allow_download=False) == snapshot
    assert rerank_model.ensure_snapshot(allow_download=True) == snapshot


def test_corrupt_or_external_reranker_assets_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    snapshot = _snapshot(cache, monkeypatch)
    model = snapshot / "onnx/model.onnx"
    model.write_bytes(b"changed")
    with pytest.raises(rerank_model.RerankModelError, match="摘要不匹配"):
        rerank_model.verify_snapshot(snapshot, cache)
    model.unlink()
    outside = tmp_path / "outside.onnx"
    outside.write_bytes(b"synthetic reranker asset")
    model.symlink_to(outside)
    with pytest.raises(rerank_model.RerankModelError, match="越过缓存目录"):
        rerank_model.verify_snapshot(snapshot, cache)


def test_reranker_loads_only_a_verified_local_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    marker = object()

    def fake_model(**kwargs: Any) -> object:
        assert kwargs["model_name"] == rerank_model.MODEL_NAME
        assert kwargs["specific_model_path"] == str(snapshot)
        assert kwargs["local_files_only"] is True
        return marker

    monkeypatch.setattr(rerank_model, "TextCrossEncoder", fake_model)
    assert rerank_model.load_model(allow_download=False) is marker
