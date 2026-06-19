import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from ..database import (
    SessionLocal,
    get_or_create_fan_lock,
    _db_write_lock,
    MAX_RETRIES,
    RETRY_DELAY,
)
from .. import models, schemas
from ..websocket_manager import manager


def _commit_with_retry(db: Session) -> None:
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            with _db_write_lock:
                db.commit()
            return
        except OperationalError as e:
            last_exception = e
            error_str = str(e).lower()
            if "locked" in error_str or "busy" in error_str:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    continue
            raise
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
    raise last_exception


class FanControlService:
    def __init__(self):
        self._rate_limit_tokens: Dict[int, float] = {}
        self._rate_limit_min_interval = 0.25

    def _check_rate_limit(self, fan_id: int) -> bool:
        now = time.monotonic()
        last_time = self._rate_limit_tokens.get(fan_id, 0)
        if now - last_time < self._rate_limit_min_interval:
            return False
        self._rate_limit_tokens[fan_id] = now
        return True

    def _execute_fan_operation(
        self,
        db: Session,
        fan_id: int,
        action: str,
        reason: str = "manual"
    ) -> Optional[models.Fan]:
        fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
        if not fan:
            return None

        old_state = fan.is_running
        need_update = False

        if action == "ON":
            if not fan.is_running:
                fan.is_running = True
                need_update = True
        elif action == "OFF":
            if fan.is_running:
                fan.is_running = False
                need_update = True
        elif action == "TOGGLE":
            fan.is_running = not fan.is_running
            need_update = True

        if need_update:
            fan.last_updated = datetime.utcnow()
            log_action = "ON" if fan.is_running else "OFF"
            log_entry = models.FanControlLog(
                fan_id=fan_id,
                action=log_action,
                reason=reason
            )
            db.add(log_entry)

        db.flush()
        _commit_with_retry(db)

        if need_update:
            try:
                db.refresh(fan)
            except Exception:
                pass

        return fan

    async def control_fan(
        self,
        fan_id: int,
        action: str,
        reason: str = "manual",
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        if not self._check_rate_limit(fan_id):
            db_temp = db or SessionLocal()
            try:
                fan = db_temp.query(models.Fan).filter(models.Fan.id == fan_id).first()
                if fan:
                    return schemas.Fan.model_validate(fan).model_dump()
                return None
            finally:
                if db is None:
                    db_temp.close()

        lock = get_or_create_fan_lock(fan_id)
        async with lock:
            should_close_db = db is None
            db_instance = db or SessionLocal()
            try:
                fan = await asyncio.to_thread(
                    self._execute_fan_operation,
                    db_instance,
                    fan_id,
                    action,
                    reason
                )

                if fan is None:
                    return None

                fan_data = schemas.Fan.model_validate(fan).model_dump()

                try:
                    await manager.broadcast(
                        {"type": "fan_status_update", "data": fan_data},
                        "fan_status"
                    )
                except Exception:
                    pass

                return fan_data
            finally:
                if should_close_db:
                    try:
                        db_instance.close()
                    except Exception:
                        pass


fan_control_service = FanControlService()
