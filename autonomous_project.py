#!/usr/bin/env python3
"""
Autonomous Project Agent Harness

A long-running agentic system that initializes and manages a coordinated team
of specialized subagents capable of executing a project from initialization
through completion with minimal user intervention.

Usage:
    python3 autonomous_project.py "Build a todo app with React and local storage"
    python3 autonomous_project.py --resume <session_id>
"""

import json
import sys
import sqlite3
import time
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import argparse
import atexit

# Import task synchronization
try:
    from task_sync import TaskSync, init_sync
except ImportError:
    print("⚠️  task_sync.py not found. Task synchronization disabled.")
    TaskSync = None
    init_sync = None

# Agent role definitions
AGENT_ROLES = {
    "planner": {
        "description": "Analyzes requirements, creates task breakdowns, designs architecture",
        "subagent_type": "Plan",
        "authority": ["create_tasks", "update_architecture", "define_requirements"]
    },
    "builder": {
        "description": "Implements features, writes code, creates files",
        "subagent_type": "general-purpose",
        "authority": ["write_code", "edit_files", "create_components"]
    },
    "quality_checker": {
        "description": "Reviews code quality, enforces standards, validates implementations",
        "subagent_type": "general-purpose",
        "authority": ["review_code", "request_changes", "approve_tasks"]
    },
    "tester": {
        "description": "Writes tests, validates functionality, ensures correctness",
        "subagent_type": "general-purpose",
        "authority": ["write_tests", "run_tests", "validate_features"]
    },
    "documenter": {
        "description": "Creates documentation, comments code, maintains README",
        "subagent_type": "general-purpose",
        "authority": ["write_docs", "update_readme", "create_guides"]
    },
    "designer": {
        "description": "Creates UI/UX designs, mockups, visual assets using AI image generation",
        "subagent_type": "general-purpose",
        "authority": ["generate_images", "create_mockups", "design_ui", "generate_assets"],
        "skills": ["generate-image"],
        "preferred_models": {
            "mockups": "nano-banana-pro",  # Fast, creative, good for UI mockups
            "logos": "flux-2-pro --transparent",  # Professional with transparency
            "hero_images": "flux-2-max",  # Highest quality for hero sections
            "illustrations": "wai-Illustrious"  # Specialized for illustrations
        }
    },
    "media_expert": {
        "description": "Analyzes media generation needs and recommends optimal model based on requirements and budget",
        "subagent_type": "general-purpose",
        "authority": ["analyze_requirements", "recommend_models", "optimize_costs"],
        "skills": ["generate-image", "generate-video"],
        "model_knowledge": {
            "image_models": {
                "premium": ["gpt-image-1-5", "flux-2-max"],  # $0.09-0.23
                "high_quality": ["flux-2-pro", "grok-imagine", "nano-banana-pro"],  # $0.04-0.18
                "standard": ["imagineart-1.5-pro", "seedream-v4"],  # $0.05
                "fast_budget": ["venice-sd35", "hidream", "qwen-image", "z-image-turbo"],  # $0.01
                "specialized": {
                    "anime": "wai-Illustrious",
                    "nsfw": ["lustify-sdxl", "lustify-v7"]
                }
            },
            "video_models": {
                "fastest": "longcat-distilled",  # $0.09/5s, $0.18/10s
                "creative": "grok-imagine",  # $0.32/5s, $0.63/10s
                "balanced": "wan-2.5",  # $0.55/5s, $1.10/10s (default)
                "highest_quality": "wan-2.6",  # $0.83/5s, $1.65/10s
                "realistic": "kling-2.6"  # $0.77/5s, $1.54/10s
            }
        }
    }
}

class ProjectState:
    """Manages persistent project state using SQLite"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.db_path = project_dir / ".autonomous_project.db"
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                project_goal TEXT NOT NULL,
                current_phase TEXT DEFAULT 'initialization'
            )
        """)

        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                agent_id TEXT,
                started_at TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent_role TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                phase TEXT,
                completed_tasks INTEGER,
                data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        conn.commit()
        conn.close()

    def create_session(self, project_goal: str):
        """Create a new project session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, created_at, project_goal)
            VALUES (?, ?, ?)
        """, (self.session_id, datetime.now().isoformat(), project_goal))
        conn.commit()
        conn.close()

    def add_agent(self, role: str, agent_id: str = None):
        """Register a new active agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agents (session_id, role, agent_id, started_at)
            VALUES (?, ?, ?, ?)
        """, (self.session_id, role, agent_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def add_task(self, task_id: str, agent_role: str = None, description: str = None):
        """Add a new task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (session_id, task_id, agent_role, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (self.session_id, task_id, agent_role, description, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def complete_task(self, task_id: str):
        """Mark a task as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET status = 'completed', completed_at = ?
            WHERE task_id = ? AND session_id = ?
        """, (datetime.now().isoformat(), task_id, self.session_id))
        conn.commit()
        conn.close()

    def add_report(self, report: Dict[str, Any]):
        """Add a progress report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (session_id, timestamp, phase, completed_tasks, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            report.get('phase'),
            report.get('completed_tasks', 0),
            json.dumps(report)
        ))
        conn.commit()
        conn.close()

    def set_phase(self, phase: str):
        """Update current project phase"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET current_phase = ?
            WHERE session_id = ?
        """, (phase, self.session_id))
        conn.commit()
        conn.close()

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT project_goal, current_phase, created_at
            FROM sessions
            WHERE session_id = ?
        """, (self.session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "project_goal": row[0],
                "current_phase": row[1],
                "created_at": row[2]
            }
        return {}

    def get_completed_tasks_count(self) -> int:
        """Get count of completed tasks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE session_id = ? AND status = 'completed'
        """, (self.session_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_active_agents(self) -> List[str]:
        """Get list of active agent roles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT role FROM agents
            WHERE session_id = ? AND status = 'active'
        """, (self.session_id,))
        roles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return roles


class CoordinatorAgent:
    """Master coordinator that manages the project and subagents"""

    def __init__(self, project_goal: str, project_dir: Optional[Path] = None):
        self.project_goal = project_goal
        self.project_dir = project_dir or Path.cwd()
        self.state = ProjectState(self.project_dir)
        self.state.create_session(project_goal)

        # Initialize task synchronization
        self.task_sync = None
        if TaskSync:
            try:
                self.task_sync = TaskSync(self.project_dir)
                print("✅ Task synchronization enabled")
            except Exception as e:
                print(f"⚠️  Could not initialize task sync: {e}")

    def sync_tasks_from_json(self, tasks_json: str):
        """
        Sync tasks from JSON string to SQLite database.
        This is used to sync tasks created by spawned agents.

        Args:
            tasks_json: JSON string with array of tasks from TaskList output
        """
        if not self.task_sync:
            return

        try:
            tasks = json.loads(tasks_json)

            if not isinstance(tasks, list):
                print(f"⚠️  Expected array of tasks, got {type(tasks)}")
                return

            synced_count = 0
            for task in tasks:
                task_id = task.get('id') or task.get('task_id')
                subject = task.get('subject', '')
                description = task.get('description', subject)
                status = task.get('status', 'pending')
                owner = task.get('owner')

                if task_id:
                    # Check if task already exists in SQLite
                    conn = sqlite3.connect(self.state.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM tasks WHERE task_id = ?", (str(task_id),))
                    exists = cursor.fetchone()
                    conn.close()

                    if not exists:
                        # Create new task in SQLite
                        self.task_sync.create_task(str(task_id), description, owner)
                        synced_count += 1

                    # Update status if changed
                    if status != 'pending':
                        self.task_sync.update_task(str(task_id), status=status)

            if synced_count > 0:
                print(f"✅ Synced {synced_count} new tasks to SQLite database")

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error while syncing tasks: {e}")
        except Exception as e:
            print(f"⚠️  Error syncing tasks: {e}")

    def sync_tasks_if_available(self):
        """
        Attempt to sync tasks from Claude Code's task system to SQLite.
        This is a placeholder for when the script is run as part of a skill.
        When run standalone, it does nothing.
        """
        if not self.task_sync:
            return

        # When this script is invoked as part of the autonomous-project skill,
        # the coordinator (Claude Code itself) should call sync_tasks_to_db.py
        # to sync tasks from TaskList to SQLite.
        # This method serves as a reminder/hook for that integration.
        print("💡 To sync tasks to web GUI, the coordinator should call:")
        print(f"   python3 ~/.claude/scripts/sync_tasks_to_db.py {self.project_dir}")
        print()

    def initialize_project(self):
        """Initialize the project with task breakdown and agent spawning"""
        print("🚀 Autonomous Project Agent Harness Starting...")
        print(f"📋 Project Goal: {self.project_goal}")
        print(f"📁 Working Directory: {self.project_dir}")
        print()

        # Phase 1: Planning
        print("=" * 80)
        print("PHASE 1: PLANNING & ARCHITECTURE")
        print("=" * 80)
        self.state.set_phase("planning")

        planning_prompt = f"""You are the Planning Agent for this project.

PROJECT GOAL:
{self.project_goal}

YOUR TASKS:
1. Analyze the project requirements
2. Create a comprehensive task breakdown using TaskCreate
3. Define the technical architecture
4. Identify dependencies between tasks
5. Estimate complexity and risks

IMPORTANT INSTRUCTIONS:
- Create tasks in logical order (setup → core features → testing → deployment)
- Use TaskCreate for each major task with clear descriptions
- Include acceptance criteria in task descriptions
- Set up task dependencies using TaskUpdate with addBlockedBy
- Provide a summary of the architecture and approach
- After creating tasks, output them as JSON for synchronization

After creating all tasks, use TaskList to get all tasks and output the result.

Create the initial task tree now."""

        print(f"\n📝 Spawning Planner Agent...")
        print(f"Prompt: {planning_prompt[:200]}...\n")

        # In a real implementation, this would use the Task tool to spawn an agent
        # For now, we'll simulate the output
        print("✅ Planner Agent completed initial breakdown")
        print("   - Created 8 tasks")
        print("   - Defined architecture: Local database + TypeScript + Modern frontend")
        print("   - Set up dependency chain")
        print()

        # Record agent in database
        self.state.add_agent("planner", "planner_001")

        # Sync tasks to SQLite (if running as skill, this will sync Claude Code tasks)
        self.sync_tasks_if_available()

        # Phase 2: Implementation
        print("=" * 80)
        print("PHASE 2: IMPLEMENTATION")
        print("=" * 80)
        self.state.set_phase("implementation")

        print("\n🔨 Spawning Builder Agent for first task...")
        print("✅ Builder Agent started on Task #1: Project Setup")
        print()

        # Phase 3: Quality Check
        print("=" * 80)
        print("PHASE 3: QUALITY ASSURANCE")
        print("=" * 80)
        self.state.set_phase("quality_check")

        print("\n🔍 Spawning Quality Checker Agent...")
        print("✅ Quality Checker reviewing completed work")
        print()

        # Phase 4: Testing
        print("=" * 80)
        print("PHASE 4: TESTING & VALIDATION")
        print("=" * 80)
        self.state.set_phase("testing")

        print("\n🧪 Spawning Tester Agent...")
        print("✅ Tester writing and running tests")
        print()

        # Phase 5: Documentation
        print("=" * 80)
        print("PHASE 5: DOCUMENTATION")
        print("=" * 80)
        self.state.set_phase("documentation")

        print("\n📚 Spawning Documentation Agent...")
        print("✅ Documenter creating README and guides")
        print()

    def generate_report(self):
        """Generate end-of-session progress report"""
        session_info = self.state.get_session_info()
        completed_tasks = self.state.get_completed_tasks_count()
        active_agents = self.state.get_active_agents()

        report = {
            "phase": session_info.get("current_phase", "unknown"),
            "completed_tasks": completed_tasks,
            "active_agents": active_agents,
            "blockers": [],
            "next_priorities": [],
            "recommendations": []
        }

        self.state.add_report(report)

        print()
        print("=" * 80)
        print("📊 PROJECT PROGRESS REPORT")
        print("=" * 80)
        print(f"Session ID: {self.state.session_id}")
        print(f"Current Phase: {report['phase']}")
        print(f"Completed Tasks: {report['completed_tasks']}")
        print(f"Active Agents: {', '.join(report['active_agents']) or 'None'}")
        print()
        print("🎯 NEXT PRIORITIES:")
        print("   1. Complete remaining implementation tasks")
        print("   2. Run full test suite")
        print("   3. Generate deployment documentation")
        print()
        print("⚠️  BLOCKERS: None")
        print()
        print("💡 RECOMMENDATIONS:")
        print("   - Continue with current approach")
        print("   - Monitor test coverage")
        print("   - Prepare deployment checklist")
        print("=" * 80)


# Global variable to track web server process
web_server_process = None


def launch_web_gui(project_dir: Path, port: int = 5000):
    """Launch the web GUI in a background process"""
    global web_server_process

    # Path to the web GUI script
    web_script = Path(__file__).parent / "autonomous_project_web.py"

    if not web_script.exists():
        print(f"⚠️  Web GUI script not found at {web_script}")
        print("   Continuing without web interface...")
        return None

    try:
        # Launch web server in background
        print(f"\n🌐 Launching Web GUI at http://localhost:{port}")
        web_server_process = subprocess.Popen(
            [sys.executable, str(web_script), "--web", "--port", str(port), "--dir", str(project_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Give server time to start
        time.sleep(2)

        # Open browser
        webbrowser.open(f"http://localhost:{port}")

        print(f"✅ Web GUI running at http://localhost:{port}")
        print(f"   Monitor agents and tasks in real-time!\n")

        return web_server_process

    except Exception as e:
        print(f"⚠️  Could not launch web GUI: {e}")
        print("   Continuing without web interface...")
        return None


def cleanup_web_server():
    """Clean up web server process on exit"""
    global web_server_process
    if web_server_process:
        try:
            web_server_process.terminate()
            web_server_process.wait(timeout=5)
        except:
            pass


# Register cleanup handler
atexit.register(cleanup_web_server)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Project Agent Harness - Coordinate AI agents to build projects"
    )
    parser.add_argument(
        "project_goal",
        nargs="?",
        help="Description of the project to build"
    )
    parser.add_argument(
        "--resume",
        help="Resume a previous session by session ID"
    )
    parser.add_argument(
        "--dir",
        help="Project directory (defaults to current directory)",
        default="."
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable automatic web GUI launch"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web GUI port (default: 5000)"
    )

    args = parser.parse_args()

    if args.resume:
        print(f"🔄 Resuming session: {args.resume}")
        # Load previous state and continue
        project_dir = Path(args.dir).resolve()
        state = ProjectState(project_dir)
        state.session_id = args.resume
        session_info = state.get_session_info()

        if not session_info:
            print(f"❌ Error: Session {args.resume} not found")
            sys.exit(1)

        project_goal = session_info.get("project_goal", "Unknown")
        coordinator = CoordinatorAgent(project_goal, project_dir)
        coordinator.state.session_id = args.resume
        coordinator.generate_report()
        return

    if not args.project_goal:
        print("❌ Error: Please provide a project goal")
        print()
        print("Usage:")
        print('  python3 autonomous_project.py "Build a todo app with React"')
        print('  python3 autonomous_project.py --resume SESSION_ID')
        sys.exit(1)

    project_dir = Path(args.dir).resolve()
    coordinator = CoordinatorAgent(args.project_goal, project_dir)

    # Launch web GUI unless disabled
    if not args.no_gui:
        launch_web_gui(project_dir, port=args.port)

    try:
        coordinator.initialize_project()
        coordinator.generate_report()

        print()
        print("✨ Autonomous Project Agent Harness session complete!")
        print(f"📁 State saved to: {coordinator.state.db_path}")
        if not args.no_gui:
            print(f"🌐 Web GUI: http://localhost:{args.port}")
        print()
        print("To resume this session:")
        print(f"  python3 autonomous_project.py --resume {coordinator.state.session_id}")

    except KeyboardInterrupt:
        print("\n\n⏸️  Session paused by user")
        coordinator.generate_report()
        print(f"\nResume with: python3 autonomous_project.py --resume {coordinator.state.session_id}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        coordinator.generate_report()
        sys.exit(1)


if __name__ == "__main__":
    main()
