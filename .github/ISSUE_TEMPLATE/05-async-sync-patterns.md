---
name: "\U0001F504 [Critical] Inconsistent Async/Sync Patterns"
about: Standardize async/await usage across the codebase
title: "[Tech Debt] Standardize async/sync patterns (571 async occurrences)"
labels: technical-debt, architecture, priority-medium
assignees: ''
---

## 🔴 Critical Issue: Inconsistent Async/Sync Patterns

### Current State
- **571 async occurrences** across 56 files
- Mixed async/sync code throughout
- Unclear which modules are async-first vs sync-first

### Impact
- 🟡 **Complexity** - Hard to reason about execution flow
- 🟡 **Performance issues** - Blocking calls in async functions
- 🟡 **Maintenance burden** - Must understand async context everywhere
- 🟡 **Anti-patterns** - Some files await synchronous functions

### Common Anti-Patterns Found

**1. Awaiting sync functions**
```python
# ❌ BAD
async def process():
    result = await sync_function()  # sync_function returns non-awaitable!
```

**2. Blocking in async functions**
```python
# ❌ BAD
async def fetch_data():
    time.sleep(5)  # Blocks entire event loop!
```

**3. Unnecessary async**
```python
# ❌ BAD - no actual async work
async def calculate(x, y):
    return x + y  # Just make this sync!
```

### Proposed Fix

#### Step 1: Audit All Async Functions
```bash
grep -r "async def\|await " caas_framework --include="*.py" > async_audit.txt
```

Categorize:
- ✅ **Legitimate async** - Actually does async I/O
- ⚠️ **Unnecessary async** - No async operations inside
- ❌ **Anti-patterns** - Blocking calls, awaiting sync functions

#### Step 2: Establish Module Conventions
```python
# caas_framework/llm/        - ASYNC-FIRST (network I/O)
# caas_framework/validation/ - SYNC (pure computation)
# caas_framework/bmad/       - ASYNC-FIRST (orchestration)
# caas_framework/codegen/    - SYNC (file generation)
```

#### Step 3: Create Async/Sync Adapters
```python
# caas_framework/utils/async_helpers.py

def sync_to_async(sync_func):
    """Run sync function in thread pool"""
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    return wrapper

async def async_to_sync(async_func, *args, **kwargs):
    """Run async function from sync context"""
    return asyncio.run(async_func(*args, **kwargs))
```

#### Step 4: Document Conventions
```markdown
# ASYNC_CONVENTIONS.md

## Async-First Modules
- `caas_framework/llm/` - Network I/O to LLM APIs
- `caas_framework/bmad/` - Orchestration with I/O
- `caas_framework/agents/` - Agent execution (may call LLM)

## Sync Modules
- `caas_framework/validation/` - Pure computation
- `caas_framework/codegen/` - File generation
- `caas_framework/models/` - Pydantic models (always sync)

## Rules
1. Only use `async` if function does actual async I/O
2. Never `time.sleep()` in async functions (use `asyncio.sleep()`)
3. Never await non-awaitable objects
4. Use `run_in_executor` for CPU-bound work in async context
```

### Effort Estimate
**16-24 hours**

### Benefits
- ✅ Clearer execution model
- ✅ Better performance (no blocking)
- ✅ Easier to reason about concurrency
- ✅ Consistent patterns across codebase

### Acceptance Criteria
- [ ] All async functions actually do async work
- [ ] No blocking calls in async functions
- [ ] No awaiting sync functions
- [ ] Documentation of async conventions
- [ ] All tests pass

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Related: #[Quality Gate Bypass] (async timeout issues)
