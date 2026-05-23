"""记忆管理单元测试"""
import pytest
from src.memory import ShortTermMemory, LongTermMemory, WorkingMemory
from src.memory.working import TaskStatus


def test_short_term_memory():
    m = ShortTermMemory("s1")
    m.add_message("user", "你好")
    m.add_message("assistant", "你好！")
    assert len(m.get_messages()) == 2
    ctx = m.get_context()
    assert "用户" in ctx and "助手" in ctx


def test_short_term_memory_clear():
    m = ShortTermMemory("s2")
    m.add_message("user", "test")
    m.clear()
    assert len(m.get_messages()) == 0


def test_long_term_memory():
    m = LongTermMemory("u1")
    m.update_preference("cat", "电子产品")
    assert m.get_preference("cat") == "电子产品"
    assert m.get_preference("missing", "default") == "default"


def test_long_term_memory_interactions():
    m = LongTermMemory("u2")
    m.add_interaction({"type": "search", "query": "iPhone"})
    interactions = m.get_recent_interactions()
    assert len(interactions) == 1
    assert "timestamp" in interactions[0]


def test_working_memory():
    m = WorkingMemory("s1")
    task = m.create_task("t1", "查库存")
    assert task.status == TaskStatus.PENDING
    updated = m.update_task("t1", status=TaskStatus.COMPLETED)
    assert updated.status == TaskStatus.COMPLETED


def test_working_memory_context():
    m = WorkingMemory("s1")
    m.set_context("order_id", "ORD001")
    assert m.get_context("order_id") == "ORD001"
    assert m.get_context("missing") is None
