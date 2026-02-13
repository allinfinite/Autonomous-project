#!/usr/bin/env python3
"""
Sync Claude Code Tasks to SQLite Database

This script syncs tasks from the current Claude Code session to the
autonomous_project SQLite database so they appear in the web GUI.

Usage:
    python3 sync_tasks_to_db.py <project_dir>
"""

import sys
import json
from pathlib import Path
from task_sync import TaskSync


def sync_from_json(project_dir: Path, tasks_json: str):
    """
    Sync tasks from JSON to SQLite database

    Args:
        project_dir: Project directory containing .autonomous_project.db
        tasks_json: JSON string with tasks array
    """
    sync = TaskSync(project_dir)

    try:
        tasks = json.loads(tasks_json)

        if not isinstance(tasks, list):
            print(f"❌ Error: Expected array of tasks, got {type(tasks)}")
            return

        synced_count = 0
        for task in tasks:
            task_id = task.get('id') or task.get('task_id')
            description = task.get('description') or task.get('subject', 'No description')
            status = task.get('status', 'pending')
            agent_role = task.get('agent_role') or task.get('owner')

            if task_id:
                sync.create_task(str(task_id), description, agent_role)
                if status != 'pending':
                    sync.update_task(str(task_id), status=status)
                synced_count += 1

        print(f"\n✅ Synced {synced_count} tasks to SQLite database")
        print(f"📁 Database: {sync.db_path}")
        print(f"🌐 View in web GUI at http://localhost:5002")

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 sync_tasks_to_db.py <project_dir> [tasks_json]")
        print("\nExample:")
        print('  python3 sync_tasks_to_db.py ~/myproject \'[{"id":"1","description":"Build X","status":"pending"}]\'')
        sys.exit(1)

    project_dir = Path(sys.argv[1]).resolve()

    if not project_dir.exists():
        print(f"❌ Error: Directory not found: {project_dir}")
        sys.exit(1)

    # Check if tasks JSON provided
    if len(sys.argv) >= 3:
        tasks_json = sys.argv[2]
        sync_from_json(project_dir, tasks_json)
    else:
        print("📝 No tasks provided. Initializing sync only.")
        sync = TaskSync(project_dir)
        print(f"✅ TaskSync initialized for {project_dir}")
        print(f"📁 Database: {sync.db_path}")


if __name__ == "__main__":
    main()
