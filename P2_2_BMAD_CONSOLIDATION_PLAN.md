# P2.2: BMADEngine Consolidation Plan

## Current Situation

### Two BMAD Versions Coexist

**app/core/bmad/** (Original - 18 files, ~247K)
- Monolithic engine.py (76K)
- Component-based: adaptive, analyzer, deployer, mapper, personality, planner, reflection, sharding, task_refiner, tester, validator
- Usage: 32 imports across app/
- Status: Original implementation, feature-complete

**caas_framework/bmad/** (Refactored - 11 files, ~245K)
- Refactored engine.py (55K)
- Refactored components: code_analyzer, completeness_validator, feature_extraction, gap_filler, golden_data, semantic_mapper, traceability, workflow_integration
- Usage: 27 imports across codebase
- Status: Cleaner architecture, modular

### Problem

- Code duplication (~247K LOC)
- Two versions create confusion
- Maintenance burden (update both versions)
- Violates DRY principle

## Consolidation Strategy

### Decision: Keep Framework Version, Create Compatibility Layer

**Rationale**:
1. Framework version has cleaner architecture
2. Smaller engine.py (55K vs 76K) - better separation of concerns
3. Already in framework (proper location)
4. More modular components

### Approach

#### Step 1: Map Components (app → framework)

| app/core/bmad | caas_framework/bmad | Status |
|---------------|---------------------|--------|
| engine.py (76K) | engine.py (55K) | Use framework (refactored) |
| analyzer.py | code_analyzer.py | Equivalent (rename) |
| validator.py | completeness_validator.py | Equivalent (rename) |
| mapper.py | semantic_mapper.py | Enhanced version |
| reflection.py | ⚠️ Missing | Need to migrate |
| adaptive.py | ⚠️ Missing | Need to migrate |
| personality.py | ⚠️ Missing | Need to migrate |
| planner.py | ⚠️ Missing | Need to migrate |
| sharding.py | ⚠️ Missing | Need to migrate |
| task_refiner.py | ⚠️ Missing | Need to migrate |
| tester.py | ⚠️ Missing | Need to migrate |
| deployer.py | ⚠️ Missing | Need to migrate |
| models.py | ⚠️ Missing | Need to migrate |

#### Step 2: Migrate Missing Components

**Priority 1 (High Usage)**:
- reflection.py (4 uses) → caas_framework/bmad/reflection.py
- models.py (2 uses) → caas_framework/bmad/models.py

**Priority 2 (Low Usage)**:
- adaptive.py, personality.py, planner.py, sharding.py, task_refiner.py, tester.py, deployer.py

#### Step 3: Create Backward Compatibility Layer

Create app/core/bmad/__init__.py that:
1. Re-exports from caas_framework.bmad
2. Provides aliases for renamed components:
   ```python
   from caas_framework.bmad.code_analyzer import CodeAnalyzer as Analyzer
   from caas_framework.bmad.completeness_validator import CompletenessValidator as Validator
   ```
3. Issues deprecation warnings

#### Step 4: Update Imports

Update all app/ files to use framework imports:
```bash
find app/ -name "*.py" -exec sed -i \
  's/from app\.core\.bmad/from caas_framework.bmad/g' {} +
```

## Detailed Steps

### Step 2.1: Migrate High-Priority Components

**Migrate reflection.py**:
```bash
cp app/core/bmad/reflection.py caas_framework/bmad/reflection.py
# Update imports in reflection.py
sed -i 's/from app\./from caas_framework./g' caas_framework/bmad/reflection.py
```

**Migrate models.py**:
```bash
cp app/core/bmad/models.py caas_framework/bmad/models.py
# Update imports
sed -i 's/from app\./from caas_framework./g' caas_framework/bmad/models.py
```

### Step 2.2: Migrate Low-Priority Components

Migrate remaining components one by one:
- adaptive.py
- personality.py
- planner.py
- sharding.py
- task_refiner.py
- tester.py
- deployer.py

### Step 2.3: Create Compatibility Layer

```python
# app/core/bmad/__init__.py
import warnings

warnings.warn(
    "Importing from app.core.bmad is deprecated. "
    "Use 'from caas_framework.bmad import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything
from caas_framework.bmad import *

# Component aliases for backward compatibility
from caas_framework.bmad.code_analyzer import CodeAnalyzer as Analyzer
from caas_framework.bmad.completeness_validator import CompletenessValidator as Validator
from caas_framework.bmad.semantic_mapper import SemanticMapper as Mapper
```

### Step 2.4: Update App Imports

Use sed to update all imports:
```bash
find app/ -name "*.py" -exec sed -i \
  -e 's/from app\.core\.bmad\.analyzer import/from caas_framework.bmad.code_analyzer import/g' \
  -e 's/from app\.core\.bmad\.validator import/from caas_framework.bmad.completeness_validator import/g' \
  -e 's/from app\.core\.bmad\.mapper import/from caas_framework.bmad.semantic_mapper import/g' \
  -e 's/from app\.core\.bmad import/from caas_framework.bmad import/g' \
  {} +
```

## Expected Outcomes

### Code Reduction
- Remove ~247K LOC of duplicated code from app/core/bmad
- Keep only ~11 files in caas_framework/bmad (+ migrated components)
- Total reduction: ~200K LOC (keeping only one version)

### Improved Maintainability
- Single source of truth for BMAD logic
- Clear module ownership (framework)
- Easier to update and extend

### Maintained Compatibility
- All existing imports continue to work (via compatibility layer)
- Deprecation warnings guide migration
- Zero breaking changes

## Verification

```bash
# 1. Check framework has all components
ls caas_framework/bmad/*.py

# 2. Check no direct app/core/bmad imports in active code
grep -r "from app\.core\.bmad" app/ --include="*.py" | grep -v __init__.py

# 3. Run tests
pytest tests/

# 4. Verify backward compatibility
python -c "from app.core.bmad import BMADEngine; print('OK')"
```

## Timeline

- Step 2.1: Migrate high-priority (30 min)
- Step 2.2: Migrate low-priority (1 hour)
- Step 2.3: Create compatibility layer (15 min)
- Step 2.4: Update imports (30 min)
- Testing & verification (30 min)

**Total**: ~3 hours

---

**Status**: Ready to execute
**Priority**: High (eliminates major code duplication)
**Risk**: Low (backward compatibility maintained)
