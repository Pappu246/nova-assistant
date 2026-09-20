import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def memory_module(monkeypatch, tmp_path):
    """Redirect DB to temp path."""
    import memory
    temp_db = tmp_path / "test_memory.db"
    monkeypatch.setattr(memory, "DB_PATH", str(temp_db))
    memory.init_db()
    return memory


def test_save_and_get(memory_module):
    memory_module.save_fact("test_key", "test_value")
    assert memory_module.get_fact("test_key") == "test_value"


def test_update_fact(memory_module):
    memory_module.save_fact("k", "v1")
    memory_module.save_fact("k", "v2")
    assert memory_module.get_fact("k") == "v2"


def test_forget_fact(memory_module):
    memory_module.save_fact("k", "v")
    memory_module.forget_fact("k")
    assert memory_module.get_fact("k") is None


def test_missing_key_returns_none(memory_module):
    assert memory_module.get_fact("nonexistent") is None


def test_list_facts_empty(memory_module):
    result = memory_module.list_facts()
    assert "kuch yaad nahi" in result.lower() or "nahi" in result.lower()


def test_list_facts_with_data(memory_module):
    memory_module.save_fact("user_name", "Pappu")
    result = memory_module.list_facts()
    assert "Pappu" in result
