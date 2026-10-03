# API reference

Rendered from `openapi.json`, which `uv run poe gen-openapi` writes from the FastAPI app. The contract and its rules (errors, events, caching) are in [B06 API contract](../phase2/B06_API_CONTRACT.md).

<div id="redoc-container"></div>
<script src="https://cdn.jsdelivr.net/npm/redoc@2.5.0/bundles/redoc.standalone.js"></script>
<script>
  Redoc.init("../../openapi.json", { hideDownloadButton: false }, document.getElementById("redoc-container"));
</script>
