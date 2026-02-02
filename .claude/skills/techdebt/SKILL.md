---
name: techdebt
description: Analyze technical debt in the codebase, focusing on duplicate code detection and automated refactoring. Use when analyzing code quality, finding duplication, or planning refactoring.
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Technical Debt Analysis & Refactoring

Systematically identify and fix technical debt in the CAAS codebase, with special focus on:
1. **Duplicate code detection** - Find similar/identical code blocks
2. **Dead code elimination** - Remove unused imports, functions, classes
3. **Import cleanup** - Fix redundant or circular imports
4. **Refactoring opportunities** - Extract common patterns into utilities

## Analysis Workflow

### Phase 1: Code Duplication Detection

Scan for duplicate code using multiple strategies:

1. **Exact duplicates** (>= 5 lines):
   ```bash
   # Use Python AST-based duplicate detection
   find . -name "*.py" -exec grep -l "def\|class" {} \; | while read file; do
       python -c "import ast; print(ast.dump(ast.parse(open('$file').read())))"
   done
   ```

2. **Similar function signatures**:
   - Search for functions with identical names across modules
   - Identify functions with >80% code similarity
   - Flag copy-pasted code with minor variations

3. **Common patterns**:
   - Repeated error handling blocks
   - Duplicate validation logic
   - Similar data transformation code
   - Redundant utility functions

### Phase 2: Dead Code Detection

Identify unused code elements:

1. **Unused imports**:
   ```bash
   # Use autoflake to detect unused imports
   find caas_framework caas_cli caas_sdk -name "*.py" -exec autoflake --check --remove-all-unused-imports {} \;
   ```

2. **Unreferenced functions/classes**:
   - Grep for function/class definitions
   - Check if they're imported/called anywhere
   - Flag private methods never used

3. **Legacy code markers**:
   - Search for `# TODO: Remove`, `# DEPRECATED`, `# LEGACY`
   - Find commented-out code blocks (>10 lines)

### Phase 3: Architecture Issues

Detect structural problems:

1. **Circular dependencies**:
   ```bash
   # Check import cycles
   python -m pydeps caas_framework --show-cycles
   ```

2. **app/ migration remnants**:
   - Search for any remaining `from app.` imports
   - Check for duplicate functionality in `caas_app/` and `caas_framework/`

3. **Inconsistent patterns**:
   - Mixed sync/async patterns
   - Inconsistent error handling
   - Varying logging approaches

### Phase 4: CAAS-Specific Debt

Focus on project-specific issues:

1. **Quality Gate bypass** (known issue):
   - File: `caas_framework/agents/collaboration.py`
   - Check if still bypassed in Discovery, Architecture, Design, Delivery phases

2. **Plugin system consistency**:
   - Verify all plugins follow `caas_framework/plugins/base.py` interface
   - Check for hardcoded provider logic vs. plugin registry usage

3. **Model validation**:
   - Ensure all data classes use Pydantic models
   - Check for dict/kwargs usage instead of typed models

4. **Test coverage gaps**:
   - Find modules without corresponding test files
   - Identify critical paths lacking E2E tests

## Output Format

Generate a structured report:

```markdown
# Technical Debt Report - [DATE]

## Executive Summary
- **Total issues**: [count]
- **High priority**: [count]
- **Estimated effort**: [hours/days]

## 🔴 Critical Issues (Fix Immediately)

### [Category]: [Title]
- **Location**: `path/to/file.py:line`
- **Type**: Duplication | Dead Code | Architecture | Security
- **Impact**: [Why this matters]
- **Effort**: Small (< 1h) | Medium (1-4h) | Large (> 4h)
- **Fix**: [Specific refactoring action]

## 🟡 Medium Priority (Next Sprint)

[Same format as above]

## 🟢 Low Priority (Backlog)

[Same format as above]

## Automated Fixes Available

List issues that can be auto-fixed:
- [ ] Remove unused imports (`autoflake --in-place`)
- [ ] Format code (`black .`)
- [ ] Sort imports (`isort .`)
- [ ] Extract duplicate function to `caas_framework/utils/[module].py`

## Refactoring Recommendations

1. **[Pattern Name]**: Extract [X] duplicate implementations
   - Locations: [file1.py:10, file2.py:25, ...]
   - Proposed utility: `caas_framework/utils/[name].py`
   - Effort: [estimate]

## Next Steps

1. [Action item 1]
2. [Action item 2]
3. ...
```

## Usage Examples

```bash
# Analyze entire codebase
/techdebt

# Focus on specific module
/techdebt caas_framework/agents/

# Quick scan for duplicates only
/techdebt --duplicates-only

# Include auto-fix suggestions
/techdebt --with-fixes
```

## Arguments Processing

- `$ARGUMENTS` can specify:
  - **Directory path**: Focus analysis on specific directory
  - **`--duplicates-only`**: Skip architecture analysis, focus on code duplication
  - **`--with-fixes`**: Generate auto-fix commands (autoflake, black, etc.)
  - **`--fix-now`**: Apply automated fixes immediately (dangerous, ask first!)

## Auto-Fix Workflow

If user requests fixes:

1. **Ask for confirmation** before making changes
2. **Create backup branch**: `git checkout -b techdebt/auto-fixes-[timestamp]`
3. **Apply safe fixes first**:
   - Remove unused imports
   - Format code (black, isort)
4. **Extract common utilities**:
   - Create new utility modules
   - Update imports
   - Run tests to verify
5. **Commit changes**:
   ```
   🧹 Clean up: [summary]

   - Removed [X] unused imports
   - Extracted [Y] duplicate functions
   - Fixed [Z] code smells

   Auto-generated by /techdebt skill
   ```
6. **Report results**: Show git diff summary

## Special Considerations for CAAS

1. **Don't break BMAD workflow** - Preserve Phase execution logic
2. **Maintain plugin compatibility** - Keep plugin interface contracts
3. **Preserve Expert Agent behavior** - Don't alter agent collaboration patterns
4. **Keep CLI backward-compatible** - Don't change command signatures
5. **Update tests** - Ensure all tests pass after refactoring

## Tools Used

- **Grep**: Pattern matching for code search
- **Glob**: Find Python files to analyze
- **Read**: Read file contents for analysis
- **Bash**: Run static analysis tools (autoflake, pylint, mypy)
- **Edit**: Apply targeted fixes to files
- **Write**: Create new utility modules

## Integration with Git

Always use version control:
- Create feature branch before applying fixes
- Commit incrementally (per category)
- Run full test suite before completing
- Provide git diff summary

## Success Metrics

Track improvements:
- Lines of code reduced
- Duplicate code percentage
- Test coverage increase
- Cyclomatic complexity reduction
- Import graph simplification
