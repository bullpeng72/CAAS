# Phase 2 Week 4-5: Core Modules Migration Plan

## Current Status Analysis

### BMAD (Business-Multi-Agent-Design)
**Status**: Partially Migrated ⚠️
- `caas_framework/bmad/`: 11 files (some refactored files)
- `app/core/bmad/`: 18 files (original implementations)

**Comparison**:
```
caas_framework/bmad/              app/core/bmad/
├── engine.py (55K)               ├── engine.py (76K) ⚠️ Different!
├── code_analyzer.py (18K)        ├── analyzer.py (9K) ⚠️ Different name!
├── completeness_validator.py     ├── validator.py (13K)
├── feature_extraction.py         ├── (missing equivalent)
├── gap_filler.py                 ├── (missing equivalent)
├── golden_data.py                ├── (missing equivalent)
├── semantic_mapper.py (29K)      ├── mapper.py (17K) ⚠️ Different!
├── traceability.py               ├── (missing equivalent)
├── workflow_integration.py       ├── (missing equivalent)
└── ...                           ├── adaptive.py (8.6K) ❌ Not in framework
                                  ├── deployer.py (13K) ❌ Not in framework
                                  ├── personality.py (12K) ❌ Not in framework
                                  ├── planner.py (12K) ❌ Not in framework
                                  ├── reflection.py (16K) ❌ Not in framework
                                  ├── sharding.py (13K) ❌ Not in framework
                                  ├── task_refiner.py (14K) ❌ Not in framework
                                  ├── tester.py (13K) ❌ Not in framework
                                  └── models.py (1.2K) ❌ Not in framework
```

**Issue**: Framework BMAD appears to be a refactored version, while app/core/bmad has the original implementation with more components.

### SDD (System Design Document)
**Status**: NOT Migrated ❌
- `caas_framework/sdd/`: Does not exist
- `app/core/sdd/`: 4 files (~46K LOC)
  - engine.py (15K)
  - multi_spec.py (11K)
  - spec_converter.py (20K)

### Factory
**Status**: NOT Migrated ❌
- `caas_framework/factory/`: Does not exist
- `app/core/factory/`: 6 files (~77K LOC)
  - crew_assembler.py (40K)
  - agent_factory.py (10K)
  - task_factory.py (6.6K)
  - tool_factory.py (14K)
  - base_factory.py (5.7K)

## Migration Strategy

### Decision: Which BMAD to Use?

**Options**:
1. **Keep caas_framework/bmad** (refactored) and update app/core/bmad to use it
2. **Migrate app/core/bmad** to caas_framework and replace current implementation
3. **Merge both**: Take best of both implementations

**Recommendation**: Option 1 (Keep refactored version)
- caas_framework/bmad appears to be cleaner, more modular
- Less LOC (more maintainable)
- Already follows framework patterns

**Action**: Create backward compatibility layer in app/core/bmad to use caas_framework/bmad

### Step-by-Step Plan

#### Step 1: BMAD Migration (Complete)
**Goal**: Make app/core/bmad use caas_framework/bmad

**Tasks**:
1. Analyze dependency between app/core/bmad files
2. Map app/core/bmad components to caas_framework/bmad equivalents
3. Create compatibility layer in app/core/bmad/__init__.py
4. Update imports in app code to use framework bmad
5. Mark app/core/bmad files as deprecated

**Estimated LOC to migrate/update**: ~0 (use compatibility layer)

#### Step 2: SDD Migration
**Goal**: app/core/sdd → caas_framework/sdd

**Tasks**:
1. Create caas_framework/sdd/ directory
2. Migrate sdd/engine.py (15K)
3. Migrate sdd/spec_converter.py (20K)
4. Migrate sdd/multi_spec.py (11K)
5. Update imports:
   - app.core.sdd → caas_framework.sdd
6. Create backward compatibility shim
7. Test SDD functionality

**Estimated LOC to migrate**: ~46K

#### Step 3: Factory Migration
**Goal**: app/core/factory → caas_framework/factory

**Tasks**:
1. Create caas_framework/factory/ directory
2. Migrate factory/base_factory.py (5.7K)
3. Migrate factory/agent_factory.py (10K)
4. Migrate factory/task_factory.py (6.6K)
5. Migrate factory/tool_factory.py (14K)
6. Migrate factory/crew_assembler.py (40K)
7. Update imports:
   - app.core.factory → caas_framework.factory
8. Create backward compatibility shim
9. Test factory functionality

**Estimated LOC to migrate**: ~77K

#### Step 4: Verification
**Tasks**:
1. Grep for remaining app.core.* imports in caas_framework
2. Run integration tests
3. Verify framework independence
4. Update documentation

## Import Mapping

```python
# Before
from app.core.bmad import BMADEngine
from app.core.sdd import SDDEngine
from app.core.factory import AgentFactory, CrewAssembler

# After
from caas_framework.bmad import BMADEngine
from caas_framework.sdd import SDDEngine
from caas_framework.factory import AgentFactory, CrewAssembler
```

## Success Criteria

✅ All core modules (BMAD, SDD, Factory) accessible from caas_framework
✅ Zero app.core.* imports in caas_framework
✅ Backward compatibility maintained (app.core.* → caas_framework.*)
✅ All existing tests pass
✅ Framework can be imported independently

## Estimated Timeline

- Step 1 (BMAD): 30 minutes (compatibility layer)
- Step 2 (SDD): 1 hour (straightforward migration)
- Step 3 (Factory): 1.5 hours (larger codebase)
- Step 4 (Verification): 30 minutes

**Total**: ~3.5 hours

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing code | Use backward compatibility shims |
| BMAD feature mismatch | Keep app/core/bmad files temporarily |
| Test failures | Extensive testing before committing |
| Import conflicts | Careful sed replacement with verification |

---

**Status**: Ready to execute
**Phase**: Phase 2 Week 4-5 (Core Modules Migration)
**Priority**: High (blocks framework independence)
