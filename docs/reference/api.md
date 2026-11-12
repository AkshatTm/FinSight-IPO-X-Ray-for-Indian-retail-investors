# OpenAPI reference

Rendered from `openapi.json`, which `uv run poe gen-openapi` writes from the FastAPI app (CI checks it is
current with `uv run poe gen-openapi --check`). Worked examples with curl are in the
[API guide](api-guide.md).

<div id="redoc-container"></div>
<script src="https://cdn.jsdelivr.net/npm/redoc@2.5.0/bundles/redoc.standalone.js"></script>
<script>
  Redoc.init("../../openapi.json", { hideDownloadButton: false }, document.getElementById("redoc-container"));
</script>
