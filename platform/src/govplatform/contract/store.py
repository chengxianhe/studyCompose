from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    ContractStatus,
    KnowledgeSnapshot,
    VerificationCase,
)
from govplatform.identity.models import Agent, Human, Principal


def insert(conn: sqlite3.Connection, contract: Contract) -> None:
    conn.execute(
        """
        INSERT INTO contracts (
            contract_id, title, goal, scope, out_of_scope, author_json,
            status, version, acceptance_criteria_json, test_cases_json,
            knowledge_refs_json, knowledge_snapshots_json, risks_json,
            open_questions_json, frozen_by, frozen_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _params(contract),
    )


def update(conn: sqlite3.Connection, contract: Contract) -> None:
    conn.execute(
        """
        UPDATE contracts SET
            title = ?, goal = ?, scope = ?, out_of_scope = ?, author_json = ?,
            status = ?, version = ?, acceptance_criteria_json = ?,
            test_cases_json = ?, knowledge_refs_json = ?,
            knowledge_snapshots_json = ?, risks_json = ?, open_questions_json = ?,
            frozen_by = ?, frozen_at = ?, created_at = ?, updated_at = ?
        WHERE contract_id = ?
        """,
        (*_params(contract)[1:], contract.contract_id),
    )


def get(conn: sqlite3.Connection, contract_id: str) -> Contract | None:
    row = conn.execute("SELECT * FROM contracts WHERE contract_id = ?", (contract_id,)).fetchone()
    if row is None:
        return None
    return _row_to_contract(row)


def _params(contract: Contract) -> tuple[object, ...]:
    return (
        contract.contract_id,
        contract.title,
        contract.goal,
        contract.scope,
        contract.out_of_scope,
        contract.author.model_dump_json(),
        contract.status.value,
        contract.version,
        json.dumps([ac.model_dump(mode="json") for ac in contract.acceptance_criteria]),
        json.dumps([tc.model_dump(mode="json") for tc in contract.test_cases]),
        json.dumps(contract.knowledge_refs),
        json.dumps([ks.model_dump(mode="json") for ks in contract.knowledge_snapshots]),
        json.dumps(contract.risks),
        json.dumps(contract.open_questions),
        contract.frozen_by,
        contract.frozen_at.isoformat() if contract.frozen_at else None,
        contract.created_at.isoformat(),
        contract.updated_at.isoformat(),
    )


def _row_to_contract(row: sqlite3.Row) -> Contract:
    author_data = json.loads(row["author_json"])
    author: Principal = (
        Human(**author_data) if author_data["principal_type"] == "human" else Agent(**author_data)
    )
    return Contract(
        contract_id=row["contract_id"],
        title=row["title"],
        goal=row["goal"],
        scope=row["scope"],
        out_of_scope=row["out_of_scope"],
        author=author,
        status=ContractStatus(row["status"]),
        version=row["version"],
        acceptance_criteria=[
            AcceptanceCriterion(**ac) for ac in json.loads(row["acceptance_criteria_json"])
        ],
        test_cases=[VerificationCase(**tc) for tc in json.loads(row["test_cases_json"])],
        knowledge_refs=json.loads(row["knowledge_refs_json"]),
        knowledge_snapshots=[
            KnowledgeSnapshot(**ks) for ks in json.loads(row["knowledge_snapshots_json"])
        ],
        risks=json.loads(row["risks_json"]),
        open_questions=json.loads(row["open_questions_json"]),
        frozen_by=row["frozen_by"],
        frozen_at=datetime.fromisoformat(row["frozen_at"]) if row["frozen_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
