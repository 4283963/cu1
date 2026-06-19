import asyncio
import random
import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from ..database import SessionLocal, _db_write_lock, MAX_RETRIES, RETRY_DELAY
from ..models import SensorNode, SensorReading
from ..websocket_manager import manager
from ..config import settings


def _commit_with_retry_and_broadcast(db: Session, reading, node):
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            with _db_write_lock:
                db.add(reading)
                db.commit()
                db.refresh(reading)
            reading_data = {
                "id": reading.id,
                "sensor_node_id": node.id,
                "sensor_node_name": node.name,
                "sensor_node_location": node.location,
                "temperature": reading.temperature,
                "humidity": reading.humidity,
                "timestamp": reading.timestamp.isoformat()
            }
            return reading_data
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


class MockSensorService:
    def __init__(self):
        self.running = False
        self.task = None

    async def generate_reading(self, node: SensorNode):
        temp_base = 25.0
        hum_base = 65.0
        temp_variation = random.uniform(-3.0, 5.0)
        hum_variation = random.uniform(-5.0, 8.0)

        temperature = round(temp_base + temp_variation, 2)
        humidity = max(30.0, min(95.0, round(hum_base + hum_variation, 2)))

        db = SessionLocal()
        try:
            reading = SensorReading(
                sensor_node_id=node.id,
                temperature=temperature,
                humidity=humidity
            )

            reading_data = await asyncio.to_thread(
                _commit_with_retry_and_broadcast,
                db, reading, node
            )

            if reading_data:
                await manager.broadcast(
                    {"type": "sensor_reading", "data": reading_data},
                    "sensor_data"
                )
        except Exception as e:
            print(f"Error generating reading for node {node.id}: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass

    async def run(self):
        self.running = True
        while self.running:
            db = SessionLocal()
            try:
                nodes = db.query(SensorNode).filter(SensorNode.is_active == True).all()
                if not nodes:
                    print("Warning: No active sensor nodes found. Create some first.")
                    await asyncio.sleep(5)
                    continue

                for node in nodes:
                    if not self.running:
                        break
                    await self.generate_reading(node)

                await asyncio.sleep(settings.sensor_update_interval)
            except Exception as e:
                print(f"Error in mock sensor service loop: {e}")
                await asyncio.sleep(settings.sensor_update_interval)
            finally:
                try:
                    db.close()
                except Exception:
                    pass

    def start(self):
        if not self.running:
            self.task = asyncio.create_task(self.run())

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()


mock_sensor_service = MockSensorService()
