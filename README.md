# Autonomous Project Agent Harness

A meta-skill that coordinates a team of specialized AI agents to build projects autonomously with minimal user intervention.

## Features

- **Master Coordinator** - Orchestrates multiple specialized agents
- **Web Dashboard** - Real-time monitoring of agents, tasks, and sessions
- **Local SQLite Database** - No cloud dependencies
- **Session Recovery** - Pause and resume projects
- **Task Synchronization** - Sync agents and tasks to web GUI

## Agent Roles

- **Planner/Architect** - Requirements analysis, task breakdown, architecture design
- **Builder/Implementer** - Feature implementation, code writing
- **Quality Checker** - Code review, standards enforcement
- **Tester/Validator** - Test creation, functionality validation
- **Documenter** - Documentation, README maintenance

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/daniellevy/autonomous-project-skill.git

# Run the install script
cd autonomous-project-skill
./install.sh
```

### Manual Install

#### For Claude Code

```bash
# Copy skill files
mkdir -p ~/.claude/skills/autonomous-project
mkdir -p ~/.claude/scripts

cp SKILL.md ~/.claude/skills/autonomous-project/
cp *.py ~/.claude/scripts/
```

#### For OpenCode

```bash
# Copy skill files
mkdir -p ~/.config/opencode/skills/autonomous-project

cp SKILL.md ~/.config/opencode/skills/autonomous-project/
cp *.py ~/.config/opencode/skills/autonomous-project/
```

## Usage

### Start a New Project

```bash
python3 ~/.claude/scripts/autonomous_project.py "Build a todo app with React"
```

### Launch Web Dashboard

```bash
python3 ~/.claude/scripts/autonomous_project_web.py --web --dir /path/to/project
```

The dashboard will automatically find an available port and open in your browser.

### Resume a Session

```bash
python3 ~/.claude/scripts/autonomous_project.py --resume 20260212_143000
```

## Syncing Agents and Tasks

To see agents and tasks in the web dashboard, sync them to the database:

```bash
# Sync an agent
python3 ~/.claude/scripts/sync_agent_to_db.py /path/to/project builder builder_001

# Sync tasks
python3 ~/.claude/scripts/sync_tasks_to_db.py /path/to/project '[{"id":"1","description":"Task 1","status":"pending"}]'

# List agents
python3 ~/.claude/scripts/sync_agent_to_db.py /path/to/project --list
```

## Requirements

- Python 3.7+
- Flask (for web GUI): `pip install flask`
- SQLite3 (built into Python)

## License

MIT
