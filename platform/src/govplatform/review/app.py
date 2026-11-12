from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from govplatform.backup import create_backup
from govplatform.config import OWNER_HUMAN_ID, db_path
from govplatform.contract import service as contracts
from govplatform.harness import service as harness
from govplatform.harness.cancellation_service import cancel
from govplatform.harness.models import HarnessRun, HarnessStatus
from govplatform.identity.models import Human
from govplatform.knowledge import service as knowledge
from govplatform.knowledge.models import KnowledgeStatus
from govplatform.knowledge.query_service import get_knowledge, list_knowledge
from govplatform.review.acceptance import acceptance_form, parse_results
from govplatform.review.catalog import task_catalog
from govplatform.review.graph import register_graph_routes
from govplatform.review.task_controls import task_controls
from govplatform.review.tickets import FormTickets
from govplatform.review.views import detail, document, fingerprint, form


def create_review_app() -> FastAPI:
    # 独立 app：不挂载信任 caller 自报身份的原型 JSON API。
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    token = secrets.token_urlsafe(32)
    owner = Human(id=OWNER_HUMAN_ID)
    tickets = FormTickets()
    register_graph_routes(app, owner, token, tickets)

    @app.middleware("http")
    async def local_only(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.client is None or request.client.host not in ("127.0.0.1", "::1"):
            return HTMLResponse("仅允许本机访问", status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    def index(status: KnowledgeStatus | None = None, offset: int = Query(default=0, ge=0)) -> str:
        page = list_knowledge(caller=owner, status=status, offset=offset)
        content = (
            "<p>逐条阅读后批准。待审内容不会进入搜索；批准 reference 也不会升级为项目硬规则。"
            "每次操作前自动备份。此页仅供你本人使用，Agent 不得代点批准。</p>"
            '<p><a href="/?status=in_review">待审核</a> · '
            '<a href="/?status=active">已批准</a> · <a href="/">全部</a></p>'
            f"<p>共 {page.total} 条</p>"
        )
        for obj in page.items:
            content += (
                f'<article><a href="/knowledge/{obj.knowledge_id}">'
                f"{escape(obj.title)}</a><br><small>{obj.status.value} · "
                f"{obj.authority_level.value} · v{obj.version}</small></article>"
            )
        if offset + page.limit < page.total:
            suffix = f"&status={status.value}" if status else ""
            content += f'<a href="/?offset={offset + page.limit}{suffix}">下一页</a>'
        return document("知识审核", content)

    @app.get("/knowledge/{key}", response_class=HTMLResponse)
    def knowledge_detail(key: str) -> str:
        obj = get_knowledge(knowledge_id=key, caller=owner)
        if obj is None:
            raise HTTPException(404, "知识不存在")
        content = (
            f"<p>状态：{obj.status.value} · 类型：{obj.type.value} · "
            f"权威级别：{obj.authority_level.value} · 版本：{obj.version}</p>"
            f"<h2>正文</h2><pre>{escape(obj.body)}</pre>"
            f"<h2>来源</h2><pre>{escape(obj.source)}</pre>"
            f"<p>生效时间：{obj.effective_at or '批准后'} · "
            f"失效时间：{obj.expire_at or '未设置'}</p>"
            f"<small>ID：{obj.knowledge_id}<br>内容摘要：{obj.content_hash}</small>"
        )
        if obj.status == KnowledgeStatus.IN_REVIEW:
            content += form(
                f"/actions/approve/{key}", "我已阅读，批准这条知识", token, obj, tickets
            )
        elif obj.status == KnowledgeStatus.ACTIVE:
            content += form(
                f"/actions/deprecate/{key}",
                "确认废弃，停止用于检索",
                token,
                obj,
                tickets,
                '<label>废弃理由<textarea name="reason" maxlength="4000" required>'
                "</textarea></label>",
            )
        return document(obj.title, content)

    @app.get("/tasks", response_class=HTMLResponse)
    def tasks() -> str:
        contract_list, runs = task_catalog(owner)
        content = (
            "<p>先冻结已确认的契约，再单独启动运行。启动只创建记录，由 Agent 执行实际任务。</p>"
        )
        for contract in contract_list:
            content += f"<article><h2>{escape(contract.title)}</h2>{detail(contract)}"
            content += task_controls(contract, runs, token, tickets)
            content += "</article>"
        for run in runs:
            contract = next(c for c in contract_list if c.contract_id == run.contract_id)
            content += (
                f'<article id="run-{run.run_id}">'
                f"<h2>{escape(contract.title)} · {run.status.value}</h2>"
                f"<p>运行 ID：{run.run_id}</p>{detail(run)}"
            )
            if run.status in (HarnessStatus.ACCEPTING, HarnessStatus.WAITING_FOR_HUMAN):
                contract = next(c for c in contract_list if c.contract_id == run.contract_id)
                content += acceptance_form(run, contract, token, tickets)
            if run.status == HarnessStatus.PASSED:
                content += form(f"/actions/deliver/{run.run_id}", "确认交付", token, run, tickets)
            if run.status not in (
                HarnessStatus.DELIVERED,
                HarnessStatus.ESCALATED,
                HarnessStatus.CANCELLED,
            ):
                content += form(
                    f"/actions/cancel/{run.run_id}",
                    "取消这次运行",
                    token,
                    run,
                    tickets,
                    '<label>取消原因<textarea name="reason" maxlength="4000" required>'
                    "</textarea></label>",
                )
            content += "</article>"
        return document("任务契约与验收", content)

    @app.post("/actions/{action}/{key}")
    async def act(action: str, key: str, request: Request) -> RedirectResponse:
        origin = request.headers.get("origin")
        if origin is not None and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "拒绝跨站操作")
        body = await request.body()
        if len(body) > 131072:
            raise HTTPException(413, "请求过大")
        try:
            fields = parse_qs(body.decode("utf-8"), max_num_fields=200)
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(400, "无法读取表单") from exc
        if any(len(values) != 1 for values in fields.values()):
            raise HTTPException(400, "表单字段重复")
        if not secrets.compare_digest(fields.get("csrf", [""])[0], token):
            raise HTTPException(403, "页面已过期，请刷新")
        obj: BaseModel | None
        selected_run: HarnessRun | None = None
        version: int | None = None
        if action in ("approve", "deprecate"):
            obj = get_knowledge(knowledge_id=key, caller=owner)
        elif action in ("freeze", "start"):
            contract = contracts.get(key, caller=owner)
            obj = contract
            version = contract.version if contract else None
        elif action in ("deliver", "accept", "cancel"):
            selected_run = harness.get(key, caller=owner)
            obj = selected_run
        else:
            raise HTTPException(404, "未知操作")
        if obj is None:
            raise HTTPException(404, "对象不存在")
        if fields.get("snapshot", [""])[0] != fingerprint(obj):
            raise HTTPException(409, "内容已变化，请刷新并重新阅读")
        if not tickets.consume(
            fields.get("ticket", [""])[0],
            f"/actions/{action}/{key}",
            fingerprint(obj),
        ):
            raise HTTPException(409, "表单已提交或过期，请刷新后重新操作")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        create_backup(db_path(), db_path().parent / "backups" / f"{stamp}-{secrets.token_hex(4)}")
        try:
            if action == "approve":
                knowledge.approve(knowledge_id=key, caller=owner)
            elif action == "deprecate":
                knowledge.deprecate(
                    knowledge_id=key, caller=owner, reason=fields.get("reason", [""])[0]
                )
            elif action == "freeze":
                contracts.freeze(contract_id=key, caller=owner, expected_version=version)
            elif action == "start":
                harness.start(contract_id=key, caller=owner)
            elif action == "cancel":
                assert selected_run is not None
                cancel(
                    run_id=key,
                    caller=owner,
                    reason=fields.get("reason", [""])[0],
                    expected_updated_at=selected_run.updated_at,
                )
            elif action == "accept":
                run = harness.get(key, caller=owner)
                assert run is not None
                # 再读后的状态也要匹配页面；服务端 CAS 防止后续并发覆盖。
                if fingerprint(run) != fields.get("snapshot", [""])[0]:
                    raise harness.HarnessStateError("运行已变化，请重新审核")
                contract = contracts.get(run.contract_id, caller=owner)
                assert contract is not None
                harness.record_acceptance(
                    run_id=key,
                    caller=owner,
                    results=parse_results(fields, contract),
                    manual_only=True,
                    expected_updated_at=run.updated_at,
                )
            else:
                harness.deliver(run_id=key, caller=owner)
        except (
            knowledge.ApprovalError,
            knowledge.KnowledgeStateError,
            knowledge.SensitiveContentError,
            contracts.ContractStateError,
            contracts.ContractConflictError,
            contracts.ContractValidationError,
            harness.HarnessStateError,
        ) as exc:
            raise HTTPException(409, str(exc)) from exc
        return RedirectResponse(
            "/" if action in ("approve", "deprecate") else "/tasks",
            status_code=303,
        )

    return app
