from __future__ import annotations

from html import escape

from pydantic import BaseModel

from govplatform.fingerprints import fingerprint as fingerprint
from govplatform.review.tickets import FormTickets


def form(
    action: str,
    label: str,
    token: str,
    obj: BaseModel,
    tickets: FormTickets,
    fields_html: str = "",
) -> str:
    snapshot = fingerprint(obj)
    ticket = tickets.issue(action, snapshot)
    return (
        f'<form method="post" action="{escape(action, quote=True)}">'
        f'<input type="hidden" name="csrf" value="{escape(token, quote=True)}">'
        f'<input type="hidden" name="snapshot" value="{snapshot}">'
        f'<input type="hidden" name="ticket" value="{ticket}">'
        f"{fields_html}"
        f'<button type="submit">{escape(label)}</button></form>'
    )


def document(title: str, content: str) -> str:
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><style>
body{{font:16px/1.65 system-ui;margin:32px auto;padding:0 24px;max-width:1000px;color:#213047}}
a{{color:#175bb0}} article{{border:1px solid #ccd5df;border-radius:12px;padding:20px;margin:20px 0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f8;padding:16px}}
button{{padding:10px 18px;background:#175bb0;color:white;border:0;border-radius:8px;cursor:pointer}}
textarea{{display:block;width:95%;min-height:90px;margin:8px 0}} fieldset{{margin:16px 0}}
small{{color:#556}} nav{{display:flex;gap:24px}} form{{margin-top:20px}}
</style><nav><a href="/">知识审核</a><a href="/graph">来源与关系</a>
<a href="/tasks">任务契约与验收</a></nav>
<h1>{escape(title)}</h1>{content}</html>"""


def detail(obj: BaseModel) -> str:
    return f"<pre>{escape(obj.model_dump_json(indent=2))}</pre>"
