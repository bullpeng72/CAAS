#!/bin/bash
# Session cleanup hook - Runs when Claude Code session ends
# Automatically detects and reports technical debt

set -e

# Get session end reason from stdin
INPUT=$(cat)
# Try jq first, fallback to grep if jq not available
if command -v jq &> /dev/null; then
    REASON=$(echo "$INPUT" | jq -r '.reason // "unknown"')
else
    REASON=$(echo "$INPUT" | grep -o '"reason":"[^"]*"' | cut -d'"' -f4)
    REASON=${REASON:-"unknown"}
fi

# Only run on normal exit or clear (not crashes)
if [[ "$REASON" != "exit" && "$REASON" != "clear" && "$REASON" != "other" ]]; then
    exit 0
fi

# Paths
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
REPORT_DIR="$PROJECT_DIR/.claude/techdebt-reports"
REPORT_FILE="$REPORT_DIR/report-$(date +%Y%m%d-%H%M%S).md"

# Create report directory
mkdir -p "$REPORT_DIR"

echo "🔍 Running technical debt analysis..." >&2

# Initialize report
cat > "$REPORT_FILE" <<EOF
# Technical Debt Report - $(date +"%Y-%m-%d %H:%M:%S")

**Session end reason**: $REASON

## Quick Scan Results

EOF

# Function to count occurrences
count_files() {
    find "$PROJECT_DIR" -path "*/.*" -prune -o -name "$1" -type f -print | wc -l | tr -d ' '
}

# 1. Check for unused imports (quick scan)
echo "### 🔸 Unused Imports" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

UNUSED_COUNT=0
for dir in caas_framework caas_cli caas_sdk; do
    if [[ -d "$PROJECT_DIR/$dir" ]]; then
        echo "Scanning $dir..." >&2
        UNUSED=$(find "$PROJECT_DIR/$dir" -name "*.py" -type f -exec grep -l "^import\|^from" {} \; | wc -l | tr -d ' ')
        UNUSED_COUNT=$((UNUSED_COUNT + UNUSED))
    fi
done

echo "- Python files with imports: **$UNUSED_COUNT**" >> "$REPORT_FILE"
echo "- **Action**: Run \`autoflake --remove-all-unused-imports -r caas_framework/ caas_cli/ caas_sdk/\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. Check for duplicate code patterns (simple heuristic)
echo "### 🔸 Potential Code Duplication" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Find functions with common names (likely duplicates)
COMMON_FUNCS=$(find "$PROJECT_DIR" -name "*.py" -type f -exec grep -h "^def " {} \; 2>/dev/null | \
    sed 's/def \([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/' | \
    sort | uniq -c | sort -rn | head -10)

if [[ -n "$COMMON_FUNCS" ]]; then
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "Most common function names (may indicate duplication):" >> "$REPORT_FILE"
    echo "$COMMON_FUNCS" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo "- No obvious duplicate function names detected" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "- **Action**: Run \`/techdebt --duplicates-only\` for detailed analysis" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. Check for TODO/FIXME comments
echo "### 🔸 Technical Debt Markers" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

TODO_COUNT=$(grep -r "# TODO\|# FIXME\|# HACK\|# XXX" "$PROJECT_DIR" \
    --include="*.py" \
    --exclude-dir=".git" \
    --exclude-dir="venv" \
    --exclude-dir=".pytest_cache" \
    --exclude-dir="__pycache__" 2>/dev/null | wc -l | tr -d ' ')

echo "- TODO/FIXME markers found: **$TODO_COUNT**" >> "$REPORT_FILE"

if [[ $TODO_COUNT -gt 0 ]]; then
    echo "" >> "$REPORT_FILE"
    echo "Top 5 debt markers:" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    grep -rn "# TODO\|# FIXME\|# HACK\|# XXX" "$PROJECT_DIR" \
        --include="*.py" \
        --exclude-dir=".git" \
        --exclude-dir="venv" \
        --exclude-dir=".pytest_cache" \
        --exclude-dir="__pycache__" 2>/dev/null | \
        head -5 >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"

# 4. Check for app/ import remnants (known migration issue)
echo "### 🔸 Migration Debt (app/ removal)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

APP_IMPORTS=$(grep -r "from app\." "$PROJECT_DIR" \
    --include="*.py" \
    --exclude-dir=".git" \
    --exclude-dir="venv" 2>/dev/null | wc -l | tr -d ' ')

if [[ $APP_IMPORTS -gt 0 ]]; then
    echo "- ⚠️ **CRITICAL**: $APP_IMPORTS files still import from \`app/\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Files to fix:" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    grep -rl "from app\." "$PROJECT_DIR" \
        --include="*.py" \
        --exclude-dir=".git" \
        --exclude-dir="venv" 2>/dev/null | \
        head -10 >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo "- ✅ No \`app/\` imports detected (migration complete)" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"

# 5. Check for commented-out code (code smell)
echo "### 🔸 Dead Code (Commented Blocks)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Count files with multiple consecutive commented lines (likely dead code)
COMMENTED_BLOCKS=$(find "$PROJECT_DIR" -name "*.py" -type f -exec awk '
    /^[[:space:]]*#/ { count++ }
    !/^[[:space:]]*#/ { if (count >= 5) blocks++; count=0 }
    END { print blocks }
' {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')

echo "- Files with large commented blocks: **${COMMENTED_BLOCKS:-0}**" >> "$REPORT_FILE"
echo "- **Action**: Review and remove dead code" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Summary
echo "## Summary & Recommendations" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**Priority Actions**:" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [[ $APP_IMPORTS -gt 0 ]]; then
    echo "1. 🔴 **CRITICAL**: Fix $APP_IMPORTS files with \`app/\` imports" >> "$REPORT_FILE"
fi

echo "1. 🟡 Run \`/techdebt\` for comprehensive analysis" >> "$REPORT_FILE"
echo "2. 🟢 Clean unused imports: \`autoflake --in-place --remove-all-unused-imports -r caas_framework/ caas_cli/ caas_sdk/\`" >> "$REPORT_FILE"
echo "3. 🟢 Format code: \`black . && isort .\`" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "📊 **Full report**: \`$REPORT_FILE\`" >> "$REPORT_FILE"
echo "🛠️ **Run full analysis**: \`/techdebt\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Print summary to stderr (visible in Claude)
echo "" >&2
echo "✅ Technical debt scan complete!" >&2
echo "📄 Report saved to: .claude/techdebt-reports/report-$(date +%Y%m%d-%H%M%S).md" >&2
echo "" >&2

# If critical issues found, suggest immediate action
if [[ $APP_IMPORTS -gt 0 ]]; then
    echo "⚠️  CRITICAL: $APP_IMPORTS files still import from app/" >&2
    echo "   Run: grep -rl 'from app\\.' . --include='*.py'" >&2
    echo "" >&2
fi

echo "💡 For detailed analysis, run: /techdebt" >&2
echo "" >&2

exit 0
