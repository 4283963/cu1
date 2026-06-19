from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from .. import models, schemas
from ..dependencies import get_db
from ..websocket_manager import manager

router = APIRouter(prefix="/api/fans", tags=["fans"])


@router.get("", response_model=List[schemas.Fan])
def get_fans(db: Session = Depends(get_db)):
    fans = db.query(models.Fan).all()
    return fans


@router.post("", response_model=schemas.Fan)
def create_fan(fan: schemas.FanCreate, db: Session = Depends(get_db)):
    db_fan = models.Fan(**fan.model_dump())
    db.add(db_fan)
    db.commit()
    db.refresh(db_fan)
    return db_fan


@router.get("/{fan_id}", response_model=schemas.Fan)
def get_fan(fan_id: int, db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")
    return fan


@router.put("/{fan_id}", response_model=schemas.Fan)
async def update_fan(fan_id: int, fan_update: schemas.FanUpdate, db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")

    update_data = fan_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fan, key, value)

    fan.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(fan)

    await manager.broadcast(
        {"type": "fan_status_update", "data": schemas.Fan.model_validate(fan).model_dump()},
        "fan_status"
    )
    return fan


@router.post("/{fan_id}/toggle", response_model=schemas.Fan)
async def toggle_fan(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")

    fan.is_running = not fan.is_running
    fan.last_updated = datetime.utcnow()

    action = "ON" if fan.is_running else "OFF"
    log_entry = models.FanControlLog(
        fan_id=fan_id,
        action=action,
        reason=reason
    )
    db.add(log_entry)
    db.commit()
    db.refresh(fan)

    fan_data = schemas.Fan.model_validate(fan).model_dump()
    await manager.broadcast(
        {"type": "fan_status_update", "data": fan_data},
        "fan_status"
    )
    return fan


@router.post("/{fan_id}/on", response_model=schemas.Fan)
async def turn_fan_on(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")

    if not fan.is_running:
        fan.is_running = True
        fan.last_updated = datetime.utcnow()
        log_entry = models.FanControlLog(
            fan_id=fan_id,
            action="ON",
            reason=reason
        )
        db.add(log_entry)
        db.commit()
        db.refresh(fan)

    fan_data = schemas.Fan.model_validate(fan).model_dump()
    await manager.broadcast(
        {"type": "fan_status_update", "data": fan_data},
        "fan_status"
    )
    return fan


@router.post("/{fan_id}/off", response_model=schemas.Fan)
async def turn_fan_off(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")

    if fan.is_running:
        fan.is_running = False
        fan.last_updated = datetime.utcnow()
        log_entry = models.FanControlLog(
            fan_id=fan_id,
            action="OFF",
            reason=reason
        )
        db.add(log_entry)
        db.commit()
        db.refresh(fan)

    fan_data = schemas.Fan.model_validate(fan).model_dump()
    await manager.broadcast(
        {"type": "fan_status_update", "data": fan_data},
        "fan_status"
    )
    return fan


@router.get("/{fan_id}/logs", response_model=List[schemas.FanControlLog])
def get_fan_logs(fan_id: int, limit: int = 50, db: Session = Depends(get_db)):
    fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
    if not fan:
        raise HTTPException(status_code=404, detail="Fan not found")

    logs = db.query(models.FanControlLog).filter(
        models.FanControlLog.fan_id == fan_id
    ).order_by(models.FanControlLog.timestamp.desc()).limit(limit).all()
    return logs


@router.websocket("/ws")
async def fan_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "fan_status")
    try:
        await manager.send_personal_message(
            {"type": "connection_established", "data": {"channel": "fan_status"}},
            websocket
        )
        while True:
            data = await websocket.receive_text()
            try:
                import json
                message = json.loads(data)
                if message.get("type") == "control_action":
                    action_data = message.get("data", {})
                    fan_id = action_data.get("fan_id")
                    action = action_data.get("action")
                    reason = action_data.get("reason", "ws_manual")

                    from ..database import SessionLocal
                    db = SessionLocal()
                    try:
                        fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
                        if fan:
                            if action == "ON":
                                fan.is_running = True
                            elif action == "OFF":
                                fan.is_running = False
                            elif action == "TOGGLE":
                                fan.is_running = not fan.is_running

                            fan.last_updated = datetime.utcnow()
                            log_entry = models.FanControlLog(
                                fan_id=fan_id,
                                action=fan.is_running and "ON" or "OFF",
                                reason=reason
                            )
                            db.add(log_entry)
                            db.commit()
                            db.refresh(fan)

                            fan_data = schemas.Fan.model_validate(fan).model_dump()
                            await manager.broadcast(
                                {"type": "fan_status_update", "data": fan_data},
                                "fan_status"
                            )
                    finally:
                        db.close()
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, "fan_status")
