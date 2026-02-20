#!/usr/bin/env bash
#
# Multi-IDE Skill Setup Script
# Creates symlinks for Cursor, Claude Code, and Qwen to use .agent/skills/
#
# Supports:
# - Google Antigravity (native .agent/skills/)
# - Claude Code (via .claude/skills/ symlink)
# - Cursor (via .cursor/skills/ symlink)
# - Qwen (via .qwen/skills/ symlink)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔧 Multi-IDE Skill Setup"
echo "========================"
echo

# Check if .agent/skills exists
if [ ! -d "$REPO_ROOT/.agent/skills" ]; then
    echo -e "${RED}✗ Error: .agent/skills directory not found${NC}"
    echo "  Expected location: $REPO_ROOT/.agent/skills"
    echo "  This is required for Google Antigravity compatibility"
    exit 1
fi

echo -e "${GREEN}✓ Found .agent/skills${NC} (Google Antigravity native)"
echo

# Function to create symlink (cross-platform)
create_symlink() {
    local target="$1"
    local link_name="$2"
    local ide_name="$3"

    # Check if link already exists
    if [ -L "$link_name" ]; then
        # It's a symlink - check if it points to the right place
        current_target=$(readlink "$link_name")
        if [ "$current_target" = "$target" ] || [ "$current_target" = ".agent/skills" ]; then
            echo -e "${GREEN}✓ $link_name${NC} already points to $target ($ide_name)"
            return 0
        else
            echo -e "${YELLOW}! $link_name${NC} exists but points to $current_target"
            read -p "  Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "  Skipped $link_name"
                return 1
            fi
            rm "$link_name"
        fi
    elif [ -e "$link_name" ]; then
        # It's a regular directory
        echo -e "${YELLOW}! $link_name${NC} exists as a directory"
        read -p "  Replace with symlink? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "  Skipped $link_name"
            return 1
        fi
        rm -rf "$link_name"
    fi

    # Create the symlink
    # Use relative path for better portability
    (cd "$REPO_ROOT" && ln -s ".agent/skills" "$(basename "$link_name")")

    if [ -L "$link_name" ]; then
        echo -e "${GREEN}✓ Created $link_name${NC} → $target ($ide_name)"
        return 0
    else
        echo -e "${RED}✗ Failed to create $link_name${NC}"
        return 1
    fi
}

# Create symlinks
echo "Creating symlinks..."
echo

create_symlink ".agent/skills" "$REPO_ROOT/.cursor/skills" "Cursor"
create_symlink ".agent/skills" "$REPO_ROOT/.claude/skills" "Claude Code"
create_symlink ".agent/skills" "$REPO_ROOT/.qwen/skills" "Qwen"

echo
echo "Summary"
echo "======="
echo
echo "Directory structure:"
echo "  .agent/skills/    - Primary (Google Antigravity native)"
echo "  .cursor/skills/   - Symlink → .agent/skills/ (Cursor)"
echo "  .claude/skills/   - Symlink → .agent/skills/ (Claude Code)"
echo "  .qwen/skills/     - Symlink → .agent/skills/ (Qwen)"
echo
echo -e "${GREEN}✓ Setup complete!${NC}"
echo
echo "Next steps:"
echo "  1. Test in Google Antigravity: Skills should work natively"
echo "  2. Test in Cursor: Skills should be discovered via .cursor/skills/"
echo "  3. Test in Claude Code: Skills should be discovered via .claude/skills/"
echo "  4. Test in Qwen: Skills should be discovered via .qwen/skills/"
echo
