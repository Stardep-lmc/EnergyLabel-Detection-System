"""集成测试：API 端点"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_config_get():
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert "positionTolerance" in data


def test_config_post():
    cfg = {
        "models": [{"name": "测试", "model": "TEST-001", "standardLabel": "A++", "enabled": True}],
        "positionTolerance": 10,
        "sensitivity": "中",
        "lightCompensation": 0,
        "camera": {"exposure": 0, "resolution": "1280x720"},
    }
    r = client.post("/api/config", json=cfg)
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_ml_status():
    r = client.get("/api/ml/status")
    assert r.status_code == 200
    assert "available" in r.json()


def test_history_empty():
    r = client.get("/api/history?page=1&pageSize=10")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "records" in data


def test_statistic():
    r = client.get("/api/statistic")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_csv():
    r = client.get("/api/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


def test_export_summary():
    r = client.get("/api/export/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "pass_rate" in data