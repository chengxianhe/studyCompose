"""Synthetic approvals ONLY inside a newly created temporary database, never a caller DB."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from govplatform.config import OWNER_HUMAN_ID, db_path
from govplatform.evaluation.models import Backend, Dataset
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType

EVALUATOR = Agent(kind="codex", session_id="synthetic-retrieval-evaluation")


@contextmanager
def corpus(dataset: Dataset, backend: Backend, es_url: str | None) -> Iterator[dict[str, str]]:
    # Process-local CLI only: don't expose this environment-switching helper in a server.
    if backend not in ("sqlite", "elasticsearch") or (backend == "elasticsearch" and not es_url):
        raise ValueError("valid backend and an explicit Elasticsearch URL are required")
    if es_url:
        parsed = urlsplit(es_url)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username
            or parsed.password
        ):
            raise ValueError("evaluation is limited to explicit local Elasticsearch endpoints")
    keys = ("GOVPLAT_DB_PATH", "GOVPLAT_ES_URL", "GOVPLAT_ES_INDEX_ALIAS", "HF_HUB_OFFLINE")
    original = {key: os.environ.get(key) for key in keys}
    production = db_path().resolve()
    with tempfile.TemporaryDirectory(prefix="govplatform-eval-") as directory:
        target = Path(directory) / "synthetic.sqlite"
        if target.resolve() == production or target.exists():
            raise ValueError("refusing to seed an existing/production database")
        os.environ["GOVPLAT_DB_PATH"] = str(target)
        os.environ["GOVPLAT_ES_INDEX_ALIAS"] = "govplatform_eval_" + uuid.uuid4().hex
        os.environ["HF_HUB_OFFLINE"] = "1"
        if backend == "elasticsearch":
            assert es_url is not None
            os.environ["GOVPLAT_ES_URL"] = es_url
        else:
            os.environ.pop("GOVPLAT_ES_URL", None)
        try:
            mapping = {}
            for doc in dataset.documents:
                obj = service.propose(
                    title=doc.title,
                    body=doc.body,
                    source="synthetic://retrieval-v1/" + doc.id,
                    type=KnowledgeType.REFERENCE,
                    authority_level=AuthorityLevel.REFERENCE,
                    caller=EVALUATOR,
                    expire_at=datetime(2000, 1, 1, tzinfo=UTC) if doc.state == "expired" else None,
                )
                service.approve(knowledge_id=obj.knowledge_id, caller=Human(id=OWNER_HUMAN_ID))
                if doc.state == "deprecated":
                    service.deprecate(
                        knowledge_id=obj.knowledge_id,
                        caller=Human(id=OWNER_HUMAN_ID),
                        reason="synthetic fixture: superseded",
                    )
                mapping[obj.knowledge_id] = doc.id
            yield mapping
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
