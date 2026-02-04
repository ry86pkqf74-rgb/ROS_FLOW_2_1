# Developer Guide

Guide for extending the ResearchFlow workflow (adding or modifying stages) and running tests.

## Adding a New Stage

You can implement a stage in one of two ways.

### Option 1: Stage protocol + `@register_stage`

Implement the `Stage` protocol and decorate the class with `@register_stage`.

**Requirements:**

- Class attributes: `stage_id` (int, 1–20), `stage_name` (str)
- Method: `async def execute(self, context: StageContext) -> StageResult`

**Example:**

```python
# services/worker/src/workflow_engine/stages/stage_NN_myname.py
from ..types import StageContext, StageResult
from ..registry import register_stage

@register_stage
class MyStage:
    stage_id = 99   # use an unused ID 1–20
    stage_name = "My Stage"

    async def execute(self, context: StageContext) -> StageResult:
        # ... use context.job_id, context.config, context.previous_results
        return StageResult(
            stage_id=self.stage_id,
            stage_name=self.stage_name,
            status="completed",
            started_at=...,
            completed_at=...,
            duration_ms=...,
            output={...},
            artifacts=[],
            errors=[],
            warnings=[],
            metadata={},
        )
```

**Where to put code:** `services/worker/src/workflow_engine/stages/stage_NN_name.py` (e.g. `stage_03_irb.py`).

**Registration:** Add an import in `services/worker/src/workflow_engine/stages/__init__.py` so the module is loaded and `@register_stage` runs:

```python
from . import stage_NN_myname
```

### Option 2: Subclass `BaseStageAgent`

Use the base class for LangChain/LangGraph integration and ManuscriptClient (TypeScript service calls).

**Requirements:**

- Subclass `BaseStageAgent`
- Set `stage_id` and `stage_name`
- Implement: `execute(context: StageContext) -> StageResult`, `get_tools() -> List[BaseTool]`, `get_prompt_template() -> PromptTemplate`
- Decorate with `@register_stage`

**Optional overrides:**

- `build_graph()` — LangGraph workflow (if `use_langgraph=True`)
- `get_quality_criteria()` — quality gate criteria

**Example:**

```python
# services/worker/src/workflow_engine/stages/stage_NN_myname.py
from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

@register_stage
class MyAgent(BaseStageAgent):
    stage_id = 99
    stage_name = "My Stage"

    async def execute(self, context: StageContext) -> StageResult:
        # ... implementation
        return StageResult(...)

    def get_tools(self):
        return []  # or list of LangChain tools

    def get_prompt_template(self):
        from langchain_core.prompts import PromptTemplate
        return PromptTemplate.from_template("...")
```

**Where to put code:** Same as Option 1: `stages/stage_NN_name.py`.

**Registration:** Same as Option 1: add the import in `stages/__init__.py`.

### Stage ID rules

- **Integer between 1 and 20** (inclusive).
- **Unique** — one stage per ID. If the ID is already registered, the decorator raises `ValueError`.
- To replace a stage, either change the existing module or renumber/remove the old one and register the new one.

**Note:** Stage 4 currently has two modules (`stage_04_hypothesis`, `stage_04_validate`). Only one is imported in `__init__.py` (hypothesis); the other is commented out due to ID conflict. See [STAGES.md](STAGES.md#stage-04-hypothesis-refinement).

---

## Testing

### Unit tests (pytest)

Tests live under `services/worker/tests/`.

**Run all worker tests:**

```bash
cd services/worker
pytest tests/ -v
```

Or from repo root:

```bash
pytest services/worker/tests/ -v
```

**Run a single file or test:**

```bash
pytest services/worker/tests/test_health_endpoints.py -v
pytest services/worker/tests/test_health_endpoints.py::test_health_returns_200 -v
```

### Stage and workflow tests

- **Health/API:** [services/worker/tests/test_health_endpoints.py](https://github.com/ry86pkqf74-rgb/researchflow-production/blob/main/services/worker/tests/test_health_endpoints.py) — FastAPI app health.
- **Ingest API:** [services/worker/tests/test_ingest_api.py](https://github.com/ry86pkqf74-rgb/researchflow-production/blob/main/services/worker/tests/test_ingest_api.py) — multi-file ingest router.
- **Workflow/stage tests:** Add tests under `services/worker/tests/` that instantiate your stage, build a `StageContext` (e.g. mock `previous_results`), call `await stage.execute(context)`, and assert on `StageResult.status`, `output`, `errors`.

**Example stage test:**

```python
import pytest
from src.workflow_engine.registry import get_stage
from src.workflow_engine.types import StageContext, StageResult

@pytest.mark.asyncio
async def test_my_stage_execute():
    cls = get_stage(99)
    assert cls is not None
    stage = cls()
    context = StageContext(job_id="test-1", config={}, governance_mode="DEMO")
    result = await stage.execute(context)
    assert isinstance(result, StageResult)
    assert result.stage_id == 99
    assert result.status in ("completed", "failed", "skipped")
```

### Integration and local dev

- **Local setup (without full Docker):** [docs/LOCAL_DEV.md](LOCAL_DEV.md)
- **Contribution and PR process:** [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Conventions

- **Docstrings:** Add a module docstring (stage purpose), class docstring (stage role, inputs/outputs if helpful), and docstrings for `execute`, `get_tools`, `get_prompt_template` (and `build_graph` if overridden). See [STAGES.md](STAGES.md) for I/O semantics.
- **No PHI in logs:** Do not log raw PHI. Use sanitized messages or structured logging without patient identifiers.
- **Governance mode:** Use `context.governance_mode` when behavior must differ between DEMO and LIVE (e.g. PHI handling, external APIs).
- **Errors:** Populate `StageResult.errors` with PHI-sanitized messages; use `warnings` for non-fatal issues.

---

## Reference

| Resource | Description |
|----------|-------------|
| [STAGES.md](STAGES.md) | All 20 stages: purpose, inputs, outputs |
| [services/worker/src/workflow_engine/registry.py](https://github.com/ry86pkqf74-rgb/researchflow-production/blob/main/services/worker/src/workflow_engine/registry.py) | `@register_stage`, `get_stage`, `list_stages` |
| [services/worker/src/workflow_engine/types.py](https://github.com/ry86pkqf74-rgb/researchflow-production/blob/main/services/worker/src/workflow_engine/types.py) | `StageContext`, `StageResult`, `Stage` protocol |
| [services/worker/src/workflow_engine/stages/base_stage_agent.py](https://github.com/ry86pkqf74-rgb/researchflow-production/blob/main/services/worker/src/workflow_engine/stages/base_stage_agent.py) | `BaseStageAgent` |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Code of conduct, setup, PR process |
| [LOCAL_DEV.md](LOCAL_DEV.md) | Local development without full Docker |
