from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from .db import get_db
from .deps import get_current_user
from .models import DailyJournal, DailyJournalTradeLink, Trade, Account
from .schemas import DailyJournalUpsert, DailyJournalOut, AttachmentOut, AttachmentUpdate
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
import os, tempfile
from datetime import datetime as dt
from io import BytesIO
from .models import Attachment
from fastapi.responses import StreamingResponse
import zipfile


router = APIRouter(prefix="/journal", tags=["journal"])

ATTACH_MAX_MB = float(os.environ.get("ATTACH_MAX_MB", "10"))
ATTACH_THUMB_SIZE = int(os.environ.get("ATTACH_THUMB_SIZE", "256"))

def _resolve_attach_base() -> str:
    base = os.environ.get("ATTACH_BASE_DIR", "/data/uploads")
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        fallback = os.path.join(tempfile.gettempdir(), "edge_uploads")
        os.makedirs(fallback, exist_ok=True)
        return fallback

ATTACH_BASE_DIR = _resolve_attach_base()


def _parse_date(d: str) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception as e:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD") from e


@router.get("/dates")
def list_dates(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    q = db.query(DailyJournal.date).filter(DailyJournal.user_id == current.id)
    if start:
        q = q.filter(DailyJournal.date >= _parse_date(start))
    if end:
        q = q.filter(DailyJournal.date <= _parse_date(end))
    rows = q.order_by(DailyJournal.date.asc()).all()
    return [r[0].strftime("%Y-%m-%d") for r in rows]


@router.get("/{d}", response_model=DailyJournalOut)
def get_journal(d: str, db: Session = Depends(get_db), current = Depends(get_current_user), account_id: Optional[int] = None):
    day = _parse_date(d)
    q = db.query(DailyJournal).filter(DailyJournal.user_id == current.id, DailyJournal.date == day)
    if account_id:
        q = q.filter(DailyJournal.account_id == account_id)
    j = q.first()
    if not j:
        raise HTTPException(404, detail="Not found")
    links = db.query(DailyJournalTradeLink.trade_id).join(Trade, Trade.id == DailyJournalTradeLink.trade_id).join(Account, Account.id == Trade.account_id, isouter=True).\
        filter(DailyJournalTradeLink.journal_id == j.id, Account.user_id == current.id).all()
    trade_ids = [r[0] for r in links]
    return DailyJournalOut(id=j.id, date=j.date.strftime("%Y-%m-%d"), title=j.title, notes_md=j.notes_md, reviewed=bool(j.reviewed), account_id=j.account_id, trade_ids=trade_ids)


@router.put("/{d}", response_model=DailyJournalOut)
def upsert_journal(d: str, body: DailyJournalUpsert, db: Session = Depends(get_db), current = Depends(get_current_user)):
    day = _parse_date(d)
    j = db.query(DailyJournal).filter(DailyJournal.user_id == current.id, DailyJournal.date == day)
    if body.account_id is not None:
        j = j.filter(DailyJournal.account_id == body.account_id)
    row = j.first()
    if not row:
        row = DailyJournal(user_id=current.id, date=day, account_id=body.account_id)
        db.add(row)
        db.flush()
    if body.title is not None:
        row.title = body.title
    if body.notes_md is not None:
        row.notes_md = body.notes_md
    if body.reviewed is not None:
        row.reviewed = bool(body.reviewed)
    db.commit(); db.refresh(row)
    links = db.query(DailyJournalTradeLink.trade_id).filter(DailyJournalTradeLink.journal_id == row.id).all()
    return DailyJournalOut(id=row.id, date=row.date.strftime("%Y-%m-%d"), title=row.title, notes_md=row.notes_md, reviewed=bool(row.reviewed), account_id=row.account_id, trade_ids=[r[0] for r in links])


@router.delete("/{d}")
def delete_journal(d: str, db: Session = Depends(get_db), current = Depends(get_current_user), account_id: Optional[int] = None):
    day = _parse_date(d)
    q = db.query(DailyJournal).filter(DailyJournal.user_id == current.id, DailyJournal.date == day)
    if account_id:
        q = q.filter(DailyJournal.account_id == account_id)
    rows = q.all()
    if not rows:
        raise HTTPException(404, detail="Not found")
    deleted_ids: list[int] = []
    for row in rows:
        # Delete attachments files if present
        atts = db.query(Attachment).filter(Attachment.journal_id == row.id).all()
        for a in atts:
            try:
                if a.storage_path and os.path.exists(a.storage_path):
                    os.remove(a.storage_path)
                if a.thumb_path and os.path.exists(a.thumb_path):
                    os.remove(a.thumb_path)
            except Exception:
                pass
        # Cascade delete rows
        db.query(Attachment).filter(Attachment.journal_id == row.id).delete(synchronize_session=False)
        db.query(DailyJournalTradeLink).filter(DailyJournalTradeLink.journal_id == row.id).delete(synchronize_session=False)
        db.delete(row)
        deleted_ids.append(row.id)
    db.commit()
    return {"deleted": len(deleted_ids), "ids": deleted_ids, "date": d}


@router.post("/{journal_id}/trades")
def set_journal_trades(journal_id: int, trade_ids: List[int] = Body(...), db: Session = Depends(get_db), current = Depends(get_current_user)):
    j = db.query(DailyJournal).filter(DailyJournal.id == journal_id, DailyJournal.user_id == current.id).first()
    if not j:
        raise HTTPException(404, detail="Journal not found")
    # Ensure all trades belong to user
    if trade_ids:
        valid_ids = [r[0] for r in db.query(Trade.id).join(Account, Account.id == Trade.account_id, isouter=True).\
            filter(Trade.id.in_(trade_ids), Account.user_id == current.id).all()]
    else:
        valid_ids = []
    # Replace links
    db.query(DailyJournalTradeLink).filter(DailyJournalTradeLink.journal_id == journal_id).delete(synchronize_session=False)
    for tid in valid_ids:
        db.add(DailyJournalTradeLink(journal_id=journal_id, trade_id=tid))
    db.commit()
    return {"journal_id": journal_id, "trade_ids": valid_ids}


# --- Attachments for Journal ---
def _ensure_journal_owned(db: Session, current, journal_id: int) -> DailyJournal:
    j = db.query(DailyJournal).filter(DailyJournal.id == journal_id, DailyJournal.user_id == current.id).first()
    if not j:
        raise HTTPException(404, detail="Journal not found")
    return j


@router.get("/{journal_id}/attachments", response_model=list[AttachmentOut])
def list_journal_attachments(journal_id: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    rows = (
        db.query(Attachment)
        .filter(Attachment.journal_id == journal_id)
        .order_by(Attachment.sort_order.asc(), Attachment.created_at.asc())
        .all()
    )
    out: list[AttachmentOut] = []
    for a in rows:
        out.append(AttachmentOut(
            id=a.id,
            filename=a.filename,
            mime_type=a.mime_type,
            size_bytes=a.size_bytes,
            timeframe=a.timeframe,
            state=a.state,
            view=a.view,
            caption=a.caption,
            reviewed=bool(a.reviewed),
            thumb_available=bool(a.thumb_path),
            thumb_url=(f"/journal/{journal_id}/attachments/{a.id}/thumb" if a.thumb_path else None),
        ))
    return out


@router.post("/{journal_id}/attachments", response_model=AttachmentOut)
async def upload_journal_attachment(
    journal_id: int,
    file: UploadFile = File(...),
    timeframe: str | None = Form(None),
    state: str | None = Form(None),
    view: str | None = Form(None),
    caption: str | None = Form(None),
    reviewed: bool | None = Form(False),
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
):
    _ensure_journal_owned(db, current, journal_id)
    content = await file.read()
    if len(content) > int(ATTACH_MAX_MB * 1024 * 1024):
        raise HTTPException(413, detail=f"File exceeds limit of {int(ATTACH_MAX_MB)} MB")
    name = file.filename or "file"
    ext = os.path.splitext(name)[1].lower()
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
    if ext not in allowed:
        raise HTTPException(400, detail="Unsupported file type")
    journal_dir = os.path.join(ATTACH_BASE_DIR, "journal", str(journal_id))
    os.makedirs(journal_dir, exist_ok=True)
    basename = f"{int(dt.now().timestamp())}_{name}"
    path = os.path.join(journal_dir, basename)
    thumb_path = None
    try:
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                from PIL import Image
                im = Image.open(BytesIO(content))
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGB")
                save_params = {}
                if ext in {".jpg", ".jpeg"}:
                    save_params.update({"quality": 92, "optimize": True})
                im.save(path, **save_params)
                # thumb
                try:
                    im_t = im.copy()
                    im_t.thumbnail((ATTACH_THUMB_SIZE, ATTACH_THUMB_SIZE))
                    thumbs_dir = os.path.join(journal_dir, "thumbs")
                    os.makedirs(thumbs_dir, exist_ok=True)
                    has_alpha = ("A" in im_t.getbands())
                    if has_alpha:
                        tname = os.path.splitext(basename)[0] + ".png"
                        thumb_path = os.path.join(thumbs_dir, tname)
                        im_t.save(thumb_path, format="PNG")
                    else:
                        tname = os.path.splitext(basename)[0] + ".jpg"
                        thumb_path = os.path.join(thumbs_dir, tname)
                        im_t = im_t.convert("RGB")
                        im_t.save(thumb_path, format="JPEG", quality=85, optimize=True)
                except Exception:
                    thumb_path = None
            except Exception:
                # fallback: save raw
                with open(path, "wb") as f:
                    f.write(content)
        else:
            with open(path, "wb") as f:
                f.write(content)
    except Exception:
        try:
            with open(path, "wb") as f:
                f.write(content)
        except Exception:
            pass

    # choose next sort order for this journal
    current_max = (
        db.query(Attachment)
        .filter(Attachment.journal_id == journal_id)
        .order_by(Attachment.sort_order.desc())
        .limit(1)
        .first()
    )
    next_order = (current_max.sort_order if current_max else 0) + 1

    a = Attachment(
        trade_id=None,  # unused for journal
        journal_id=journal_id,
        user_id=None,
        filename=name,
        mime_type=file.content_type,
        size_bytes=len(content),
        storage_path=path,
        thumb_path=thumb_path,
        sort_order=next_order,
        timeframe=timeframe,
        state=state,
        view=view,
        caption=caption,
        reviewed=bool(reviewed),
    )
    db.add(a); db.commit(); db.refresh(a)
    return AttachmentOut(
        id=a.id,
        filename=a.filename,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        timeframe=a.timeframe,
        state=a.state,
        view=a.view,
        caption=a.caption,
        reviewed=bool(a.reviewed),
        thumb_available=bool(a.thumb_path),
        thumb_url=(f"/journal/{journal_id}/attachments/{a.id}/thumb" if a.thumb_path else None),
    )


@router.get("/{journal_id}/attachments/{att_id}/download")
def download_journal_attachment(journal_id: int, att_id: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    a = db.query(Attachment).filter(Attachment.id == att_id, Attachment.journal_id == journal_id).first()
    if not a:
        raise HTTPException(404, detail="Attachment not found")
    return FileResponse(a.storage_path, filename=a.filename, media_type=a.mime_type)


@router.get("/{journal_id}/attachments/{att_id}/thumb")
def download_journal_attachment_thumb(journal_id: int, att_id: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    a = db.query(Attachment).filter(Attachment.id == att_id, Attachment.journal_id == journal_id).first()
    if not a or not a.thumb_path or not os.path.exists(a.thumb_path):
        raise HTTPException(404, detail="Thumbnail not available")
    ext = os.path.splitext(a.thumb_path)[1].lower()
    media = "image/jpeg" if ext in (".jpg", ".jpeg") else ("image/png" if ext == ".png" else "application/octet-stream")
    return FileResponse(a.thumb_path, filename=os.path.basename(a.thumb_path), media_type=media)


@router.delete("/{journal_id}/attachments/{att_id}")
def delete_journal_attachment(journal_id: int, att_id: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    a = db.query(Attachment).filter(Attachment.id == att_id, Attachment.journal_id == journal_id).first()
    if not a:
        raise HTTPException(404, detail="Attachment not found")
    try:
        if a.storage_path and os.path.exists(a.storage_path):
            os.remove(a.storage_path)
        if a.thumb_path and os.path.exists(a.thumb_path):
            os.remove(a.thumb_path)
    except Exception:
        pass
    db.delete(a); db.commit()
    return {"deleted": att_id}


@router.patch("/{journal_id}/attachments/{att_id}", response_model=AttachmentOut)
def update_journal_attachment(
    journal_id: int,
    att_id: int,
    body: AttachmentUpdate,
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
):
    _ensure_journal_owned(db, current, journal_id)
    a = db.query(Attachment).filter(Attachment.id == att_id, Attachment.journal_id == journal_id).first()
    if not a:
        raise HTTPException(404, detail="Attachment not found")
    if body.timeframe is not None:
        a.timeframe = body.timeframe
    if body.state is not None:
        a.state = body.state
    if body.view is not None:
        a.view = body.view
    if body.caption is not None:
        a.caption = body.caption
    if body.reviewed is not None:
        a.reviewed = bool(body.reviewed)
    db.commit(); db.refresh(a)
    return AttachmentOut(
        id=a.id,
        filename=a.filename,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        timeframe=a.timeframe,
        state=a.state,
        view=a.view,
        caption=a.caption,
        reviewed=bool(a.reviewed),
        thumb_available=bool(a.thumb_path),
        thumb_url=(f"/journal/{journal_id}/attachments/{a.id}/thumb" if a.thumb_path else None),
    )


@router.post("/{journal_id}/attachments/reorder")
def reorder_journal_attachments(journal_id: int, ids: List[int], db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    if not isinstance(ids, list) or not all(isinstance(x, int) for x in ids):
        raise HTTPException(400, detail="Body must be a list of attachment IDs")
    rows = db.query(Attachment).filter(Attachment.journal_id == journal_id, Attachment.id.in_(ids)).all()
    if len(rows) != len(set(ids)):
        raise HTTPException(400, detail="One or more attachments invalid")
    for idx, att_id in enumerate(ids):
        db.query(Attachment).filter(Attachment.id == att_id).update({Attachment.sort_order: idx})
    db.commit()
    return {"reordered": len(ids)}


@router.post("/{journal_id}/attachments/batch-delete")
def batch_delete_journal_attachments(journal_id: int, ids: List[int], db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    if not isinstance(ids, list) or not all(isinstance(x, int) for x in ids):
        raise HTTPException(400, detail="Body must be a list of attachment IDs")
    rows = db.query(Attachment).filter(Attachment.journal_id == journal_id, Attachment.id.in_(ids)).all()
    count = 0
    for a in rows:
        try:
            if a.storage_path and os.path.exists(a.storage_path):
                os.remove(a.storage_path)
            if a.thumb_path and os.path.exists(a.thumb_path):
                os.remove(a.thumb_path)
        except Exception:
            pass
        db.delete(a); count += 1
    db.commit()
    return {"deleted": count}


@router.post("/{journal_id}/attachments/zip")
def zip_journal_attachments(journal_id: int, ids: List[int], db: Session = Depends(get_db), current = Depends(get_current_user)):
    _ensure_journal_owned(db, current, journal_id)
    if not isinstance(ids, list) or not all(isinstance(x, int) for x in ids):
        raise HTTPException(400, detail="Body must be a list of attachment IDs")
    rows = db.query(Attachment).filter(Attachment.journal_id == journal_id, Attachment.id.in_(ids)).all()
    if not rows:
        raise HTTPException(404, detail="No attachments found")

    def iter_zip():
        buf = BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
            for a in rows:
                try:
                    arcname = a.filename or f"att-{a.id}"
                    if a.storage_path and os.path.exists(a.storage_path):
                        z.write(a.storage_path, arcname=arcname)
                except Exception:
                    continue
        buf.seek(0)
        data = buf.read()
        yield data

    filename = f"journal-{journal_id}-attachments.zip"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter_zip(), media_type="application/zip", headers=headers)
