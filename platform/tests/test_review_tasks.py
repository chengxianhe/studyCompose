from __future__ import annotations

import re
import sqlite3

import pytest
from fastapi.testclient import TestClient
from gate_fixtures import record_fixture_gate

from govplatform.contract import freeze_service, service, store
from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    ContractStatus,
    VerificationCase,
    VerificationType,
)
from govplatform.db.connection import get_connection
from govplatform.harness import service as harness
from govplatform.harness.models import AcceptanceResult, HarnessStatus
from govplatform.identity.models import Agent, Human
from govplatform.review.app import create_review_app


@pytest.fixture
def contract(codex_agent: Agent) -> Contract:
    return service.create(
        title="测试任务",
        goal="验证审核闭环",
        scope="测试数据库",
        caller=codex_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="存在草稿",
                action="确认范围",
                input="测试数据",
                expected_result="可追踪任务运行",
                verification_type=VerificationType.AUTOMATED_TEST,
                test_case_ids=["TC-1"],
            )
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="测试闭环")],
    )


def submit(client: TestClient, action: str) -> int:
    page = client.get("/tasks").text
    matched = re.search(rf'<form method="post" action="{action}">(.*?)</form>', page, re.S)
    assert matched is not None
    fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', matched[1]))
    return client.post(action, data=fields, follow_redirects=False).status_code


def test_human_task_controls(contract: Contract, codex_agent: Agent) -> None:
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 123)
    ) as client:
        assert submit(client, f"/actions/freeze/{contract.contract_id}") == 303
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM harness_runs").fetchone()[0] == 0
        assert submit(client, f"/actions/start/{contract.contract_id}") == 303
        with get_connection() as conn:
            run_id = conn.execute("SELECT run_id FROM harness_runs").fetchone()[0]
        record_fixture_gate(
            run_id=run_id,
            caller=codex_agent,
            passed=True,
            command="fixture",
            summary="test evidence",
        )
        harness.record_acceptance(
            run_id=run_id,
            caller=codex_agent,
            results=[
                AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="fixture passed")
            ],
        )
        assert submit(client, f"/actions/deliver/{run_id}") == 303
        run = harness.get(run_id, caller=codex_agent)
        assert run is not None and run.status == HarnessStatus.DELIVERED


def test_freeze_stale_version_rejected(
    contract: Contract, codex_agent: Agent, owner_human: Human
) -> None:
    service.update(
        contract_id=contract.contract_id, caller=codex_agent, expected_version=1, scope="new scope"
    )
    with pytest.raises(service.ContractConflictError):
        service.freeze(contract_id=contract.contract_id, caller=owner_human, expected_version=1)


def test_freeze_does_not_overwrite_concurrent_update(
    contract: Contract,
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = store.update

    def raced(
        conn: sqlite3.Connection, obj: Contract, *, expected_version: int | None = None
    ) -> bool:
        service.update(
            contract_id=contract.contract_id,
            caller=codex_agent,
            expected_version=1,
            scope="concurrent scope",
        )
        return original(conn, obj, expected_version=expected_version)

    # 只替换 freeze 看到的 store 对象，避免同时拦截 update_service 的写入。
    from types import SimpleNamespace

    monkeypatch.setattr(freeze_service, "contract_store", SimpleNamespace(update=raced))
    with pytest.raises(service.ContractConflictError):
        service.freeze(contract_id=contract.contract_id, caller=owner_human)
    current = service.get(contract.contract_id, caller=codex_agent)
    assert current is not None and current.scope == "concurrent scope"
    assert current.status == ContractStatus.DRAFT


def test_draft_write_cannot_unfreeze_contract(contract: Contract, owner_human: Human) -> None:
    service.freeze(contract_id=contract.contract_id, caller=owner_human)
    with get_connection() as conn:
        assert not store.update(conn, contract, expected_version=1)


def test_repeated_start_form_creates_only_one_run(contract: Contract, owner_human: Human) -> None:
    service.freeze(contract_id=contract.contract_id, caller=owner_human)
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 123)
    ) as client:
        page = client.get("/tasks").text
        fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', page))
        action = f"/actions/start/{contract.contract_id}"
        assert client.post(action, data=fields, follow_redirects=False).status_code == 303
        assert client.post(action, data=fields, follow_redirects=False).status_code == 409
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM harness_runs").fetchone()[0] == 1
        # 刷新新表单也不能误开第二条活动运行。
        assert submit(client, action) == 409
