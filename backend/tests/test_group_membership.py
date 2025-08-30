import pytest
from config import settings
import dependencies as deps
import schemas


def test_is_user_in_group_debug(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    u = schemas.User(email="a@b.com")
    assert deps.is_user_in_group(u, "g1") is True


def test_is_user_in_group_non_debug_with_groups(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    u = schemas.User(email="a@b.com", groups=["x", "y"]) 
    assert deps.is_user_in_group(u, "y") is True
    assert deps.is_user_in_group(u, "z") is False
