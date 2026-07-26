from src.Infrastructure.Worker.tasks.ping_task import ping


def test_ping_task_roundtrip():
    result = ping.delay("hello")
    output = result.get(timeout=10)
    assert output == {"message": "hello", "worker": "ok"}


def test_ping_task_different_message():
    result = ping.delay("world")
    output = result.get(timeout=10)
    assert output["message"] == "world"
    assert output["worker"] == "ok"
