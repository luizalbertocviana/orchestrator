"""Broker wrapper for inter-agent message handling.

This module provides a Python interface to the broker shell script,
allowing agents and the orchestrator to send, read, and acknowledge messages.
"""

import subprocess
import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class BrokerError(Exception):
    """Exception raised for broker command failures."""
    pass


class BrokerWrapper:
    """Wrapper for the broker shell script.

    Provides methods for sending, reading, and acknowledging messages
    in the multi-agent SDLC system.
    """

    def __init__(
        self,
        broker_path: Optional[str] = None,
        messages_file: Optional[str] = None,
        target_project_root: Optional[Path] = None,
    ):
        """Initialize the broker wrapper.

        Args:
            broker_path: Path to the broker script. Defaults to 'tools/broker' relative to orchestrator root.
            messages_file: Path to the messages JSONL file. Defaults to 'messages.jsonl' in target project root.
            target_project_root: Root of the target project being worked on. Defaults to current working directory.
                Used to resolve messages_file path. The broker_path is resolved relative to the orchestrator root.
        """
        # Find orchestrator root (where .git directory is) - for broker_path
        self.orchestrator_root = self._find_project_root()
        
        # Target project root - for messages_file (where the project being developed is)
        self.target_project_root = target_project_root or Path.cwd()

        if broker_path:
            self.broker_path = Path(broker_path)
            if not self.broker_path.is_absolute():
                self.broker_path = self.orchestrator_root / self.broker_path
        else:
            self.broker_path = self.orchestrator_root / "tools" / "broker"

        self.messages_file = messages_file
        if self.messages_file and not Path(self.messages_file).is_absolute():
            self.messages_file = str(self.target_project_root / self.messages_file)

        self._env = os.environ.copy()
        if self.messages_file:
            self._env["MESSAGES_FILE"] = self.messages_file

    def _find_project_root(self) -> Path:
        """Find the orchestrator project root by looking for .git directory.

        This method starts from the orchestrator's own directory (where this script resides)
        and walks up the directory tree to find the .git directory, ensuring it always
        returns the orchestrator project root regardless of the current working directory.

        Returns:
            Path to the orchestrator project root
        """
        # Start from the directory where this module is located
        current = Path(__file__).resolve().parent
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
        # Fallback to current working directory if .git not found
        return Path.cwd()

    def _run_command(self, args: List[str]) -> str:
        """Run a broker command and return stdout.
        
        Args:
            args: Command arguments (without 'broker' prefix)
            
        Returns:
            Command stdout as string
            
        Raises:
            BrokerError: If command fails
        """
        cmd = [str(self.broker_path)] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._env
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise BrokerError(f"Broker command failed: {e.stderr}")
        except FileNotFoundError:
            raise BrokerError(f"Broker script not found at {self.broker_path}")
    
    def send_message(self, from_agent: str, to_agent: str, content: str) -> str:
        """Send a message to another agent.
        
        Args:
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            content: Message content
            
        Returns:
            The message ID (e.g., 'msg_1234567890_a1b2c3d4')
            
        Raises:
            BrokerError: If sending fails
        """
        output = self._run_command([
            "send",
            "--from", from_agent,
            "--to", to_agent,
            "--content", content
        ])
        # Output is JSON, extract id
        try:
            msg = json.loads(output.strip())
            return msg.get("id", "")
        except json.JSONDecodeError:
            # If output is not JSON, return empty string
            return ""
    
    def read_messages(self, agent_name: str, include_acknowledged: bool = False) -> List[Dict]:
        """Read messages for an agent.
        
        Args:
            agent_name: Name of the agent to read messages for
            include_acknowledged: If True, include already acknowledged messages
            
        Returns:
            List of message dictionaries
        """
        args = ["read", agent_name]
        if include_acknowledged:
            args.append("--all")
        
        try:
            output = self._run_command(args)
            if not output.strip():
                return []
            # Output may be multiple JSON objects (JSONL) or single JSON array
            messages = []
            for line in output.strip().splitlines():
                if line.strip():
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return messages
        except BrokerError:
            return []
    
    def acknowledge_message(self, msg_id: str) -> bool:
        """Acknowledge a message.
        
        Args:
            msg_id: The message ID to acknowledge
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_command(["ack", msg_id])
            return True
        except BrokerError:
            return False
    
    def acknowledge_messages(self, msg_ids: List[str]) -> int:
        """Acknowledge multiple messages.
        
        Args:
            msg_ids: List of message IDs to acknowledge
            
        Returns:
            Number of messages successfully acknowledged
        """
        if not msg_ids:
            return 0
        
        try:
            self._run_command(["ack"] + msg_ids)
            return len(msg_ids)
        except BrokerError:
            # Try acknowledging one by one
            count = 0
            for msg_id in msg_ids:
                if self.acknowledge_message(msg_id):
                    count += 1
            return count
    
    def count_pending(self, agent_name: str) -> int:
        """Count pending (unacknowledged) messages for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Number of pending messages
        """
        messages = self.read_messages(agent_name, include_acknowledged=False)
        return len(messages)

    def _parse_json_objects(self, content: str) -> List[Dict]:
        """Parse multiple JSON objects from content (handles pretty-printed JSON).

        The broker script outputs pretty-printed JSON (multi-line), not JSONL.
        This method uses json.JSONDecoder.raw_decode() to properly parse
        consecutive JSON objects, handling all JSON edge cases correctly
        (strings with braces, escaped quotes, nested structures, etc.).

        Args:
            content: The file content containing multiple JSON objects

        Returns:
            List of parsed JSON objects
        """
        decoder = json.JSONDecoder()
        objects = []
        pos = 0

        while pos < len(content):
            # Skip whitespace
            while pos < len(content) and content[pos].isspace():
                pos += 1

            if pos >= len(content):
                break

            try:
                obj, end_idx = decoder.raw_decode(content, pos)
                if isinstance(obj, dict):
                    objects.append(obj)
                pos = end_idx
            except json.JSONDecodeError:
                # Skip invalid content and continue
                pos += 1

        return objects

    def get_all_pending(self) -> List[Dict]:
        """Get all pending (unacknowledged) messages from the messages file.

        The broker script outputs pretty-printed JSON (multi-line objects),
        not JSONL. This method properly parses that format.

        Returns:
            List of pending message dictionaries
        """
        messages_file = self.messages_file or str(self.target_project_root / "messages.jsonl")

        if not Path(messages_file).exists():
            return []

        try:
            with open(messages_file, 'r') as f:
                content = f.read()
        except (IOError, OSError):
            return []

        all_messages = self._parse_json_objects(content)

        # Filter for unacknowledged messages only
        return [msg for msg in all_messages if msg.get("timestamp_ack") is None]
    
    def count_by_agent(self) -> Dict[str, int]:
        """Count pending messages per agent.
        
        Returns:
            Dict mapping agent names to pending message counts
        """
        all_pending = self.get_all_pending()
        counts: Dict[str, int] = {}
        
        for msg in all_pending:
            to_agent = msg.get("to", "")
            if to_agent:
                counts[to_agent] = counts.get(to_agent, 0) + 1
        
        return counts
    
    def generate_context(self) -> str:
        """Generate context information for agents.

        Provides system state overview (pending messages by agent).

        Returns:
            Context string with system state
        """
        counts = self.count_by_agent()
        total_pending = sum(counts.values())
        
        lines = [
            "# Broker Message State",
            "",
            f"Total pending messages: {total_pending}",
            "",
            "Messages by agent:"
        ]
        
        if counts:
            for agent, count in sorted(counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {agent}: {count}")
        else:
            lines.append("  (no pending messages)")
        
        lines.append("")
        lines.append(f"Messages file: {self.messages_file or 'messages.jsonl'}")
        
        return "\n".join(lines)
    
    def verify(self) -> bool:
        """Verify that the broker script exists and is executable.

        Returns:
            True if broker is available, False otherwise
        """
        return self.broker_path.exists() and os.access(self.broker_path, os.X_OK)

    def get_onboard_content(self) -> str:
        """Returns full 'broker onboard' output for agent context.

        This method executes 'broker onboard' and returns the complete
        usage documentation for inclusion in agent context.

        Returns:
            Complete onboard documentation string
        """
        try:
            return self._run_command(["onboard"])
        except BrokerError:
            return ""


# Global instance for convenience
_broker: Optional[BrokerWrapper] = None


def get_broker() -> BrokerWrapper:
    """Get the global broker instance.
    
    Returns:
        BrokerWrapper instance
    """
    global _broker
    if _broker is None:
        _broker = BrokerWrapper()
    return _broker
