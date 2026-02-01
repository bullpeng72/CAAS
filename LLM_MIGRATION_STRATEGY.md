# LLM Migration Strategy: app/llm → caas_framework/llm

## Overview

Migrate LLM functionality from `app/llm/` to `caas_framework/llm/` to achieve framework independence while maintaining backward compatibility.

## Current Structure

```
app/llm/
├── __init__.py (55 LOC)
├── chains.py (1,488 LOC) - Chain implementations
├── chain_factory.py (293 LOC) - Factory pattern for chains
├── client.py (352 LOC) - LLM client interface
└── response_parser.py (506 LOC) - Response parsing utilities

Total: 2,694 LOC
```

## Issues Found

### Missing Prompts Directory
`chains.py` imports from `app/llm/prompts.*` which doesn't exist:
- `app.llm.prompts.analysis` - Analysis prompts
- `app.llm.prompts.domain_classification` - Domain classification prompts
- `app.llm.prompts.spec_generation` - Spec generation prompts
- `app.llm.prompts.concretization` - Concretization prompts

**Resolution**: Create stub prompt modules during migration as placeholders.

## Dependencies Analysis

### External Dependencies (Need Updates)

| Current | New | Files Affected |
|---------|-----|----------------|
| `app.utils.logger` | `logging` (stdlib) | All files |
| `app.utils.config` | `caas_framework.config` | client.py |
| `app.utils.json_helper` | `caas_framework.utils.json_helper` | chains.py, response_parser.py |
| `app.models.schemas` | `caas_framework.models` | chains.py |
| `app.models.domain_types` | `caas_framework.models` | chains.py |
| `app.knowledge.ontology` | Keep as-is (app layer) | chains.py |

### Internal Dependencies (Within llm/)

| Current | New |
|---------|-----|
| `app.llm.client` | `caas_framework.llm.client` |
| `app.llm.chains` | `caas_framework.llm.chains` |
| `app.llm.chain_factory` | `caas_framework.llm.chain_factory` |
| `app.llm.response_parser` | `caas_framework.llm.response_parser` |
| `app.llm.prompts.*` | `caas_framework.llm.prompts.*` (new) |

## Migration Steps

### Step 2.1: Create Prompt Stubs ✓
Create placeholder prompt modules:
- `caas_framework/llm/prompts/__init__.py`
- `caas_framework/llm/prompts/analysis.py`
- `caas_framework/llm/prompts/domain_classification.py`
- `caas_framework/llm/prompts/spec_generation.py`
- `caas_framework/llm/prompts/concretization.py`

### Step 2.2: Migrate Core Modules
Migrate in dependency order:

**2.2a: client.py** (352 LOC)
- Update: `app.utils.config` → `caas_framework.config`
- Update: `app.utils.logger` → `logging`
- Create: `caas_framework/llm/client.py`

**2.2b: response_parser.py** (506 LOC)
- Update: `app.utils.logger` → `logging`
- Update: `app.utils.json_helper` → `caas_framework.utils.json_helper`
- Create: `caas_framework/llm/response_parser.py`

**2.2c: chain_factory.py** (293 LOC)
- Update: `app.utils.logger` → `logging`
- Create: `caas_framework/llm/chain_factory.py`

**2.2d: chains.py** (1,488 LOC)
- Update: `app.llm.prompts.*` → `caas_framework.llm.prompts.*`
- Update: `app.utils.json_helper` → `caas_framework.utils.json_helper`
- Update: `app.utils.logger` → `logging`
- Update: `app.models.schemas` → `caas_framework.models`
- Update: `app.models.domain_types` → `caas_framework.models`
- Update: `app.llm.chain_factory` → `caas_framework.llm.chain_factory`
- Update: `app.llm.client` → `caas_framework.llm.client` (TYPE_CHECKING)
- Keep: `app.knowledge.ontology` (app layer dependency)
- Create: `caas_framework/llm/chains.py`

**2.2e: __init__.py** (55 LOC)
- Update exports to use new paths
- Create: `caas_framework/llm/__init__.py`

### Step 2.3: Create Backward Compatibility Shim
Create `app/llm/__init__.py` that re-exports from `caas_framework.llm/`:
```python
import warnings
warnings.warn(
    "Importing from app.llm is deprecated. "
    "Use 'from caas_framework.llm import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)
from caas_framework.llm import *
```

### Step 2.4: Update Framework Imports
Search and update any framework files that import from `app.llm`:
```bash
grep -r "from app\.llm" caas_framework/
```

### Step 2.5: Test Migration
- Import all classes from both paths
- Verify identity (old imports === new imports)
- Test chain creation and execution
- Verify response parsing

### Step 2.6: Commit & Document
- Commit migrated files
- Update documentation
- Create migration completion report

## Special Considerations

### 1. Optional Dependencies (LangChain)
`chains.py` has optional LangChain imports with graceful fallback:
```python
try:
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
```
✓ Keep this pattern during migration

### 2. App Layer Dependencies
`chains.py` imports from `app.knowledge.ontology`:
```python
from app.knowledge.ontology import (
    AgentRole, TaskType, ROLE_TASK_MAPPINGS, TASK_TOOL_MAPPINGS
)
```
✓ Keep these imports (framework can depend on app for knowledge)

### 3. Logging Strategy
Replace `app.utils.logger.get_logger()` with standard `logging.getLogger()`:
```python
# Before
from app.utils.logger import get_logger
logger = get_logger("llm.chains")

# After
import logging
logger = logging.getLogger("caas_framework.llm.chains")
```

### 4. JSONHelper Availability
Verify `caas_framework.utils.json_helper` exists, or create it if missing.

## File Structure After Migration

```
caas_framework/
└── llm/
    ├── __init__.py (55 LOC)
    ├── client.py (352 LOC)
    ├── response_parser.py (506 LOC)
    ├── chain_factory.py (293 LOC)
    ├── chains.py (1,488 LOC)
    └── prompts/
        ├── __init__.py
        ├── analysis.py (stub)
        ├── domain_classification.py (stub)
        ├── spec_generation.py (stub)
        └── concretization.py (stub)

app/
└── llm/
    └── __init__.py (backward compat shim)
```

## Success Criteria

✅ All 2,694 LOC migrated successfully
✅ Zero `app.llm` imports in caas_framework (except app knowledge dependencies)
✅ Backward compatibility maintained (app.llm → caas_framework.llm)
✅ Deprecation warnings issued
✅ All imports work from both paths
✅ Framework independence achieved (except allowed app knowledge dependency)

## Estimated LOC Changes

- Files migrated: 5 files (2,694 LOC)
- Prompt stubs created: 4 files (~100 LOC)
- Backward compat shim: 1 file (~30 LOC)
- Framework updates: TBD (depends on grep results)

Total new/modified: ~2,824 LOC

## Timeline

- Step 2.1: Prompt stubs (10 min)
- Step 2.2: Core migration (60 min)
- Step 2.3: Backward compat (10 min)
- Step 2.4: Framework updates (15 min)
- Step 2.5: Testing (20 min)
- Step 2.6: Commit & docs (10 min)

**Total**: ~2 hours

---

**Status**: Ready to execute
**Phase**: Phase 2 Week 3 (Models & LLM Migration)
**Risk**: Low (following proven models migration pattern)
