"""contract/ 内部模块共用的东西——异常、小工具函数、不记审计的内部读取。

`service.py` 之前一个文件装了 create/update/freeze/request_waiver 全部
逻辑，超过了项目 250 行/文件的上限。拆分之后，公开 API（`contract_
service.create/update/freeze/get/request_waiver/is_ac_waived` 以及所有
异常类型）还是从 `service.py` 那一个入口暴露，调用方（api/routes、
mcp_server、harness/、测试）不用改任何 import——只是内部实现挪到了
`update_service.py`/`freeze_service.py`/`waiver_service.py` 这几个文件里，
它们都依赖这里的公共部分，`service.py` 反过来不依赖它们（避免循环
import）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from govplatform.contract import store as contract_store
from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    VerificationCase,
)
from govplatform.db.connection import get_connection
from govplatform.identity.models import Human, Principal
from govplatform.knowledge.sensitive import find_sensitive_reason


class ContractStateError(Exception):
    """在错误的状态下操作契约时抛出（比如改已冻结的、给不存在的 contract_id
    操作、豁免针对非冻结契约）。
    """


class ContractConflictError(Exception):
    """update() 时 expected_version 跟数据库里当前的版本对不上时抛出。

    契约草稿期可能有多个 Agent（或者你自己）在改，update() 是整份覆盖式
    的——不做这个检查的话，后写的会悄悄覆盖先写的，没有任何提示。调用方
    必须先 get() 拿到当前版本号，带着它来 update()，对不上就说明中间被
    别人改过了，拒绝这次写入，让调用方重新读一遍最新内容再决定怎么改，
    而不是盲目覆盖。
    """


class SensitiveContentError(Exception):
    """create()/update()/request_waiver() 因为正文疑似包含敏感信息被拒绝时抛出。"""


def now() -> datetime:
    return datetime.now(UTC)


def principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id


def sensitive_reason_in_contract(
    *,
    title: str,
    goal: str,
    scope: str,
    out_of_scope: str | None,
    acceptance_criteria: list[AcceptanceCriterion],
    test_cases: list[VerificationCase],
    risks: list[str],
    open_questions: list[str],
) -> str | None:
    ac_texts = [
        text
        for ac in acceptance_criteria
        for text in (ac.precondition, ac.action, ac.input, ac.expected_result)
    ]
    tc_texts = [tc.description for tc in test_cases]
    return find_sensitive_reason(
        title, goal, scope, out_of_scope or "", *ac_texts, *tc_texts, *risks, *open_questions
    )


def get_without_audit(contract_id: str) -> Contract | None:
    """内部/跨模块用——不记审计，因为调用方（update()/freeze()/
    request_waiver() 自身）已经在各自的操作里记了审计，不需要"读一次"
    也单独记一条。对外暴露给 MCP/HTTP 的读操作用 service.py 里的
    get()，会记审计。
    """
    with get_connection() as conn:
        return contract_store.get(conn, contract_id)
