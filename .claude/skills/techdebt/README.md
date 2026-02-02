# Technical Debt Skill for CAAS

This skill helps identify and fix technical debt in the CAAS codebase.

## Quick Start

```bash
# Basic analysis
/techdebt

# Analyze specific module
/techdebt caas_framework/agents/

# Focus on duplicates
/techdebt --duplicates-only

# Get auto-fix suggestions
/techdebt --with-fixes
```

## Files in This Skill

- **SKILL.md** - Main skill instructions for Claude
- **template.md** - Report template (Jinja2 format)
- **criteria.md** - Detailed debt classification criteria
- **README.md** - This file

## How It Works

1. **Discovery Phase**: Scans codebase for issues
   - Duplicate code detection (AST-based)
   - Dead code identification
   - Architecture smells
   - CAAS-specific patterns

2. **Analysis Phase**: Classifies and prioritizes
   - Critical (fix now) / Medium (next sprint) / Low (backlog)
   - Estimates effort (Small/Medium/Large)
   - Identifies auto-fixable issues

3. **Reporting Phase**: Generates structured report
   - Issue breakdown by severity
   - Refactoring recommendations
   - Auto-fix commands
   - Metrics projections

4. **Fixing Phase** (optional): Applies automated fixes
   - Creates git branch
   - Runs safe fixes (imports, formatting)
   - Commits changes incrementally
   - Runs tests

## Common Use Cases

### Before Sprint Planning
```
/techdebt
```
Get overview of tech debt to include in sprint backlog.

### Before Major Refactor
```
/techdebt caas_framework/bmad/ --with-fixes
```
Analyze module before refactoring to identify issues.

### After Code Review
```
/techdebt caas_framework/agents/collaboration.py
```
Deep dive into specific file flagged in review.

### Periodic Cleanup
```
/techdebt --duplicates-only
```
Monthly duplicate code removal.

## Integration with Development Workflow

### Pre-commit Hook (Optional)

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run quick tech debt scan on changed files

CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$")

if [ -n "$CHANGED_FILES" ]; then
    echo "Running tech debt scan on changed files..."
    # Add your scan logic here
    # Exit 1 if critical issues found
fi
```

### CI/CD Integration

Add to `.gitlab-ci.yml` or GitHub Actions:

```yaml
techdebt:
  stage: quality
  script:
    - pip install autoflake pylint
    - autoflake --check --recursive caas_framework/
    - pylint --fail-under=8.0 caas_framework/
  allow_failure: true  # Don't block merges
  only:
    - merge_requests
```

### Weekly Report

Schedule a weekly tech debt analysis:

```bash
# Add to crontab
0 9 * * 1 cd /path/to/caas && claude --session techdebt-weekly "/techdebt --with-fixes" > reports/techdebt-$(date +%Y%m%d).md
```

## Safety Guidelines

### Always Safe
- ✅ Analyzing code (read-only)
- ✅ Generating reports
- ✅ Suggesting fixes

### Ask First
- ⚠️ Creating git branches
- ⚠️ Modifying files
- ⚠️ Running formatters

### Never Auto-apply
- 🛑 Deleting files
- 🛑 Changing public APIs
- 🛑 Modifying BMAD workflow
- 🛑 Refactoring without tests

## Customization

### Add Project-Specific Patterns

Edit `SKILL.md` to add custom detection:

```markdown
### Phase X: Custom Pattern Detection

Detect [your pattern]:
1. Search for [pattern]
2. Check if [condition]
3. Flag as [severity]
```

### Adjust Severity Thresholds

Edit `criteria.md` to change what's considered critical vs medium vs low.

### Change Report Format

Edit `template.md` to customize the output format.

## Troubleshooting

### Skill not loading
```bash
# Check if skill is discovered
claude --list-skills

# Verify YAML frontmatter is valid
cat .claude/skills/techdebt/SKILL.md | head -n 10
```

### Analysis taking too long
```bash
# Use directory-specific analysis
/techdebt caas_framework/agents/

# Skip expensive checks
/techdebt --duplicates-only
```

### False positives
Edit `criteria.md` to adjust thresholds or add exceptions.

## Contributing

To improve this skill:

1. Add new detection patterns to `SKILL.md`
2. Update severity criteria in `criteria.md`
3. Enhance report template in `template.md`
4. Test with: `/techdebt [test-path]`
5. Commit improvements to version control

## Resources

- [CAAS Architecture Guide](../../docs/3_시스템_문서/아키텍처_가이드.md)
- [Development Methodology](../../docs/2_개발_방법론/전문가_방법론_가이드.md)
- [CLAUDE.md](../../CLAUDE.md) - Project context

## Version History

- **v1.0.0** (2026-02-02): Initial release
  - Duplicate code detection
  - Dead code identification
  - CAAS-specific patterns
  - Auto-fix suggestions
