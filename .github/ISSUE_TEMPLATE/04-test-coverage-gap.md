---
name: "\U0001F9EA [Critical] Test Coverage Gap (20% → 80%)"
about: Improve test coverage to production-ready levels
title: "[Tech Debt] Improve test coverage from 20% to 80%"
labels: testing, technical-debt, priority-high
assignees: ''
---

## 🔴 Critical Issue: Test Coverage Gap

### Current State
- **Framework files**: 236 Python files
- **Test files**: 47 test files
- **Coverage ratio**: ~0.2 (20%)
- **Target**: 80%+ coverage

### Impact
- 🔴 **High risk of regressions** - Changes may break existing functionality
- 🔴 **Low confidence in refactoring** - Can't safely restructure code
- 🔴 **Difficult debugging** - Unclear where bugs originate
- 🔴 **Poor documentation** - Tests serve as usage examples

### Priority Areas (Critical Paths)

**Phase 1: Core Workflows (40 hours)**
1. **BMAD Engine** (`caas_framework/bmad/engine.py`) - 56KB, 0 dedicated tests
2. **Code Generators** (`caas_framework/codegen/`) - High risk
3. **Validators** (`caas_framework/validation/`) - Quality assurance

**Phase 2: Expert Agents (20 hours)**
4. **Collaboration** (`caas_framework/agents/collaboration.py`) - 80KB
5. **Agent Designer** (`caas_framework/agents/agent_designer.py`)
6. **Code Generator Agent** (`caas_framework/agents/code_generator.py`)

**Phase 3: Framework Core (20 hours)**
7. **Framework** (`caas_framework/framework.py`)
8. **Plugin System** (`caas_framework/plugins/`)
9. **LLM Clients** (`caas_framework/llm/`)

### Proposed Approach

#### 1. Set Up Coverage Tracking
```bash
pytest --cov=caas_framework --cov-report=html --cov-report=term-missing
```

Add to CI/CD:
```yaml
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: |
    pytest --cov=caas_framework --cov-report=xml --cov-report=term
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
```

#### 2. Focus on Integration Tests
E2E tests for major workflows:
- `tests/test_e2e_full_generation.py` - Complete generation workflow
- `tests/test_e2e_bmad_phases.py` - All 6 BMAD phases
- `tests/test_e2e_validation.py` - Validation pipeline

#### 3. Add Unit Tests for Critical Paths
```python
# tests/test_bmad_engine.py
def test_phase_0_concretization():
    """Test Golden Data generation"""

def test_phase_1_discovery():
    """Test requirement analysis"""

def test_phase_execution_sequence():
    """Test phases execute in order"""
```

### Effort Estimate
**40-80 hours** (incremental over 2-3 sprints)
- Phase 1: 40 hours
- Phase 2: 20 hours
- Phase 3: 20 hours

### Benefits
- ✅ Safe refactoring
- ✅ Faster debugging
- ✅ Better documentation (tests as examples)
- ✅ Higher code quality
- ✅ Easier onboarding

### Acceptance Criteria
- [ ] Overall coverage ≥ 80%
- [ ] Critical paths coverage ≥ 90%
- [ ] All public APIs have tests
- [ ] E2E tests for major workflows
- [ ] Coverage tracked in CI/CD
- [ ] Coverage badge in README

### Metrics to Track
- Lines covered / Total lines
- Branch coverage (>75%)
- Function coverage (>85%)
- Class coverage (>80%)

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Blocked by: #[Oversized Files] (hard to test large files)
- Enables: Safe refactoring initiatives

### Incremental Plan
**Sprint 1** (20 hours): BMAD Engine + Core workflows → 40% coverage
**Sprint 2** (20 hours): Expert Agents + Validation → 60% coverage
**Sprint 3** (20 hours): Plugins + Utilities → 80% coverage
