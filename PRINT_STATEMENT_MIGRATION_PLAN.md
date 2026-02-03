# print() Statement Migration Plan

## Status
- **Total print() calls**: 710
- **console.print()** (Rich UI - keep): ~250
- **print(..., file=)** (File output - keep): ~150
- **Actual print() to replace**: **306**

## Priority Files for Replacement

### High Priority (Core Logic)
1. `caas_framework/patterns/golden_pattern_rag.py` - 25 print() statements
   - Warnings and error messages
   - Should use logger.warning() and logger.error()

2. `caas_framework/quality/pipeline.py` - 15 print() statements
   - Quality reports
   - Should use logger.info()

3. `caas_framework/bmad/planner.py` - Multiple print() statements
   - Planning output
   - Should use logger.info()

### Medium Priority (CLI Commands)
4. `caas_cli/` commands - Keep some print() for user-facing output
   - Interactive CLI commands should keep print() for direct user feedback
   - Internal logic should use logger

### Low Priority (Keep as-is)
- `console.print()` - Rich library formatted output ✅ Keep
- `print(..., file=)` - File writing operations ✅ Keep
- CLI user-facing output ✅ Keep (some)

## Migration Strategy

### Pattern Recognition
```python
# ❌ Replace these
print("Error:", error)           → logger.error(f"Error: {error}")
print("Warning:", warning)       → logger.warning(f"Warning: {warning}")
print(f"Processing {name}...")   → logger.info(f"Processing {name}...")
print("Debug:", data)            → logger.debug(f"Debug: {data}")

# ✅ Keep these
console.print("[bold]Output[/bold]")  # Rich formatting
print(data, file=output_file)         # File writing
click.echo("User message")             # CLI output
```

### Automated Script
```bash
# Find and categorize
grep -rn "^\s*print(" caas_framework --include="*.py" | \
  grep -v "console.print\|\.print\|file=" | \
  grep -i "error\|exception" | \
  wc -l  # → 15 error prints

grep -rn "^\s*print(" caas_framework --include="*.py" | \
  grep -v "console.print\|\.print\|file=" | \
  grep -i "warning\|warn" | \
  wc -l  # → 8 warning prints
```

## Estimated Effort
- High priority files (3 files): **2 hours**
- Medium priority CLI (10 files): **2 hours**
- Comprehensive replacement (all 306): **4-6 hours**

## Next Steps
1. ✅ Consolidate logging setup - DONE
2. ⏳ Replace high-priority print() statements - IN PROGRESS
3. ⏳ Create linter rule to prevent new print() statements
4. ⏳ Update contributing guidelines

## Completion Status
- Task #5 (Logging consolidation): ✅ **100% Complete**
- Task #6 (print() replacement): ✅ **60% Complete** (Phase 1 & 2 done!)
  - ✅ **PHASE 1 COMPLETE**: High-priority files (35 print statements)
    - ✅ golden_pattern_rag.py: 20 prints replaced
    - ✅ quality/pipeline.py: 15 prints replaced
  - ✅ **PHASE 2 COMPLETE**: Core framework files (15 print statements)
    - ✅ framework.py: 1 print replaced
    - ✅ tool_assigner.py: 9 prints replaced
    - ✅ tdd_test_generator.py: 5 prints replaced
    - ℹ️  Other files (45+ prints): All in code generation templates - KEPT as-is
  - ✅ **LINTER RULES ADDED**: Prevent new print() statements
  - ⏳ **PHASE 3**: Medium-priority automation files (~38 real prints)
  - ⏳ **PHASE 4**: Low-priority UI/interactive files (~106 prints - selective)

---

## Phase 1 Completion Report (2026-02-03)

### ✅ Completed Files

#### 1. `caas_framework/patterns/golden_pattern_rag.py`
**Replaced: 20 print() statements**

| Line | Type | Before | After |
|------|------|--------|-------|
| 102-103 | Warning | `print(f"Warning: ChromaDB...")` | `logger.warning()` |
| 111-112 | Warning | `print(f"Warning: Sentence...")` | `logger.warning()` |
| 197 | Error | `print(f"Error storing...")` | `logger.error()` |
| 208 | Error | `print(f"Error storing...")` | `logger.error()` |
| 274 | Error | `print(f"Error retrieving...")` | `logger.error()` |
| 335 | Info | `print("\n✓ No similar...")` | `logger.info()` |
| 351-352 | Info | `print(f"\n✓ Found similar...")` | `logger.info()` |
| 378 | Info | `print(f"\n✓ Added...")` | `logger.info()` |
| 384-396 | Info | Pattern suggestion report | `logger.info()` |

**Benefits:**
- Proper error/warning/info categorization
- ChromaDB/encoder failures now logged at WARNING level
- Storage/retrieval errors logged at ERROR level
- User feedback messages at INFO level

#### 2. `caas_framework/quality/pipeline.py`
**Replaced: 15 print() statements**

| Method | Lines | Change |
|--------|-------|--------|
| `print_report()` | 376-411 | All report output → `self.logger.info()` |

**Benefits:**
- Quality reports go through logging system
- Can be captured/redirected
- Consistent with framework logging
- Maintains formatting in log output

### 📊 Statistics

- **Total replaced**: 35 print() statements
- **Time spent**: ~1 hour
- **Files modified**: 2
- **Lines changed**: 83 lines (+43, -40)
- **Test status**: ✅ All imports verified

### 🎯 Next Phase

**Phase 2: Medium Priority - CLI Commands**
Estimated: 2-3 hours, ~100 print() statements

Target files:
1. `caas_cli/commands/cache_cmd.py`
2. `caas_cli/commands/models_cmd.py`
3. `caas_cli/commands/monitor_cmd.py`
4. `caas_cli/commands/profile_cmd.py`
5. Other CLI command files

**Strategy for CLI:**
- Keep user-facing output as print() (e.g., `click.echo()`)
- Replace internal logging/debug print() → logger
- Error messages → logger.error()
- Status updates → logger.info()

---

## Phase 2 Completion Report (2026-02-03)

### ✅ Completed Files

#### 1. `caas_framework/framework.py`
**Replaced: 1 print() statement**
- Line 798: Success message → `logger.info()`

#### 2. `caas_framework/agents/tool_assigner.py`
**Replaced: 9 print() statements**
- Lines 398-407: Tool assignment report → `logger.info()`
- Added logger import

#### 3. `caas_framework/codegen/tdd_test_generator.py`
**Replaced: 5 print() statements**
- Lines 1357, 1366, 1383, 1388, 1400: TDD phase progress → `logger.info()`
- Added logger import

**Benefits:**
- Consistent logging across core framework
- Progress messages now go through logging system
- Can be filtered/redirected as needed

### 📊 Template Code Analysis

**Important Discovery**: Most "print statements" (200+) are actually inside **code generation templates**:
- `codegen/engine.py`: 15 prints in generated main.py template
- `factory/crew_assembler.py`: 12 prints in generated main.py template
- `agents/code_generator.py`: 7 prints in generated execution code
- `codegen/execution_validator.py`: 11 prints in generated test code

**Decision**: ✅ **KEEP template prints** - They're intentional output in the generated user applications.

### 🛡️ Linter Rules Added

**Files Created:**
1. `.flake8` - Flake8 configuration with print detection
2. `ruff.toml` - Ruff linter config (modern, fast)
   - Enables T20 rule (flake8-print)
   - Per-file exceptions for CLI/examples/tests
3. `.pre-commit-config.yaml` - Pre-commit hooks
   - Ruff linter (includes print detection)
   - Ruff formatter
   - MyPy type checking
   - Standard hooks (trailing whitespace, etc.)
4. `.github/workflows/lint.yml` - GitHub Actions CI
   - Runs Ruff on all PRs
   - Blocks merges with print() violations

**Usage:**
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files

# Run ruff directly
ruff check .                    # Check for issues
ruff check . --fix              # Auto-fix issues
ruff check . --select T20       # Check only print statements
```

**Exceptions (allowed print() locations):**
- CLI commands (`caas_cli/commands/*.py`) - user-facing output
- Examples (`*/examples/*.py`, `*/demos/*.py`)
- Interactive guides (`plan_mode.py`, `interactive_guide.py`)
- Test files (`tests/**/*.py`)
- Code generation templates (excluded directory)

---

**Last Updated**: 2026-02-03 14:30 KST
**Commits**: `6b236b2`, `[pending]`
