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
- Task #6 (print() replacement): **20% Complete** (High-priority identification done)
  - Next session: Replace print() in golden_pattern_rag.py and quality/pipeline.py
