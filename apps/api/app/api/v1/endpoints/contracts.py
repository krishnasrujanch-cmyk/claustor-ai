"""Claustor AI — Contract Endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.domain.schemas.contract import (
    ContractDetailOut, ContractListOut, ContractOut,
    ContractUploadResponse, ProcessingStatus,
)
from app.infrastructure.database.session import get_db
from app.services.contract_service import ContractService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ContractUploadResponse, status_code=202)
async def upload_contract(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.can_upload:
        raise HTTPException(status_code=403, detail="Role cannot upload contracts")
    file_bytes = await file.read()
    service = ContractService(db)
    await service.check_contract_limit(user.org_id, user.plan)
    service.validate_file(file.filename or "contract.pdf", file_bytes, file.content_type)
    contract, queue_pos = await service.create_and_queue(
        org_id=user.org_id, user_id=user.id,
        filename=file.filename or "contract.pdf",
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/pdf",
    )
    wait_times = {"free": 900, "starter": 1800, "professional": 600, "enterprise": 120}
    return ContractUploadResponse(
        contract_id=contract.id, status="queued",
        message="Contract uploaded. AI analysis in progress.",
        queue_position=queue_pos,
        estimated_wait_seconds=wait_times.get(user.plan, 900),
    )


@router.get("/", response_model=ContractListOut)
async def list_contracts(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    risk_level: str | None = Query(None),
    search: str | None = Query(None),
):
    service = ContractService(db)
    contracts, total = await service.list_contracts(
        org_id=user.org_id, page=page, page_size=page_size,
        status_filter=status_filter, risk_level=risk_level, search=search,
    )
    return ContractListOut(
        contracts=[ContractOut.model_validate(c) for c in contracts],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{contract_id}/status", response_model=ProcessingStatus)
async def get_status(
    contract_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContractService(db)
    result = await service.get_processing_status(contract_id=contract_id, org_id=user.org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contract not found")
    return result


@router.get("/{contract_id}", response_model=ContractDetailOut)
async def get_contract(
    contract_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContractService(db)
    contract = await service.get_contract(contract_id=contract_id, org_id=user.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractDetailOut.model_validate(contract)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_admin and user.role != "contract_manager":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    service = ContractService(db)
    deleted = await service.delete_contract(contract_id=contract_id, org_id=user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")
