import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def identity_module(monkeypatch, tmp_path):
    """Redirect identity.json to a temp path."""
    import identity
    temp_file = tmp_path / "identity.json"
    monkeypatch.setattr(identity, "IDENTITY_PATH", str(temp_file))
    return identity


def test_default_name_is_boss(identity_module):
    assert identity_module.get_name() == "Boss"
    assert identity_module.has_name() is False


def test_set_name(identity_module):
    r = identity_module.set_name("Pappu")
    assert r["ok"] is True
    assert identity_module.get_name() == "Pappu"
    assert identity_module.has_name() is True


def test_change_requires_confirmation(identity_module):
    identity_module.set_name("Pappu")
    r = identity_module.set_name("Rahul")
    assert r["ok"] is False
    assert r.get("pending") is True
    assert identity_module.get_name() == "Pappu"


def test_change_with_confirmation(identity_module):
    identity_module.set_name("Pappu")
    r = identity_module.set_name("Rahul", confirmed=True)
    assert r["ok"] is True
    assert identity_module.get_name() == "Rahul"


def test_clear_name(identity_module):
    identity_module.set_name("Pappu")
    identity_module.clear_name()
    assert identity_module.get_name() == "Boss"


def test_invalid_name_rejected(identity_module):
    assert identity_module.set_name("")["ok"] is False
    assert identity_module.set_name("x" * 100)["ok"] is False


def test_case_insensitive_same_name(identity_module):
    identity_module.set_name("Pappu")
    r = identity_module.set_name("pappu")
    assert r["ok"] is True  # Same name, different case - allowed
