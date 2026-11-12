"""Show the active run beside its contract instead of offering duplicate starts."""

from govplatform.contract.models import Contract, ContractStatus
from govplatform.harness.models import HarnessRun, HarnessStatus
from govplatform.review.tickets import FormTickets
from govplatform.review.views import form

_LABELS = {
    HarnessStatus.DEVELOPING: "正在开发",
    HarnessStatus.REPAIRING: "正在修复",
    HarnessStatus.ACCEPTING: "正在检查",
    HarnessStatus.WAITING_FOR_HUMAN: "等待人工审查",
    HarnessStatus.PASSED: "检查通过，等待确认交付",
}


def task_controls(
    contract: Contract,
    runs: list[HarnessRun],
    token: str,
    tickets: FormTickets,
) -> str:
    if contract.status == ContractStatus.DRAFT:
        return form(
            f"/actions/freeze/{contract.contract_id}",
            "我已确认范围，冻结契约",
            token,
            contract,
            tickets,
        )
    active = next(
        (run for run in runs if run.contract_id == contract.contract_id and run.status in _LABELS),
        None,
    )
    if active:
        return (
            f'<p role="status">已启动 · {_LABELS[active.status]}</p>'
            f'<a href="#run-{active.run_id}">查看当前运行与下一步</a>'
        )
    return form(f"/actions/start/{contract.contract_id}", "开始一次运行", token, contract, tickets)
