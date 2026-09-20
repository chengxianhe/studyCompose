"""harness/ 内部模块共用的东西——跟 contract/_shared.py 同样的理由：
`service.py` 单个文件超过了项目 250 行的上限，把 `record_acceptance()`
拆去了 `acceptance_service.py`，两边都要用的小工具放这里，避免循环
import。外部调用方还是只用 `from govplatform.harness import service as
harness_service`，不受影响。
"""

from __future__ import annotations

from datetime import UTC, datetime

from govplatform.identity.models import Human, Principal

# 原方案 §10.4："同一契约下最多三轮修复"。
MAX_REPAIR_ROUNDS = 3


class HarnessStateError(Exception):
    """在错误的状态下调用 start()/record_entry_gate()/record_acceptance()/
    deliver() 时抛出——比如对一份非 frozen 的契约 start()，或者入门禁还
    没过就想记录验收结果。
    """


def now() -> datetime:
    return datetime.now(UTC)


def principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id
