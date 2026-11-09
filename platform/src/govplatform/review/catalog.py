from __future__ import annotations

from govplatform.contract import service as contracts
from govplatform.contract.models import Contract
from govplatform.db.connection import get_connection
from govplatform.harness import service as harness
from govplatform.harness.models import HarnessRun
from govplatform.identity.models import Human


def task_catalog(caller: Human) -> tuple[list[Contract], list[HarnessRun]]:
    # 本机页完整显示历史；对象详情沿用原服务的身份校验和审计。
    with get_connection() as conn:
        contract_ids = [
            row[0]
            for row in conn.execute("SELECT contract_id FROM contracts ORDER BY created_at DESC")
        ]
        run_ids = [
            row[0]
            for row in conn.execute("SELECT run_id FROM harness_runs ORDER BY created_at DESC")
        ]
    return (
        [obj for key in contract_ids if (obj := contracts.get(key, caller=caller)) is not None],
        [run for key in run_ids if (run := harness.get(key, caller=caller)) is not None],
    )
