---
name: "📊 [Medium] Excessive Logging Setup Duplication"
about: Consolidate logging initialization across 74 files
title: "[Tech Debt] Consolidate logging setup (171 occurrences)"
labels: technical-debt, code-quality, priority-medium
assignees: ''
---

## 🟡 Medium Priority: Excessive Logging Setup Duplication

### Current State
- **171 occurrences** of `import logging` + `logger = logging.getLogger(__name__)` across **74 files**

### Pattern
```python
# Repeated in 74 files
import logging

logger = logging.getLogger(__name__)
```

### Impact
- 🟡 **Boilerplate code** - Same pattern copied everywhere
- 🟡 **Inconsistency** - Some use `__name__`, others use hardcoded names
- 🟡 **Not critical** - Works fine, just adds noise

### Proposed Fix

#### Create Centralized Logger Utility
```python
# caas_framework/utils/logging.py

import logging
from typing import Optional

def get_logger(name: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """
    Get or create a logger with standard configuration.

    Args:
        name: Logger name (defaults to caller's __name__)
        level: Log level (defaults to INFO)

    Returns:
        Configured logger instance

    Example:
        >>> from caas_framework.utils.logging import get_logger
        >>> logger = get_logger()
        >>> logger.info("Message")
    """
    if name is None:
        # Auto-detect caller's module name
        import inspect
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else "caas_framework"

    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    return logger
```

#### Update All Files
**Before:**
```python
import logging

logger = logging.getLogger(__name__)
```

**After:**
```python
from caas_framework.utils.logging import get_logger

logger = get_logger()
```

### Effort Estimate
**2-3 hours** (mostly automated with regex replace)

### Automated Migration
```bash
# Find all files with logging pattern
grep -rl "import logging" caas_framework caas_cli --include="*.py" > logging_files.txt

# For each file, replace pattern (can be automated with sed/awk)
```

### Benefits
- ✅ Less boilerplate
- ✅ Consistent logging setup
- ✅ Easier to add global logging configuration
- ✅ Single place to add features (e.g., structured logging)

### Acceptance Criteria
- [ ] `caas_framework/utils/logging.py` created
- [ ] All 74 files migrated
- [ ] Tests pass
- [ ] No regression in logging behavior

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Low priority (cosmetic improvement)
