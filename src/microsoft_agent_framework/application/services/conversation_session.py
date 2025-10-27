"""Session management for automatic thread handling."""

import json
from pathlib import Path


class ConversationSession:
    """Manages conversation sessions with automatic thread handling."""

    def __init__(self, session_dir: str = ".sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.current_session_file = self.session_dir / "current.json"

    def get_current_thread_id(self, agent_type: str = "supervisor") -> str | None:
        """Get the current active thread ID for an agent type."""
        if not self.current_session_file.exists():
            return None

        try:
            with open(self.current_session_file) as f:
                session_data = json.load(f)

            return session_data.get("threads", {}).get(agent_type)
        except (json.JSONDecodeError, KeyError):
            return None

    def set_current_thread_id(self, agent_type: str, thread_id: str) -> None:
        """Set the current active thread ID for an agent type."""
        session_data = {"threads": {}}

        # Load existing session data
        if self.current_session_file.exists():
            try:
                with open(self.current_session_file) as f:
                    session_data = json.load(f)
            except (json.JSONDecodeError, KeyError):
                session_data = {"threads": {}}

        # Ensure threads dict exists
        if "threads" not in session_data:
            session_data["threads"] = {}

        # Update thread for agent type
        session_data["threads"][agent_type] = thread_id

        # Save session data
        with open(self.current_session_file, "w") as f:
            json.dump(session_data, f, indent=2)

    def clear_current_thread(self, agent_type: str) -> None:
        """Clear the current active thread for an agent type."""
        if not self.current_session_file.exists():
            return

        try:
            with open(self.current_session_file) as f:
                session_data = json.load(f)

            if "threads" in session_data and agent_type in session_data["threads"]:
                del session_data["threads"][agent_type]

                with open(self.current_session_file, "w") as f:
                    json.dump(session_data, f, indent=2)
        except (json.JSONDecodeError, KeyError):
            pass

    def clear_all_sessions(self) -> None:
        """Clear all session data."""
        if self.current_session_file.exists():
            self.current_session_file.unlink()

    def get_session_info(self) -> dict:
        """Get current session information."""
        if not self.current_session_file.exists():
            return {"threads": {}}

        try:
            with open(self.current_session_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return {"threads": {}}
