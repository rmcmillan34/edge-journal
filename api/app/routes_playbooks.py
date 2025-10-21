from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from .deps import get_current_user
from .db import get_db
from .models import User, PlaybookTemplate
from .schemas import (
    PlaybookTemplateCreate,
    PlaybookTemplateOut,
    PlaybookTemplateUpdate,
    PlaybookEvaluateIn,
    PlaybookEvaluateOut,
    PlaybookField,
    PlaybookTemplateCloneIn,
)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def _serialize_schema(fields: List[PlaybookField]) -> str:
    return json.dumps([f.model_dump() for f in fields])


def _deserialize_schema(schema_json: str) -> List[PlaybookField]:
    raw = json.loads(schema_json)
    return [PlaybookField(**item) for item in raw]


def _quickstart_templates() -> List[dict]:
    return [
        {
            "slug": "pre_risk_setup",
            "name": "Pre-Trade: Risk & Setup",
            "purpose": "pre",
            "description": "Confirm setup quality, news risk, and intended risk before entry.",
            "schema": [
                {"key": "setup_criteria_met", "label": "Setup criteria met", "type": "boolean", "required": True, "weight": 1},
                {"key": "news_checked", "label": "News checked", "type": "boolean", "required": True, "weight": 1},
                {"key": "intended_risk_pct", "label": "Intended Risk %", "type": "number", "required": True, "weight": 1, "validation": {"min": 0, "max": 5}},
                {"key": "rr_planned", "label": "Planned R:R", "type": "number", "required": False, "weight": 0.5, "validation": {"min": 0, "max": 10}},
            ],
            "template_max_risk_pct": 1.0,
            "grade_thresholds": {"A": 0.9, "B": 0.75, "C": 0.6},
            "risk_schedule": {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0},
        },
        {
            "slug": "in_management",
            "name": "In-Trade: Management",
            "purpose": "in",
            "description": "Check adherence to management rules and stop discipline.",
            "schema": [
                {"key": "followed_plan", "label": "Followed Plan", "type": "boolean", "required": True, "weight": 1},
                {"key": "moved_stop_rules", "label": "Moved stop per rules", "type": "boolean", "required": False, "weight": 1},
                {"key": "added_per_rules", "label": "Added per rules", "type": "boolean", "required": False, "weight": 0.5},
                {"key": "trade_confidence", "label": "Confidence", "type": "rating", "required": False, "weight": 0.5},
            ],
            "template_max_risk_pct": 1.0,
            "grade_thresholds": {"A": 0.9, "B": 0.75, "C": 0.6},
            "risk_schedule": {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0},
        },
        {
            "slug": "post_review",
            "name": "Post-Trade: Review",
            "purpose": "post",
            "description": "Assess execution quality and document lessons.",
            "schema": [
                {"key": "setup_ok", "label": "Setup criteria met", "type": "boolean", "required": True, "weight": 1},
                {"key": "entry_quality", "label": "Entry quality", "type": "rating", "required": False, "weight": 1},
                {"key": "exit_quality", "label": "Exit quality", "type": "rating", "required": False, "weight": 1},
                {"key": "intended_risk_pct", "label": "Intended Risk %", "type": "number", "required": False, "weight": 1, "validation": {"min": 0, "max": 5}},
                {"key": "lesson", "label": "Lesson", "type": "text", "required": False, "weight": 0.5},
            ],
            "template_max_risk_pct": 1.0,
            "grade_thresholds": {"A": 0.9, "B": 0.75, "C": 0.6},
            "risk_schedule": {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0},
        },
    ]


@router.get("/templates/quickstart")
def list_quickstart_templates():
    return {"items": _quickstart_templates()}


@router.post("/templates/quickstart/{slug}", response_model=PlaybookTemplateOut)
def create_quickstart_template(
    slug: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    qs = next((x for x in _quickstart_templates() if x["slug"] == slug), None)
    if not qs:
        raise HTTPException(status_code=404, detail="Quickstart not found")
    body = PlaybookTemplateCreate(
        name=qs["name"],
        purpose=qs["purpose"],
        strategy_bindings=None,
        schema=[PlaybookField(**f) for f in qs["schema"]],
        grade_thresholds=qs["grade_thresholds"],
        risk_schedule=qs["risk_schedule"],
        template_max_risk_pct=qs["template_max_risk_pct"],
    )
    return create_template(body, db=db, current=current)


def _validate_unique_keys(fields: List[PlaybookField]):
    seen = set()
    dups = []
    for f in fields:
        k = (f.key or '').strip().lower()
        if not k:
            dups.append('(empty key)')
            continue
        if k in seen:
            dups.append(f.key)
        seen.add(k)
    if dups:
        raise HTTPException(status_code=400, detail=f"Duplicate or invalid field keys: {', '.join(sorted(set(dups)))}")


@router.get("/templates", response_model=List[PlaybookTemplateOut])
def list_templates(
    purpose: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(PlaybookTemplate).filter(PlaybookTemplate.user_id == current.id)
    if purpose:
        q = q.filter(PlaybookTemplate.purpose == purpose)
    if active is not None:
        q = q.filter(PlaybookTemplate.is_active == active)
    rows = q.order_by(PlaybookTemplate.name, PlaybookTemplate.version.desc()).all()
    out: List[PlaybookTemplateOut] = []
    for r in rows:
        out.append(
            PlaybookTemplateOut(
                id=r.id,
                name=r.name,
                purpose=r.purpose,
                version=r.version,
                is_active=r.is_active,
                schema=_deserialize_schema(r.schema_json),
                grade_thresholds=json.loads(r.grade_thresholds_json) if r.grade_thresholds_json else None,
                risk_schedule=json.loads(r.risk_schedule_json) if r.risk_schedule_json else None,
                template_max_risk_pct=r.template_max_risk_pct,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )
    return out


@router.post("/templates", response_model=PlaybookTemplateOut)
def create_template(
    body: PlaybookTemplateCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _validate_unique_keys(body.schema)
    row = PlaybookTemplate(
        user_id=current.id,
        name=body.name,
        purpose=body.purpose,
        strategy_bindings_json=json.dumps(body.strategy_bindings) if body.strategy_bindings is not None else None,
        schema_json=_serialize_schema(body.schema),
        version=1,
        is_active=True,
        grade_scale="A_B_C_D",
        grade_thresholds_json=json.dumps(body.grade_thresholds) if body.grade_thresholds else None,
        risk_schedule_json=json.dumps(body.risk_schedule) if body.risk_schedule else None,
        template_max_risk_pct=body.template_max_risk_pct,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PlaybookTemplateOut(
        id=row.id,
        name=row.name,
        purpose=row.purpose,
        version=row.version,
        is_active=row.is_active,
        schema=_deserialize_schema(row.schema_json),
        grade_thresholds=json.loads(row.grade_thresholds_json) if row.grade_thresholds_json else None,
        risk_schedule=json.loads(row.risk_schedule_json) if row.risk_schedule_json else None,
        template_max_risk_pct=row.template_max_risk_pct,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.patch("/templates/{template_id}", response_model=PlaybookTemplateOut)
def update_template(
    template_id: int,
    body: PlaybookTemplateUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    existing = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == template_id, PlaybookTemplate.user_id == current.id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    # Version bump: create a new row with version+1 and updated fields
    new_version = (existing.version or 1) + 1
    if body.schema is not None:
        _validate_unique_keys(body.schema)
    row = PlaybookTemplate(
        user_id=current.id,
        name=body.name or existing.name,
        purpose=body.purpose or existing.purpose,
        strategy_bindings_json=json.dumps(body.strategy_bindings) if body.strategy_bindings is not None else existing.strategy_bindings_json,
        schema_json=_serialize_schema(body.schema) if body.schema is not None else existing.schema_json,
        version=new_version,
        is_active=True,
        grade_scale=existing.grade_scale,
        grade_thresholds_json=json.dumps(body.grade_thresholds) if body.grade_thresholds is not None else existing.grade_thresholds_json,
        risk_schedule_json=json.dumps(body.risk_schedule) if body.risk_schedule is not None else existing.risk_schedule_json,
        template_max_risk_pct=body.template_max_risk_pct if body.template_max_risk_pct is not None else existing.template_max_risk_pct,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PlaybookTemplateOut(
        id=row.id,
        name=row.name,
        purpose=row.purpose,
        version=row.version,
        is_active=row.is_active,
        schema=_deserialize_schema(row.schema_json),
        grade_thresholds=json.loads(row.grade_thresholds_json) if row.grade_thresholds_json else None,
        risk_schedule=json.loads(row.risk_schedule_json) if row.risk_schedule_json else None,
        template_max_risk_pct=row.template_max_risk_pct,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.post("/templates/{template_id}/export")
def export_template(
    template_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == template_id, PlaybookTemplate.user_id == current.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    payload = {
        "name": row.name,
        "purpose": row.purpose,
        "strategy_bindings": json.loads(row.strategy_bindings_json) if row.strategy_bindings_json else None,
        "schema": json.loads(row.schema_json),
        "version": row.version,
        "grade_thresholds": json.loads(row.grade_thresholds_json) if row.grade_thresholds_json else None,
        "risk_schedule": json.loads(row.risk_schedule_json) if row.risk_schedule_json else None,
        "template_max_risk_pct": row.template_max_risk_pct,
    }
    return payload


@router.post("/templates/import", response_model=PlaybookTemplateOut)
def import_template(
    body: PlaybookTemplateCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # Treat import as create with provided values; version starts at 1 for user namespace
    _validate_unique_keys(body.schema)
    return create_template(body, db=db, current=current)


@router.delete("/templates/{template_id}", response_model=PlaybookTemplateOut)
def archive_template(
    template_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == template_id, PlaybookTemplate.user_id == current.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    row.is_active = False
    db.commit()
    db.refresh(row)
    return PlaybookTemplateOut(
        id=row.id,
        name=row.name,
        purpose=row.purpose,
        version=row.version,
        is_active=row.is_active,
        schema=_deserialize_schema(row.schema_json),
        grade_thresholds=json.loads(row.grade_thresholds_json) if row.grade_thresholds_json else None,
        risk_schedule=json.loads(row.risk_schedule_json) if row.risk_schedule_json else None,
        template_max_risk_pct=row.template_max_risk_pct,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.post("/templates/{template_id}/clone", response_model=PlaybookTemplateOut)
def clone_template(
    template_id: int,
    body: PlaybookTemplateCloneIn = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    src = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == template_id, PlaybookTemplate.user_id == current.id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Template not found")
    new_name = (body.name if body and body.name else f"{src.name} (Copy)").strip()
    new_purpose = (body.purpose if body and body.purpose else src.purpose)
    row = PlaybookTemplate(
        user_id=current.id,
        name=new_name,
        purpose=new_purpose,
        strategy_bindings_json=src.strategy_bindings_json,
        schema_json=src.schema_json,
        version=1,
        is_active=True,
        grade_scale=src.grade_scale,
        grade_thresholds_json=src.grade_thresholds_json,
        risk_schedule_json=src.risk_schedule_json,
        template_max_risk_pct=src.template_max_risk_pct,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PlaybookTemplateOut(
        id=row.id,
        name=row.name,
        purpose=row.purpose,
        version=row.version,
        is_active=row.is_active,
        schema=_deserialize_schema(row.schema_json),
        grade_thresholds=json.loads(row.grade_thresholds_json) if row.grade_thresholds_json else None,
        risk_schedule=json.loads(row.risk_schedule_json) if row.risk_schedule_json else None,
        template_max_risk_pct=row.template_max_risk_pct,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.post("/evaluate", response_model=PlaybookEvaluateOut)
def evaluate_playbook(
    body: PlaybookEvaluateIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # Load template if id provided
    schema = body.schema
    grade_thresholds = body.grade_thresholds or {"A": 0.9, "B": 0.75, "C": 0.6}
    risk_schedule = body.risk_schedule or {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0}
    template_max = body.template_max_risk_pct
    if body.template_id and not schema:
        t = db.query(PlaybookTemplate).filter(PlaybookTemplate.id == body.template_id, PlaybookTemplate.user_id == current.id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        schema = _deserialize_schema(t.schema_json)
        template_max = template_max if template_max is not None else t.template_max_risk_pct
    if not schema:
        raise HTTPException(status_code=400, detail="Missing schema for evaluation")

    # Validate required minimally and compute compliance
    values = body.values or {}
    total_weight = 0.0
    satisfied = 0.0
    for field in schema:
        w = field.weight or 1.0
        total_weight += w
        val = values.get(field.key)
        ok = False
        if field.type == 'boolean':
            ok = bool(val) is True
        elif field.type in ('text','rich_text'):
            ok = val is not None and str(val).strip() != ''
        elif field.type == 'number':
            try:
                num = float(val)
                ok = True
                if field.validation:
                    if 'min' in field.validation and num < float(field.validation['min']):
                        ok = False
                    if 'max' in field.validation and num > float(field.validation['max']):
                        ok = False
            except Exception:
                ok = False
        elif field.type == 'select':
            if field.validation and 'options' in field.validation:
                ok = val in field.validation['options']
            else:
                ok = val is not None
        elif field.type == 'rating':
            try:
                r = float(val)
                ok = 0 <= r <= 5
            except Exception:
                ok = False
        if ok:
            satisfied += w

    compliance = (satisfied / total_weight) if total_weight > 0 else 0.0

    # Grade mapping
    grade = 'D'
    if compliance >= grade_thresholds.get('A', 0.9):
        grade = 'A'
    elif compliance >= grade_thresholds.get('B', 0.75):
        grade = 'B'
    elif compliance >= grade_thresholds.get('C', 0.6):
        grade = 'C'

    # Risk cap breakdown and final cap
    grade_cap = risk_schedule.get(grade, 0.0)
    caps = [c for c in [template_max, grade_cap, body.account_max_risk_pct] if c is not None]
    risk_cap = min(caps) if caps else grade_cap

    exceeded = None
    messages: List[str] = []
    if body.intended_risk_pct is not None:
        try:
            intended = float(body.intended_risk_pct)
            cap = float(risk_cap) if risk_cap is not None else 0.0
            exceeded = intended > cap
            if exceeded:
                tpl_part = f"template {template_max}%" if template_max is not None else "template n/a"
                acct_part = f"account {body.account_max_risk_pct}%" if body.account_max_risk_pct is not None else "account n/a"
                messages.append(
                    f"Intended risk {intended}% exceeds cap {cap}% (grade {grade}; {tpl_part}; {acct_part})."
                )
        except Exception:
            exceeded = None

    return PlaybookEvaluateOut(
        compliance_score=round(compliance, 4),
        grade=grade,
        risk_cap_pct=float(risk_cap) if risk_cap is not None else 0.0,
        cap_breakdown={
            "template": float(template_max) if template_max is not None else None,
            "grade": float(grade_cap) if grade_cap is not None else None,
            "account": float(body.account_max_risk_pct) if body.account_max_risk_pct is not None else None,
        },
        exceeded=exceeded,
        messages=messages or None,
    )


@router.get("/grades")
def get_grades_for_trades(
    trade_ids: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Return the latest playbook grade for each trade ID provided.

    Query param: trade_ids = comma-separated list of IDs.
    """
    from .models import PlaybookResponse
    ids = [int(x) for x in trade_ids.split(',') if x.strip().isdigit()]
    if not ids:
        return {"grades": {}}
    rows = (
        db.query(PlaybookResponse)
        .filter(PlaybookResponse.user_id == current.id, PlaybookResponse.trade_id.in_(ids))
        .order_by(PlaybookResponse.trade_id.asc(), PlaybookResponse.created_at.desc())
        .all()
    )
    latest = {}
    for r in rows:
        tid = r.trade_id
        if tid not in latest:
            latest[tid] = r.computed_grade or None
    return {"grades": latest}
