#!/bin/bash
# ResearchFlow Production Cleanup Script
# Generated: 2026-01-29
# Run from: /Users/ros/Documents/GitHub/researchflow-production

set -e
cd "$(dirname "$0")"

echo "🧹 ResearchFlow Production Cleanup Script"
echo "=========================================="

# Function to confirm actions
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# 1. Archive old checkpoint files
echo ""
echo "📁 Step 1: Archive old checkpoint/phase documentation"
if [ -n "$(ls CHECKPOINT_*.md PHASE*.md 2>/dev/null)" ]; then
    mkdir -p docs/archive/checkpoints docs/archive/phases
    
    if confirm "Move CHECKPOINT_*.md to docs/archive/checkpoints/?"; then
        mv CHECKPOINT_*.md docs/archive/checkpoints/ 2>/dev/null || true
        echo "  ✅ Moved checkpoint files"
    fi
    
    if confirm "Move PHASE*.md to docs/archive/phases/?"; then
        mv PHASE*.md docs/archive/phases/ 2>/dev/null || true
        echo "  ✅ Moved phase files"
    fi
fi

# 2. Add missing directories to git
echo ""
echo "📦 Step 2: Add missing directories to git"
MISSING_DIRS="apps binder config evals integration-prompts k8s notebooks planning prompts types"
for dir in $MISSING_DIRS; do
    if [ -d "$dir" ] && ! git ls-files --error-unmatch "$dir" &>/dev/null; then
        if confirm "Add $dir/ to git?"; then
            git add "$dir/"
            echo "  ✅ Added $dir/"
        fi
    fi
done

# 3. Add missing config files
echo ""
echo "⚙️ Step 3: Add missing config files"
MISSING_FILES="playwright.config.ts vercel.json mkdocs.yml"
for file in $MISSING_FILES; do
    if [ -f "$file" ] && ! git ls-files --error-unmatch "$file" &>/dev/null; then
        if confirm "Add $file to git?"; then
            git add "$file"
            echo "  ✅ Added $file"
        fi
    fi
done

# 4. Add docker-compose variants
echo ""
echo "🐳 Step 4: Add docker-compose variants"
for file in docker-compose.*.yml; do
    if [ -f "$file" ] && ! git ls-files --error-unmatch "$file" &>/dev/null; then
        if confirm "Add $file to git?"; then
            git add "$file"
            echo "  ✅ Added $file"
        fi
    fi
done

# 5. Clean build artifacts (optional)
echo ""
echo "🗑️ Step 5: Clean build artifacts (optional)"
if confirm "Remove node_modules/ and .pnpm-store/ (~735MB)?"; then
    rm -rf node_modules .pnpm-store
    echo "  ✅ Removed package caches"
    echo "  ℹ️ Run 'pnpm install' to restore"
fi

if confirm "Remove playwright-report/ and test-results/?"; then
    rm -rf playwright-report test-results
    echo "  ✅ Removed test outputs"
fi

# 6. Commit changes
echo ""
echo "📤 Step 6: Commit and push changes"
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    if confirm "Commit all staged changes?"; then
        read -p "Commit message: " commit_msg
        git commit -m "${commit_msg:-chore: cleanup and add missing local files}"
        
        if confirm "Push to origin?"; then
            git push
            echo "  ✅ Pushed to origin"
        fi
    fi
fi

echo ""
echo "✨ Cleanup complete!"
echo "   See CLEANUP_ANALYSIS.md for full report"
