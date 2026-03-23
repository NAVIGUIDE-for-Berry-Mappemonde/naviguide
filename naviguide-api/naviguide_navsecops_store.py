"""
NavSecOps — SQLite persistence for synced MR intelligence reports.

Database file: naviguide-api/var/navsecops.db (directory gitignored).
Uses stdlib sqlite3 only (no extra pip dependency).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _db_path() -> Path:
    root = Path(__file__).resolve().parent / "var"
    root.mkdir(parents=True, exist_ok=True)
    return root / "navsecops.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create table if missing (idempotent)."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS navsecops_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                merge_request_iid INTEGER NOT NULL,
                source_commit_sha TEXT NOT NULL,
                route_file TEXT NOT NULL,
                report_markdown TEXT NOT NULL,
                raw_analysis TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (project_id, merge_request_iid, source_commit_sha)
            )
            """
        )
        conn.commit()


def upsert_report(
    project_id: int,
    merge_request_iid: int,
    source_commit_sha: str,
    route_file: str,
    report_markdown: str,
    raw_analysis: Optional[Dict[str, Any]],
) -> int:
    """
    Insert or update row keyed by (project_id, merge_request_iid, source_commit_sha).
    Returns row id.
    """
    init_db()
    raw_json = json.dumps(raw_analysis, ensure_ascii=False) if raw_analysis is not None else None
    now = _utc_now_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO navsecops_reports (
                project_id, merge_request_iid, source_commit_sha,
                route_file, report_markdown, raw_analysis,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, merge_request_iid, source_commit_sha) DO UPDATE SET
                route_file = excluded.route_file,
                report_markdown = excluded.report_markdown,
                raw_analysis = excluded.raw_analysis,
                updated_at = excluded.updated_at
            """,
            (
                project_id,
                merge_request_iid,
                source_commit_sha.strip(),
                route_file,
                report_markdown,
                raw_json,
                now,
                now,
            ),
        )
        conn.commit()
        cur = conn.execute(
            """
            SELECT id FROM navsecops_reports
            WHERE project_id = ? AND merge_request_iid = ? AND source_commit_sha = ?
            """,
            (project_id, merge_request_iid, source_commit_sha.strip()),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("upsert failed: row not found after write")
        return int(row["id"])


@dataclass
class ReportListRow:
    id: int
    project_id: int
    merge_request_iid: int
    source_commit_sha: str
    route_file: str
    report_markdown: str
    created_at: str
    updated_at: str


def list_reports(
    *,
    project_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ReportListRow]:
    init_db()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    q = """
        SELECT id, project_id, merge_request_iid, source_commit_sha,
               route_file, report_markdown, created_at, updated_at
        FROM navsecops_reports
    """
    args: List[Any] = []
    if project_id is not None:
        q += " WHERE project_id = ?"
        args.append(project_id)
    q += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    args.extend([limit, offset])
    with _connect() as conn:
        rows = conn.execute(q, args).fetchall()
    return [
        ReportListRow(
            id=int(r["id"]),
            project_id=int(r["project_id"]),
            merge_request_iid=int(r["merge_request_iid"]),
            source_commit_sha=str(r["source_commit_sha"]),
            route_file=str(r["route_file"]),
            report_markdown=str(r["report_markdown"]),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]


def get_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, project_id, merge_request_iid, source_commit_sha,
                   route_file, report_markdown, raw_analysis, created_at, updated_at
            FROM navsecops_reports WHERE id = ?
            """,
            (report_id,),
        ).fetchone()
    if not row:
        return None
    raw = row["raw_analysis"]
    parsed: Optional[Any] = None
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
    return {
        "id": int(row["id"]),
        "project_id": int(row["project_id"]),
        "merge_request_iid": int(row["merge_request_iid"]),
        "source_commit_sha": str(row["source_commit_sha"]),
        "route_file": str(row["route_file"]),
        "report_markdown": str(row["report_markdown"]),
        "raw_analysis": parsed,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }
