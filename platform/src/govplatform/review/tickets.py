"""单进程审核页的一次性表单票据；避免双击或重试重复产生治理动作。"""

import secrets
import threading
import time
from collections import OrderedDict


class FormTickets:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: OrderedDict[str, tuple[str, str, float]] = OrderedDict()

    def issue(self, action: str, snapshot: str) -> str:
        ticket = secrets.token_urlsafe(32)
        with self._lock:
            self._pending[ticket] = (action, snapshot, time.monotonic() + 3600)
            while len(self._pending) > 1000:
                self._pending.popitem(last=False)
        return ticket

    def consume(self, ticket: str, action: str, snapshot: str) -> bool:
        with self._lock:
            expected = self._pending.get(ticket)
            if expected is None or expected[:2] != (action, snapshot):
                return False
            del self._pending[ticket]
            return expected[2] >= time.monotonic()
