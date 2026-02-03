---
name: "\U0001F4DD [Medium] Replace print() with Logging"
about: Remove print() statements from 33 files
title: "[Tech Debt] Replace print() with proper logging (33 files)"
labels: technical-debt, logging, good-first-issue
assignees: ''
---

## 🟡 Medium Priority: Replace print() with Logging

### Current State
- **33 files** use `print()` instead of proper logging

### Impact
- 🟡 **No log levels** - Can't filter INFO vs DEBUG vs ERROR
- 🟡 **Can't disable** - Always prints to stdout
- 🟡 **No context** - Missing timestamps, module names
- 🟡 **Not production-ready** - Can't redirect to log files

### Proposed Fix

#### Replace All print() Statements
**Before:**
```python
print("Processing data...")
print(f"Found {count} items")
print("Error occurred:", error)
```

**After:**
```python
from caas_framework.utils.logging import get_logger

logger = get_logger()

logger.info("Processing data...")
logger.debug(f"Found {count} items")
logger.error("Error occurred: %s", error)
```

### Migration Guidelines
- `print("Info message")` → `logger.info("Info message")`
- `print("Debug:", data)` → `logger.debug("Debug: %s", data)`
- `print("ERROR:", err)` → `logger.error("Error: %s", err)`
- `print()` (blank) → Remove (or `logger.debug("---")` if needed)

### Find All print() Usage
```bash
grep -rn "print(" caas_framework caas_cli --include="*.py" | wc -l
# Output: 33 files
```

### Effort Estimate
**2 hours** (straightforward find-and-replace)

### Benefits
- ✅ Proper log levels (DEBUG, INFO, WARNING, ERROR)
- ✅ Can disable/filter logs
- ✅ Adds timestamps and context
- ✅ Production-ready logging
- ✅ Can redirect to files/syslog

### Acceptance Criteria
- [ ] Zero `print()` statements in `caas_framework/` and `caas_cli/`
- [ ] All replaced with appropriate logger calls
- [ ] Log levels make sense (INFO, DEBUG, ERROR)
- [ ] Tests still pass

### Good First Issue
This is a great task for new contributors! Simple, well-defined, low risk.

### Related Issues
- Part of Tech Debt Report 2026-02-03
- Related: #[Logging Duplication]
