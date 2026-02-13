#!/usr/bin/env python3
"""
Sync Agent to SQLite Database

This script syncs an agent to the autonomous_project SQLite database
so it appears in the web GUI.

Usage:
    python3 sync_agent_to_db.py <project_dir> <role> <agent_id> [session_id]
    python3 sync_agent_to_db.py /path/to/project builder builder_001
    python3 sync_agent_to_db.py /path/to/project planner planner_001 20260213_120000
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime


def sync_agent(
    project_dir: Path, role: str, agent_id: str, session_id: str = None, status: str = "active"
):
    """
    Sync an agent to SQLite database

    Args:
        project_dir: Project directory containing .autonomous_project.db
        role: Agent role (planner, builder, quality_checker, tester, documenter)
        agent_id: Unique agent identifier
        session_id: Session ID (auto-detected if None)
        status: Agent status (active, retired)
    """
    db_path = project_dir / ".autonomous_project.db"

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        print("   Run the autonomous project first to initialize the database.")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if not session_id:
        cursor.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            cursor.execute(
                """
                INSERT INTO sessions (session_id, created_at, project_goal, current_phase)
                VALUES (?, ?, ?, ?)
            """,
                (session_id, datetime.now().isoformat(), "Autonomous Project", "implementation"),
            )
            conn.commit()
            print(f"📝 Created new session: {session_id}")

    cursor.execute(
        """
        INSERT INTO agents (session_id, role, agent_id, started_at, status)
        VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, role, agent_id, datetime.now().isoformat(), status),
    )

    conn.commit()
    conn.close()

    print(f"✅ Synced agent to SQLite: {role} ({agent_id}) [{status}]")
    return True


def update_agent_status(project_dir: Path, agent_id: str, status: str):
    """Update an agent's status in the database"""
    db_path = project_dir / ".autonomous_project.db"

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE agents SET status = ? WHERE agent_id = ?
    """,
        (status, agent_id),
    )

    if cursor.rowcount > 0:
        conn.commit()
        print(f"✅ Updated agent status: {agent_id} → {status}")
    else:
        print(f"⚠️  Agent not found: {agent_id}")

    conn.close()
    return True


def list_agents(project_dir: Path):
    """List all agents in the database"""
    db_path = project_dir / ".autonomous_project.db"

    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT agent_id, role, status, started_at FROM agents ORDER BY started_at DESC
    """)

    agents = cursor.fetchall()
    conn.close()

    if not agents:
        print("No agents found in database.")
        return

    print(f"\n📋 Agents in {project_dir}:")
    print("-" * 60)
    for agent_id, role, status, started_at in agents:
        print(f"  {role:15} {agent_id:20} [{status:7}] {started_at}")
    print("-" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  Sync agent:    python3 sync_agent_to_db.py <project_dir> <role> <agent_id> [session_id]"
        )
        print(
            "  Update status: python3 sync_agent_to_db.py <project_dir> --update <agent_id> <status>"
        )
        print("  List agents:   python3 sync_agent_to_db.py <project_dir> --list")
        print()
        print(
            "Roles: planner, builder, quality_checker, tester, documenter, designer, media_expert"
        )
        print("Statuses: active, retired")
        sys.exit(1)

    project_dir = Path(sys.argv[1]).resolve()

    if not project_dir.exists():
        print(f"❌ Error: Directory not found: {project_dir}")
        sys.exit(1)

    if len(sys.argv) >= 3 and sys.argv[2] == "--list":
        list_agents(project_dir)
        return

    if len(sys.argv) >= 5 and sys.argv[2] == "--update":
        update_agent_status(project_dir, sys.argv[3], sys.argv[4])
        return

    if len(sys.argv) < 4:
        print("❌ Error: Missing role and agent_id")
        print("Usage: python3 sync_agent_to_db.py <project_dir> <role> <agent_id> [session_id]")
        sys.exit(1)

    role = sys.argv[2]
    agent_id = sys.argv[3]
    session_id = sys.argv[4] if len(sys.argv) >= 5 else None

    sync_agent(project_dir, role, agent_id, session_id)


if __name__ == "__main__":
    main()
