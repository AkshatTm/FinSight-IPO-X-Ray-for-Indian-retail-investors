"""B3.3a: the Cloud Run definitions, Dockerfiles and workflows agree with the code and hold no
secrets. Nothing here talks to Google Cloud."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

from finsight.core.config import ENV_KEYS, JobsConfig, load_settings

ROOT = Path(__file__).resolve().parents[2]
GCP = ROOT / "deploy" / "gcp"

SPEC = importlib.util.spec_from_file_location("render_deploy", ROOT / "scripts/render_deploy.py")
assert SPEC is not None
assert SPEC.loader is not None
render_deploy = importlib.util.module_from_spec(SPEC)
sys.modules["render_deploy"] = render_deploy
SPEC.loader.exec_module(render_deploy)

VALUES = {
    "GCP_PROJECT": "demo-proj",
    "GCP_REGION": "asia-southeast1",
    "IMAGE_TAG": "v1",
    "FINSIGHT_BUCKET": "demo-bucket",
    "SUPABASE_URL": "https://x.supabase.co",
    "VERCEL_HOST": "finsight.vercel.app",
}


def rendered(name: str) -> dict:  # type: ignore[type-arg]
    text = render_deploy.render((GCP / name).read_text(encoding="utf-8"), VALUES)
    return json.loads(text) if name.endswith(".json") else yaml.safe_load(text)


def containers(doc: dict) -> list[dict]:  # type: ignore[type-arg]
    spec = doc["spec"]["template"]["spec"]
    return (
        spec["containers"] if doc["kind"] == "Service" else spec["template"]["spec"]["containers"]
    )


def test_templates_use_only_known_placeholders() -> None:
    for path in render_deploy.templates():
        assert render_deploy.placeholders(path.read_text(encoding="utf-8")) <= set(
            render_deploy.NAMES
        ), path.name
    with pytest.raises(KeyError, match="IMAGE_TAG"):
        render_deploy.render("x: ${IMAGE_TAG}", {})


def test_job_names_match_the_launcher_config() -> None:
    jobs = JobsConfig()
    assert rendered("worker-job.yaml")["metadata"]["name"] == jobs.cpu_job_name
    assert rendered("gpu-job.yaml")["metadata"]["name"] == jobs.gpu_job_name


def test_images_regions_and_profiles() -> None:
    expected = {
        "api-service.yaml": ("api", "cloud"),
        "worker-job.yaml": ("worker", "cloud"),
        "gpu-job.yaml": ("gpu-worker", "cloud_gpu"),
        "sweep-job.yaml": ("worker", "cloud"),
    }
    for name, (image, profile) in expected.items():
        doc = rendered(name)
        assert doc["metadata"]["labels"]["cloud.googleapis.com/location"] == "asia-southeast1"
        (c,) = containers(doc)
        assert c["image"] == f"asia-southeast1-docker.pkg.dev/demo-proj/finsight/{image}:v1"
        env = {e["name"]: e.get("value") for e in c["env"]}
        assert env["FINSIGHT_PROFILE"] == profile
        load_settings(profile)  # the profile exists


def test_secrets_are_references_never_values() -> None:
    known = set(ENV_KEYS) | {"FINSIGHT_ROOT"}
    for name in ("api-service.yaml", "worker-job.yaml", "gpu-job.yaml", "sweep-job.yaml"):
        (c,) = containers(rendered(name))
        for e in c["env"]:
            assert e["name"] in known, (name, e["name"])
            if e["name"] in {"FINSIGHT_DB__URL", "FINSIGHT_AUTH__JWT_SECRET"}:
                assert "valueFrom" in e, (name, e["name"])
                assert "value" not in e, (name, e["name"])
    secretish = re.compile(r"postgres(ql)?://|eyJ[A-Za-z0-9_-]{10,}|AKIA|-----BEGIN|service_role")
    for path in [*GCP.iterdir(), *(ROOT / "deploy").glob("*.Dockerfile")]:
        assert not secretish.search(path.read_text(encoding="utf-8")), path.name


def test_cost_guards() -> None:
    api = rendered("api-service.yaml")["spec"]["template"]
    assert api["metadata"]["annotations"]["autoscaling.knative.dev/minScale"] == "0"
    assert int(api["metadata"]["annotations"]["autoscaling.knative.dev/maxScale"]) <= 3
    gpu = rendered("gpu-job.yaml")["spec"]["template"]
    assert gpu["metadata"]["annotations"]["run.googleapis.com/gpu-zonal-redundancy-disabled"]
    inner = gpu["spec"]["template"]["spec"]
    assert inner["nodeSelector"]["run.googleapis.com/accelerator"] == "nvidia-l4"
    assert inner["containers"][0]["resources"]["limits"]["nvidia.com/gpu"] == "1"
    lifecycle = rendered("gcs-lifecycle.json")["rule"][0]
    retention = load_settings("cloud").uploads.retention_days
    assert lifecycle["condition"]["age"] > retention  # the sweep job deletes first
    assert lifecycle["condition"]["matchesPrefix"] == ["docs/"]


def test_volumes_are_read_only_gcs_mounts() -> None:
    for name in ("api-service.yaml", "worker-job.yaml", "gpu-job.yaml"):
        doc = rendered(name)
        spec = doc["spec"]["template"]["spec"]
        volumes = (
            spec["volumes"] if doc["kind"] == "Service" else spec["template"]["spec"]["volumes"]
        )
        for v in volumes:
            assert v["csi"]["driver"] == "gcsfuse.run.googleapis.com"
            assert v["csi"]["readOnly"] is True
        ann = doc["spec"]["template"]["metadata"]["annotations"]
        assert ann["run.googleapis.com/execution-environment"] == "gen2"


def test_cpu_images_have_no_torch_and_gpu_image_is_not_built_in_pr_ci() -> None:
    for name in ("api", "worker"):
        text = (ROOT / "deploy" / f"{name}.Dockerfile").read_text(encoding="utf-8")
        assert "--group ml " not in text
        assert "torch" not in text.replace("no torch", "")
        assert "--no-default-groups" in text
        assert "--frozen" in text
    for path in [ROOT / "Dockerfile", *(ROOT / "deploy").glob("*.Dockerfile")]:
        # the prebuilt "CPU" wheels there are musl-linked and fail on Debian (B3.3a CI)
        assert "abetlen.github.io" not in path.read_text(encoding="utf-8"), path.name
    lint = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "-f deploy/gpu.Dockerfile" not in lint  # hadolint only, never built in PR CI


def test_images_workflow_is_manual_and_keyless() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/images.yml").read_text(encoding="utf-8"))
    triggers = wf[True]  # YAML 1.1 reads the `on:` key as True
    assert set(triggers) == {"workflow_dispatch"}
    text = (ROOT / ".github/workflows/images.yml").read_text(encoding="utf-8")
    assert "workload_identity_provider" in text
    assert "credentials_json" not in text
    assert "secrets." not in text
