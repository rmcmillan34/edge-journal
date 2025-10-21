from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import datetime as dt

from .deps import get_current_user
from .db import get_db
from .models import User, PlaybookResponse, PlaybookTemplate, PlaybookEvidenceLink, DailyJournal
from .schemas import (
    PlaybookResponseCreate,
    PlaybookResponseOut,
    EvidenceCreate,
    EvidenceOut,
)

router = APIRouter(prefix="", tags=["playbook-responses"])


@router.get("/trades/{trade_id}/playbook-responses", response_model=List[PlaybookResponseOut])
def list_trade_responses(
    trade_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    rows = (
        db.query(PlaybookResponse)
        .filter(PlaybookResponse.user_id == current.id, PlaybookResponse.trade_id == trade_id)
        .order_by(PlaybookResponse.created_at.desc())
        .all()
    )
    # Prefetch template meta for involved template_ids
    tpl_ids = sorted({r.template_id for r in rows})
    tpl_meta_map = {}
    if tpl_ids:
        tpls = (
            db.query(PlaybookTemplate)
            .filter(PlaybookTemplate.user_id == current.id, PlaybookTemplate.id.in_(tpl_ids))
            .all()
        )
        for t in tpls:
            tpl_meta_map[t.id] = {"id": t.id, "name": t.name, "purpose": t.purpose}
    out: List[PlaybookResponseOut] = []
    for r in rows:
        out.append(
            PlaybookResponseOut(
                id=r.id,
                template_id=r.template_id,
                template_version=r.template_version,
                values=json.loads(r.values_json),
                comments=json.loads(r.comments_json) if r.comments_json else None,
                computed_grade=r.computed_grade,
                compliance_score=r.compliance_score,
                intended_risk_pct=r.intended_risk_pct,
                created_at=r.created_at.isoformat() if r.created_at else None,
                template_meta=(
                    {
                        "id": r.template_id,
                        "name": tpl_meta_map.get(r.template_id, {}).get("name"),
                        "purpose": tpl_meta_map.get(r.template_id, {}).get("purpose"),
                        "version": r.template_version,
                    }
                    if r.template_id in tpl_meta_map
                    else None
                ),
            )
        )
    return out


@router.post("/trades/{trade_id}/playbook-responses", response_model=PlaybookResponseOut)
def upsert_trade_response(
    trade_id: int,
    body: PlaybookResponseCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    tpl = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == body.template_id, PlaybookTemplate.user_id == current.id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    version = body.template_version or tpl.version
    # upsert: find existing response for same trade+template+version; if exists, update; else create
    resp = (
        db.query(PlaybookResponse)
        .filter(
            PlaybookResponse.user_id == current.id,
            PlaybookResponse.trade_id == trade_id,
            PlaybookResponse.template_id == body.template_id,
            PlaybookResponse.template_version == version,
        )
        .first()
    )
    # Compute compliance and grade inline to persist
    try:
        schema = json.loads(tpl.schema_json)
    except Exception:
        schema = []
    # Minimal evaluator (mirrors /playbooks/evaluate)
    grade_thresholds = None
    try:
        grade_thresholds = json.loads(tpl.grade_thresholds_json) if tpl.grade_thresholds_json else None
    except Exception:
        grade_thresholds = None
    grade_thresholds = grade_thresholds or {"A": 0.9, "B": 0.75, "C": 0.6}
    values = body.values or {}
    total_weight = 0.0
    satisfied = 0.0
    for f in schema:
        w = f.get('weight', 1.0) or 1.0
        total_weight += w
        val = values.get(f.get('key'))
        ok = False
        t = f.get('type')
        if t == 'boolean':
            ok = bool(val) is True
        elif t in ('text','rich_text'):
            ok = val is not None and str(val).strip() != ''
        elif t == 'number':
            try:
                num = float(val)
                ok = True
                v = f.get('validation') or {}
                if 'min' in v and num < float(v['min']): ok = False
                if 'max' in v and num > float(v['max']): ok = False
            except Exception:
                ok = False
        elif t == 'select':
            v = f.get('validation') or {}
            if 'options' in v:
                ok = val in v['options']
            else:
                ok = val is not None
        elif t == 'rating':
            try:
                r = float(val)
                ok = 0 <= r <= 5
            except Exception:
                ok = False
        if ok:
            satisfied += w
    compliance = (satisfied / total_weight) if total_weight > 0 else 0.0
    grade = 'D'
    if compliance >= grade_thresholds.get('A', 0.9):
        grade = 'A'
    elif compliance >= grade_thresholds.get('B', 0.75):
        grade = 'B'
    elif compliance >= grade_thresholds.get('C', 0.6):
        grade = 'C'

    if not resp:
        resp = PlaybookResponse(
            user_id=current.id,
            trade_id=trade_id,
            journal_id=None,
            template_id=body.template_id,
            template_version=version,
            entry_type="trade_playbook",
            values_json=json.dumps(body.values),
            comments_json=json.dumps(body.comments) if body.comments else None,
            intended_risk_pct=body.intended_risk_pct,
            computed_grade=grade,
            compliance_score=compliance,
        )
        db.add(resp)
    else:
        resp.values_json = json.dumps(body.values)
        resp.comments_json = json.dumps(body.comments) if body.comments else None
        resp.intended_risk_pct = body.intended_risk_pct
        resp.computed_grade = grade
        resp.compliance_score = compliance
    db.commit()
    db.refresh(resp)
    return PlaybookResponseOut(
        id=resp.id,
        template_id=resp.template_id,
        template_version=resp.template_version,
        values=json.loads(resp.values_json),
        comments=json.loads(resp.comments_json) if resp.comments_json else None,
        computed_grade=resp.computed_grade,
        compliance_score=resp.compliance_score,
        intended_risk_pct=resp.intended_risk_pct,
        created_at=resp.created_at.isoformat() if resp.created_at else None,
        template_meta={
            "id": tpl.id,
            "name": tpl.name,
            "purpose": tpl.purpose,
            "version": resp.template_version,
        },
    )


@router.post("/playbook-responses/{response_id}/evidence", response_model=EvidenceOut)
def add_evidence(
    response_id: int,
    body: EvidenceCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    resp = db.query(PlaybookResponse).filter(PlaybookResponse.id == response_id, PlaybookResponse.user_id == current.id).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    row = PlaybookEvidenceLink(
        response_id=response_id,
        field_key=body.field_key,
        source_kind=body.source_kind,
        source_id=body.source_id,
        url=body.url,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return EvidenceOut(
        id=row.id,
        field_key=row.field_key,
        source_kind=row.source_kind,
        source_id=row.source_id,
        url=row.url,
        note=row.note,
    )


@router.delete("/playbook-responses/{response_id}/evidence/{evidence_id}")
def delete_evidence(
    response_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    resp = db.query(PlaybookResponse).filter(PlaybookResponse.id == response_id, PlaybookResponse.user_id == current.id).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    row = db.query(PlaybookEvidenceLink).filter(PlaybookEvidenceLink.id == evidence_id, PlaybookEvidenceLink.response_id == response_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/playbook-responses/{response_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(
    response_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    resp = db.query(PlaybookResponse).filter(PlaybookResponse.id == response_id, PlaybookResponse.user_id == current.id).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    rows = db.query(PlaybookEvidenceLink).filter(PlaybookEvidenceLink.response_id == response_id).order_by(PlaybookEvidenceLink.id.asc()).all()
    return [EvidenceOut(id=r.id, field_key=r.field_key, source_kind=r.source_kind, source_id=r.source_id, url=r.url, note=r.note) for r in rows]


# --- Instrument Checklist (Daily Journal mode) ---

def _find_journal_by_date(db: Session, user_id: int, date_str: str) -> Optional[DailyJournal]:
    try:
        d = dt.date.fromisoformat(date_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")
    return (
        db.query(DailyJournal)
        .filter(DailyJournal.user_id == user_id, DailyJournal.date == d)
        .first()
    )


@router.get("/journal/{date}/instrument/{symbol}/playbook-response", response_model=Optional[PlaybookResponseOut])
def get_instrument_checklist(
    date: str,
    symbol: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    journal = _find_journal_by_date(db, current.id, date)
    if not journal:
        raise HTTPException(status_code=404, detail="Daily journal not found for date")
    rows = (
        db.query(PlaybookResponse)
        .filter(
            PlaybookResponse.user_id == current.id,
            PlaybookResponse.journal_id == journal.id,
            PlaybookResponse.entry_type == "instrument_checklist",
        )
        .order_by(PlaybookResponse.created_at.desc())
        .all()
    )
    # Prefer one whose values_json has matching symbol (if present)
    for r in rows:
        try:
            vals = json.loads(r.values_json)
        except Exception:
            vals = {}
        if str(vals.get("symbol") or vals.get("instrument") or "").upper() == symbol.upper():
            tpl = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == r.template_id, PlaybookTemplate.user_id == current.id).first()
            return PlaybookResponseOut(
                id=r.id,
                template_id=r.template_id,
                template_version=r.template_version,
                values=vals,
                comments=json.loads(r.comments_json) if r.comments_json else None,
                computed_grade=r.computed_grade,
                compliance_score=r.compliance_score,
                intended_risk_pct=r.intended_risk_pct,
                created_at=r.created_at.isoformat() if r.created_at else None,
                template_meta=(
                    {
                        "id": tpl.id,
                        "name": tpl.name,
                        "purpose": tpl.purpose,
                        "version": r.template_version,
                    }
                    if tpl
                    else None
                ),
            )
    # If none match symbol, return latest if any (or null)
    if rows:
        r = rows[0]
        tpl = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == r.template_id, PlaybookTemplate.user_id == current.id).first()
        return PlaybookResponseOut(
            id=r.id,
            template_id=r.template_id,
            template_version=r.template_version,
            values=json.loads(r.values_json),
            comments=json.loads(r.comments_json) if r.comments_json else None,
            computed_grade=r.computed_grade,
            compliance_score=r.compliance_score,
            intended_risk_pct=r.intended_risk_pct,
            created_at=r.created_at.isoformat() if r.created_at else None,
            template_meta=(
                {
                    "id": tpl.id,
                    "name": tpl.name,
                    "purpose": tpl.purpose,
                    "version": r.template_version,
                }
                if tpl
                else None
            ),
        )
    return None


@router.get("/journal/{date}/instrument/{symbol}/playbook-responses", response_model=List[PlaybookResponseOut])
def list_instrument_checklists(
    date: str,
    symbol: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    journal = _find_journal_by_date(db, current.id, date)
    if not journal:
        raise HTTPException(status_code=404, detail="Daily journal not found for date")
    rows = (
        db.query(PlaybookResponse)
        .filter(
            PlaybookResponse.user_id == current.id,
            PlaybookResponse.journal_id == journal.id,
            PlaybookResponse.entry_type == "instrument_checklist",
        )
        .order_by(PlaybookResponse.created_at.desc())
        .all()
    )
    tpl_ids = sorted({r.template_id for r in rows})
    tpl_meta_map = {}
    if tpl_ids:
        tpls = (
            db.query(PlaybookTemplate)
            .filter(PlaybookTemplate.user_id == current.id, PlaybookTemplate.id.in_(tpl_ids))
            .all()
        )
        for t in tpls:
            tpl_meta_map[t.id] = {"id": t.id, "name": t.name, "purpose": t.purpose}
    out: List[PlaybookResponseOut] = []
    for r in rows:
        vals = {}
        try:
            vals = json.loads(r.values_json)
        except Exception:
            vals = {}
        # If symbol provided, include all but prioritize display via client; we include all here
        out.append(
            PlaybookResponseOut(
                id=r.id,
                template_id=r.template_id,
                template_version=r.template_version,
                values=vals,
                comments=json.loads(r.comments_json) if r.comments_json else None,
                computed_grade=r.computed_grade,
                compliance_score=r.compliance_score,
                intended_risk_pct=r.intended_risk_pct,
                created_at=r.created_at.isoformat() if r.created_at else None,
                template_meta=(
                    {
                        "id": r.template_id,
                        "name": tpl_meta_map.get(r.template_id, {}).get("name"),
                        "purpose": tpl_meta_map.get(r.template_id, {}).get("purpose"),
                        "version": r.template_version,
                    }
                    if r.template_id in tpl_meta_map
                    else None
                ),
            )
        )
    return out

@router.post("/journal/{date}/instrument/{symbol}/playbook-response", response_model=PlaybookResponseOut)
def upsert_instrument_checklist(
    date: str,
    symbol: str,
    body: PlaybookResponseCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    journal = _find_journal_by_date(db, current.id, date)
    if not journal:
        raise HTTPException(status_code=404, detail="Daily journal not found for date")
    tpl = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == body.template_id, PlaybookTemplate.user_id == current.id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    version = body.template_version or tpl.version

    # ensure symbol present in values for later lookup
    values = dict(body.values or {})
    values.setdefault("symbol", symbol)

    # find existing matching by journal+template+version and symbol (if possible)
    candidates = (
        db.query(PlaybookResponse)
        .filter(
            PlaybookResponse.user_id == current.id,
            PlaybookResponse.journal_id == journal.id,
            PlaybookResponse.template_id == body.template_id,
            PlaybookResponse.template_version == version,
            PlaybookResponse.entry_type == "instrument_checklist",
        )
        .all()
    )
    match: Optional[PlaybookResponse] = None
    for r in candidates:
        try:
            vals = json.loads(r.values_json)
        except Exception:
            vals = {}
        if str(vals.get("symbol") or vals.get("instrument") or "").upper() == symbol.upper():
            match = r
            break

    # Compute compliance/grade
    try:
        schema = json.loads(tpl.schema_json)
    except Exception:
        schema = []
    grade_thresholds = None
    try:
        grade_thresholds = json.loads(tpl.grade_thresholds_json) if tpl.grade_thresholds_json else None
    except Exception:
        grade_thresholds = None
    grade_thresholds = grade_thresholds or {"A": 0.9, "B": 0.75, "C": 0.6}
    total_weight = 0.0
    satisfied = 0.0
    for f in schema:
        w = f.get('weight', 1.0) or 1.0
        total_weight += w
        val = values.get(f.get('key'))
        ok = False
        t = f.get('type')
        if t == 'boolean':
            ok = bool(val) is True
        elif t in ('text','rich_text'):
            ok = val is not None and str(val).strip() != ''
        elif t == 'number':
            try:
                num = float(val)
                ok = True
                v = f.get('validation') or {}
                if 'min' in v and num < float(v['min']): ok = False
                if 'max' in v and num > float(v['max']): ok = False
            except Exception:
                ok = False
        elif t == 'select':
            v = f.get('validation') or {}
            if 'options' in v:
                ok = val in v['options']
            else:
                ok = val is not None
        elif t == 'rating':
            try:
                r = float(val)
                ok = 0 <= r <= 5
            except Exception:
                ok = False
        if ok:
            satisfied += w
    compliance = (satisfied / total_weight) if total_weight > 0 else 0.0
    grade = 'D'
    if compliance >= grade_thresholds.get('A', 0.9):
        grade = 'A'
    elif compliance >= grade_thresholds.get('B', 0.75):
        grade = 'B'
    elif compliance >= grade_thresholds.get('C', 0.6):
        grade = 'C'

    if not match:
        match = PlaybookResponse(
            user_id=current.id,
            trade_id=None,
            journal_id=journal.id,
            template_id=body.template_id,
            template_version=version,
            entry_type="instrument_checklist",
            values_json=json.dumps(values),
            comments_json=json.dumps(body.comments) if body.comments else None,
            intended_risk_pct=body.intended_risk_pct,
            computed_grade=grade,
            compliance_score=compliance,
        )
        db.add(match)
    else:
        match.values_json = json.dumps(values)
        match.comments_json = json.dumps(body.comments) if body.comments else None
        match.intended_risk_pct = body.intended_risk_pct
        match.computed_grade = grade
        match.compliance_score = compliance
    db.commit()
    db.refresh(match)
    return PlaybookResponseOut(
        id=match.id,
        template_id=match.template_id,
        template_version=match.template_version,
        values=json.loads(match.values_json),
        comments=json.loads(match.comments_json) if match.comments_json else None,
        computed_grade=match.computed_grade,
        compliance_score=match.compliance_score,
        intended_risk_pct=match.intended_risk_pct,
        created_at=match.created_at.isoformat() if match.created_at else None,
        template_meta={
            "id": tpl.id,
            "name": tpl.name,
            "purpose": tpl.purpose,
            "version": match.template_version,
        },
    )
