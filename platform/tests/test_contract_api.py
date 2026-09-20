from __future__ import annotations

from fastapi.testclient import TestClient

from govplatform.api.app import create_app

_CLAUDE_CODE_CALLER = {
    "principal_type": "agent",
    "kind": "claude-code",
    "session_id": "api-test",
}
_OWNER_CALLER = {"principal_type": "human", "id": "chengxianhe0@gmail.com"}


def test_freeze_requires_human_owner() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/contracts",
        json={
            "title": "API 起草的契约",
            "goal": "目标",
            "scope": "范围",
            "caller": _CLAUDE_CODE_CALLER,
            "acceptance_criteria": [
                {
                    "ac_id": "AC-1",
                    "precondition": "前置条件",
                    "action": "操作步骤",
                    "input": "输入数据",
                    "expected_result": "预期结果",
                    "verification_type": "automated_test",
                    "test_case_ids": ["TC-1"],
                }
            ],
            "test_cases": [{"tc_id": "TC-1", "description": "用例"}],
        },
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["contract_id"]

    agent_freeze = client.post(
        f"/contracts/{contract_id}/freeze", json={"caller": _CLAUDE_CODE_CALLER}
    )
    assert agent_freeze.status_code == 403

    owner_freeze = client.post(f"/contracts/{contract_id}/freeze", json={"caller": _OWNER_CALLER})
    assert owner_freeze.status_code == 200
    assert owner_freeze.json()["status"] == "frozen"

    get_response = client.post(f"/contracts/{contract_id}/get", json={"caller": _OWNER_CALLER})
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "frozen"


def test_freeze_rejects_incomplete_contract_with_422() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/contracts",
        json={"title": "空契约", "goal": "目标", "scope": "范围", "caller": _CLAUDE_CODE_CALLER},
    )
    contract_id = create_response.json()["contract_id"]

    freeze_response = client.post(
        f"/contracts/{contract_id}/freeze", json={"caller": _OWNER_CALLER}
    )
    assert freeze_response.status_code == 422


def test_update_rejects_stale_version_with_409() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/contracts",
        json={
            "title": "并发编辑测试",
            "goal": "目标",
            "scope": "范围",
            "caller": _CLAUDE_CODE_CALLER,
        },
    )
    contract_id = create_response.json()["contract_id"]

    first_update = client.put(
        f"/contracts/{contract_id}",
        json={"caller": _CLAUDE_CODE_CALLER, "expected_version": 1, "title": "第一次修改"},
    )
    assert first_update.status_code == 200
    assert first_update.json()["version"] == 2

    stale_update = client.put(
        f"/contracts/{contract_id}",
        json={"caller": _CLAUDE_CODE_CALLER, "expected_version": 1, "title": "基于旧版本的修改"},
    )
    assert stale_update.status_code == 409
