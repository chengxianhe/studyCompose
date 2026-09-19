from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, Contract, VerificationCase
from govplatform.contract.service import (
    ContractStateError,
    ContractValidationError,
    SensitiveContentError,
)
from govplatform.identity.models import Principal, PrincipalNotAllowedError

router = APIRouter(prefix="/contracts", tags=["contracts"])


class CreateContractRequest(BaseModel):
    title: str
    goal: str
    scope: str
    caller: Principal
    out_of_scope: str | None = None
    acceptance_criteria: list[AcceptanceCriterion] | None = None
    test_cases: list[VerificationCase] | None = None
    knowledge_refs: list[str] | None = None
    risks: list[str] | None = None
    open_questions: list[str] | None = None


class UpdateContractRequest(BaseModel):
    caller: Principal
    title: str | None = None
    goal: str | None = None
    scope: str | None = None
    out_of_scope: str | None = None
    acceptance_criteria: list[AcceptanceCriterion] | None = None
    test_cases: list[VerificationCase] | None = None
    knowledge_refs: list[str] | None = None
    risks: list[str] | None = None
    open_questions: list[str] | None = None


class FreezeContractRequest(BaseModel):
    caller: Principal


class GetContractRequest(BaseModel):
    caller: Principal


@router.post("", response_model=Contract)
def create_contract(request: CreateContractRequest) -> Contract:
    try:
        return contract_service.create(
            title=request.title,
            goal=request.goal,
            scope=request.scope,
            caller=request.caller,
            out_of_scope=request.out_of_scope,
            acceptance_criteria=request.acceptance_criteria,
            test_cases=request.test_cases,
            knowledge_refs=request.knowledge_refs,
            risks=request.risks,
            open_questions=request.open_questions,
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SensitiveContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{contract_id}", response_model=Contract)
def update_contract(contract_id: str, request: UpdateContractRequest) -> Contract:
    try:
        return contract_service.update(
            contract_id=contract_id,
            caller=request.caller,
            title=request.title,
            goal=request.goal,
            scope=request.scope,
            out_of_scope=request.out_of_scope,
            acceptance_criteria=request.acceptance_criteria,
            test_cases=request.test_cases,
            knowledge_refs=request.knowledge_refs,
            risks=request.risks,
            open_questions=request.open_questions,
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ContractStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SensitiveContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{contract_id}/freeze", response_model=Contract)
def freeze_contract(contract_id: str, request: FreezeContractRequest) -> Contract:
    try:
        return contract_service.freeze(contract_id=contract_id, caller=request.caller)
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ContractStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ContractValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# 用 POST 而不是标准的 GET——GET 没有请求体，没法带上结构化的 caller
# （跟 knowledge.search 用 POST 而不是 GET 是同一个原因）。
@router.post("/{contract_id}/get", response_model=Contract | None)
def get_contract(contract_id: str, request: GetContractRequest) -> Contract | None:
    return contract_service.get(contract_id, caller=request.caller)
