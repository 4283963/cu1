import asyncio
import random
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import SensorNode, SensorReading
from ..websocket_manager import manager
from ..config import settings


class MockSensorService:
    def __init__(self):
        self.running = False
        self.task = None

    async def generate_reading(self, node: SensorNode) -> SensorReading:
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
            await manager.broadcast(
                {"type": "sensor_reading", "data": reading_data},
                "sensor_data"
            )
            return reading
        finally:
            db.close()

    async def run(self):
        self.running = True
        db = SessionLocal()
        try:
            nodes = db.query(SensorNode).filter(SensorNode.is_active == True).all()
            if not nodes:
                print("Warning: No active sensor nodes found. Create some first.")
                return
        finally:
            db.close()

        while self.running:
            db = SessionLocal()
            try:
                nodes = db.query(SensorNode).filter(SensorNode.is_active == True).all()
                for node in nodes:
                    await self.generate_reading(node)
                await asyncio.sleep(settings.sensor_update_interval)
            except Exception as e:
                print(f"Error in mock sensor service: {e}")
                await asyncio.sleep(settings.sensor_update_interval)
            finally:
                db.close()

    def start(self):
        if not self.running:
            self.task = asyncio.create_task(self.run())

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()


mock_sensor_service = MockSensorService()
