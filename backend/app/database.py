from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import time
import asyncio
import threading
from functools import wraps
from .config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_db_write_lock = threading.Lock()
_async_fan_locks = {}
_async_fan_locks_guard = threading.Lock()

MAX_RETRIES = 5
RETRY_DELAY = 0.1


def get_or_create_fan_lock(fan_id):
    with _async_fan_locks_guard:
        if fan_id not in _async_fan_locks:
            _async_fan_locks[fan_id] = asyncio.Lock()
        return _async_fan_locks[fan_id]


def with_db_retry_sync(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                last_exception = e
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                raise
        raise last_exception
    return wrapper


def safe_db_operation(db, operation_func, *args, **kwargs):
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            with _db_write_lock:
                return operation_func(db, *args, **kwargs)
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


def get_db():
    db = SessionLocal()
    try:
        for attempt in range(MAX_RETRIES):
            try:
                db.execute(text("SELECT 1"))
                break
            except OperationalError as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    continue
                raise
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass
