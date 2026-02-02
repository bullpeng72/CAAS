# /techdebt Skill - Complete Usage Guide

## 🎯 Quick Start

The `/techdebt` skill is now installed and configured to:
1. ✅ Analyze technical debt on demand with `/techdebt`
2. ✅ Automatically scan for issues when sessions end
3. ✅ Generate reports in `.claude/techdebt-reports/`

## 📋 Manual Usage

### Basic Commands

```bash
# Full analysis of entire codebase
/techdebt

# Analyze specific directory
/techdebt caas_framework/agents/

# Focus on duplicate code only
/techdebt --duplicates-only

# Get auto-fix suggestions
/techdebt --with-fixes

# Apply fixes (will ask for confirmation)
/techdebt --fix-now
```

### What Gets Analyzed

1. **Code Duplication**
   - Exact duplicate blocks (>= 15 lines)
   - Similar functions (>80% similarity)
   - Common patterns across files

2. **Dead Code**
   - Unused imports
   - Unreferenced functions/classes
   - Commented-out code blocks

3. **Architecture Issues**
   - Circular dependencies
   - app/ migration remnants
   - Inconsistent patterns

4. **CAAS-Specific Debt**
   - Quality Gate bypass status
   - Plugin system consistency
   - BMAD workflow issues

## 🤖 Automatic Session-End Scan

The system automatically runs a **quick technical debt scan** when your Claude session ends.

### What Happens

1. **Trigger**: Session ends (exit, clear, etc.)
2. **Quick Scan**:
   - Counts unused imports
   - Finds duplicate function names
   - Checks TODO/FIXME markers
   - Detects app/ import remnants
   - Identifies commented code blocks
3. **Report**: Saved to `.claude/techdebt-reports/report-YYYYMMDD-HHMMSS.md`
4. **Notification**: Summary printed to terminal

### Example Output

```
🔍 Running technical debt analysis...
Scanning caas_framework...
Scanning caas_cli...
Scanning caas_sdk...

✅ Technical debt scan complete!
📄 Report saved to: .claude/techdebt-reports/report-20260202-140530.md

💡 For detailed analysis, run: /techdebt
```

### Disable Auto-Scan (if needed)

To disable automatic scanning on session end:

**Option 1: Remove hook from settings**
Edit `.claude/settings.local.json` and remove the `"hooks"` section.

**Option 2: Modify the script**
Edit `.claude/hooks/session-cleanup.sh` and change the exit condition:
```bash
# Only run on manual trigger
if [[ "$REASON" != "manual" ]]; then
    exit 0
fi
```

## 📊 Understanding Reports

### Quick Scan Report (Session-End)

```markdown
# Technical Debt Report - 2026-02-02 14:05:30

## Quick Scan Results

### 🔸 Unused Imports
- Python files with imports: **120**
- **Action**: Run `autoflake --remove-all-unused-imports -r ...`

### 🔸 Potential Code Duplication
- Most common function names detected
- **Action**: Run `/techdebt --duplicates-only`

### 🔸 Technical Debt Markers
- TODO/FIXME markers found: **45**

### 🔸 Migration Debt (app/ removal)
- ✅ No `app/` imports detected (migration complete)

### 🔸 Dead Code (Commented Blocks)
- Files with large commented blocks: **8**

## Summary & Recommendations
1. 🟡 Run `/techdebt` for comprehensive analysis
2. 🟢 Clean unused imports
3. 🟢 Format code
```

### Full Analysis Report (/techdebt)

Much more detailed, includes:
- File-by-file duplicate detection
- Specific refactoring recommendations
- Auto-fix commands
- Effort estimates
- Code metrics before/after

## 🛠️ Common Workflows

### Before Starting Work

```bash
# Check current tech debt state
/techdebt

# Review recent reports
ls -lt .claude/techdebt-reports/ | head -5
```

### During Development

```bash
# Check specific module you're working on
/techdebt caas_framework/bmad/

# Quick duplicate check
/techdebt --duplicates-only
```

### Before Committing

```bash
# Full analysis with fix suggestions
/techdebt --with-fixes

# Apply safe fixes
autoflake --in-place --remove-all-unused-imports -r caas_framework/
black caas_framework/ caas_cli/ caas_sdk/
isort caas_framework/ caas_cli/ caas_sdk/

# Re-check
/techdebt

# Run tests
pytest
```

### Sprint Planning

```bash
# Generate comprehensive report
/techdebt

# Review high-priority items
cat .claude/techdebt-reports/report-*.md | grep "🔴 Critical"

# Estimate effort
cat .claude/techdebt-reports/report-*.md | grep "Effort:"
```

### After Refactoring

```bash
# Verify improvements
/techdebt

# Compare metrics
diff .claude/techdebt-reports/report-before.md \
     .claude/techdebt-reports/report-after.md
```

## 🔧 Customization

### Adjust Scan Thresholds

Edit `.claude/hooks/session-cleanup.sh`:

```bash
# Change duplicate detection threshold
# Original: count >= 5
# More strict: count >= 3
/^[[:space:]]*#/ { count++ }
!/^[[:space:]]*#/ { if (count >= 3) blocks++; count=0 }
```

### Add Custom Checks

Add to `.claude/hooks/session-cleanup.sh`:

```bash
# 6. Check for your custom pattern
echo "### 🔸 Custom Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

CUSTOM_COUNT=$(grep -r "YOUR_PATTERN" "$PROJECT_DIR" \
    --include="*.py" 2>/dev/null | wc -l | tr -d ' ')

echo "- Pattern occurrences: **$CUSTOM_COUNT**" >> "$REPORT_FILE"
```

### Customize Report Format

Edit `.claude/skills/techdebt/template.md` to change full report structure.

Edit `.claude/skills/techdebt/criteria.md` to adjust severity thresholds.

## 📈 Metrics Tracking

### Track Progress Over Time

```bash
# Create monthly report
mkdir -p reports/monthly/
cat .claude/techdebt-reports/report-202602*.md > reports/monthly/february-2026.md

# Count trends
echo "Feb 2026 Stats:" > reports/trends.txt
grep "TODO/FIXME markers found:" .claude/techdebt-reports/report-202602*.md | \
    awk '{sum+=$NF} END {print "Avg TODO markers:", sum/NR}' >> reports/trends.txt
```

### Git Integration

```bash
# Commit reports periodically
git add .claude/techdebt-reports/
git commit -m "📊 Update tech debt reports"

# Track in CI/CD
# Add to .gitlab-ci.yml or GitHub Actions
```

## 🚨 Troubleshooting

### Hook Not Running

```bash
# Check if hook is configured
cat .claude/settings.local.json | jq '.hooks'

# Check if script is executable
ls -l .claude/hooks/session-cleanup.sh
# Should show: -rwxr-xr-x

# Make executable if needed
chmod +x .claude/hooks/session-cleanup.sh

# Test manually
echo '{"reason":"test"}' | .claude/hooks/session-cleanup.sh
```

### Skill Not Loading

```bash
# Verify skill exists
ls -la .claude/skills/techdebt/

# Check YAML frontmatter
head -10 .claude/skills/techdebt/SKILL.md

# Restart Claude Code session
```

### Reports Not Generating

```bash
# Check permissions
ls -la .claude/techdebt-reports/

# Create directory manually
mkdir -p .claude/techdebt-reports

# Check disk space
df -h .
```

### False Positives

Edit criteria in:
- `.claude/skills/techdebt/criteria.md` - Adjust thresholds
- `.claude/hooks/session-cleanup.sh` - Modify detection logic
- `.claude/skills/techdebt/SKILL.md` - Change analysis patterns

## 🎓 Best Practices

### Do's ✅

- **Review reports regularly** (weekly/sprint)
- **Fix quick wins first** (unused imports, formatting)
- **Track metrics over time** (measure improvement)
- **Commit fixes incrementally** (small, focused commits)
- **Run tests after fixes** (ensure nothing breaks)
- **Share reports with team** (collaborative cleanup)

### Don'ts ❌

- **Don't ignore critical issues** (app/ imports, security)
- **Don't auto-fix without review** (always verify)
- **Don't refactor without tests** (write tests first!)
- **Don't bulk-delete code** (review commented code first)
- **Don't skip CI checks** (run full test suite)

## 📚 Resources

- [Skill Instructions](SKILL.md) - Full analysis workflow
- [Report Template](template.md) - Output format
- [Debt Criteria](criteria.md) - Classification rules
- [Project Context](../../CLAUDE.md) - CAAS architecture
- [Development Guide](../../docs/2_개발_방법론/전문가_방법론_가이드.md)

## 🆘 Support

If you encounter issues:

1. Check this guide first
2. Review [README.md](README.md) in this directory
3. Test hook manually: `echo '{"reason":"test"}' | .claude/hooks/session-cleanup.sh`
4. Check Claude Code logs (if available)
5. Open an issue in the project repository

---

**Version**: 1.0.0
**Last Updated**: 2026-02-02
**Maintainer**: CAAS Team
