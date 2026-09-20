from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from govplatform.harness.models import (
    AcceptanceResult,
    GateResult,
    HarnessRun,
    HarnessStatus,
    RepairRound,
)


def insert(conn: sqlite3.Connection, run: HarnessRun) -> None:
    conn.execute(
        """
        INSERT INTO harness_runs (
            run_id, contract_id, status, repair_round,
            entry_gate_results_json, acceptance_results_json,
            repair_rounds_json, escalation_reason, started_by,
            created_at, updated_at, delivered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _params(run),
    )


def update(conn: sqlite3.Connection, run: HarnessRun) -> None:
    conn.execute(
        """
        UPDATE harness_runs SET
            contract_id = ?, status = ?, repair_round = ?,
            entry_gate_results_json = ?, acceptance_results_json = ?,
            repair_rounds_json = ?, escalation_reason = ?, started_by = ?,
            created_at = ?, updated_at = ?, delivered_at = ?
        WHERE run_id = ?
        """,
        (*_params(run)[1:], run.run_id),
    )


def get(conn: sqlite3.Connection, run_id: str) -> HarnessRun | None:
    row = conn.execute("SELECT * FROM harness_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return _row_to_run(row)


def _params(run: HarnessRun) -> tuple[object, ...]:
    return (
        run.run_id,
        run.contract_id,
        run.status.value,
        run.repair_round,
        json.dumps([g.model_dump(mode="json") for g in run.entry_gate_results]),
        json.dumps([a.model_dump(mode="json") for a in run.acceptance_results]),
        json.dumps([r.model_dump(mode="json") for r in run.repair_rounds]),
        run.escalation_reason,
        run.started_by,
        run.created_at.isoformat(),
        run.updated_at.isoformat(),
        run.delivered_at.isoformat() if run.delivered_at else None,
    )


def _row_to_run(row: sqlite3.Row) -> HarnessRun:
    return HarnessRun(
        run_id=row["run_id"],
        contract_id=row["contract_id"],
        status=HarnessStatus(row["status"]),
        repair_round=row["repair_round"],
        entry_gate_results=[GateResult(**g) for g in json.loads(row["entry_gate_results_json"])],
        acceptance_results=[
            AcceptanceResult(**a) for a in json.loads(row["acceptance_results_json"])
        ],
        repair_rounds=[RepairRound(**r) for r in json.loads(row["repair_rounds_json"])],
        escalation_reason=row["escalation_reason"],
        started_by=row["started_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        delivered_at=datetime.fromisoformat(row["delivered_at"]) if row["delivered_at"] else None,
    )
