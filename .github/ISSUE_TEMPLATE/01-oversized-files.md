---
name: "\U0001F3CB️ [Critical] Oversized Files (God Objects)"
about: Refactor large files that violate Single Responsibility Principle
title: "[Tech Debt] Refactor oversized files (80KB collaboration.py, 59KB chains.py, 56KB engine.py)"
labels: technical-debt, refactoring, priority-high
assignees: ''
---

## 🔴 Critical Issue: Oversized Files (God Objects)

### Description
Multiple files in the codebase have grown to massive sizes (40-80KB), indicating violation of the Single Responsibility Principle and making them difficult to maintain, test, and understand.

### Location
**Top 5 offenders:**
1. `caas_framework/agents/collaboration.py` - **80KB**
2. `caas_framework/llm/chains.py` - **59KB**
3. `caas_framework/bmad/engine.py` - **56KB**
4. `caas_framework/agents/code_generator.py` - **47KB**
5. `caas_framework/factory/crew_assembler.py` - **40KB**

### Impact
- 🔴 **High cyclomatic complexity** - Hard to reason about control flow
- 🔴 **Poor testability** - Too many responsibilities to test in isolation
- 🔴 **Maintenance nightmare** - Changes require understanding entire file
- 🔴 **Merge conflicts** - High likelihood of concurrent edits
- 🔴 **Likely mixing concerns** - Multiple responsibilities in one module

### Proposed Fix

#### 1. `collaboration.py` (80KB) → Split into submodules:
```
caas_framework/agents/collaboration/
├── __init__.py              # Main orchestrator
├── orchestrator.py          # CollaborationOrchestrator class
├── quality_gates.py         # Quality gate evaluation logic
├── context.py               # CollaborationContext dataclass
├── refinement.py            # Refinement loops and feedback
└── validation.py            # Validation coordination
```

#### 2. `llm/chains.py` (59KB) → Split by chain type:
```
caas_framework/llm/chains/
├── __init__.py              # Chain registry
├── analysis_chains.py       # Requirement analysis chains
├── design_chains.py         # Architecture/design chains
├── generation_chains.py     # Code generation chains
└── validation_chains.py     # Validation chains
```

#### 3. `bmad/engine.py` (56KB) → Extract phase handlers:
```
caas_framework/bmad/
├── engine.py                # Core orchestration only (~500 lines)
├── phases/
│   ├── __init__.py
│   ├── discovery.py         # Phase 1 handler
│   ├── architecture.py      # Phase 2 handler
│   ├── design.py            # Phase 3 handler
│   ├── development.py       # Phase 4 handler
│   └── delivery.py          # Phase 5 handler
```

#### 4. `agents/code_generator.py` (47KB) → Split generators:
```
caas_framework/agents/code_generator/
├── __init__.py              # Main agent class
├── agent_core.py            # Core code generator logic
├── python_generator.py      # Python-specific generation
├── crewai_generator.py      # CrewAI-specific generation
└── template_renderer.py     # Template rendering logic
```

#### 5. `factory/crew_assembler.py` (40KB) → Split assembly steps:
```
caas_framework/factory/
├── crew_assembler.py        # Main orchestration (~500 lines)
├── assembly/
│   ├── agent_builder.py     # Agent assembly
│   ├── task_builder.py      # Task assembly
│   ├── tool_builder.py      # Tool assembly
│   └── validation.py        # Assembly validation
```

### Effort Estimate
**16-24 hours** for all 5 files (3-5 hours each)

### Benefits
- ✅ Easier to navigate and understand
- ✅ Better testability (unit tests per submodule)
- ✅ Clearer separation of concerns
- ✅ Reduced merge conflicts
- ✅ Easier onboarding for new developers

### Acceptance Criteria
- [ ] Each module is < 500 lines of code
- [ ] All existing tests still pass
- [ ] New submodules have clear docstrings
- [ ] Public API remains unchanged (backward compatible)
- [ ] Code coverage maintained or improved

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Blocks: Test coverage improvements (hard to test large files)
- Related: #[LLM Client/Helper Overlap]
