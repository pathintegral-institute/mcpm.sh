#!/bin/bash
# Update LLM.txt file for AI agents

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🤖 Updating LLM.txt for AI agents..."
echo "📁 Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Generate the llm.txt file
echo "🔄 Generating llm.txt..."
python scripts/generate_llm_txt.py

# Check if there are changes
if git diff --quiet llm.txt; then
    echo "✅ llm.txt is already up to date"
else
    echo "📝 llm.txt has been updated"
    echo ""
    echo "Changes:"
    git diff --stat llm.txt
    echo ""
    echo "To commit these changes:"
    echo "  git add llm.txt"
    echo "  git commit -m 'docs: update llm.txt for AI agents'"
fi

echo "✅ Done!"