import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional
from ..database import SessionLocal, text
from .. import models
from ..services.fan_service import fan_control_service
from ..websocket_manager import manager


def _parse_ids(ids_str):
    try:
        return json.loads(ids_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_time(time_str: str):
    try:
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return hour, minute
    except (ValueError, IndexError):
        return None, None


def _is_time_in_range(current_hour: int, current_minute: int, start_str: str, end_str: str) -> bool:
    sh, sm = _parse_time(start_str)
    eh, em = _parse_time(end_str)
    if sh is None or eh is None:
        return False

    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    current_minutes = current_hour * 60 + current_minute

    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    else:
        return current_minutes >= start_minutes or current_minutes <= end_minutes


class ScheduleService:
    def __init__(self):
        self.running = False
        self.task = None
        self.fan_active_schedules: Dict[int, Set[int]] = {}
        self.check_interval = 30

    async def run(self):
        self.running = True
        while self.running:
            try:
                await self._check_and_execute_schedules()
            except Exception as e:
                print(f"Schedule service error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_and_execute_schedules(self):
        now = datetime.now()
        weekday = now.weekday()
        current_hour = now.hour
        current_minute = now.minute

        db = SessionLocal()
        try:
            schedules = db.query(models.FanSchedule).filter(
                models.FanSchedule.is_enabled == True
            ).all()

            new_active: Dict[int, Set[int]] = {}
            inactive_fans_checked: Set[int] = set()

            for schedule in schedules:
                fan_ids = _parse_ids(schedule.fan_ids)
                weekdays = _parse_ids(schedule.weekdays)

                if not fan_ids or not weekdays:
                    continue

                if weekday not in weekdays:
                    continue

                in_time_range = _is_time_in_range(
                    current_hour, current_minute,
                    schedule.start_time, schedule.end_time
                )

                if not in_time_range:
                    continue

                avg_temp = await self._get_avg_temperature_for_fans(db, fan_ids)

                should_run = self._should_run_fans(
                    avg_temp,
                    schedule.target_temperature,
                    fan_ids,
                    db
                )

                for fan_id in fan_ids:
                    if fan_id not in new_active:
                        new_active[fan_id] = set()
                    new_active[fan_id].add(schedule.id)

                    if should_run:
                        await self._ensure_fan_on(fan_id, schedule.id, schedule.target_temperature)
                    else:
                        inactive_fans_checked.add(fan_id)

            for fan_id in inactive_fans_checked:
                has_other_active = fan_id in new_active and len(new_active[fan_id]) > 0
                if not has_other_active:
                    await self._ensure_fan_off_if_no_schedule(fan_id, new_active)

            self.fan_active_schedules = new_active

            for schedule in schedules:
                try:
                    schedule.last_triggered = now
                    db.add(schedule)
                except Exception:
                    pass

            try:
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass

        finally:
            try:
                db.close()
            except Exception:
                pass

    async def _get_avg_temperature_for_fans(self, db, fan_ids):
        try:
            from ..models import SensorReading
            readings = db.query(SensorReading).order_by(
                SensorReading.timestamp.desc()
            ).limit(20).all()

            if readings:
                temps = [r.temperature for r in readings if r.temperature]
                if temps:
                    return sum(temps) / len(temps)
        except Exception as e:
            print(f"Error getting temperature: {e}")
        return None

    def _should_run_fans(self, avg_temp, target_temp, fan_ids, db):
        if avg_temp is None:
            return True

        temp_diff = avg_temp - target_temp

        for fan_id in fan_ids:
            try:
                fan = db.query(models.Fan).filter(models.Fan.id == fan_id).first()
                if fan:
                    if temp_diff >= 1.0:
                        return True
                    if fan.is_running and temp_diff <= -0.5:
                        return False
                    if fan.is_running:
                        return True
            except Exception:
                pass

        return temp_diff >= 0.5

    async def _ensure_fan_on(self, fan_id: int, schedule_id: int, target_temp: float):
        try:
            result = await fan_control_service.control_fan(
                fan_id, "ON", reason=f"schedule_{schedule_id}_T>={target_temp}°C"
            )
            return result is not None
        except Exception as e:
            print(f"Failed to turn on fan {fan_id}: {e}")
            return False

    async def _ensure_fan_off_if_no_schedule(self, fan_id: int, active_schedules: Dict[int, Set[int]]):
        if fan_id in active_schedules and len(active_schedules[fan_id]) > 0:
            return

        try:
            await fan_control_service.control_fan(
                fan_id, "OFF", reason="schedule_end"
            )
        except Exception as e:
            print(f"Failed to turn off fan {fan_id}: {e}")

    def start(self):
        if not self.running:
            self.task = asyncio.create_task(self.run())
            print("Schedule service started")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            print("Schedule service stopped")


schedule_service = ScheduleService()
