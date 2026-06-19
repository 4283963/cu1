from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SensorNodeBase(BaseModel):
    name: str
    location: str
    is_active: Optional[bool] = True


class SensorNodeCreate(SensorNodeBase):
    pass


class SensorNode(SensorNodeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SensorReadingBase(BaseModel):
    sensor_node_id: int
    temperature: float
    humidity: float


class SensorReadingCreate(SensorReadingBase):
    pass


class SensorReading(SensorReadingBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class SensorReadingWithNode(SensorReading):
    sensor_node: SensorNode


class FanBase(BaseModel):
    name: str
    location: str
    is_running: Optional[bool] = False
    is_auto: Optional[bool] = False


class FanCreate(FanBase):
    pass


class FanUpdate(BaseModel):
    is_running: Optional[bool] = None
    is_auto: Optional[bool] = None
    name: Optional[str] = None
    location: Optional[str] = None


class Fan(FanBase):
    id: int
    created_at: datetime
    last_updated: datetime

    class Config:
        from_attributes = True


class FanControlAction(BaseModel):
    fan_id: int
    action: str
    reason: Optional[str] = "manual"


class FanControlLogBase(BaseModel):
    fan_id: int
    action: str
    reason: Optional[str] = "manual"


class FanControlLog(FanControlLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    type: str
    data: dict
