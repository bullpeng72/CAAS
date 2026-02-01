# Models Migration Strategy - Phase 2 Week 3

**Date:** 2026-02-01
**Task:** R2.1 - Models & LLM Migration
**Status:** Planning

---

## Executive Summary

The migration of `app/models/` to `caas_framework/models/` is more complex than initially anticipated due to:
- **Class conflicts**: 11 duplicate classes with different implementations
- **Import dependencies**: 93 files affected (32 from app.models, 61 from caas_framework.models)
- **Circular patterns**: 3 files import from BOTH locations
- **Version divergence**: Critical classes have evolved in both places

**Strategy**: Phased migration with backward compatibility shim to prevent breaking changes.

---

## Problem Analysis

### 1. Duplicate Classes (Critical)

| Class | app.models.schemas | caas_framework.models | Status |
|-------|-------------------|----------------------|--------|
| **ConcretizedRequirement** | 143 LOC, quality metrics | 95 LOC, 6 core specs | **DIVERGED** |
| **AgentSpecModel** | With llm field | Simplified | **CONFLICT** |
| **TaskSpecModel** | More fields | Basic fields | **CONFLICT** |
| **ValidationIssue** | Basic | Comprehensive | **CONFLICT** |
| **ValidationResult** | Basic | Comprehensive | **CONFLICT** |
| **GoldenValidationReport** | Old structure | New structure | **CONFLICT** |
| **ComplianceStatus** | Enum | Enum | **DUPLICATE** |
| **MissingItem** | Old | New | **CONFLICT** |
| **ExtraItem** | Old | New | **CONFLICT** |
| **MismatchedItem** | Old | New | **CONFLICT** |
| **FeatureSpec** | Old | New | **CONFLICT** |

### 2. Classes Only in app.models (Must Migrate)

**High-priority** (used by 5+ files):
- `RequirementAnalysis` (used by 19 files)
- `ArchitectureDesign` (used by 5 files)
- `QualityMetrics` (used by 8 files)

**Medium-priority** (used by 2-4 files):
- `CrewSpec`
- `GeneratedProject`
- `DataModelSpec`
- `UIPageRequirement`
- `BackendAPIRequirement`

**Low-priority** (used by 1 file):
- `WorkflowType`, `ProjectTemplate`, `HTTPMethod` (enums)
- `LLMConfigSpec`
- `AgentRequirement`, `TaskRequirement`

### 3. Cross-Dependencies (Critical)

```python
# Framework depends on app (VIOLATION)
caas_framework/validation/golden_validator.py:
    from app.models.schemas import ConcretizedRequirement  # ❌

caas_framework/bmad/engine.py:
    from app.models.artifact_types import ArtifactType  # ❌
```

---

## Migration Strategy

### Phase 1: Unify Models (This Week)

**Goal**: Create single source of truth in `caas_framework/models/`

#### Step 1.1: Create Unified Models Module

**Create:**
- `caas_framework/models/schemas.py` - Merge ALL classes from both sources
- `caas_framework/models/artifact_types.py` - Move from app/
- `caas_framework/models/domain_types.py` - Move from app/
- `caas_framework/models/tool_registry.py` - Move from app/

**Strategy for Conflicts:**
1. **ConcretizedRequirement**: Use caas_framework version (newer, 6 core specs)
2. **AgentSpecModel**: Use app version (more complete, has llm field)
3. **TaskSpecModel**: Use app version (more complete)
4. **Validation models**: Use caas_framework version (more comprehensive)
5. **Analysis models**: Move RequirementAnalysis, ArchitectureDesign from app

#### Step 1.2: Create Backward Compatibility Shim

**Update `app/models/__init__.py`:**
```python
"""
Backward Compatibility Shim

This module re-exports from caas_framework.models to maintain
backward compatibility. All new code should import from caas_framework.

DEPRECATED: This module will be removed in v3.0
"""

import warnings

# Re-export everything from caas_framework
from caas_framework.models.schemas import *
from caas_framework.models.artifact_types import *
from caas_framework.models.domain_types import *
from caas_framework.models.tool_registry import *
from caas_framework.models.specifications import *
from caas_framework.models.validation import *

warnings.warn(
    "Importing from app.models is deprecated. "
    "Use 'from caas_framework.models import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)
```

#### Step 1.3: Update Framework Imports

**Update these files to use caas_framework.models:**
- `caas_framework/validation/golden_validator.py` (remove app.models import)
- `caas_framework/bmad/engine.py` (remove app.models import)
- All other caas_framework/* files (ensure consistent imports)

#### Step 1.4: Test Backward Compatibility

**Verify:**
```python
# Old imports still work (with deprecation warning)
from app.models.schemas import ConcretizedRequirement  # ✅ Works
from app.models import RequirementAnalysis  # ✅ Works

# New imports work
from caas_framework.models import ConcretizedRequirement  # ✅ Works
from caas_framework.models import RequirementAnalysis  # ✅ Works

# Both point to same class
assert app.models.schemas.ConcretizedRequirement is caas_framework.models.ConcretizedRequirement
```

---

### Phase 2: Update Framework Imports (This Week)

**Goal**: Ensure all caas_framework/* uses caas_framework.models

**Files to update (61+ files):**
- All caas_framework/validation/*
- All caas_framework/bmad/*
- All caas_framework/codegen/*
- All caas_framework/agents/*
- All caas_framework/fixing/*

**Change:**
```python
# Before
from caas_framework.models.specifications import ConcretizedRequirement

# After (if needed, but mostly already correct)
from caas_framework.models import ConcretizedRequirement
```

---

### Phase 3: Gradual App Migration (Optional, Future)

**Goal**: Gradually update app/* imports (not required for framework independence)

**Can be done later:**
- Update app/llm/* (5 files)
- Update app/core/* (13 files)
- Update app/codegen/* (5 files)
- Update app/artifacts/* (3 files)
- Update app/workflow/* (2 files)

**No rush** - backward compatibility shim allows old imports to work.

---

## Implementation Plan

### Week 3 Day 1-2: Unify Models

**Tasks:**
1. ✅ Analyze current state (DONE)
2. Create `caas_framework/models/schemas.py` (unified)
   - Merge classes from app/models/schemas.py
   - Merge classes from caas_framework/models/specifications.py
   - Resolve conflicts (use newer/more complete version)
3. Move supporting modules:
   - app/models/artifact_types.py → caas_framework/models/artifact_types.py
   - app/models/domain_types.py → caas_framework/models/domain_types.py
   - app/models/tool_registry.py → caas_framework/models/tool_registry.py
4. Update `caas_framework/models/__init__.py` to export all
5. Create backward compatibility shim in `app/models/__init__.py`

### Week 3 Day 3: Update Framework Imports

**Tasks:**
1. Update caas_framework/validation/golden_validator.py
2. Update caas_framework/bmad/engine.py
3. Run tests to verify no breakage
4. Update any other caas_framework/* files with old imports

### Week 3 Day 4: LLM Migration

**Tasks:**
1. Create `caas_framework/llm/` directory
2. Move all files from app/llm/ to caas_framework/llm/:
   - chains.py (1,488 LOC)
   - client.py (352 LOC)
   - response_parser.py (506 LOC)
   - chain_factory.py (293 LOC)
3. Update imports in moved files
4. Create backward compatibility shim in app/llm/__init__.py

### Week 3 Day 5: Testing & Validation

**Tasks:**
1. Run full test suite
2. Check for circular dependencies
3. Verify framework independence:
   - caas_framework should NOT import from app
   - app CAN import from caas_framework
4. Write migration tests
5. Update documentation

---

## Success Criteria

✅ **Framework Independence:**
- Zero imports from app/* in caas_framework/*
- Framework can be used standalone

✅ **Backward Compatibility:**
- All existing code works without changes
- Deprecation warnings guide users to new imports

✅ **No Duplicates:**
- Each model class exists in exactly ONE location
- app.models is pure re-export shim

✅ **Tests Pass:**
- All existing tests pass
- New migration tests added

---

## Risk Mitigation

### Risk 1: Breaking Changes

**Mitigation**: Backward compatibility shim in app.models
- Old imports redirect to new location
- Deprecation warnings (not errors)
- Gradual migration path

### Risk 2: Circular Dependencies

**Mitigation**: Clear dependency direction
- caas_framework → self-contained
- app → caas_framework (one-way)
- Tests detect circular imports

### Risk 3: Merge Conflicts

**Mitigation**: Automated conflict resolution
- For duplicates, choose newer/more complete version
- Document all merge decisions
- Preserve all functionality

### Risk 4: Test Failures

**Mitigation**: Incremental validation
- Test after each file migration
- Rollback if tests fail
- Fix before proceeding

---

## Files to Create/Modify

### New Files (4)
1. `caas_framework/models/schemas.py` (merged, ~1,500 LOC)
2. `caas_framework/models/artifact_types.py` (moved, ~171 LOC)
3. `caas_framework/models/domain_types.py` (moved, ~227 LOC)
4. `caas_framework/models/tool_registry.py` (moved, ~872 LOC)

### Modified Files (10+)
1. `caas_framework/models/__init__.py` (updated exports)
2. `app/models/__init__.py` (backward compat shim)
3. `app/models/schemas.py` (deprecated marker)
4. `caas_framework/validation/golden_validator.py` (import update)
5. `caas_framework/bmad/engine.py` (import update)
6. Plus 5+ other framework files

### Deprecated Files (4)
1. `app/models/schemas.py` → Use caas_framework.models.schemas
2. `app/models/artifact_types.py` → Use caas_framework.models.artifact_types
3. `app/models/domain_types.py` → Use caas_framework.models.domain_types
4. `app/models/tool_registry.py` → Use caas_framework.models.tool_registry

---

## Next Steps

1. **Execute Step 1.1**: Create unified models module
2. **Execute Step 1.2**: Create backward compatibility shim
3. **Execute Step 1.3**: Update framework imports
4. **Execute Step 1.4**: Test and validate

**Estimated Time:** 1-2 days for models, 1 day for LLM, 1 day for testing = 3-4 days total

---

**Status:** READY TO EXECUTE
**Approved:** Pending user confirmation
