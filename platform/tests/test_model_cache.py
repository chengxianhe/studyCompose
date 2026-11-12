from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from govplatform import model_cache


def _cached_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = b"synthetic model asset"
    monkeypatch.setattr(
        model_cache, "MODEL_SHA256", {"model_optimized.onnx": hashlib.sha256(data).hexdigest()}
    )
    snapshot = model_cache.snapshot_directory(tmp_path)
    snapshot.mkdir(parents=True)
    (snapshot / "model_optimized.onnx").write_bytes(data)
    return snapshot


def test_cache_path_is_stable_and_override_must_be_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    expected = Path(model_cache.__file__).resolve().parents[2] / ".data" / "models"
    assert model_cache.cache_directory() == expected
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    assert model_cache.cache_directory() == tmp_path
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", "relative/model-cache")
    with pytest.raises(model_cache.ModelCacheError, match="绝对路径"):
        model_cache.cache_directory()


def test_cached_snapshot_is_verified_without_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _cached_snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))

    def unexpected_download(**_kwargs: Any) -> None:
        pytest.fail("cached model must not contact the model repository")

    monkeypatch.setattr(model_cache, "snapshot_download", unexpected_download)
    assert model_cache.ensure_snapshot(allow_download=False) == snapshot
    assert model_cache.ensure_snapshot(allow_download=True) == snapshot


def test_missing_corrupt_and_external_model_files_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    snapshot = _cached_snapshot(cache, monkeypatch)
    file = snapshot / "model_optimized.onnx"
    file.write_bytes(b"changed")
    with pytest.raises(model_cache.ModelCacheError, match="摘要不匹配"):
        model_cache.verify_snapshot(snapshot, cache)
    file.unlink()
    with pytest.raises(model_cache.ModelCacheError, match="缺失"):
        model_cache.verify_snapshot(snapshot, cache)
    external = tmp_path / "outside-model-file"
    external.write_bytes(b"synthetic model asset")
    file.symlink_to(external)
    with pytest.raises(model_cache.ModelCacheError, match="越过缓存目录"):
        model_cache.verify_snapshot(snapshot, cache)


def test_prepare_downloads_fixed_revision_and_check_does_not_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    with pytest.raises(model_cache.ModelCacheError, match="尚未预下载"):
        model_cache.ensure_snapshot(allow_download=False)

    def fake_download(**kwargs: Any) -> str:
        assert kwargs["repo_id"] == model_cache.MODEL_REPOSITORY
        assert kwargs["revision"] == model_cache.MODEL_REVISION
        assert kwargs["cache_dir"] == str(tmp_path)
        return str(_cached_snapshot(tmp_path, monkeypatch))

    monkeypatch.setattr(model_cache, "snapshot_download", fake_download)
    assert model_cache.ensure_snapshot(allow_download=True) == model_cache.snapshot_directory(
        tmp_path
    )


def test_model_loading_uses_only_verified_local_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _cached_snapshot(tmp_path, monkeypatch)
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    marker = object()

    def fake_model(**kwargs: Any) -> object:
        assert kwargs["model_name"] == model_cache.MODEL_NAME
        assert kwargs["cache_dir"] == str(tmp_path)
        assert kwargs["specific_model_path"] == str(snapshot)
        assert kwargs["local_files_only"] is True
        return marker

    monkeypatch.setattr(model_cache, "TextEmbedding", fake_model)
    assert model_cache.load_model(allow_download=False) is marker
