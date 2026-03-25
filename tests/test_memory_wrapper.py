"""Tests for the memory wrapper module."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from orchestrator.memory_wrapper import MemoryWrapper, MemoryError, get_memory


@pytest.fixture
def temp_memory_file():
    """Create a temporary memory file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def memory_wrapper(temp_memory_file):
    """Create a MemoryWrapper instance with temp memory file."""
    return MemoryWrapper(memory_file=temp_memory_file)


class TestMemoryWrapperInit:
    """Tests for MemoryWrapper initialization."""

    def test_init_default_paths(self):
        """Test initialization with default paths."""
        wrapper = MemoryWrapper()
        assert wrapper.memory_path is not None
        assert wrapper.memory_file is None

    def test_init_custom_memory_file(self, temp_memory_file):
        """Test initialization with custom memory file."""
        wrapper = MemoryWrapper(memory_file=temp_memory_file)
        assert wrapper.memory_file == temp_memory_file

    def test_init_custom_memory_path(self):
        """Test initialization with custom memory path."""
        wrapper = MemoryWrapper(memory_path="/custom/memory")
        assert str(wrapper.memory_path) == "/custom/memory"

    def test_init_custom_memory_path_absolute(self):
        """Test initialization with absolute memory path."""
        wrapper = MemoryWrapper(memory_path="/absolute/path/memory")
        assert str(wrapper.memory_path) == "/absolute/path/memory"

    def test_init_custom_memory_path_relative(self):
        """Test initialization with relative memory path."""
        wrapper = MemoryWrapper(memory_path="relative/path/memory")
        # Should be joined with project root
        assert "relative/path/memory" in str(wrapper.memory_path)

    def test_init_custom_memory_file_absolute(self, temp_memory_file):
        """Test initialization with absolute memory file path."""
        abs_path = os.path.abspath(temp_memory_file)
        wrapper = MemoryWrapper(memory_file=abs_path)
        assert wrapper.memory_file == abs_path

    def test_init_custom_memory_file_relative(self, temp_memory_file):
        """Test initialization with relative memory file path."""
        wrapper = MemoryWrapper(memory_file="relative/memory.jsonl")
        # Should be joined with project root
        assert "relative/memory.jsonl" in wrapper.memory_file

    def test_find_project_root_no_git(self):
        """Test _find_project_root when no .git directory exists."""
        wrapper = MemoryWrapper()
        # Should return current directory if no .git found
        root = wrapper._find_project_root()
        assert isinstance(root, Path)

    def test_init_target_project_root(self, temp_memory_file):
        """Test initialization with custom target_project_root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            wrapper = MemoryWrapper(target_project_root=target_root)
            assert wrapper.target_project_root == target_root
            assert wrapper.memory_file is None

    def test_init_target_project_root_memory_file(self):
        """Test memory_file resolved relative to target_project_root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            wrapper = MemoryWrapper(memory_file="memory.jsonl", target_project_root=target_root)
            assert wrapper.memory_file == str(target_root / "memory.jsonl")
            assert "tools/memory" in str(wrapper.memory_path)

    def test_init_separate_roots(self):
        """Test that orchestrator_root and target_project_root are separate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            wrapper = MemoryWrapper(target_project_root=target_root)
            assert wrapper.target_project_root == target_root
            assert hasattr(wrapper, 'orchestrator_root')


class TestMemoryWrapperRunCommand:
    """Tests for _run_command method."""

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run, memory_wrapper):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(stdout='output')

        result = memory_wrapper._run_command(["list"])

        assert result == "output"
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_command_called_process_error(self, mock_run, memory_wrapper):
        """Test handling of CalledProcessError."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "memory", stderr="error")

        with pytest.raises(MemoryError, match="Memory command failed"):
            memory_wrapper._run_command(["list"])

    @patch('subprocess.run')
    def test_run_command_file_not_found(self, mock_run, memory_wrapper):
        """Test handling of FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(MemoryError, match="Memory script not found"):
            memory_wrapper._run_command(["list"])


class TestMemoryWrapperCreateItem:
    """Tests for create_item method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_task_success(self, mock_cmd, memory_wrapper):
        """Test creating a task item."""
        mock_cmd.return_value = json.dumps({"id": "mem_123_abc"})

        item_id = memory_wrapper.create_item(
            item_type="task",
            title="Test task",
            content="Description",
            priority=1,
            assignee="Developer",
            status="pending",
            tags=["test", "priority"]
        )

        assert item_id == "mem_123_abc"
        mock_cmd.assert_called_once()
        args = mock_cmd.call_args[0][0]
        assert "create" in args
        assert "--type" in args
        assert "task" in args
        assert "Test task" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_note_success(self, mock_cmd, memory_wrapper):
        """Test creating a note item."""
        mock_cmd.return_value = json.dumps({"id": "mem_456_def"})

        item_id = memory_wrapper.create_item(
            item_type="note",
            title="Important note",
            content="Content",
            tags=["info"],
            category="discovery"
        )

        assert item_id == "mem_456_def"
        args = mock_cmd.call_args[0][0]
        assert "--category" in args
        assert "discovery" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_metric_success(self, mock_cmd, memory_wrapper):
        """Test creating a metric item."""
        mock_cmd.return_value = json.dumps({"id": "mem_789_ghi"})

        item_id = memory_wrapper.create_item(
            item_type="metric",
            name="coverage",
            value=85,
            unit="percent",
            trend="increasing"
        )

        assert item_id == "mem_789_ghi"
        args = mock_cmd.call_args[0][0]
        assert "--name" in args
        assert "coverage" in args
        assert "--value" in args
        assert "85" in args
        assert "--unit" in args
        assert "percent" in args
        assert "--trend" in args
        assert "increasing" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_decision_success(self, mock_cmd, memory_wrapper):
        """Test creating a decision item."""
        mock_cmd.return_value = json.dumps({"id": "mem_001_jkl"})

        item_id = memory_wrapper.create_item(
            item_type="decision",
            title="Use PostgreSQL",
            context="Need relational DB",
            consequence="Must manage migrations",
            alternatives=["MySQL", "SQLite"],
            decision_status="decided"
        )

        assert item_id == "mem_001_jkl"
        args = mock_cmd.call_args[0][0]
        assert "--context" in args
        assert "--consequence" in args
        assert "--alternatives" in args
        assert "MySQL,SQLite" in args
        assert "--decision-status" in args
        assert "decided" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_artifact_success(self, mock_cmd, memory_wrapper):
        """Test creating an artifact item."""
        mock_cmd.return_value = json.dumps({"id": "mem_002_mno"})

        item_id = memory_wrapper.create_item(
            item_type="artifact",
            title="Auth module",
            path="src/auth.py",
            checksum="abc123",
            artifact_type="code"
        )

        assert item_id == "mem_002_mno"
        args = mock_cmd.call_args[0][0]
        assert "--path" in args
        assert "src/auth.py" in args
        assert "--checksum" in args
        assert "abc123" in args
        assert "--artifact-type" in args
        assert "code" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_blocker_success(self, mock_cmd, memory_wrapper):
        """Test creating a blocker item."""
        mock_cmd.return_value = json.dumps({"id": "mem_003_pqr"})

        item_id = memory_wrapper.create_item(
            item_type="blocker",
            title="Waiting for API spec",
            urgency="high",
            blocked_by="Architect",
            affects=["task_1", "task_2"],
            resolution="Need clarification"
        )

        assert item_id == "mem_003_pqr"
        args = mock_cmd.call_args[0][0]
        assert "--urgency" in args
        assert "high" in args
        assert "--blocked-by" in args
        assert "Architect" in args
        assert "--affects" in args
        assert "task_1,task_2" in args
        assert "--resolution" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_task_with_due_iteration(self, mock_cmd, memory_wrapper):
        """Test creating a task with due iteration."""
        mock_cmd.return_value = json.dumps({"id": "mem_004_stu"})

        item_id = memory_wrapper.create_item(
            item_type="task",
            title="Task with deadline",
            due_iteration=10
        )

        assert item_id == "mem_004_stu"
        args = mock_cmd.call_args[0][0]
        assert "--due-iteration" in args
        assert "10" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_item_invalid_json(self, mock_cmd, memory_wrapper):
        """Test handling of invalid JSON output."""
        mock_cmd.return_value = "not json"

        item_id = memory_wrapper.create_item("task", "Test")

        assert item_id == ""

    @patch.object(MemoryWrapper, '_run_command')
    def test_create_item_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("command failed")

        with pytest.raises(MemoryError):
            memory_wrapper.create_item("task", "Test")


class TestMemoryWrapperListItems:
    """Tests for list_items method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_no_filters(self, mock_cmd, memory_wrapper):
        """Test listing all items."""
        mock_cmd.return_value = json.dumps([
            {"id": "1", "type": "task"},
            {"id": "2", "type": "note"}
        ])

        items = memory_wrapper.list_items()

        assert len(items) == 2
        args = mock_cmd.call_args[0][0]
        assert "list" in args
        assert "--json" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_with_filters(self, mock_cmd, memory_wrapper):
        """Test listing with filters."""
        mock_cmd.return_value = json.dumps([{"id": "1", "type": "task"}])

        items = memory_wrapper.list_items(
            item_type="task",
            status="pending",
            assignee="Developer",
            priority=1,
            priority_min=0,
            priority_max=2,
            tags=["test"],
            since=5,
            until=10,
            name="coverage",
            limit=10
        )

        assert len(items) == 1
        args = mock_cmd.call_args[0][0]
        assert "--type" in args
        assert "--status" in args
        assert "--assignee" in args
        assert "--priority" in args
        assert "--priority-min" in args
        assert "--priority-max" in args
        assert "--tag" in args
        assert "--since" in args
        assert "--until" in args
        assert "--name" in args
        assert "--limit" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_multiple_tags(self, mock_cmd, memory_wrapper):
        """Test listing with multiple tags."""
        mock_cmd.return_value = json.dumps([])

        items = memory_wrapper.list_items(tags=["tag1", "tag2", "tag3"])

        args = mock_cmd.call_args[0][0]
        tag_count = args.count("--tag")
        assert tag_count == 3

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_empty_output(self, mock_cmd, memory_wrapper):
        """Test handling of empty output."""
        mock_cmd.return_value = ""

        items = memory_wrapper.list_items()

        assert items == []

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        items = memory_wrapper.list_items()

        assert items == []

    @patch.object(MemoryWrapper, '_run_command')
    def test_list_items_invalid_json(self, mock_cmd, memory_wrapper):
        """Test handling of invalid JSON."""
        mock_cmd.return_value = "not json"

        items = memory_wrapper.list_items()

        assert items == []


class TestMemoryWrapperShowItem:
    """Tests for show_item method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_show_item_success(self, mock_cmd, memory_wrapper):
        """Test showing an item."""
        item_data = {"id": "mem_123", "title": "Test", "type": "task"}
        mock_cmd.return_value = json.dumps(item_data)

        result = memory_wrapper.show_item("mem_123")

        assert result == item_data
        args = mock_cmd.call_args[0][0]
        assert "show" in args
        assert "mem_123" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_show_item_empty_output(self, mock_cmd, memory_wrapper):
        """Test handling of empty output."""
        mock_cmd.return_value = ""

        result = memory_wrapper.show_item("mem_123")

        assert result == {}

    @patch.object(MemoryWrapper, '_run_command')
    def test_show_item_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.show_item("mem_123")

        assert result == {}

    @patch.object(MemoryWrapper, '_run_command')
    def test_show_item_invalid_json(self, mock_cmd, memory_wrapper):
        """Test handling of invalid JSON."""
        mock_cmd.return_value = "not json"

        result = memory_wrapper.show_item("mem_123")

        assert result == {}


class TestMemoryWrapperUpdateItem:
    """Tests for update_item method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_basic(self, mock_cmd, memory_wrapper):
        """Test basic item update."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            title="New title",
            content="New content",
            status="completed",
            priority=0,
            assignee="Tester"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "update" in args
        assert "mem_123" in args
        assert "--title" in args
        assert "--content" in args
        assert "--status" in args
        assert "--priority" in args
        assert "--assignee" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_tags(self, mock_cmd, memory_wrapper):
        """Test updating tags."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            tags=["new", "tags"],
            add_tags=["added"],
            remove_tags=["removed"]
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--tags" in args
        assert "new,tags" in args
        assert "--add-tags" in args
        assert "added" in args
        assert "--remove-tags" in args
        assert "removed" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_metric(self, mock_cmd, memory_wrapper):
        """Test updating a metric."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            value=95,
            trend="stable"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--value" in args
        assert "95" in args
        assert "--trend" in args
        assert "stable" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_artifact(self, mock_cmd, memory_wrapper):
        """Test updating an artifact."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            path="new/path.py",
            checksum="xyz789",
            artifact_type="doc"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--path" in args
        assert "--checksum" in args
        assert "--artifact-type" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_blocker(self, mock_cmd, memory_wrapper):
        """Test updating a blocker."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            affects=["task1", "task2"],
            resolution="Fixed"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--affects" in args
        assert "task1,task2" in args
        assert "--resolution" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_task(self, mock_cmd, memory_wrapper):
        """Test updating a task."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            due_iteration=15,
            category="important"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--due-iteration" in args
        assert "15" in args
        assert "--category" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_decision(self, mock_cmd, memory_wrapper):
        """Test updating a decision."""
        mock_cmd.return_value = ""

        result = memory_wrapper.update_item(
            "mem_123",
            alternatives=["A", "B", "C"],
            decision_status="superseded"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "--alternatives" in args
        assert "A,B,C" in args
        assert "--decision-status" in args
        assert "superseded" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_update_item_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.update_item("mem_123", title="Test")

        assert result is False


class TestMemoryWrapperDeleteItem:
    """Tests for delete_item method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_delete_item_success(self, mock_cmd, memory_wrapper):
        """Test successful deletion."""
        mock_cmd.return_value = ""

        result = memory_wrapper.delete_item("mem_123")

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "delete" in args
        assert "mem_123" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_delete_item_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.delete_item("mem_123")

        assert result is False


class TestMemoryWrapperSearch:
    """Tests for search method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_basic(self, mock_cmd, memory_wrapper):
        """Test basic search."""
        mock_cmd.return_value = json.dumps([
            {"id": "1", "title": "auth related"},
            {"id": "2", "title": "more auth"}
        ])

        results = memory_wrapper.search("authentication")

        assert len(results) == 2
        args = mock_cmd.call_args[0][0]
        assert "search" in args
        assert "authentication" in args
        assert "--json" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_with_type_filter(self, mock_cmd, memory_wrapper):
        """Test search with type filter."""
        mock_cmd.return_value = json.dumps([])

        results = memory_wrapper.search("test", item_type="note")

        args = mock_cmd.call_args[0][0]
        assert "--type" in args
        assert "note" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_with_limit(self, mock_cmd, memory_wrapper):
        """Test search with limit."""
        mock_cmd.return_value = json.dumps([])

        results = memory_wrapper.search("test", limit=5)

        args = mock_cmd.call_args[0][0]
        assert "--limit" in args
        assert "5" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_empty_output(self, mock_cmd, memory_wrapper):
        """Test handling of empty output."""
        mock_cmd.return_value = ""

        results = memory_wrapper.search("test")

        assert results == []

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        results = memory_wrapper.search("test")

        assert results == []

    @patch.object(MemoryWrapper, '_run_command')
    def test_search_invalid_json(self, mock_cmd, memory_wrapper):
        """Test handling of invalid JSON."""
        mock_cmd.return_value = "not json"

        results = memory_wrapper.search("test")

        assert results == []


class TestMemoryWrapperLinkItems:
    """Tests for link_items method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_link_items_success(self, mock_cmd, memory_wrapper):
        """Test successful linking."""
        mock_cmd.return_value = ""

        result = memory_wrapper.link_items(
            "mem_123",
            "mem_456",
            "depends-on"
        )

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "link" in args
        assert "mem_123" in args
        assert "--related-to" in args
        assert "mem_456" in args
        assert "--relation" in args
        assert "depends-on" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_link_items_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.link_items("mem_123", "mem_456", "blocks")

        assert result is False


class TestMemoryWrapperUnlinkItems:
    """Tests for unlink_items method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_unlink_items_success(self, mock_cmd, memory_wrapper):
        """Test successful unlinking."""
        mock_cmd.return_value = ""

        result = memory_wrapper.unlink_items("mem_123", "mem_456")

        assert result is True
        args = mock_cmd.call_args[0][0]
        assert "unlink" in args
        assert "mem_123" in args
        assert "--related-to" in args
        assert "mem_456" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_unlink_items_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.unlink_items("mem_123", "mem_456")

        assert result is False


class TestMemoryWrapperStats:
    """Tests for stats method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_stats_basic(self, mock_cmd, memory_wrapper):
        """Test getting stats."""
        mock_cmd.return_value = json.dumps({
            "total": 10,
            "by_type": {"task": 5, "note": 3, "decision": 2},
            "by_status": {"pending": 4, "completed": 6}
        })

        result = memory_wrapper.stats()

        assert result["total"] == 10
        assert "task" in result["by_type"]
        args = mock_cmd.call_args[0][0]
        assert "stats" in args
        assert "--json" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_stats_with_type_filter(self, mock_cmd, memory_wrapper):
        """Test stats with type filter."""
        mock_cmd.return_value = json.dumps({"total": 5})

        result = memory_wrapper.stats(item_type="task")

        assert result["total"] == 5
        args = mock_cmd.call_args[0][0]
        assert "--type" in args
        assert "task" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_stats_empty_output(self, mock_cmd, memory_wrapper):
        """Test handling of empty output."""
        mock_cmd.return_value = ""

        result = memory_wrapper.stats()

        assert result == {}

    @patch.object(MemoryWrapper, '_run_command')
    def test_stats_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.stats()

        assert result == {}

    @patch.object(MemoryWrapper, '_run_command')
    def test_stats_invalid_json(self, mock_cmd, memory_wrapper):
        """Test handling of invalid JSON."""
        mock_cmd.return_value = "not json"

        result = memory_wrapper.stats()

        assert result == {}


class TestMemoryWrapperGetOnboardContent:
    """Tests for get_onboard_content method."""

    @patch.object(MemoryWrapper, '_run_command')
    def test_get_onboard_content_success(self, mock_cmd, memory_wrapper):
        """Test getting onboard content."""
        mock_cmd.return_value = "Memory tool documentation..."

        result = memory_wrapper.get_onboard_content()

        assert result == "Memory tool documentation..."
        args = mock_cmd.call_args[0][0]
        assert "onboard" in args

    @patch.object(MemoryWrapper, '_run_command')
    def test_get_onboard_content_memory_error(self, mock_cmd, memory_wrapper):
        """Test handling of MemoryError."""
        mock_cmd.side_effect = MemoryError("failed")

        result = memory_wrapper.get_onboard_content()

        assert result == ""


class TestMemoryWrapperGenerateContext:
    """Tests for generate_context method."""

    @patch.object(MemoryWrapper, 'stats')
    @patch.object(MemoryWrapper, 'list_items')
    def test_generate_context_full(self, mock_list, mock_stats, memory_wrapper):
        """Test context generation with data."""
        mock_stats.return_value = {
            "total": 47,
            "by_type": {"task": 23, "note": 8, "decision": 5, "metric": 4, "blocker": 3, "artifact": 4},
            "by_status": {"pending": 12, "in_progress": 5, "completed": 25, "blocked": 3}
        }
        mock_list.side_effect = [
            # Blockers
            [
                {"metadata": {"type_specific": {"urgency": "high"}}},
                {"metadata": {"type_specific": {"urgency": "medium"}}},
                {"metadata": {"type_specific": {"urgency": "medium"}}},
            ],
            # High priority tasks
            [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}],
            # Decisions
            [
                {"id": "mem_123_abc", "title": "Use PostgreSQL", "metadata": {"type_specific": {"decision_status": "decided"}}},
                {"id": "mem_456_def", "title": "JWT for auth", "metadata": {"type_specific": {"decision_status": "proposed"}}},
            ],
            # Metrics
            [
                {"metadata": {"type_specific": {"name": "coverage", "value": 85, "unit": "percent"}}},
                {"metadata": {"type_specific": {"name": "tech_debt_items", "value": 7, "unit": "count"}}},
            ],
        ]

        context = memory_wrapper.generate_context()

        assert "# Memory State" in context
        assert "Total items: 47" in context
        assert "By type:" in context
        assert "By status:" in context
        assert "Active Blockers (urgency):" in context
        assert "critical: 0" in context
        assert "high: 1" in context
        assert "medium: 2" in context
        assert "Pending High-Priority Tasks (priority 0-1): 5" in context
        assert "Recent Decisions:" in context
        assert "Use PostgreSQL" in context
        assert "Key Metrics:" in context
        assert "coverage: 85percent" in context

    @patch.object(MemoryWrapper, 'stats')
    @patch.object(MemoryWrapper, 'list_items')
    def test_generate_context_empty(self, mock_list, mock_stats, memory_wrapper):
        """Test context generation with no data."""
        mock_stats.return_value = {"total": 0, "by_type": {}, "by_status": {}}
        mock_list.return_value = []

        context = memory_wrapper.generate_context()

        assert "# Memory State" in context
        assert "Total items: 0" in context
        assert "Active Blockers (urgency):" in context
        assert "critical: 0" in context
        assert "Recent Decisions: (none)" in context
        assert "Key Metrics: (none)" in context

    @patch.object(MemoryWrapper, 'stats')
    @patch.object(MemoryWrapper, 'list_items')
    def test_generate_context_blocker_urgency_levels(self, mock_list, mock_stats, memory_wrapper):
        """Test all urgency levels are counted correctly."""
        mock_stats.return_value = {"total": 0, "by_type": {}, "by_status": {}}
        mock_list.side_effect = [
            # Blockers with all urgency levels
            [
                {"metadata": {"type_specific": {"urgency": "critical"}}},
                {"metadata": {"type_specific": {"urgency": "high"}}},
                {"metadata": {"type_specific": {"urgency": "medium"}}},
                {"metadata": {"type_specific": {"urgency": "low"}}},
                {"metadata": {"type_specific": {"urgency": "critical"}}},
            ],
            [],  # High priority tasks
            [],  # Decisions
            [],  # Metrics
        ]

        context = memory_wrapper.generate_context()

        assert "critical: 2" in context
        assert "high: 1" in context
        assert "medium: 1" in context
        assert "low: 1" in context

    @patch.object(MemoryWrapper, 'stats')
    @patch.object(MemoryWrapper, 'list_items')
    def test_generate_context_unknown_urgency(self, mock_list, mock_stats, memory_wrapper):
        """Test handling of unknown urgency level."""
        mock_stats.return_value = {"total": 0, "by_type": {}, "by_status": {}}
        mock_list.side_effect = [
            # Blocker with unknown urgency
            [{"metadata": {"type_specific": {"urgency": "unknown"}}}],
            [],  # High priority tasks
            [],  # Decisions
            [],  # Metrics
        ]

        context = memory_wrapper.generate_context()

        # Should not crash, unknown urgency is ignored
        assert "Active Blockers (urgency):" in context


class TestMemoryWrapperVerify:
    """Tests for verify method."""

    def test_verify_exists_and_executable(self, memory_wrapper):
        """Test verification when memory script exists."""
        result = memory_wrapper.verify()
        assert isinstance(result, bool)

    def test_verify_nonexistent(self, temp_memory_file):
        """Test verification when script doesn't exist."""
        wrapper = MemoryWrapper(memory_path="/nonexistent/memory", memory_file=temp_memory_file)

        result = wrapper.verify()

        assert result is False


class TestGetMemory:
    """Tests for get_memory function."""

    def test_get_memory_singleton(self):
        """Test that get_memory returns same instance."""
        import orchestrator.memory_wrapper as mw
        mw._memory = None

        m1 = get_memory()
        m2 = get_memory()

        assert m1 is m2


class TestMemoryError:
    """Tests for MemoryError exception."""

    def test_memory_error_instantiation(self):
        """Test creating MemoryError."""
        error = MemoryError("test message")
        assert str(error) == "test message"
        assert isinstance(error, Exception)
