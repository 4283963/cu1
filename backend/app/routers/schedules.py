from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime
from .. import models, schemas
from ..dependencies import get_db

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


def _serialize_ids(ids):
    return json.dumps(ids)


def _parse_ids(ids_str):
    try:
        return json.loads(ids_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _to_schema(schedule):
    return schemas.FanSchedule(
        id=schedule.id,
        name=schedule.name,
        fan_ids=_parse_ids(schedule.fan_ids),
        weekdays=_parse_ids(schedule.weekdays),
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        target_temperature=schedule.target_temperature,
        is_enabled=schedule.is_enabled,
        created_at=schedule.created_at,
        last_triggered=schedule.last_triggered
    )


@router.get("", response_model=List[schemas.FanSchedule])
def get_schedules(db: Session = Depends(get_db)):
    schedules = db.query(models.FanSchedule).order_by(models.FanSchedule.created_at.desc()).all()
    return [_to_schema(s) for s in schedules]


@router.get("/{schedule_id}", response_model=schemas.FanSchedule)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(models.FanSchedule).filter(models.FanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _to_schema(schedule)


@router.post("", response_model=schemas.FanSchedule)
def create_schedule(schedule: schemas.FanScheduleCreate, db: Session = Depends(get_db)):
    if not schedule.fan_ids:
        raise HTTPException(status_code=400, detail="At least one fan must be selected")
    if not schedule.weekdays:
        raise HTTPException(status_code=400, detail="At least one weekday must be selected")

    db_schedule = models.FanSchedule(
        name=schedule.name,
        fan_ids=_serialize_ids(schedule.fan_ids),
        weekdays=_serialize_ids(schedule.weekdays),
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        target_temperature=schedule.target_temperature,
        is_enabled=schedule.is_enabled
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return _to_schema(db_schedule)


@router.put("/{schedule_id}", response_model=schemas.FanSchedule)
def update_schedule(schedule_id: int, schedule_update: schemas.FanScheduleUpdate, db: Session = Depends(get_db)):
    schedule = db.query(models.FanSchedule).filter(models.FanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = schedule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "fan_ids":
            schedule.fan_ids = _serialize_ids(value)
        elif key == "weekdays":
            schedule.weekdays = _serialize_ids(value)
        else:
            setattr(schedule, key, value)

    db.commit()
    db.refresh(schedule)
    return _to_schema(schedule)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(models.FanSchedule).filter(models.FanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(schedule)
    db.commit()
    return {"status": "success", "message": "Schedule deleted"}


@router.post("/{schedule_id}/toggle", response_model=schemas.FanSchedule)
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(models.FanSchedule).filter(models.FanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_enabled = not schedule.is_enabled
    db.commit()
    db.refresh(schedule)
    return _to_schema(schedule)
