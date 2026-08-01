"""Test infrastructure."""
import os, tempfile, shutil, atexit, logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.core.security import get_password_hash, create_access_token
from app.models.user import UserProfile
from app.models.product import Product

logger = logging.getLogger(__name__)

# ── Disable Redis for tests (prevents 5s connection timeouts) ──
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

@pytest.fixture(autouse=True)
def disable_redis(monkeypatch):
    """Mock Redis to avoid connection timeouts in tests."""
    def _mock_get_redis():
        return None
    monkeypatch.setattr("app.core.redis.get_redis_client", _mock_get_redis)
    monkeypatch.setattr("app.core.redis.is_redis_available", lambda: False)
    yield


# ── Database engine: DATABASE_URL env → PostgreSQL, else SQLite fallback ──
_database_url = os.environ.get("DATABASE_URL")
_is_ci = os.environ.get("CI", "").lower() in ("true", "1", "yes")

if _database_url:
    # DATABASE_URL explicitly set — must use it, fail hard if unreachable
    try:
        _test_engine = create_engine(_database_url)
        with _test_engine.connect():
            pass
    except Exception as e:
        raise RuntimeError(
            f"DATABASE_URL={_database_url} connection failed: {e}. "
            "DATABASE_URL is explicitly set; refusing to silently downgrade to SQLite."
        ) from e
elif _is_ci:
    raise RuntimeError(
        "CI=true but DATABASE_URL is not set. "
        "CI must connect to a real PostgreSQL instance. "
        "Set DATABASE_URL in your CI configuration."
    )
else:
    # SQLite fallback — only for local dev without DATABASE_URL and not in CI
    _tmpdir = tempfile.mkdtemp(prefix="test_cms_")
    _test_db = os.path.join(_tmpdir, "test.db")
    atexit.register(lambda: shutil.rmtree(_tmpdir, ignore_errors=True))
    _test_engine = create_engine(
        f"sqlite:///{_test_db}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Rebuild database before each test."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture(autouse=True)
def clear_rate_limiter(monkeypatch):
    # P0: Mock RateLimiter.check to always allow in tests (Redis is disabled)
    monkeypatch.setattr("app.core.redis.RateLimiter.check", lambda *a, **kw: True)
    yield


@pytest.fixture
def db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(db):
    user = UserProfile(
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        display_name="Test Admin",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def editor_user(db):
    user = UserProfile(
        email="editor@test.com",
        password_hash=get_password_hash("editor123"),
        display_name="Test Editor",
        role="editor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_user(db):
    user = UserProfile(
        email="viewer@test.com",
        password_hash=get_password_hash("viewer123"),
        display_name="Test Viewer",
        role="viewer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    return create_access_token({"sub": admin_user.id})


@pytest.fixture
def editor_token(editor_user):
    return create_access_token({"sub": editor_user.id})


@pytest.fixture
def viewer_token(viewer_user):
    return create_access_token({"sub": viewer_user.id})


@pytest.fixture
def reviewer_user(db):
    user = UserProfile(
        email="reviewer@test.com",
        password_hash=get_password_hash("reviewer123"),
        display_name="Test Reviewer",
        role="reviewer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def reviewer_token(reviewer_user):
    return create_access_token({"sub": reviewer_user.id})


@pytest.fixture
def disabled_user(db):
    user = UserProfile(
        email="disabled@test.com",
        password_hash=get_password_hash("disabled123"),
        display_name="Test Disabled",
        role="viewer",
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def disabled_user_token(disabled_user):
    return create_access_token({"sub": disabled_user.id})


@pytest.fixture
def sample_product(db, admin_user):
    product = Product(
        sku="TEST-001",
        product_name_zh="Test Product ZH",
        product_name_en="Test Product",
        category="General",
        brand="TestBrand",
        color_zh="Red",
        color_en="Red",
        material_zh="Plastic",
        material_en="Plastic",
        price=9.99,
        currency="USD",
        stock=50,
        weight=0.5,
        weight_unit="kg",
        origin="China",
        created_by=admin_user.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
