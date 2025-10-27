"""
Reports API Routes

Endpoints for generating and managing PDF reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import os

from .db import get_db
from .deps import get_current_user
from .models import User
from .schemas import ReportGenerateRequest, ReportHistoryOut
from .reports import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORTS_BASE_DIR = os.environ.get("REPORTS_BASE_DIR", "/data/exports")


@router.post("/generate")
def generate_report(
    body: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Generate PDF report and return as download.

    Supports multiple report types:
    - trade: Single trade detail report
    - daily: Daily performance report
    - weekly: Weekly performance report
    - monthly: Monthly performance report with hierarchical breakdown
    - yearly: Full year report
    - ytd: Year-to-date report
    - alltime: All-time performance report

    For "separate" account_separation_mode, returns ZIP file with multiple PDFs.
    Otherwise returns single PDF.
    """
    generator = ReportGenerator(db, current.id)

    # Generate PDF based on report type
    content_bytes = None
    content_type = None
    filename = None

    try:
        if body.type == "trade":
            if not body.period.trade_id:
                raise HTTPException(status_code=400, detail="trade_id required for trade report")
            content_bytes, content_type = generator.generate_trade_report(
                body.period.trade_id,
                body.theme,
                body.include_screenshots
            )
            filename = f"trade_report_{body.period.trade_id}.pdf"

        elif body.type == "daily":
            if not body.period.date:
                raise HTTPException(status_code=400, detail="date required for daily report")

            from datetime import datetime
            report_date = datetime.strptime(body.period.date, "%Y-%m-%d").date()

            content_bytes, content_type = generator.generate_daily_report(
                report_date,
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme,
                body.include_screenshots
            )
            filename = f"daily_report_{body.period.date}" + (".zip" if content_type == "application/zip" else ".pdf")

        elif body.type == "weekly":
            if not body.period.year or not body.period.week:
                raise HTTPException(status_code=400, detail="year and week required for weekly report")
            content_bytes, content_type = generator.generate_weekly_report(
                body.period.year,
                body.period.week,
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme,
                body.include_screenshots
            )
            filename = f"weekly_report_{body.period.year}_W{body.period.week}" + (".zip" if content_type == "application/zip" else ".pdf")

        elif body.type == "monthly":
            if not body.period.year or not body.period.month:
                raise HTTPException(status_code=400, detail="year and month required for monthly report")

            content_bytes, content_type = generator.generate_monthly_report(
                body.period.year,
                body.period.month,
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme,
                body.include_screenshots
            )
            filename = f"monthly_report_{body.period.year}_{body.period.month:02d}" + (".zip" if content_type == "application/zip" else ".pdf")

        elif body.type == "yearly":
            if not body.period.year:
                raise HTTPException(status_code=400, detail="year required for yearly report")
            content_bytes, content_type = generator.generate_yearly_report(
                body.period.year,
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme
            )
            filename = f"yearly_report_{body.period.year}" + (".zip" if content_type == "application/zip" else ".pdf")

        elif body.type == "ytd":
            content_bytes, content_type = generator.generate_ytd_report(
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme
            )
            current_year = datetime.utcnow().year
            filename = f"ytd_report_{current_year}" + (".zip" if content_type == "application/zip" else ".pdf")

        elif body.type == "alltime":
            content_bytes, content_type = generator.generate_alltime_report(
                body.account_ids,
                body.account_separation_mode,
                body.view_id,
                body.theme
            )
            filename = f"alltime_report_{datetime.utcnow().strftime('%Y%m%d')}" + (".zip" if content_type == "application/zip" else ".pdf")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported report type: {body.type}")

    except HTTPException:
        # Re-raise HTTPException to preserve status code
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Report type '{body.type}' is not yet implemented"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error for debugging
        print(f"[ERROR] Report generation failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    # Save to disk for history (skip in CI/test environments without /data access)
    try:
        user_reports_dir = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports")
        os.makedirs(user_reports_dir, exist_ok=True)

        filepath = os.path.join(user_reports_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content_bytes)
    except Exception as e:
        print(f"[ERROR] Failed to save report to disk: {e}")
        # Continue even if save fails - still return the content

    # Return PDF or ZIP as response
    return Response(
        content=content_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content_bytes))
        }
    )


@router.get("/history")
def list_report_history(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
) -> List[ReportHistoryOut]:
    """
    List previously generated reports for the current user.

    Returns a list of report metadata including filename, type, creation time, and file size.
    Reports are sorted by creation time (newest first).
    """
    user_reports_dir = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports")

    if not os.path.exists(user_reports_dir):
        return []

    reports = []
    try:
        for filename in os.listdir(user_reports_dir):
            if filename.endswith(".pdf"):
                filepath = os.path.join(user_reports_dir, filename)
                try:
                    stat = os.stat(filepath)

                    # Parse report type from filename (format: {type}_report_*.pdf)
                    report_type = "unknown"
                    if "_report_" in filename:
                        report_type = filename.split("_report_")[0]

                    reports.append(
                        ReportHistoryOut(
                            id=hash(filename) & 0x7FFFFFFF,  # Generate positive int ID from hash
                            filename=filename,
                            report_type=report_type,
                            created_at=datetime.fromtimestamp(stat.st_mtime),
                            file_size_bytes=stat.st_size
                        )
                    )
                except OSError as e:
                    # Skip files that can't be accessed
                    print(f"[WARN] Could not access report file {filename}: {e}")
                    continue

        # Sort by creation time, newest first
        reports.sort(key=lambda r: r.created_at, reverse=True)

    except OSError as e:
        print(f"[ERROR] Failed to list reports directory: {e}")
        return []

    return reports


@router.get("/download/{filename}")
def download_report(
    filename: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Download a previously generated report by filename.

    Security: Ensures the filename doesn't contain path traversal characters
    and belongs to the current user.
    """
    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow PDF files
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be downloaded")

    filepath = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports", filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(filepath, "rb") as f:
            pdf_bytes = f.read()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes))
            }
        )
    except Exception as e:
        print(f"[ERROR] Failed to read report file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read report file")


@router.delete("/{filename}")
def delete_report(
    filename: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Delete a report from history.

    Security: Ensures the filename doesn't contain path traversal characters
    and belongs to the current user.
    """
    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow PDF files
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be deleted")

    filepath = os.path.join(REPORTS_BASE_DIR, str(current.id), "reports", filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        os.remove(filepath)
        return {"message": "Report deleted successfully", "filename": filename}
    except Exception as e:
        print(f"[ERROR] Failed to delete report file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete report file")
