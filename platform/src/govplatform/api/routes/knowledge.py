from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from govplatform.identity.models import Principal, PrincipalNotAllowedError
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.knowledge.service import (
    ApprovalError,
    InvalidTimeRangeError,
    ProposeResponse,
    SensitiveContentError,
)
from govplatform.search import service as search_service
from govplatform.search.service import SearchResponse

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ProposeRequest(BaseModel):
    title: str
    type: KnowledgeType
    body: str
    source: str
    authority_level: AuthorityLevel
    caller: Principal
    tags: list[str] | None = None
    effective_at: datetime | None = None
    expire_at: datetime | None = None


class SearchRequest(BaseModel):
    query: str
    caller: Principal
    knowledge_type: KnowledgeType | None = None
    limit: int = 10


class ApproveRequest(BaseModel):
    caller: Principal


@router.post("/propose", response_model=ProposeResponse)
def propose_knowledge(request: ProposeRequest) -> ProposeResponse:
    try:
        obj = knowledge_service.propose(
            title=request.title,
            type=request.type,
            body=request.body,
            source=request.source,
            authority_level=request.authority_level,
            caller=request.caller,
            tags=request.tags,
            effective_at=request.effective_at,
            expire_at=request.expire_at,
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SensitiveContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidTimeRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProposeResponse(knowledge_id=obj.knowledge_id, status=obj.status, version=obj.version)


@router.post("/search", response_model=SearchResponse)
def search_knowledge(request: SearchRequest) -> SearchResponse:
    try:
        return search_service.search(
            query=request.query,
            caller=request.caller,
            knowledge_type=request.knowledge_type,
            limit=request.limit,
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{knowledge_id}/approve", response_model=ProposeResponse)
def approve_knowledge(knowledge_id: str, request: ApproveRequest) -> ProposeResponse:
    try:
        obj = knowledge_service.approve(knowledge_id=knowledge_id, caller=request.caller)
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProposeResponse(knowledge_id=obj.knowledge_id, status=obj.status, version=obj.version)
