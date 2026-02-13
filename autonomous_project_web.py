#!/usr/bin/env python3
"""
Autonomous Project Agent Harness - Web GUI Edition

Includes a Flask-based web interface for managing agents, tasks, and sessions.

Usage:
    python3 autonomous_project_web.py --web                    # Start web GUI
    python3 autonomous_project_web.py --web --port 5001       # Custom port
    python3 autonomous_project_web.py "Build a todo app"      # CLI mode (original)
"""

import json
import sys
import sqlite3
import time
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import argparse
import webbrowser
from threading import Thread

try:
    from flask import (
        Flask,
        render_template_string,
        jsonify,
        request,
        send_from_directory,
    )
except ImportError:
    print("Flask not installed. Install with: pip install flask")
    sys.exit(1)

# Import the original coordinator
sys.path.insert(0, str(Path(__file__).parent))

# Agent role definitions
AGENT_ROLES = {
    "planner": {
        "description": "Analyzes requirements, creates task breakdowns, designs architecture",
        "subagent_type": "Plan",
        "authority": ["create_tasks", "update_architecture", "define_requirements"],
    },
    "builder": {
        "description": "Implements features, writes code, creates files",
        "subagent_type": "general-purpose",
        "authority": ["write_code", "edit_files", "create_components"],
    },
    "quality_checker": {
        "description": "Reviews code quality, enforces standards, validates implementations",
        "subagent_type": "general-purpose",
        "authority": ["review_code", "request_changes", "approve_tasks"],
    },
    "tester": {
        "description": "Writes tests, validates functionality, ensures correctness",
        "subagent_type": "general-purpose",
        "authority": ["write_tests", "run_tests", "validate_features"],
    },
    "documenter": {
        "description": "Creates documentation, comments code, maintains README",
        "subagent_type": "general-purpose",
        "authority": ["write_docs", "update_readme", "create_guides"],
    },
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

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, created_at, project_goal, current_phase
            FROM sessions
            ORDER BY created_at DESC
        """)
        sessions = []
        for row in cursor.fetchall():
            sessions.append(
                {
                    "session_id": row[0],
                    "created_at": row[1],
                    "project_goal": row[2],
                    "current_phase": row[3],
                }
            )
        conn.close()
        return sessions

    def get_all_tasks(self, session_id: str = None) -> List[Dict[str, Any]]:
        """Get all tasks, optionally filtered by session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                """
                SELECT id, session_id, task_id, agent_role, description, status, created_at, completed_at
                FROM tasks
                WHERE session_id = ?
                ORDER BY created_at DESC
            """,
                (session_id,),
            )
        else:
            cursor.execute("""
                SELECT id, session_id, task_id, agent_role, description, status, created_at, completed_at
                FROM tasks
                ORDER BY created_at DESC
            """)

        tasks = []
        for row in cursor.fetchall():
            tasks.append(
                {
                    "id": row[0],
                    "session_id": row[1],
                    "task_id": row[2],
                    "agent_role": row[3],
                    "description": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "completed_at": row[7],
                }
            )
        conn.close()
        return tasks

    def get_all_agents(self, session_id: str = None) -> List[Dict[str, Any]]:
        """Get all agents, optionally filtered by session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                """
                SELECT id, session_id, role, agent_id, started_at, status
                FROM agents
                WHERE session_id = ?
                ORDER BY started_at DESC
            """,
                (session_id,),
            )
        else:
            cursor.execute("""
                SELECT id, session_id, role, agent_id, started_at, status
                FROM agents
                ORDER BY started_at DESC
            """)

        agents = []
        for row in cursor.fetchall():
            agents.append(
                {
                    "id": row[0],
                    "session_id": row[1],
                    "role": row[2],
                    "agent_id": row[3],
                    "started_at": row[4],
                    "status": row[5],
                }
            )
        conn.close()
        return agents

    def add_task(
        self,
        task_id: str,
        agent_role: str = None,
        description: str = None,
        session_id: str = None,
    ):
        """Add a new task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        sid = session_id or self.session_id
        cursor.execute(
            """
            INSERT INTO tasks (session_id, task_id, agent_role, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (sid, task_id, agent_role, description, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def update_task(
        self,
        task_id: str,
        status: str = None,
        agent_role: str = None,
        description: str = None,
    ):
        """Update a task"""
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

        conn.close()

    def delete_task(self, task_id: str):
        """Delete a task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()


# Flask Web App
app = Flask(__name__)
state = None


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Project Agent Harness</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 16px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .card h2 {
            color: #333;
            font-size: 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: auto;
        }

        .badge.pending { background: #fef3c7; color: #92400e; }
        .badge.in-progress { background: #dbeafe; color: #1e40af; }
        .badge.completed { background: #d1fae5; color: #065f46; }
        .badge.active { background: #dcfce7; color: #166534; }
        .badge.retired { background: #f3f4f6; color: #6b7280; }

        .task-list, .agent-list, .session-list {
            list-style: none;
        }

        .task-item, .agent-item, .session-item {
            padding: 15px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 10px;
            transition: all 0.2s;
        }

        .task-item:hover, .agent-item:hover, .session-item:hover {
            border-color: #667eea;
            background: #f9fafb;
        }

        .task-header, .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .task-title {
            font-weight: 600;
            color: #111827;
        }

        .task-description {
            color: #6b7280;
            font-size: 14px;
            margin-top: 5px;
        }

        .task-meta {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            font-size: 12px;
            color: #9ca3af;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
        }

        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
        }

        .btn-success { background: #10b981; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-warning { background: #f59e0b; color: white; }

        .actions {
            display: flex;
            gap: 8px;
        }

        .form-group {
            margin-bottom: 15px;
        }

        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #374151;
            font-size: 14px;
        }

        input, textarea, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
        }

        textarea {
            resize: vertical;
            min-height: 80px;
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }

        .modal-header {
            margin-bottom: 20px;
        }

        .modal-header h3 {
            color: #111827;
            font-size: 20px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-number {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 12px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #9ca3af;
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Autonomous Project Agent Harness</h1>
            <p class="subtitle">Manage AI agents, tasks, and project sessions</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalTasks">0</div>
                <div class="stat-label">Total Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="activeTasks">0</div>
                <div class="stat-label">Active Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalAgents">0</div>
                <div class="stat-label">Total Agents</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalSessions">0</div>
                <div class="stat-label">Sessions</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>
                    📋 Tasks
                    <button class="btn btn-primary btn-small" onclick="openAddTaskModal()">+ Add Task</button>
                </h2>
                <ul class="task-list" id="taskList"></ul>
            </div>

            <div class="card">
                <h2>🤖 Agents</h2>
                <ul class="agent-list" id="agentList"></ul>
            </div>
        </div>

        <div class="card">
            <h2>💾 Sessions</h2>
            <ul class="session-list" id="sessionList"></ul>
        </div>
    </div>

    <!-- Add Task Modal -->
    <div class="modal" id="addTaskModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Add New Task</h3>
            </div>
            <form id="addTaskForm">
                <div class="form-group">
                    <label>Task ID</label>
                    <input type="text" name="task_id" required placeholder="task-001">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" required placeholder="What needs to be done?"></textarea>
                </div>
                <div class="form-group">
                    <label>Agent Role</label>
                    <select name="agent_role">
                        <option value="">Unassigned</option>
                        <option value="planner">Planner</option>
                        <option value="builder">Builder</option>
                        <option value="quality_checker">Quality Checker</option>
                        <option value="tester">Tester</option>
                        <option value="documenter">Documenter</option>
                    </select>
                </div>
                <div class="actions">
                    <button type="submit" class="btn btn-primary">Add Task</button>
                    <button type="button" class="btn btn-secondary" onclick="closeAddTaskModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Edit Task Modal -->
    <div class="modal" id="editTaskModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Edit Task</h3>
            </div>
            <form id="editTaskForm">
                <input type="hidden" name="task_id">
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" required></textarea>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Agent Role</label>
                    <select name="agent_role">
                        <option value="">Unassigned</option>
                        <option value="planner">Planner</option>
                        <option value="builder">Builder</option>
                        <option value="quality_checker">Quality Checker</option>
                        <option value="tester">Tester</option>
                        <option value="documenter">Documenter</option>
                    </select>
                </div>
                <div class="actions">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <button type="button" class="btn btn-secondary" onclick="closeEditTaskModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let currentEditTaskId = null;

        async function fetchData() {
            try {
                const [tasks, agents, sessions] = await Promise.all([
                    fetch('/api/tasks').then(r => r.json()),
                    fetch('/api/agents').then(r => r.json()),
                    fetch('/api/sessions').then(r => r.json())
                ]);

                renderTasks(tasks);
                renderAgents(agents);
                renderSessions(sessions);
                updateStats(tasks, agents, sessions);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        function updateStats(tasks, agents, sessions) {
            document.getElementById('totalTasks').textContent = tasks.length;
            document.getElementById('activeTasks').textContent = tasks.filter(t => t.status !== 'completed').length;
            document.getElementById('totalAgents').textContent = agents.length;
            document.getElementById('totalSessions').textContent = sessions.length;
        }

        function renderTasks(tasks) {
            const list = document.getElementById('taskList');
            if (tasks.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p>No tasks yet. Add one to get started!</p></div>';
                return;
            }

            list.innerHTML = tasks.map(task => `
                <li class="task-item">
                    <div class="task-header">
                        <span class="task-title">${task.task_id}</span>
                        <span class="badge ${task.status}">${task.status.replace('_', ' ')}</span>
                    </div>
                    <div class="task-description">${task.description || 'No description'}</div>
                    <div class="task-meta">
                        ${task.agent_role ? `<span>👤 ${task.agent_role}</span>` : '<span>👤 Unassigned</span>'}
                        <span>📅 ${new Date(task.created_at).toLocaleString()}</span>
                    </div>
                    <div class="actions" style="margin-top: 10px;">
                        <button class="btn btn-warning btn-small" onclick="editTask('${task.task_id}')">Edit</button>
                        ${task.status !== 'completed' ? `<button class="btn btn-success btn-small" onclick="updateTaskStatus('${task.task_id}', 'completed')">Complete</button>` : ''}
                        <button class="btn btn-danger btn-small" onclick="deleteTask('${task.task_id}')">Delete</button>
                    </div>
                </li>
            `).join('');
        }

        function renderAgents(agents) {
            const list = document.getElementById('agentList');
            if (agents.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🤖</div><p>No agents spawned yet</p></div>';
                return;
            }

            list.innerHTML = agents.map(agent => `
                <li class="agent-item">
                    <div class="agent-header">
                        <span class="task-title">${agent.role}</span>
                        <span class="badge ${agent.status}">${agent.status}</span>
                    </div>
                    <div class="task-meta">
                        ${agent.agent_id ? `<span>🆔 ${agent.agent_id}</span>` : ''}
                        <span>📅 ${new Date(agent.started_at).toLocaleString()}</span>
                    </div>
                </li>
            `).join('');
        }

        function renderSessions(sessions) {
            const list = document.getElementById('sessionList');
            if (sessions.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💾</div><p>No sessions found</p></div>';
                return;
            }

            list.innerHTML = sessions.map(session => `
                <li class="session-item">
                    <div class="task-header">
                        <span class="task-title">${session.session_id}</span>
                        <span class="badge ${session.current_phase}">${session.current_phase}</span>
                    </div>
                    <div class="task-description">${session.project_goal}</div>
                    <div class="task-meta">
                        <span>📅 ${new Date(session.created_at).toLocaleString()}</span>
                    </div>
                </li>
            `).join('');
        }

        function openAddTaskModal() {
            document.getElementById('addTaskModal').classList.add('active');
        }

        function closeAddTaskModal() {
            document.getElementById('addTaskModal').classList.remove('active');
            document.getElementById('addTaskForm').reset();
        }

        function openEditTaskModal() {
            document.getElementById('editTaskModal').classList.add('active');
        }

        function closeEditTaskModal() {
            document.getElementById('editTaskModal').classList.remove('active');
            document.getElementById('editTaskForm').reset();
            currentEditTaskId = null;
        }

        async function editTask(taskId) {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            const task = tasks.find(t => t.task_id === taskId);

            if (task) {
                currentEditTaskId = taskId;
                const form = document.getElementById('editTaskForm');
                form.task_id.value = taskId;
                form.description.value = task.description || '';
                form.status.value = task.status;
                form.agent_role.value = task.agent_role || '';
                openEditTaskModal();
            }
        }

        document.getElementById('addTaskForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);

            await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            closeAddTaskModal();
            fetchData();
        });

        document.getElementById('editTaskForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);

            await fetch(`/api/tasks/${data.task_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            closeEditTaskModal();
            fetchData();
        });

        async function updateTaskStatus(taskId, status) {
            await fetch(`/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            fetchData();
        }

        async function deleteTask(taskId) {
            if (confirm('Are you sure you want to delete this task?')) {
                await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                fetchData();
            }
        }

        // Close modals when clicking outside
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });
        });

        // Initial load and refresh every 3 seconds
        fetchData();
        setInterval(fetchData, 3000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/sessions")
def get_sessions():
    global state
    if not state:
        return jsonify([])
    sessions = state.get_all_sessions()
    return jsonify(sessions)


@app.route("/api/tasks")
def get_tasks():
    global state
    if not state:
        return jsonify([])
    session_id = request.args.get("session_id")
    tasks = state.get_all_tasks(session_id)
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def add_task():
    global state
    if not state:
        return jsonify({"error": "No state available"}), 400

    data = request.json
    state.add_task(
        task_id=data["task_id"],
        agent_role=data.get("agent_role"),
        description=data.get("description"),
    )
    return jsonify({"success": True})


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    global state
    if not state:
        return jsonify({"error": "No state available"}), 400

    data = request.json
    state.update_task(
        task_id=task_id,
        status=data.get("status"),
        agent_role=data.get("agent_role"),
        description=data.get("description"),
    )
    return jsonify({"success": True})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    global state
    if not state:
        return jsonify({"error": "No state available"}), 400

    state.delete_task(task_id)
    return jsonify({"success": True})


@app.route("/api/agents")
def get_agents():
    global state
    if not state:
        return jsonify([])
    session_id = request.args.get("session_id")
    agents = state.get_all_agents(session_id)
    return jsonify(agents)


def find_available_port(start_port=5000, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port after {max_attempts} attempts")


def run_web_server(port=None, project_dir=None):
    """Start the web server"""
    global state

    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir).resolve()

    state = ProjectState(project_dir)

    if port is None:
        port = find_available_port()

    print(f"\n🌐 Starting Autonomous Project Web GUI...")
    print(f"📁 Project Directory: {project_dir}")
    print(f"💾 Database: {state.db_path}")
    print(f"🚀 Server: http://localhost:{port}")
    print(f"\n✨ Opening browser...\n")

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    Thread(target=open_browser, daemon=True).start()

    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Project Agent Harness - Web GUI Edition"
    )
    parser.add_argument("--web", action="store_true", help="Start web GUI")
    parser.add_argument(
        "--port", type=int, default=None, help="Web server port (default: auto-detect)"
    )
    parser.add_argument(
        "--dir", help="Project directory (defaults to current directory)", default="."
    )

    args = parser.parse_args()

    if args.web:
        run_web_server(port=args.port, project_dir=args.dir)
    else:
        print("Use --web to start the web GUI")
        print(f"Example: python3 {Path(__file__).name} --web")


if __name__ == "__main__":
    main()
