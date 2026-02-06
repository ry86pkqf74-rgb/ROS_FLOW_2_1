# Worker import errors backlog

Short list of known import/runtime issues in the worker so they are not forgotten when migrating more stages.

---

## 1. Missing `src.agents.writing.types`

**File:** `services/worker/src/agents/stage17_citation_generation.py` (lines 27–28)

**Issue:** The code imports:

```python
from .writing.types import ReferenceState, CitationStyle, Reference
```

The writing module does not have a `types` module. The types live in **`reference_types.py`** (`services/worker/src/agents/writing/reference_types.py`), which defines `ReferenceState`, `CitationStyle`, `Reference`, etc.

**Suggested fix (choose one):**

- **Option A:** Add `services/worker/src/agents/writing/types.py` that re-exports from `reference_types`:
  ```python
  from .reference_types import ReferenceState, CitationStyle, Reference  # and any others needed
  ```
- **Option B:** Change the import in `stage17_citation_generation.py` to:
  ```python
  from .writing.reference_types import ReferenceState, CitationStyle, Reference
  ```

---

## 2. Logger undefined in `stage17_citation_generation.py`

**File:** `services/worker/src/agents/stage17_citation_generation.py`

**Issue:** `logger` is used inside the `try` block (e.g. `logger.info("Enhanced reference management system available")`) before it is defined. The line `logger = logging.getLogger(__name__)` appears later in the file (after the try/except). If the import of the enhanced reference management system succeeds, the code hits `logger.info(...)` and raises `NameError` because `logger` is not yet defined.

**Suggested fix:** Define the module-level logger before the `try` block that uses it. Move:

```python
logger = logging.getLogger(__name__)
```

to above the block that starts with:

```python
try:
    from .writing.reference_management_service import get_reference_service
    ...
    logger.info("Enhanced reference management system available")
```

So that `logger` is always defined before any use.
