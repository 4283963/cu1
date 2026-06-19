from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import engine, Base, SessionLocal
from .models import SensorNode, Fan
from .routers import sensors, fans, schedules
from .services.mock_sensor import mock_sensor_service
from .services.schedule_service import schedule_service


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(SensorNode).count() == 0:
            default_nodes = [
                SensorNode(name="节点-A1", location="一号养殖区-东侧", is_active=True),
                SensorNode(name="节点-A2", location="一号养殖区-西侧", is_active=True),
                SensorNode(name="节点-B1", location="二号养殖区-北侧", is_active=True),
                SensorNode(name="节点-B2", location="二号养殖区-南侧", is_active=True),
            ]
            db.add_all(default_nodes)

        if db.query(Fan).count() == 0:
            default_fans = [
                Fan(name="排风扇-1", location="一号养殖区-东墙", is_running=False, is_auto=False),
                Fan(name="排风扇-2", location="一号养殖区-西墙", is_running=False, is_auto=False),
                Fan(name="排风扇-3", location="二号养殖区-北墙", is_running=False, is_auto=False),
                Fan(name="排风扇-4", location="二号养殖区-南墙", is_running=False, is_auto=False),
            ]
            db.add_all(default_fans)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mock_sensor_service.start()
    schedule_service.start()
    yield
    mock_sensor_service.stop()
    schedule_service.stop()


app = FastAPI(
    title="蚕桑养殖温湿度监控系统",
    description="基于 FastAPI 的蚕桑养殖基地温湿度监控与排风扇远程控制系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router)
app.include_router(fans.router)
app.include_router(schedules.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "silkworm-monitor",
        "version": "1.0.0"
    }
