#!/bin/bash
# Install script for Autonomous Project Agent Harness
# Works with Claude Code and OpenCode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🤖 Installing Autonomous Project Agent Harness..."
echo ""

# Detect which platforms to install for
INSTALL_CLAUDE=false
INSTALL_OPENCODE=false

if [ -d "$HOME/.claude" ]; then
    INSTALL_CLAUDE=true
    echo "✓ Claude Code detected"
fi

if [ -d "$HOME/.config/opencode" ]; then
    INSTALL_OPENCODE=true
    echo "✓ OpenCode detected"
fi

if [ "$INSTALL_CLAUDE" = false ] && [ "$INSTALL_OPENCODE" = false ]; then
    echo "Creating directories..."
    mkdir -p "$HOME/.claude/skills/autonomous-project"
    mkdir -p "$HOME/.claude/scripts"
    INSTALL_CLAUDE=true
fi

echo ""

# Install for Claude Code
if [ "$INSTALL_CLAUDE" = true ]; then
    echo "📦 Installing for Claude Code..."
    
    mkdir -p "$HOME/.claude/skills/autonomous-project"
    mkdir -p "$HOME/.claude/scripts"
    
    cp "$SCRIPT_DIR/SKILL.md" "$HOME/.claude/skills/autonomous-project/"
    cp "$SCRIPT_DIR/autonomous_project.py" "$HOME/.claude/scripts/"
    cp "$SCRIPT_DIR/autonomous_project_web.py" "$HOME/.claude/scripts/"
    cp "$SCRIPT_DIR/task_sync.py" "$HOME/.claude/scripts/"
    cp "$SCRIPT_DIR/sync_tasks_to_db.py" "$HOME/.claude/scripts/"
    cp "$SCRIPT_DIR/sync_agent_to_db.py" "$HOME/.claude/scripts/"
    
    chmod +x "$HOME/.claude/scripts/"*.py
    
    echo "  ✓ Skills: $HOME/.claude/skills/autonomous-project/"
    echo "  ✓ Scripts: $HOME/.claude/scripts/"
fi

# Install for OpenCode
if [ "$INSTALL_OPENCODE" = true ]; then
    echo "📦 Installing for OpenCode..."
    
    mkdir -p "$HOME/.config/opencode/skills/autonomous-project"
    
    cp "$SCRIPT_DIR/SKILL.md" "$HOME/.config/opencode/skills/autonomous-project/"
    cp "$SCRIPT_DIR/autonomous_project.py" "$HOME/.config/opencode/skills/autonomous-project/"
    cp "$SCRIPT_DIR/autonomous_project_web.py" "$HOME/.config/opencode/skills/autonomous-project/"
    cp "$SCRIPT_DIR/task_sync.py" "$HOME/.config/opencode/skills/autonomous-project/"
    cp "$SCRIPT_DIR/sync_tasks_to_db.py" "$HOME/.config/opencode/skills/autonomous-project/"
    cp "$SCRIPT_DIR/sync_agent_to_db.py" "$HOME/.config/opencode/skills/autonomous-project/"
    
    chmod +x "$HOME/.config/opencode/skills/autonomous-project/"*.py
    
    echo "  ✓ Skills: $HOME/.config/opencode/skills/autonomous-project/"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  python3 ~/.claude/scripts/autonomous_project.py \"Build a todo app\""
echo "  python3 ~/.claude/scripts/autonomous_project_web.py --web --dir /path/to/project"
echo ""
