"""Memory wrapper for unified knowledge store.

This module provides a Python interface to the memory shell script,
allowing agents and the orchestrator to create, read, update, and delete
memory items (tasks, notes, metrics, decisions, artifacts, blockers).
"""

import subprocess
import json
import os
from typing import List, Dict, Optional, Any
from pathlib import Path


class MemoryError(Exception):
    """Exception raised for memory command failures."""
    pass


class MemoryWrapper:
    """Wrapper for the memory shell script.

    Provides methods for CRUD operations on memory items
    in the multi-agent SDLC system.
    """

    def __init__(
        self,
        memory_path: Optional[str] = None,
        memory_file: Optional[str] = None,
        target_project_root: Optional[Path] = None,
    ):
        """Initialize the memory wrapper.

        Args:
            memory_path: Path to the memory script. Defaults to 'tools/memory' relative to orchestrator root.
            memory_file: Path to the memory JSONL file. Defaults to 'memory.jsonl' in target project root.
            target_project_root: Root of the target project being worked on. Defaults to current working directory.
                Used to resolve memory_file path. The memory_path is resolved relative to the orchestrator root.
        """
        # Find orchestrator root (where .git directory is) - for memory_path
        self.orchestrator_root = self._find_project_root()

        # Target project root - for memory_file (where the project being developed is)
        self.target_project_root = target_project_root or Path.cwd()

        if memory_path:
            self.memory_path = Path(memory_path)
            if not self.memory_path.is_absolute():
                self.memory_path = self.orchestrator_root / self.memory_path
        else:
            self.memory_path = self.orchestrator_root / "tools" / "memory"

        self.memory_file = memory_file
        if self.memory_file and not Path(self.memory_file).is_absolute():
            self.memory_file = str(self.target_project_root / self.memory_file)

        self._env = os.environ.copy()
        if self.memory_file:
            self._env["MEMORY_FILE"] = self.memory_file

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
        """Run a memory command and return stdout.

        Args:
            args: Command arguments (without 'memory' prefix)

        Returns:
            Command stdout as string

        Raises:
            MemoryError: If command fails
        """
        cmd = [str(self.memory_path)] + args
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
            raise MemoryError(f"Memory command failed: {e.stderr}")
        except FileNotFoundError:
            raise MemoryError(f"Memory script not found at {self.memory_path}")

    def create_item(
        self,
        item_type: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        priority: int = 2,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Create a new memory item.

        Args:
            item_type: Type of item (task, note, metric, decision, artifact, blocker)
            title: Item title (not required for metrics)
            content: Detailed content/description
            priority: Priority level 0-4 (default: 2)
            assignee: Assigned agent name
            status: Item status (default: pending)
            tags: List of tags
            **kwargs: Type-specific arguments

        Returns:
            The item ID (e.g., 'mem_1234567890_a1b2c3d4')

        Raises:
            MemoryError: If creation fails
        """
        args = ["create", "--type", item_type]

        if title:
            args.append(title)

        if content:
            args.extend(["--content", content])

        args.extend(["--priority", str(priority)])

        if assignee:
            args.extend(["--assignee", assignee])

        if status:
            args.extend(["--status", status])

        if tags:
            args.extend(["--tags", ",".join(tags)])

        # Type-specific arguments
        if item_type == "task":
            if "due_iteration" in kwargs:
                args.extend(["--due-iteration", str(kwargs["due_iteration"])])

        elif item_type == "note":
            if "category" in kwargs:
                args.extend(["--category", kwargs["category"]])

        elif item_type == "metric":
            if "name" in kwargs:
                args.extend(["--name", kwargs["name"]])
            if "value" in kwargs:
                args.extend(["--value", str(kwargs["value"])])
            if "unit" in kwargs:
                args.extend(["--unit", kwargs["unit"]])
            if "trend" in kwargs:
                args.extend(["--trend", kwargs["trend"]])

        elif item_type == "decision":
            if "context" in kwargs:
                args.extend(["--context", kwargs["context"]])
            if "consequence" in kwargs:
                args.extend(["--consequence", kwargs["consequence"]])
            if "alternatives" in kwargs:
                args.extend(["--alternatives", ",".join(kwargs["alternatives"])])
            if "decision_status" in kwargs:
                args.extend(["--decision-status", kwargs["decision_status"]])

        elif item_type == "artifact":
            if "path" in kwargs:
                args.extend(["--path", kwargs["path"]])
            if "checksum" in kwargs:
                args.extend(["--checksum", kwargs["checksum"]])
            if "artifact_type" in kwargs:
                args.extend(["--artifact-type", kwargs["artifact_type"]])

        elif item_type == "blocker":
            if "urgency" in kwargs:
                args.extend(["--urgency", kwargs["urgency"]])
            if "blocked_by" in kwargs:
                args.extend(["--blocked-by", kwargs["blocked_by"]])
            if "affects" in kwargs:
                args.extend(["--affects", ",".join(kwargs["affects"])])
            if "resolution" in kwargs:
                args.extend(["--resolution", kwargs["resolution"]])

        output = self._run_command(args)
        # Output is JSON, extract id
        try:
            item = json.loads(output.strip())
            return item.get("id", "")
        except json.JSONDecodeError:
            return ""

    def list_items(
        self,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[int] = None,
        priority_min: Optional[int] = None,
        priority_max: Optional[int] = None,
        tags: Optional[List[str]] = None,
        since: Optional[int] = None,
        until: Optional[int] = None,
        name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """List memory items with optional filters.

        Args:
            item_type: Filter by type
            status: Filter by status
            assignee: Filter by assignee
            priority: Filter by exact priority
            priority_min: Filter by minimum priority (<=)
            priority_max: Filter by maximum priority (>=)
            tags: Filter by tags (list of tag strings)
            since: Filter items created since iteration N
            until: Filter items created until iteration N
            name: Filter metrics by name
            limit: Limit results to N items

        Returns:
            List of item dictionaries
        """
        args = ["list", "--json"]

        if item_type:
            args.extend(["--type", item_type])

        if status:
            args.extend(["--status", status])

        if assignee:
            args.extend(["--assignee", assignee])

        if priority is not None:
            args.extend(["--priority", str(priority)])

        if priority_min is not None:
            args.extend(["--priority-min", str(priority_min)])

        if priority_max is not None:
            args.extend(["--priority-max", str(priority_max)])

        if tags:
            for tag in tags:
                args.extend(["--tag", tag])

        if since is not None:
            args.extend(["--since", str(since)])

        if until is not None:
            args.extend(["--until", str(until)])

        if name:
            args.extend(["--name", name])

        if limit:
            args.extend(["--limit", str(limit)])

        try:
            output = self._run_command(args)
            if not output.strip():
                return []
            # Output is JSON array
            return json.loads(output.strip())
        except (MemoryError, json.JSONDecodeError):
            return []

    def show_item(self, item_id: str) -> Dict:
        """Show details of a specific memory item.

        Args:
            item_id: Item ID (e.g., 'mem_1234567890_a1b2c3d4')

        Returns:
            Item dictionary with full details
        """
        try:
            output = self._run_command(["show", item_id])
            if not output.strip():
                return {}
            return json.loads(output.strip())
        except (MemoryError, json.JSONDecodeError):
            return {}

    def update_item(
        self,
        item_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> bool:
        """Update an existing memory item.

        Args:
            item_id: Item ID to update
            title: Update title
            content: Update content
            status: Update status
            priority: Update priority
            assignee: Update assignee
            tags: Replace all tags
            add_tags: Add to existing tags
            remove_tags: Remove from existing tags
            **kwargs: Type-specific update arguments

        Returns:
            True if successful, False otherwise
        """
        args = ["update", item_id]

        if title:
            args.extend(["--title", title])

        if content:
            args.extend(["--content", content])

        if status:
            args.extend(["--status", status])

        if priority is not None:
            args.extend(["--priority", str(priority)])

        if assignee:
            args.extend(["--assignee", assignee])

        if tags:
            args.extend(["--tags", ",".join(tags)])

        if add_tags:
            args.extend(["--add-tags", ",".join(add_tags)])

        if remove_tags:
            args.extend(["--remove-tags", ",".join(remove_tags)])

        # Type-specific updates
        if "value" in kwargs:
            args.extend(["--value", str(kwargs["value"])])
        if "trend" in kwargs:
            args.extend(["--trend", kwargs["trend"]])
        if "path" in kwargs:
            args.extend(["--path", kwargs["path"]])
        if "checksum" in kwargs:
            args.extend(["--checksum", kwargs["checksum"]])
        if "artifact_type" in kwargs:
            args.extend(["--artifact-type", kwargs["artifact_type"]])
        if "affects" in kwargs:
            args.extend(["--affects", ",".join(kwargs["affects"])])
        if "resolution" in kwargs:
            args.extend(["--resolution", kwargs["resolution"]])
        if "due_iteration" in kwargs:
            args.extend(["--due-iteration", str(kwargs["due_iteration"])])
        if "category" in kwargs:
            args.extend(["--category", kwargs["category"]])
        if "alternatives" in kwargs:
            args.extend(["--alternatives", ",".join(kwargs["alternatives"])])
        if "decision_status" in kwargs:
            args.extend(["--decision-status", kwargs["decision_status"]])

        try:
            self._run_command(args)
            return True
        except MemoryError:
            return False

    def delete_item(self, item_id: str) -> bool:
        """Delete a memory item.

        Args:
            item_id: Item ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_command(["delete", item_id])
            return True
        except MemoryError:
            return False

    def search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Search memory items by text query.

        Args:
            query: Search query (matches title, content, tags)
            item_type: Filter by type
            limit: Limit results

        Returns:
            List of matching item dictionaries
        """
        args = ["search", query, "--json"]

        if item_type:
            args.extend(["--type", item_type])

        if limit:
            args.extend(["--limit", str(limit)])

        try:
            output = self._run_command(args)
            if not output.strip():
                return []
            return json.loads(output.strip())
        except (MemoryError, json.JSONDecodeError):
            return []

    def link_items(self, item_id: str, related_to: str, relation: str) -> bool:
        """Create a relation between two memory items.

        Args:
            item_id: Source item ID
            related_to: Target item ID
            relation: Relation type (blocks, blocked-by, implements, depends-on, references, supersedes, duplicate-of)

        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_command([
                "link", item_id,
                "--related-to", related_to,
                "--relation", relation
            ])
            return True
        except MemoryError:
            return False

    def unlink_items(self, item_id: str, related_to: str) -> bool:
        """Remove a relation between two memory items.

        Args:
            item_id: Source item ID
            related_to: Target item ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_command(["unlink", item_id, "--related-to", related_to])
            return True
        except MemoryError:
            return False

    def stats(self, item_type: Optional[str] = None) -> Dict:
        """Show statistics about memory items.

        Args:
            item_type: Filter by type

        Returns:
            Dictionary with statistics
        """
        args = ["stats", "--json"]

        if item_type:
            args.extend(["--type", item_type])

        try:
            output = self._run_command(args)
            if not output.strip():
                return {}
            return json.loads(output.strip())
        except (MemoryError, json.JSONDecodeError):
            return {}

    def get_onboard_content(self) -> str:
        """Returns full 'memory onboard' output for agent context.

        Returns:
            Complete onboard documentation string
        """
        try:
            return self._run_command(["onboard"])
        except MemoryError:
            return ""

    def generate_context(self) -> str:
        """Generate context information for agents.

        Returns formatted memory state including:
        - Item counts by type/status
        - Active blockers by urgency
        - High-priority pending tasks
        - Recent decisions
        - Key metrics

        Returns:
            Context string with memory state
        """
        lines = ["# Memory State", ""]

        # Get overall stats
        all_stats = self.stats()

        # Total items
        total = all_stats.get("total", 0)
        lines.append(f"Total items: {total}")

        # By type
        by_type = all_stats.get("by_type", {})
        if by_type:
            type_parts = [f"{t}({c})" for t, c in sorted(by_type.items())]
            lines.append(f"By type: {', '.join(type_parts)}")

        # By status
        by_status = all_stats.get("by_status", {})
        if by_status:
            status_parts = [f"{s}({c})" for s, c in sorted(by_status.items())]
            lines.append(f"By status: {', '.join(status_parts)}")

        lines.append("")

        # Active blockers by urgency
        blockers = self.list_items(item_type="blocker", status="pending")
        urgency_counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for blocker in blockers:
            urgency = blocker.get("metadata", {}).get("type_specific", {}).get("urgency", "low")
            if urgency in urgency_counts:
                urgency_counts[urgency] += 1

        lines.append("Active Blockers (urgency):")
        for urgency in ["critical", "high", "medium", "low"]:
            lines.append(f"  {urgency}: {urgency_counts[urgency]}")

        lines.append("")

        # High-priority pending tasks
        high_priority_tasks = self.list_items(
            item_type="task",
            status="pending",
            priority_min=0,
            priority_max=1,
        )
        lines.append(f"Pending High-Priority Tasks (priority 0-1): {len(high_priority_tasks)}")

        lines.append("")

        # Recent decisions
        decisions = self.list_items(item_type="decision", limit=5)
        if decisions:
            lines.append("Recent Decisions:")
            for decision in decisions:
                item_id = decision.get("id", "")
                title = decision.get("title", "")
                decision_status = decision.get("metadata", {}).get("type_specific", {}).get("decision_status", "unknown")
                lines.append(f"  - {item_id}: \"{title}\" ({decision_status})")
        else:
            lines.append("Recent Decisions: (none)")

        lines.append("")

        # Key metrics
        metrics = self.list_items(item_type="metric")
        if metrics:
            lines.append("Key Metrics:")
            for metric in metrics:
                name = metric.get("metadata", {}).get("type_specific", {}).get("name", "unknown")
                value = metric.get("metadata", {}).get("type_specific", {}).get("value", 0)
                unit = metric.get("metadata", {}).get("type_specific", {}).get("unit", "")
                lines.append(f"  - {name}: {value}{unit}")
        else:
            lines.append("Key Metrics: (none)")

        lines.append("")
        lines.append(f"Memory file: {self.memory_file or 'memory.jsonl'}")

        return "\n".join(lines)

    def verify(self) -> bool:
        """Verify that the memory script exists and is executable.

        Returns:
            True if memory is available, False otherwise
        """
        return self.memory_path.exists() and os.access(self.memory_path, os.X_OK)


# Global instance for convenience
_memory: Optional[MemoryWrapper] = None


def get_memory() -> MemoryWrapper:
    """Get the global memory instance.

    Returns:
        MemoryWrapper instance
    """
    global _memory
    if _memory is None:
        _memory = MemoryWrapper()
    return _memory
