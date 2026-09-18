from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from govplatform.config import ALLOWED_AGENT_KINDS, OWNER_HUMAN_ID


class Human(BaseModel):
    principal_type: Literal["human"] = "human"
    id: str


class Agent(BaseModel):
    principal_type: Literal["agent"] = "agent"
    kind: str
    session_id: str


Principal = Annotated[Human | Agent, Field(discriminator="principal_type")]


class PrincipalNotAllowedError(PermissionError):
    """自报的身份没通过白名单检查时抛出。"""


def resolve_principal(caller: Human | Agent) -> Human | Agent:
    if isinstance(caller, Human):
        if caller.id != OWNER_HUMAN_ID:
            raise PrincipalNotAllowedError(f"human id {caller.id!r} is not the configured owner")
        return caller
    if caller.kind not in ALLOWED_AGENT_KINDS:
        raise PrincipalNotAllowedError(f"agent kind {caller.kind!r} is not allowlisted")
    return caller
