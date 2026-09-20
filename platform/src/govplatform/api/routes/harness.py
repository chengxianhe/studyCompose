from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.harness.service import HarnessStateError
from govplatform.identity.models import Principal, PrincipalNotAllowedError

router = APIRouter(prefix="/harness-runs", tags=["harness"])


class StartRunRequest(BaseModel):
    contract_id: str
    caller: Principal


class RecordEntryGateRequest(BaseModel):
    caller: Principal
    passed: bool
    command: str
    summary: str


class RecordAcceptanceRequest(BaseModel):
    caller: Principal
    results: list[AcceptanceResult]


class DeliverRequest(BaseModel):
    caller: Principal


class GetRunRequest(BaseModel):
    caller: Principal


@router.post("", response_model=HarnessRun)
def start_run(request: StartRunRequest) -> HarnessRun:
    try:
        return harness_service.start(contract_id=request.contract_id, caller=request.caller)
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HarnessStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/entry-gate", response_model=HarnessRun)
def record_entry_gate(run_id: str, request: RecordEntryGateRequest) -> HarnessRun:
    try:
        return harness_service.record_entry_gate(
            run_id=run_id,
            caller=request.caller,
            passed=request.passed,
            command=request.command,
            summary=request.summary,
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HarnessStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/acceptance", response_model=HarnessRun)
def record_acceptance(run_id: str, request: RecordAcceptanceRequest) -> HarnessRun:
    try:
        return harness_service.record_acceptance(
            run_id=run_id, caller=request.caller, results=request.results
        )
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HarnessStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/deliver", response_model=HarnessRun)
def deliver_run(run_id: str, request: DeliverRequest) -> HarnessRun:
    try:
        return harness_service.deliver(run_id=run_id, caller=request.caller)
    except PrincipalNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HarnessStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/get", response_model=HarnessRun | None)
def get_run(run_id: str, request: GetRunRequest) -> HarnessRun | None:
    return harness_service.get(run_id, caller=request.caller)
