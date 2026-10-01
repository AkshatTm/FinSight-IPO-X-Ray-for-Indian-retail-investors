import threading
import time
from pathlib import Path

from finsight.voice import AsrManager, Transcript


class FakeBackend:
    def __init__(self) -> None:
        self.loaded = False
        self.load_calls = 0
        self.unload_calls = 0
        self.running = threading.Event()
        self.release = threading.Event()
        self.block = False

    def load(self) -> float:
        self.loaded = True
        self.load_calls += 1
        return 0.1

    def unload(self) -> None:
        self.loaded = False
        self.unload_calls += 1

    def transcribe_detailed(self, audio_path: Path, language: str = "hi") -> Transcript:
        if self.block:
            self.running.set()
            self.release.wait(2)
        return Transcript("नमस्ते", language, 3.0, 0.5, "fake")


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_lazy_load_on_first_use_only() -> None:
    backend, clock = FakeBackend(), Clock()
    manager = AsrManager(backend, clock=clock)
    assert manager.status() == {"loaded": False, "lazy": True, "idle_s": None, "loads": 0}
    manager.transcribe(Path("a.m4a"))
    manager.transcribe(Path("b.m4a"))
    assert backend.load_calls == 1
    assert manager.status()["loaded"] is True


def test_unloads_after_the_idle_period_not_before() -> None:
    backend, clock = FakeBackend(), Clock()
    manager = AsrManager(backend, idle_s=120, clock=clock)
    manager.transcribe(Path("a.m4a"))
    clock.now += 119
    assert not manager.unload_if_idle()
    assert backend.loaded
    clock.now += 2
    assert manager.unload_if_idle()
    assert not backend.loaded
    assert not manager.unload_if_idle()  # nothing left to unload


def test_use_resets_the_idle_timer_and_reload_counts() -> None:
    backend, clock = FakeBackend(), Clock()
    manager = AsrManager(backend, idle_s=120, clock=clock)
    manager.transcribe(Path("a.m4a"))
    clock.now += 100
    manager.transcribe(Path("b.m4a"))
    clock.now += 100
    assert not manager.unload_if_idle()
    clock.now += 30
    assert manager.unload_if_idle()
    manager.transcribe(Path("c.m4a"))
    assert manager.loads == 2


def test_never_unloads_under_a_running_request() -> None:
    backend = FakeBackend()
    backend.block = True
    clock = Clock()
    manager = AsrManager(backend, idle_s=0, clock=clock)
    worker = threading.Thread(target=lambda: manager.transcribe(Path("a.m4a")))
    worker.start()
    assert backend.running.wait(2)
    result: list[bool] = []
    checker = threading.Thread(target=lambda: result.append(manager.unload_if_idle()))
    checker.start()
    time.sleep(0.05)
    assert backend.loaded  # still waiting for the lock: not unloaded mid-request
    backend.release.set()
    worker.join(2)
    checker.join(2)
    assert backend.unload_calls <= 1


def test_watchdog_thread_unloads_an_idle_model() -> None:
    backend = FakeBackend()
    manager = AsrManager(backend, idle_s=0.05)
    manager.transcribe(Path("a.m4a"))
    manager.start(poll_s=0.01)
    deadline = time.time() + 2
    while backend.loaded and time.time() < deadline:
        time.sleep(0.01)
    manager.stop()
    assert not backend.loaded
