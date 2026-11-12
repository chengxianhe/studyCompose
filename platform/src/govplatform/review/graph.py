from __future__ import annotations

import secrets
from datetime import UTC, datetime
from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from govplatform.backup import create_backup
from govplatform.config import db_path
from govplatform.graph import query_service, review_service
from govplatform.graph.models import GraphError, Relation, ReviewSnapshot, SourceRevision
from govplatform.identity.models import Human
from govplatform.review.tickets import FormTickets
from govplatform.review.views import detail, document, fingerprint, form


def register_graph_routes(app: FastAPI, owner: Human, token: str, tickets: FormTickets) -> None:
    @app.get("/graph", response_class=HTMLResponse)
    def catalog(offset: int = Query(default=0, ge=0, le=100000)) -> str:
        page = query_service.list_records(caller=owner, offset=offset)
        content = (
            "<p>关系需逐条审核。来源由调用方登记，尚未联网核验。"
            "潜在影响不等于知识失效；批准替代关系不会自动废弃旧知识。</p>"
            '<p><a href="/graph/sources">来源版本目录</a></p>'
        )
        for item in page.items:
            assert isinstance(item, Relation)
            content += (
                f'<article><a href="/graph/relations/{item.relation_id}">'
                f"{item.kind} · {item.status}</a><p>{escape(item.reason)}</p></article>"
            )
        if page.has_more:
            content += f'<a href="/graph?offset={offset + page.limit}">下一页</a>'
        return document("来源与关系审核", content)

    @app.get("/graph/sources", response_class=HTMLResponse)
    def source_catalog(offset: int = Query(default=0, ge=0, le=100000)) -> str:
        page = query_service.list_records(caller=owner, kind="source", offset=offset)
        content = "<p>登记时间不表示语义版本的新旧；缺少摘要的来源无法核对具体正文。</p>"
        for item in page.items:
            assert isinstance(item, SourceRevision)
            content += (
                f'<article><a href="/graph/sources/{item.source_id}">'
                f"{escape(item.locator)}</a> · {escape(item.version_label or '版本未知')}"
                "</article>"
            )
        if page.has_more:
            content += f'<a href="/graph/sources?offset={offset + page.limit}">下一页</a>'
        return document("来源版本", content)

    @app.get("/graph/sources/{key}", response_class=HTMLResponse)
    def source_detail(key: str) -> str:
        obj = query_service.get(key=key, kind="source", caller=owner)
        if not isinstance(obj, SourceRevision):
            raise HTTPException(404, "来源不存在")
        return document("来源版本记录", "<p>调用方登记，未联网核验。</p>" + detail(obj))

    @app.get("/graph/relations/{key}", response_class=HTMLResponse)
    def relation_detail(key: str) -> str:
        obj = query_service.get(key=key, kind="relation", caller=owner)
        if not isinstance(obj, ReviewSnapshot):
            raise HTTPException(404, "关系不存在")
        content = (
            f"<p>关系：{obj.relation.kind} · 状态：{obj.relation.status}</p>"
            f"<h2>理由</h2><pre>{escape(obj.relation.reason)}</pre>"
            f"<h2>适用范围</h2><pre>{escape(obj.relation.applicability)}</pre>"
            "<h2>关联知识</h2>"
        )
        for state in obj.knowledge_states:
            content += (
                f'<p><a href="/knowledge/{escape(str(state["id"]), quote=True)}">'
                f'{escape(str(state["title"]))}</a> · {escape(str(state["status"]))}'
                f' · 版本 {state["version"]} · 当前有效：{state["valid"]}</p>'
            )
        content += ("<h2>来源证据</h2><p>请核对原始材料及适用范围；"
                    "来源由调用方登记，未联网核验。</p>")
        for source in obj.sources:
            content += (
                f'<p><a href="/graph/sources/{source.source_id}">{escape(source.locator)}</a>'
                f' · {escape(source.version_label or "版本未知")}</p>'
            )
        content += "<details><summary>查看绑定摘要与审计字段</summary>" + detail(obj) + "</details>"
        if obj.relation.status == "in_review":
            content += form(
                f"/graph/actions/approve/{key}", "我已核对证据，批准关系", token, obj, tickets
            )
        if obj.relation.status != "revoked":
            content += form(
                f"/graph/actions/revoke/{key}",
                "撤销这条关系",
                token,
                obj,
                tickets,
                '<label>理由<textarea name="reason" maxlength="4000" required></textarea></label>',
            )
        return document("关系审核", content)

    @app.post("/graph/actions/{action}/{key}")
    async def act(action: str, key: str, request: Request) -> RedirectResponse:
        origin = request.headers.get("origin")
        if origin is not None and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "拒绝跨站操作")
        body = await request.body()
        if len(body) > 32768:
            raise HTTPException(413, "请求过大")
        try:
            fields = parse_qs(body.decode("utf-8"), max_num_fields=5)
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(400, "无法读取表单") from exc
        if any(len(v) != 1 for v in fields.values()):
            raise HTTPException(400, "表单字段重复")
        if not secrets.compare_digest(fields.get("csrf", [""])[0], token):
            raise HTTPException(403, "页面已过期，请刷新")
        if action not in ("approve", "revoke"):
            raise HTTPException(404, "未知操作")
        obj = query_service.get(key=key, kind="relation", caller=owner)
        if not isinstance(obj, ReviewSnapshot):
            raise HTTPException(404, "关系不存在")
        expected = fields.get("snapshot", [""])[0]
        if expected != fingerprint(obj) or not tickets.consume(
            fields.get("ticket", [""])[0], f"/graph/actions/{action}/{key}", expected
        ):
            raise HTTPException(409, "对象或表单已变化，请刷新并重新阅读")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        create_backup(db_path(), db_path().parent / "backups" / f"{stamp}-{secrets.token_hex(4)}")
        try:
            review_service.review(
                relation_id=key,
                caller=owner,
                expected_snapshot=expected,
                action=action,
                reason=fields.get("reason", [""])[0],
            )
        except GraphError as exc:
            raise HTTPException(409, str(exc)) from exc
        return RedirectResponse(f"/graph/relations/{key}", status_code=303)
