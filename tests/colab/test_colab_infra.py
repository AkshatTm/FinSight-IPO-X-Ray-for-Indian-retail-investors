"""C0.2: Colab helpers, compute log and HF upload helper (CPU only, temp dirs, fake client)."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


common = load("colab_common", "notebooks/colab/_common.py")
log_compute = load("log_compute", "scripts/log_compute.py")
hf_upload = load("hf_upload", "scripts/hf_upload.py")


def test_checkpointer_syncs_and_resumes(tmp_path: Path) -> None:
    ck = common.Checkpointer(tmp_path / "local", tmp_path / "drive", every=2)
    ck.append("raw.jsonl", {"id": "a"})
    assert not (tmp_path / "drive" / "raw.jsonl").exists()  # below the interval
    ck.append("raw.jsonl", {"id": "b"})
    assert (tmp_path / "drive" / "raw.jsonl").exists()
    ck.append("raw.jsonl", {"id": "c"})
    ck.sync()
    # new runtime: empty local disk, Drive has the data
    ck2 = common.Checkpointer(tmp_path / "local2", tmp_path / "drive", every=2)
    assert ck2.done_ids("raw.jsonl") == {"a", "b", "c"}


def test_done_ids_ignores_torn_line(tmp_path: Path) -> None:
    ck = common.Checkpointer(tmp_path / "l", tmp_path / "d")
    ck.path("x.jsonl").write_text('{"id": "a"}\n{"id": "b', encoding="utf-8")
    assert ck.done_ids("x.jsonl") == {"a"}


def test_latest_trainer_checkpoint(tmp_path: Path) -> None:
    ck = common.Checkpointer(tmp_path / "l", tmp_path / "d")
    assert ck.latest_trainer_checkpoint() is None
    for n in (5, 20, 100):
        (ck.local / "trainer" / f"checkpoint-{n}").mkdir(parents=True)
    assert ck.latest_trainer_checkpoint().endswith("checkpoint-100")


def test_mount_drive_local_fallback(tmp_path: Path) -> None:
    out = common.mount_drive("job", root=tmp_path)
    assert out == tmp_path / "job"
    assert out.is_dir()


def test_gpu_class() -> None:
    assert common.gpu_class("NVIDIA A100-SXM4-80GB") == "A100"
    assert common.gpu_class("NVIDIA L4") == "L4"
    assert common.gpu_class("Tesla T4") == "T4"
    assert common.gpu_class("RTX 2050") == "other"


def test_run_summary_units(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(common, "gpu_info", lambda: {"gpu": "NVIDIA L4", "driver": "580.82.07"})
    monkeypatch.setattr(common.time, "time", lambda: 7200.0)
    s = common.run_summary(
        tmp_path, "t", started=0.0, units_before=100.0, units_after=96.92, items_done=5
    )
    assert s["gpu_class"] == "L4"
    assert s["units_used"] == 3.08
    assert s["units_per_hour_observed"] == 1.54
    assert json.loads((tmp_path / "run_summary.json").read_text())["job"] == "t"


def test_log_compute_schema_and_dedupe(tmp_path: Path) -> None:
    log = tmp_path / "c" / "compute_log.jsonl"
    row = {"job": "j", "finished_utc": "2026-01-01T00:00:00+00:00", "gpu_class": "T4"}
    assert log_compute.append_rows([row, row], log) == 1
    assert log_compute.append_rows([row], log) == 0
    with pytest.raises(ValueError, match="missing"):
        log_compute.append_rows([{"job": "x"}], log)
    assert len(log_compute.read_log(log)) == 1


def test_log_compute_manual_cli(tmp_path: Path) -> None:
    log = tmp_path / "l.jsonl"
    rc = log_compute.main(
        [
            "--log",
            str(log),
            "--manual",
            "--job",
            "rate_check",
            "--gpu-class",
            "A100",
            "--units-per-hour",
            "6.77",
        ]
    )
    assert rc == 0
    row = log_compute.read_log(log)[0]
    assert row["units_per_hour_observed"] == 6.77
    assert "manual" in row["source"]


def test_hf_refuses_merged_weights(tmp_path: Path) -> None:
    (tmp_path / "model.safetensors").write_bytes(b"x")
    with pytest.raises(hf_upload.UploadRefused):
        hf_upload.collect([tmp_path])
    with pytest.raises(hf_upload.UploadRefused):
        hf_upload.check_file(tmp_path / "pytorch_model.bin")


def test_hf_allows_adapter_gguf_onnx(tmp_path: Path) -> None:
    for n in ("adapter_model.safetensors", "adapter_config.json", "m.gguf", "c.onnx", "README.md"):
        (tmp_path / n).write_bytes(b"x")
    assert len(hf_upload.collect([tmp_path])) == 5


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def create_repo(self, repo, private, exist_ok):
        self.calls.append(("create", repo, private))

    def upload_file(self, path_or_fileobj, path_in_repo, repo_id):
        self.calls.append(("up", path_in_repo, repo_id))


def test_hf_upload_private_with_fake_client(tmp_path: Path) -> None:
    (tmp_path / "adapter_config.json").write_text("{}")
    fc = FakeClient()
    files = hf_upload.collect([tmp_path])
    names = hf_upload.upload(files, tmp_path, "AkshatTm/finsight-x", fc)
    assert names == ["adapter_config.json"]
    assert fc.calls[0] == ("create", "AkshatTm/finsight-x", True)
    dry = FakeClient()
    hf_upload.upload(files, tmp_path, "r/x", dry, dry_run=True)
    assert dry.calls == []


def test_colab_notebooks_are_current_and_valid() -> None:
    mk = load("make_colab_notebooks", "scripts/make_colab_notebooks.py")
    assert mk.main(["--check"]) == 0
    for name in mk.BUILDERS:
        nb = json.loads((mk.OUT / name).read_text(encoding="utf-8"))
        assert nb["nbformat"] == 4
        code = [c for c in nb["cells"] if c["cell_type"] == "code"]
        for c in code:  # every code cell must at least parse
            compile("".join(c["source"]), name, "exec")
        assert any("parameters" in c["metadata"].get("tags", []) for c in code)
        assert any("run_summary" in "".join(c["source"]) for c in code)


def _cell_source(nb: dict, tag: str | None = None, index: int | None = None) -> str:
    cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    if tag is not None:
        [c] = [c for c in cells if tag in c["metadata"].get("tags", [])]
        return "".join(c["source"])
    assert index is not None
    return "".join(cells[index]["source"])


@pytest.mark.parametrize(
    ("gpu_gb", "slugs"),
    [(80, ["qwen3-14b-awq", "qwen3-32b-awq"]), (24, ["qwen3-14b-awq"])],  # L4-only fallback
)
def test_teacher_notebook_runs_end_to_end_with_fake_vllm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gpu_gb: int, slugs: list[str]
) -> None:
    """Smoke (C2.2): the real cells run on 20 fake risks with stub torch/vllm and Drive in tmp."""
    import sys
    import types

    from real import loader

    from finsight.risks import teacher

    mk = load("make_colab_notebooks", "scripts/make_colab_notebooks.py")
    nb = mk.teacher()
    job = tmp_path / "drive" / "teacher_bakeoff"
    job.mkdir(parents=True)
    rows = loader.fake_risks()
    (job / "bakeoff_risks.jsonl").write_text(
        "\n".join(json.dumps({"risk_id": f"r{i}", "title": r.get("title", ""), "body": r["body"]})
                  for i, r in enumerate(rows)), encoding="utf-8")  # fmt: skip

    torch = types.ModuleType("torch")
    torch.__version__ = "0-fake"
    torch.cuda = types.SimpleNamespace(
        get_device_properties=lambda i: types.SimpleNamespace(total_memory=gpu_gb * 1024**3),
        empty_cache=lambda: None,
    )
    vllm = types.ModuleType("vllm")
    reply = json.dumps({"category": "financial", "seriousness_1to5": 3, "hard_fact": True,
                        "simple": "A short plain sentence.", "numbers_copied": []})  # fmt: skip

    class FakeLLM:
        def __init__(self, **kw: object) -> None:
            self.kw = kw

        def chat(self, chats, params, use_tqdm=False, chat_template_kwargs=None):  # type: ignore[no-untyped-def]
            assert chat_template_kwargs == {"enable_thinking": False}
            return [
                types.SimpleNamespace(outputs=[types.SimpleNamespace(text=reply)]) for _ in chats
            ]

    vllm.LLM = FakeLLM
    vllm.SamplingParams = lambda **kw: kw
    sp = types.ModuleType("vllm.sampling_params")
    sp.GuidedDecodingParams = lambda json: {"json": json}
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "vllm", vllm)
    monkeypatch.setitem(sys.modules, "vllm.sampling_params", sp)
    monkeypatch.setattr(common, "DRIVE_ROOT", tmp_path / "drive")

    ns: dict = {"mount_drive": lambda j: common.mount_drive(j, root=tmp_path / "drive"),
                "Checkpointer": lambda local_dir, drive_dir, every: common.Checkpointer(
                    tmp_path / "local", drive_dir, every),
                "run_summary": common.run_summary, "gpu_info": common.gpu_info,
                "unassign_runtime": common.unassign_runtime, "STARTED": 0.0}  # fmt: skip
    exec(_cell_source(nb, "parameters"), ns)
    ns.update(SMOKE=True, EVERY=7)
    exec(_cell_source(nb, "teacher-run"), ns)
    exec(_cell_source(nb, "teacher-prompt"), ns)
    assert ns["messages"]("T", "b") == teacher.messages("T", "b")
    exec(_cell_source(nb, index=-2), ns)  # body
    exec(_cell_source(nb, index=-1), ns)  # run_summary
    out = job / "out"
    assert sorted(p.name for p in out.glob("raw_*.jsonl")) == [f"raw_{s}.jsonl" for s in slugs]
    for slug in slugs:
        raw = (out / f"raw_{slug}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(raw) == 20  # SMOKE: 20 risks per model
        assert json.loads(raw[0])["model"].lower().endswith(slug)
        assert json.loads((out / f"run_summary_{slug}.json").read_text())["written"] == 20
    assert json.loads((job / "run_summary.json").read_text())["job"] == "teacher_bakeoff"
