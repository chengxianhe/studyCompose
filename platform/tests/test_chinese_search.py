from govplatform.identity.models import Agent
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType
from govplatform.search.index import BM25Corpus, tokenize


def test_chinese_phrase_embedded_in_sentence() -> None:
    from datetime import UTC, datetime

    obj = KnowledgeObject(
        knowledge_id="test",
        title="项目交付要求",
        body="验收证据需关联任务记录",
        type=KnowledgeType.PROJECT_STANDARD,
        source="test",
        authority_level=AuthorityLevel.PROJECT,
        author=Agent(kind="codex", session_id="test"),
        content_hash="test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert BM25Corpus([obj]).query("验收证据", limit=10)[0][0] == obj
    assert BM25Corpus([obj]).query("数据库", limit=10) == []
    assert (
        BM25Corpus([obj.model_copy(update={"title": "!!!", "body": "..."})]).query(
            "test",
            limit=10,
        )
        == []
    )


def test_mixed_ascii_and_chinese_tokens() -> None:
    assert tokenize("UseCase验收证据 v2") == ["usecase", "验收", "收证", "证据", "v2"]
    assert tokenize("日") == ["日"]
    assert tokenize("...!!!") == []
