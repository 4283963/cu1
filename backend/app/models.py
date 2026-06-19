from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class SensorNode(Base):
    __tablename__ = "sensor_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    readings = relationship("SensorReading", back_populates="sensor_node", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_node_id = Column(Integer, ForeignKey("sensor_nodes.id"), nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    sensor_node = relationship("SensorNode", back_populates="readings")


class Fan(Base):
    __tablename__ = "fans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location = Column(String, nullable=False)
    is_running = Column(Boolean, default=False)
    is_auto = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    control_logs = relationship("FanControlLog", back_populates="fan", cascade="all, delete-orphan")


class FanControlLog(Base):
    __tablename__ = "fan_control_logs"

    id = Column(Integer, primary_key=True, index=True)
    fan_id = Column(Integer, ForeignKey("fans.id"), nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, default="manual")

    fan = relationship("Fan", back_populates="control_logs")


class FanSchedule(Base):
    __tablename__ = "fan_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    fan_ids = Column(String, nullable=False, default="[]")
    weekdays = Column(String, nullable=False, default="[]")
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    target_temperature = Column(Float, nullable=False, default=26.0)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)

