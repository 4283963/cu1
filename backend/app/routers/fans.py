from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
from .. import models, schemas
from ..dependencies import get_db
from ..websocket_manager import manager
from ..services.fan_service import fan_control_service

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

    from datetime import datetime
    fan.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(fan)

    fan_data = schemas.Fan.model_validate(fan).model_dump()
    try:
        await manager.broadcast(
            {"type": "fan_status_update", "data": fan_data},
            "fan_status"
        )
    except Exception:
        pass
    return fan


@router.post("/{fan_id}/toggle", response_model=schemas.Fan)
async def toggle_fan(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    try:
        fan_data = await fan_control_service.control_fan(fan_id, "TOGGLE", reason, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle fan: {str(e)}")

    if fan_data is None:
        raise HTTPException(status_code=404, detail="Fan not found")
    return fan_data


@router.post("/{fan_id}/on", response_model=schemas.Fan)
async def turn_fan_on(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    try:
        fan_data = await fan_control_service.control_fan(fan_id, "ON", reason, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to turn on fan: {str(e)}")

    if fan_data is None:
        raise HTTPException(status_code=404, detail="Fan not found")
    return fan_data


@router.post("/{fan_id}/off", response_model=schemas.Fan)
async def turn_fan_off(fan_id: int, reason: str = "manual", db: Session = Depends(get_db)):
    try:
        fan_data = await fan_control_service.control_fan(fan_id, "OFF", reason, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to turn off fan: {str(e)}")

    if fan_data is None:
        raise HTTPException(status_code=404, detail="Fan not found")
    return fan_data


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
    message_queue: asyncio.Queue = asyncio.Queue()
    processing_task = None

    async def process_messages():
        while True:
            try:
                message = await message_queue.get()
                try:
                    msg_data = json.loads(message)
                    if msg_data.get("type") == "control_action":
                        action_data = msg_data.get("data", {})
                        fan_id = action_data.get("fan_id")
                        action = action_data.get("action")
                        reason = action_data.get("reason", "ws_manual")

                        if fan_id and action:
                            try:
                                result = await fan_control_service.control_fan(fan_id, action, reason)
                                if result:
                                    pass
                            except Exception as e:
                                print(f"Fan control error via WS: {e}")
                except (json.JSONDecodeError, ValueError):
                    pass
                except Exception as e:
                    print(f"WS message processing error: {e}")
                finally:
                    message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"WS queue processor error: {e}")

    try:
        await manager.send_personal_message(
            {"type": "connection_established", "data": {"channel": "fan_status"}},
            websocket
        )

        processing_task = asyncio.create_task(process_messages())

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                try:
                    message_queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except Exception:
                break

    finally:
        if processing_task:
            processing_task.cancel()
            try:
                await processing_task
            except (asyncio.CancelledError, Exception):
                pass
        manager.disconnect(websocket, "fan_status")
