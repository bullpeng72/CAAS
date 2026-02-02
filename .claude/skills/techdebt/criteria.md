# Technical Debt Criteria for CAAS

## Code Duplication

### Critical (Must fix)
- Exact duplicate blocks >= 15 lines
- Duplicate business logic across 3+ files
- Copy-pasted validation/error handling in core modules

### Medium (Should fix)
- Similar function implementations (>80% similarity)
- Duplicate utility functions across 2 modules
- Repeated patterns in agent implementations

### Low (Nice to fix)
- Small helper functions duplicated 2x
- Similar but intentionally different implementations
- Configuration/setup code duplicates

## Dead Code

### Critical
- Entire modules imported nowhere
- Public APIs with zero callers (after deprecation period)
- Test files for deleted modules

### Medium
- Private methods never called
- Commented code blocks >50 lines
- Import statements for deleted modules

### Low
- Unused parameters in private methods
- Debug print statements
- Commented single lines

## Architecture Debt

### Critical
- Circular dependencies between major modules
- Hardcoded dependencies bypassing plugin system
- Missing error handling in critical paths (BMAD phases)
- Security vulnerabilities (SQL injection, path traversal)

### Medium
- Inconsistent async/sync patterns in same module
- Mixed use of dict vs Pydantic models
- Quality Gate bypass (known issue - planned fix)
- Missing abstractions for repeated patterns

### Low
- Inconsistent naming conventions
- Missing type hints on public methods
- Suboptimal import organization

## CAAS-Specific Patterns

### Migration Debt (app/ → caas_framework/)
- **Critical**: Any `from app.` imports in active code
- **Medium**: Duplicate logic in `caas_app/` and `caas_framework/`
- **Low**: Old comments referencing `app/` structure

### Plugin System Debt
- **Critical**: Hardcoded LLM provider logic outside plugin system
- **Medium**: Plugins not following `PluginBase` interface
- **Low**: Missing plugin registration logging

### Expert Agent Debt
- **Critical**: Agent collaboration breaking on edge cases
- **Medium**: Duplicate agent creation logic
- **Low**: Inconsistent agent logging patterns

### BMAD Workflow Debt
- **Critical**: Phase execution failures not properly handled
- **Medium**: Quality Gate bypass in multiple phases
- **Low**: Phase transition logging inconsistencies

## Refactoring Priorities

### Extraction Candidates

**High value**:
1. Duplicate validation logic → `caas_framework/utils/validation.py`
2. Common LLM retry logic → `caas_framework/utils/llm_helpers.py`
3. File I/O patterns → `caas_framework/utils/file_ops.py`
4. Error formatting → `caas_framework/utils/errors.py`

**Medium value**:
1. Agent initialization patterns → `caas_framework/agents/mixins/`
2. Task creation helpers → `caas_framework/agents/mixins/task_helpers.py`
3. Config validation → `caas_framework/config/validators.py`

**Low value**:
1. Small formatting utilities
2. One-time migration scripts
3. Test fixtures

## Test Coverage Gaps

### Critical (Core functionality untested)
- BMAD phase transitions with failures
- Plugin fallback mechanisms
- Multi-model routing logic
- Auto-fixing Level 3 (LLM-based)

### Medium (Important flows partially tested)
- CLI commands with edge cases
- Validation orchestrator combinations
- Session management concurrent operations

### Low (Nice to have)
- Error message formatting
- Logging output
- CLI help text

## Code Smells to Flag

### Complexity
- Functions >50 lines (flag for review)
- Cyclomatic complexity >10
- Nesting depth >4

### Maintainability
- Magic numbers (use constants)
- String literals repeated 3+ times (use constants)
- Functions with >5 parameters (use config objects)

### Pythonic Code
- Manual iteration instead of comprehensions
- `if x == True` instead of `if x`
- Mutable default arguments
- Bare `except:` clauses

## Automated Fix Safety Levels

### Safe (Can auto-apply)
- Remove unused imports
- Format code (black, isort)
- Add missing type hints (simple cases)
- Fix obvious typos in comments

### Review Required (Suggest but don't apply)
- Extract duplicate functions
- Refactor complex logic
- Change public APIs
- Modify error handling

### Manual Only (Flag for human review)
- Architectural changes
- Breaking changes
- Security-related modifications
- Changes to BMAD workflow logic

## Effort Estimation Guidelines

### Small (< 1 hour)
- Remove unused imports/code
- Format code
- Rename variables for consistency
- Add missing docstrings

### Medium (1-4 hours)
- Extract 1-2 duplicate functions
- Add missing tests for one module
- Refactor one complex function
- Fix one architectural smell

### Large (> 4 hours)
- Major module refactoring
- Extract common patterns across 5+ files
- Redesign plugin interface
- Fix circular dependencies

## Success Criteria

A refactoring is successful when:

1. ✅ All existing tests pass
2. ✅ No new warnings from mypy/pylint
3. ✅ Code coverage maintained or improved
4. ✅ Performance maintained or improved
5. ✅ Git diff is reviewable (< 500 lines per commit)
6. ✅ Documentation updated if public API changed
7. ✅ No breaking changes to CLI interface
8. ✅ BMAD workflow executes successfully

## When NOT to Refactor

Avoid refactoring when:

- ❌ Feature deadline is <1 week away
- ❌ Major version release in progress
- ❌ Code works and won't be touched for 6+ months
- ❌ Refactoring would break backward compatibility
- ❌ Test coverage is <50% (write tests first!)
- ❌ No clear improvement in maintainability
- ❌ Team doesn't have capacity to review properly
