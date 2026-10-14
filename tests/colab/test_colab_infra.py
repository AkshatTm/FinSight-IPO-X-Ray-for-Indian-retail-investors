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
    """Smoke (C2.2): the real cells run on 20 fake risks, stub torch/vllm, a folder as the Hub."""
    import sys
    import types

    from real import loader

    from finsight.risks import teacher

    mk = load("make_colab_notebooks", "scripts/make_colab_notebooks.py")
    nb = mk.teacher()
    hub = common.DirBackend(tmp_path / "hub")
    rows = loader.fake_risks()
    src = tmp_path / "bakeoff_risks.jsonl"
    src.write_text(
        "\n".join(json.dumps({"risk_id": f"r{i}", "title": r.get("title", ""), "body": r["body"]})
                  for i, r in enumerate(rows)), encoding="utf-8")  # fmt: skip
    hub.put([(src, "bakeoff/in/bakeoff_risks.jsonl")])

    torch = types.ModuleType("torch")
    torch.__version__ = "0-fake"
    torch.cuda = types.SimpleNamespace(
        get_device_properties=lambda i: types.SimpleNamespace(total_memory=gpu_gb * 1024**3),
        get_device_name=lambda i: "NVIDIA A100-SXM4-80GB" if gpu_gb == 80 else "NVIDIA L4",
        get_device_capability=lambda i=0: (8, 0),
        empty_cache=lambda: None,
    )
    vllm = types.ModuleType("vllm")
    reply = json.dumps({"category": "financial", "seriousness_1to5": 3, "hard_fact": True,
                        "simple": "A short plain sentence.", "numbers_copied": []})  # fmt: skip
    seen_kw: list[dict] = []

    class FakeLLM:
        def __init__(self, **kw: object) -> None:
            seen_kw.append(kw)

        def chat(self, chats, params, use_tqdm=False, chat_template_kwargs=None):  # type: ignore[no-untyped-def]
            assert chat_template_kwargs == {"enable_thinking": False}
            assert params["max_tokens"] == 300
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

    unassigned: list[bool] = []
    ns: dict = {
        "JobIO": lambda job, io, hf_repo=None, token=None: common.JobIO(
            job, "hf", store=hub, work=tmp_path / "work"),
        "hf_secret": lambda: "x", "gpu_config": common.gpu_config,
        "run_summary": common.run_summary,
        "gpu_info": common.gpu_info, "STARTED": 0.0,
        "unassign_runtime": lambda enabled: unassigned.append(enabled),
    }  # fmt: skip
    exec(_cell_source(nb, "parameters"), ns)
    assert ns["PRESET"] == "bakeoff_smoke"
    assert ns["IO"] == "hf"
    assert ns["UNASSIGN"] is True
    assert ns["MAX_TOKENS"] == 300
    ns.update(EVERY=7)
    exec(_cell_source(nb, "teacher-run"), ns)
    exec(_cell_source(nb, "teacher-prompt"), ns)
    assert ns["messages"]("T", "b") == teacher.messages("T", "b")
    exec(_cell_source(nb, "teacher-main"), ns)
    out = tmp_path / "hub" / "bakeoff" / "out"  # every batch was uploaded to the "Hub"
    assert sorted(p.name for p in out.glob("raw_*.jsonl")) == [f"raw_{s}.jsonl" for s in slugs]
    for slug in slugs:
        raw = (out / f"raw_{slug}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(raw) == 20  # SMOKE: 20 risks per model
        assert json.loads(raw[0])["model"].lower().endswith(slug)
        assert json.loads((out / f"run_summary_{slug}.json").read_text())["written"] == 20
    final = json.loads((out / "run_summary.json").read_text())
    assert final["job"] == "bakeoff"
    assert final["preset"] == "bakeoff_smoke"
    assert all(kw["quantization"] == "awq_marlin" for kw in seen_kw)
    assert unassigned == [True]  # the runtime is released at the end


def test_teacher_notebook_releases_gpu_on_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    mk = load("make_colab_notebooks", "scripts/make_colab_notebooks.py")
    nb = mk.teacher()
    torch = types.ModuleType("torch")
    torch.cuda = types.SimpleNamespace(
        get_device_properties=lambda i: (_ for _ in ()).throw(RuntimeError("no gpu")),
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "vllm", types.ModuleType("vllm"))
    monkeypatch.setitem(sys.modules, "vllm.sampling_params", types.ModuleType("x"))
    vllm = sys.modules["vllm"]
    vllm.LLM = vllm.SamplingParams = object  # type: ignore[attr-defined]
    unassigned: list[bool] = []
    ns: dict = {"unassign_runtime": lambda enabled: unassigned.append(enabled), "STARTED": 0.0}
    exec(_cell_source(nb, "parameters"), ns)
    with pytest.raises(RuntimeError, match="no gpu"):
        exec(_cell_source(nb, "teacher-main"), ns)
    assert unassigned == [True]


def test_checkpointer_resumes_from_the_hub_on_a_new_runtime(tmp_path: Path) -> None:
    hub = common.DirBackend(tmp_path / "hub")
    ck = common.Checkpointer(tmp_path / "a", None, every=1, store=hub, remote_prefix="j/out")
    ck.append("raw.jsonl", {"id": "x"})
    ck.append("raw.jsonl", {"id": "y"})
    fresh = common.Checkpointer(tmp_path / "b", None, every=1, store=hub, remote_prefix="j/out")
    assert fresh.done_ids("raw.jsonl") == {"x", "y"}


@pytest.mark.parametrize(
    ("name", "gb", "tier", "quant"),
    [
        ("NVIDIA H100 80GB HBM3", 79.1, "H100", "awq_marlin"),
        ("NVIDIA A100-SXM4-80GB", 79.2, "A100-80GB", "awq_marlin"),
        ("NVIDIA A100-SXM4-40GB", 39.5, "A100-40GB", "awq_marlin"),
        ("NVIDIA L4", 22.5, "L4", "awq_marlin"),
        ("Tesla T4", 14.6, "T4", "awq"),
        ("NVIDIA RTX PRO 6000 Blackwell Server Edition", 95.0, "G4", "awq_marlin"),
    ],
)
def test_gpu_config_by_tier(name: str, gb: float, tier: str, quant: str) -> None:
    cfg = common.gpu_config(name, gb)
    assert (cfg["tier"], cfg["quant"]) == (tier, quant)
    assert 0.8 <= cfg["gpu_mem"] <= 0.95


def test_gpu_config_g4_blackwell() -> None:
    """Colab G4 = RTX PRO 6000 Blackwell (sm120, 96 GB): FP8 + NVFP4 native, big batches."""
    name = "NVIDIA RTX PRO 6000 Blackwell Server Edition"
    assert common.gpu_class(name) == "G4"
    cfg = common.gpu_config(name, 95.0, (12, 0))
    assert (cfg["tier"], cfg["fp8_ok"], cfg["nvfp4_ok"]) == ("G4", True, True)
    assert (cfg["max_num_seqs"], cfg["batch"]) == (256, 512)
    assert common.OBSERVED_UNITS_PER_HOUR["G4"] == 8.9
    assert not common.gpu_config("NVIDIA L4", 22.0).get("batch")  # small GPUs keep the preset batch


def _teacher_helpers() -> dict:
    """``model_fits`` and ``load_kwargs`` from the generated teacher-main cell."""
    mk = load("make_colab_notebooks", "scripts/make_colab_notebooks.py")
    src = _cell_source(mk.teacher(), "teacher-main")
    ns: dict = {"QUANT_OVERRIDE": None}
    exec("import re\n" + src[src.index("def model_fits") : src.index("def main")], ns)
    return ns


def test_teacher_load_kwargs_by_checkpoint_type(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    fake = types.ModuleType("transformers")  # offline: VLM configs have a vision_config
    fake.AutoConfig = types.SimpleNamespace(  # type: ignore[attr-defined]
        from_pretrained=lambda repo: types.SimpleNamespace(
            vision_config={} if "Qwen3.8" in repo else None
        )
    )
    monkeypatch.setitem(sys.modules, "transformers", fake)
    ns = _teacher_helpers()
    awq = ns["load_kwargs"]("Qwen/Qwen3-32B-AWQ", "awq_marlin")
    assert (awq["quantization"], awq["dtype"]) == ("awq_marlin", "float16")
    assert "limit_mm_per_prompt" not in awq
    for repo in ("Qwen/Qwen3.8-27B-FP8", "google/gemma-4-31B-it-qat-w4a16-ct",
                 "mistralai/Mistral-Small-4-119B-2603-NVFP4"):  # fmt: skip
        kw = ns["load_kwargs"](repo, "awq_marlin")
        assert (kw["quantization"], kw["dtype"]) == (None, "auto")  # scheme from the checkpoint
    vlm = ns["load_kwargs"]("Qwen/Qwen3.8-27B-FP8", "awq_marlin")
    assert vlm["limit_mm_per_prompt"] == {"image": 0, "video": 0}  # text-only


def test_teacher_model_fits_by_size_and_precision() -> None:
    fits = _teacher_helpers()["model_fits"]
    assert fits("Qwen/Qwen3.8-27B-FP8", 95.0, 0.90)
    assert not fits("Qwen/Qwen3.8-27B-FP8", 22.0, 0.90)  # ~34 GiB FP8 does not fit an L4
    assert fits("Qwen/Qwen3-32B-AWQ", 79.0, 0.92)
    assert fits("mistralai/Mistral-Small-4-119B-2603-NVFP4", 95.0, 0.90)
    assert not fits("mistralai/Mistral-Small-4-119B-2603-NVFP4", 79.0, 0.92)


def test_gpu_config_unknown_gpu_uses_capability() -> None:
    assert common.gpu_config("NVIDIA RTX 6000 Ada", 48, (8, 9))["quant"] == "awq_marlin"
    assert common.gpu_config("Some Old GPU", 12, (7, 5))["quant"] == "awq"


def test_jobio_modes(tmp_path: Path) -> None:
    hub = common.DirBackend(tmp_path / "hub")
    src = tmp_path / "in.jsonl"
    src.write_text("{}\n", encoding="utf-8")
    hub.put([(src, "job/in/in.jsonl")])
    io = common.JobIO("job", "hf", store=hub, work=tmp_path / "w")
    assert io.fetch_input("in.jsonl").read_text() == "{}\n"
    with pytest.raises(FileNotFoundError):
        io.fetch_input("nope.jsonl")
    with pytest.raises(ValueError, match="HF_TOKEN"):
        common.JobIO("job", "hf", work=tmp_path / "w2")
    drive = common.JobIO("job", "drive", drive_root=tmp_path / "drive", work=tmp_path / "w3")
    assert drive.fetch_input("a.jsonl") == tmp_path / "drive" / "job" / "a.jsonl"
