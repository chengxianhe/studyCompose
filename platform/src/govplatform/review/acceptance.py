from html import escape

from fastapi import HTTPException

from govplatform.contract.models import Contract, VerificationType
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.review.tickets import FormTickets
from govplatform.review.views import form


def acceptance_form(run: HarnessRun, contract: Contract, token: str, tickets: FormTickets) -> str:
    fields = "<p>只填写你亲自核验的项目。待定项不会算通过；不通过会进入修复。</p>"
    count = 0
    for index, ac in enumerate(contract.acceptance_criteria):
        if ac.verification_type != VerificationType.MANUAL_EVIDENCE:
            continue
        count += 1
        fields += (
            f"<fieldset><legend>{escape(ac.ac_id)}</legend>"
            f"<p>前置：{escape(ac.precondition)}<br>操作：{escape(ac.action)}"
            f"<br>输入：{escape(ac.input)}<br>预期：{escape(ac.expected_result)}</p>"
            f'<label>结论 <select name="decision_{index}">'
            '<option value="pending">待定</option><option value="pass">通过</option>'
            '<option value="fail">不通过，需要修复</option></select></label>'
            f'<label>验证方法、实际结果及证据位置<textarea name="evidence_{index}" '
            'maxlength="4000"></textarea></label></fieldset>'
        )
    if not count:
        return ""
    return form(
        f"/actions/accept/{run.run_id}", "提交本次人工验收结论", token, run, tickets, fields
    )


def parse_results(fields: dict[str, list[str]], contract: Contract) -> list[AcceptanceResult]:
    results = []
    for index, ac in enumerate(contract.acceptance_criteria):
        if ac.verification_type != VerificationType.MANUAL_EVIDENCE:
            continue
        decision = fields.get(f"decision_{index}", ["pending"])[0]
        if decision == "pending":
            continue
        if decision not in ("pass", "fail"):
            raise HTTPException(422, "未知验收结论")
        evidence = fields.get(f"evidence_{index}", [""])[0].strip()
        if not evidence or len(evidence) > 4000:
            raise HTTPException(422, "已给结论的项目必须填写 1 至 4000 字证据")
        results.append(
            AcceptanceResult(ac_id=ac.ac_id, passed=decision == "pass", evidence_summary=evidence)
        )
    if not results:
        raise HTTPException(422, "至少填写一条人工验收结论")
    return results
