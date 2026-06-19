from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..dependencies import get_db
from ..websocket_manager import manager

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("/nodes", response_model=List[schemas.SensorNode])
def get_sensor_nodes(db: Session = Depends(get_db)):
    nodes = db.query(models.SensorNode).all()
    return nodes


@router.post("/nodes", response_model=schemas.SensorNode)
def create_sensor_node(node: schemas.SensorNodeCreate, db: Session = Depends(get_db)):
    db_node = models.SensorNode(**node.model_dump())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node


@router.get("/nodes/{node_id}", response_model=schemas.SensorNode)
def get_sensor_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(models.SensorNode).filter(models.SensorNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Sensor node not found")
    return node


@router.get("/readings", response_model=List[schemas.SensorReadingWithNode])
def get_readings(limit: int = 100, db: Session = Depends(get_db)):
    readings = db.query(models.SensorReading).order_by(
        models.SensorReading.timestamp.desc()
    ).limit(limit).all()
    return readings[::-1]


@router.get("/readings/latest", response_model=List[schemas.SensorReadingWithNode])
def get_latest_readings(db: Session = Depends(get_db)):
    nodes = db.query(models.SensorNode).filter(models.SensorNode.is_active == True).all()
    latest_readings = []
    for node in nodes:
        reading = db.query(models.SensorReading).filter(
            models.SensorReading.sensor_node_id == node.id
        ).order_by(models.SensorReading.timestamp.desc()).first()
        if reading:
            latest_readings.append(reading)
    return latest_readings


@router.get("/nodes/{node_id}/readings", response_model=List[schemas.SensorReading])
def get_node_readings(node_id: int, limit: int = 100, db: Session = Depends(get_db)):
    node = db.query(models.SensorNode).filter(models.SensorNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Sensor node not found")
    readings = db.query(models.SensorReading).filter(
        models.SensorReading.sensor_node_id == node_id
    ).order_by(models.SensorReading.timestamp.desc()).limit(limit).all()
    return readings[::-1]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "sensor_data")
    try:
        await manager.send_personal_message(
            {"type": "connection_established", "data": {"channel": "sensor_data"}},
            websocket
        )
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(
                {"type": "echo", "data": {"message": data}},
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, "sensor_data")
