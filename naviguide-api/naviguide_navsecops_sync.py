"""
NavSecOps — persist and list intelligence reports (Phase 3).

POST /sync-report — upsert report for an MR commit (Bearer auth).
GET /reports — paginated list (Bearer auth).
GET /reports/{report_id} — single report including parsed raw_analysis JSON (Bearer auth).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from naviguide_navsecops_auth import verify_navsecops_token
from naviguide_navsecops_store import get_report_by_id, list_reports, upsert_report

log = logging.getLogger("navsecops.sync")

router = APIRouter(tags=["navsecops"])


class SyncReportRequest(BaseModel):
    project_id: int = Field(..., ge=1, description="GitLab project id")
    merge_request_iid: int = Field(..., ge=1, description="Merge request IID")
    source_commit_sha: str = Field(
        ...,
        min_length=7,
        max_length=64,
        description="Source commit SHA for this pipeline run",
    )
    route_file: str = Field(..., min_length=1, description="Route GeoJSON path in repo")
    report_markdown: str = Field(..., min_length=1, description="Markdown posted or equivalent")
    raw_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional full analyze JSON response (stored as JSON text)",
    )


class SyncReportResponse(BaseModel):
    id: int
    project_id: int
    merge_request_iid: int
    source_commit_sha: str
    status: str = "stored"


class ReportListItem(BaseModel):
    id: int
    project_id: int
    merge_request_iid: int
    source_commit_sha: str
    route_file: str
    report_markdown: str
    created_at: str
    updated_at: str


class ReportListResponse(BaseModel):
    items: List[ReportListItem]
    limit: int
    offset: int


@router.post("/sync-report", response_model=SyncReportResponse)
async def sync_report(
    body: SyncReportRequest,
    _token: str = Depends(verify_navsecops_token),
):
    try:
        row_id = await asyncio.to_thread(
            upsert_report,
            body.project_id,
            body.merge_request_iid,
            body.source_commit_sha,
            body.route_file,
            body.report_markdown,
            body.raw_analysis,
        )
    except Exception as exc:
        log.exception("sync-report failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to persist report") from exc

    return SyncReportResponse(
        id=row_id,
        project_id=body.project_id,
        merge_request_iid=body.merge_request_iid,
        source_commit_sha=body.source_commit_sha.strip(),
    )


@router.get("/reports", response_model=ReportListResponse)
async def get_reports(
    project_id: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _token: str = Depends(verify_navsecops_token),
):
    rows = await asyncio.to_thread(
        list_reports, project_id=project_id, limit=limit, offset=offset
    )
    items = [
        ReportListItem(
            id=r.id,
            project_id=r.project_id,
            merge_request_iid=r.merge_request_iid,
            source_commit_sha=r.source_commit_sha,
            route_file=r.route_file,
            report_markdown=r.report_markdown,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return ReportListResponse(items=items, limit=limit, offset=offset)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    _token: str = Depends(verify_navsecops_token),
):
    data = await asyncio.to_thread(get_report_by_id, report_id)
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")
    return data
