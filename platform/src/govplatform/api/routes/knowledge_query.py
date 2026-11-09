from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from govplatform.identity.models import Principal, PrincipalNotAllowedError
from govplatform.knowledge.models import KnowledgeObject, KnowledgeStatus
from govplatform.knowledge.query_service import KnowledgePage, get_knowledge, list_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ListRequest(BaseModel):
    caller: Principal
    status: KnowledgeStatus | None = KnowledgeStatus.IN_REVIEW
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class GetRequest(BaseModel):
    caller: Principal


@router.post("/list")
def list_objects(request: ListRequest) -> KnowledgePage:
    try:
        return list_knowledge(
            caller=request.caller, status=request.status, offset=request.offset, limit=request.limit
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/{knowledge_id}/get")
def get_object(knowledge_id: str, request: GetRequest) -> KnowledgeObject | None:
    try:
        return get_knowledge(knowledge_id=knowledge_id, caller=request.caller)
    except PrincipalNotAllowedError as exc:
        raise HTTPException(403, str(exc)) from exc
