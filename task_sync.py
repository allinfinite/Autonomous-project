#!/usr/bin/env python3
"""
Task Synchronization Layer

Bridges Claude Code's task system with the autonomous_project SQLite database
so that tasks appear in both the web GUI and Claude Code's task list.

Usage:
    from task_sync import sync_create_task, sync_update_task
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


class TaskSync:
    """Synchronizes tasks between Claude Code and SQLite database"""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.db_path = self.project_dir / ".autonomous_project.db"
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database exists with proper schema"""
        if not self.db_path.exists():
            # Initialize database if it doesn't exist
            from autonomous_project import ProjectState
            state = ProjectState(self.project_dir)

    def create_task(self, task_id: str, description: str, agent_role: Optional[str] = None, session_id: Optional[str] = None):
        """
        Create task in SQLite database

        Args:
            task_id: Unique task identifier (e.g., "1", "task-001")
            description: Task description
            agent_role: Assigned agent role (planner, builder, etc.)
            session_id: Session ID (auto-detected if None)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get latest session if not provided
        if not session_id:
            cursor.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1")
            result = cursor.fetchone()
            session_id = result[0] if result else datetime.now().strftime("%Y%m%d_%H%M%S")

        # Insert task
        cursor.execute("""
            INSERT INTO tasks (session_id, task_id, agent_role, description, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (session_id, task_id, agent_role, description, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        print(f"✅ Synced task to SQLite: {task_id}")

    def update_task(self, task_id: str, status: Optional[str] = None, agent_role: Optional[str] = None, description: Optional[str] = None):
        """
        Update task in SQLite database

        Args:
            task_id: Task identifier to update
            status: New status (pending, in_progress, awaiting_approval, completed)
            agent_role: New agent role
            description: New description
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status == "completed":
                updates.append("completed_at = ?")
                params.append(datetime.now().isoformat())

        if agent_role:
            updates.append("agent_role = ?")
            params.append(agent_role)

        if description:
            updates.append("description = ?")
            params.append(description)

        if updates:
            params.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
            cursor.execute(query, params)
            conn.commit()
            print(f"✅ Synced task update to SQLite: {task_id} → {status or 'updated'}")

        conn.close()

    def delete_task(self, task_id: str):
        """Delete task from SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()
        print(f"✅ Deleted task from SQLite: {task_id}")

    def get_session_id(self) -> Optional[str]:
        """Get the most recent session ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None


# Global instance (will be set by coordinator)
_sync_instance: Optional[TaskSync] = None


def init_sync(project_dir: Path):
    """Initialize the sync instance"""
    global _sync_instance
    _sync_instance = TaskSync(project_dir)
    return _sync_instance


def sync_create_task(task_id: str, description: str, agent_role: Optional[str] = None):
    """
    Create task in both Claude Code and SQLite

    Usage in coordinator:
        # Instead of just: TaskCreate(...)
        # Do: sync_create_task("task-001", "Build feature X", "builder")
        # Then also: TaskCreate(...) for Claude Code
    """
    if _sync_instance:
        _sync_instance.create_task(task_id, description, agent_role)
    else:
        print("⚠️  TaskSync not initialized. Call init_sync(project_dir) first.")


def sync_update_task(task_id: str, status: Optional[str] = None, agent_role: Optional[str] = None, description: Optional[str] = None):
    """
    Update task in both Claude Code and SQLite

    Usage in coordinator:
        # Instead of just: TaskUpdate(taskId=..., status=...)
        # Do: sync_update_task("task-001", status="completed")
        # Then also: TaskUpdate(...) for Claude Code
    """
    if _sync_instance:
        _sync_instance.update_task(task_id, status, agent_role, description)
    else:
        print("⚠️  TaskSync not initialized. Call init_sync(project_dir) first.")


def sync_delete_task(task_id: str):
    """Delete task from both systems"""
    if _sync_instance:
        _sync_instance.delete_task(task_id)
    else:
        print("⚠️  TaskSync not initialized. Call init_sync(project_dir) first.")


if __name__ == "__main__":
    # Test the sync
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 task_sync.py <project_dir>")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    sync = TaskSync(project_dir)

    # Test create
    sync.create_task("test-001", "Test task", "builder")

    # Test update
    sync.update_task("test-001", status="in_progress")

    # Test complete
    sync.update_task("test-001", status="completed")

    print("\n✅ Sync test completed!")
