---
name: "\U0001F500 [Critical] LLM Client/Helper Overlap"
about: Consolidate duplicate LLM invocation utilities
title: "[Tech Debt] Consolidate LLM Client and LLM Helper modules"
labels: technical-debt, duplication, priority-high
assignees: ''
---

## 🔴 Critical Issue: LLM Client/Helper Overlap

### Description
Two modules provide overlapping LLM invocation functionality, leading to confusion and duplicate code.

### Location
- `caas_framework/llm/client.py` - Unified LLM client for multiple providers
- `caas_framework/utils/llm_helper.py` - Helper utilities for LLM invocation

### Overlap Analysis
Both modules provide:
- LLM invocation with message format
- Error handling and retry logic
- Response parsing

`LLMHelper.invoke_with_message()` duplicates functionality that should be in `LLMClient`.

### Impact
- 🔴 **Unclear separation of concerns** - Which module to use when?
- 🔴 **Code duplication** - Same patterns implemented twice
- 🔴 **Maintenance burden** - Bug fixes need to be applied in two places
- 🔴 **API confusion** - Developers don't know which to import

### Proposed Fix

**Option 1: Merge into llm/client.py (Recommended)**
```python
# caas_framework/llm/client.py
class LLMClient:
    """Unified LLM client with all invocation utilities"""

    def invoke_with_message(self, prompt: str, **kwargs) -> str:
        """Standard message invocation (moved from llm_helper)"""

    def safe_invoke(self, prompt: str, default="", **kwargs) -> str:
        """Safe invocation with error handling (moved from llm_helper)"""
```

**Option 2: Make llm_helper.py a thin wrapper**
```python
# caas_framework/utils/llm_helper.py (deprecated)
from caas_framework.llm.client import LLMClient

class LLMHelper:
    """Deprecated: Use LLMClient directly"""

    @staticmethod
    @deprecated("Use LLMClient.invoke_with_message() instead")
    def invoke_with_message(llm, prompt):
        return LLMClient(llm).invoke_with_message(prompt)
```

### Effort Estimate
**2-4 hours**

### Steps
1. Audit all usage of `LLMHelper` (find references)
2. Move unique functionality from `llm_helper.py` to `llm/client.py`
3. Update all imports to use `LLMClient`
4. Add deprecation warnings to `llm_helper.py`
5. Run tests to verify
6. Remove `llm_helper.py` in next major version

### Benefits
- ✅ Single source of truth for LLM invocation
- ✅ Clearer API surface
- ✅ Easier to maintain and extend
- ✅ Consistent error handling across codebase

### Acceptance Criteria
- [ ] All LLM invocation goes through `llm/client.py`
- [ ] `llm_helper.py` either removed or deprecated
- [ ] All tests pass
- [ ] No regression in error handling
- [ ] Documentation updated

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Related: #[Excessive Logging Setup Duplication]
