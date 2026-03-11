import subprocess
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

class Bead(BaseModel):
    id: str
    title: str
    status: str
    priority: Optional[int] = None
    type: Optional[str] = None
    description: Optional[str] = None

class BeadsWrapper:
    def __init__(self, executable: str = "bd"):
        self.executable = executable

    def _run_command(self, args: List[str]) -> str:
        """Runs a beads command and returns the output."""
        try:
            result = subprocess.run(
                [self.executable] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Some commands might return non-zero exit codes but still be useful
            # or we might want to handle them differently
            return e.stdout.strip() or e.stderr.strip()

    def list_issues(self, status: Optional[str] = None) -> str:
        """Lists issues, optionally filtered by status."""
        args = ["list"]
        if status:
            args.append(f"--status={status}")
        return self._run_command(args)

    def create_issue(self, title: str, description: Optional[str] = None, 
                     issue_type: str = "task", priority: int = 2) -> str:
        """Creates a new issue."""
        args = ["create", "--title", title, "--type", issue_type, "--priority", str(priority)]
        if description:
            args.extend(["--description", description])
        return self._run_command(args)

    def close_issue(self, issue_id: str, reason: Optional[str] = None) -> str:
        """Closes an issue."""
        args = ["close", issue_id]
        if reason:
            args.extend(["--reason", reason])
        return self._run_command(args)

    def get_ready(self) -> str:
        """Shows issues ready to work."""
        return self._run_command(["ready"])

    def get_state(self) -> str:
        """Returns the full project state from beads."""
        return self.list_issues()

    def send_message(self, from_agent: str, to_agent: str, content: str) -> str:
        """Sends an inter-agent message by creating a bead."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        title = f"MESSAGE: [{timestamp}] {from_agent}→{to_agent}: {content}"
        return self.create_issue(title, issue_type="task", priority=3)

# Global instance
beads = BeadsWrapper()
