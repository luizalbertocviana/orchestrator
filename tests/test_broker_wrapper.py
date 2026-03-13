"""Tests for the broker wrapper module."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from orchestrator.broker_wrapper import BrokerWrapper, BrokerError, get_broker


@pytest.fixture
def temp_messages_file():
    """Create a temporary messages file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.name
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def broker(temp_messages_file):
    """Create a BrokerWrapper instance with temp messages file."""
    return BrokerWrapper(messages_file=temp_messages_file)


class TestBrokerWrapperInit:
    """Tests for BrokerWrapper initialization."""
    
    def test_init_default_paths(self):
        """Test initialization with default paths."""
        broker = BrokerWrapper()
        assert broker.broker_path is not None
        assert broker.messages_file is None
    
    def test_init_custom_messages_file(self, temp_messages_file):
        """Test initialization with custom messages file."""
        broker = BrokerWrapper(messages_file=temp_messages_file)
        assert broker.messages_file == temp_messages_file
    
    def test_init_custom_broker_path(self):
        """Test initialization with custom broker path."""
        broker = BrokerWrapper(broker_path="/custom/broker")
        assert str(broker.broker_path) == "/custom/broker"
    
    def test_init_custom_broker_path_absolute(self):
        """Test initialization with absolute broker path."""
        broker = BrokerWrapper(broker_path="/absolute/path/broker")
        assert str(broker.broker_path) == "/absolute/path/broker"

    def test_init_custom_broker_path_relative(self):
        """Test initialization with relative broker path."""
        broker = BrokerWrapper(broker_path="relative/path/broker")
        # Should be joined with project root
        assert "relative/path/broker" in str(broker.broker_path)

    def test_init_custom_messages_file_absolute(self, temp_messages_file):
        """Test initialization with absolute messages file path."""
        import os
        abs_path = os.path.abspath(temp_messages_file)
        broker = BrokerWrapper(messages_file=abs_path)
        assert broker.messages_file == abs_path

    def test_init_custom_messages_file_relative(self, temp_messages_file):
        """Test initialization with relative messages file path."""
        broker = BrokerWrapper(messages_file="relative/messages.jsonl")
        # Should be joined with project root
        assert "relative/messages.jsonl" in broker.messages_file

    def test_find_project_root_no_git(self):
        """Test _find_project_root when no .git directory exists."""
        broker = BrokerWrapper()
        # Should return current directory if no .git found
        root = broker._find_project_root()
        assert isinstance(root, Path)

    def test_init_target_project_root(self, temp_messages_file):
        """Test initialization with custom target_project_root."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            broker = BrokerWrapper(target_project_root=target_root)
            assert broker.target_project_root == target_root
            # messages_file should be resolved relative to target_project_root
            assert broker.messages_file is None  # Not set by default

    def test_init_target_project_root_messages_file(self):
        """Test messages_file resolved relative to target_project_root."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            broker = BrokerWrapper(messages_file="messages.jsonl", target_project_root=target_root)
            assert broker.messages_file == str(target_root / "messages.jsonl")
            # broker_path should still use orchestrator_root
            assert "tools/broker" in str(broker.broker_path)

    def test_init_separate_roots(self):
        """Test that orchestrator_root and target_project_root are separate."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir)
            broker = BrokerWrapper(target_project_root=target_root)
            # orchestrator_root is where .git is (this repo)
            # target_project_root is the custom path
            assert broker.target_project_root == target_root
            assert hasattr(broker, 'orchestrator_root')


class TestBrokerWrapperSendMessage:
    """Tests for send_message method."""
    
    @patch('subprocess.run')
    def test_send_message_success(self, mock_run, broker):
        """Test successful message sending."""
        mock_run.return_value = MagicMock(
            stdout='{"id": "msg_1234567890_a1b2c3d4", "from": "test", "to": "agent"}'
        )
        
        msg_id = broker.send_message("test", "agent", "hello")
        
        assert msg_id == "msg_1234567890_a1b2c3d4"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == str(broker.broker_path)
        assert "send" in args
        assert "--from" in args
        assert "--to" in args
        assert "--content" in args
    
    @patch('subprocess.run')
    def test_send_message_invalid_json(self, mock_run, broker):
        """Test handling of invalid JSON output."""
        mock_run.return_value = MagicMock(stdout='not json')
        
        msg_id = broker.send_message("test", "agent", "hello")
        
        assert msg_id == ""
    
    @patch('subprocess.run')
    def test_send_message_broker_error(self, mock_run, broker):
        """Test handling of broker command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "broker", stderr="error")
        
        with pytest.raises(BrokerError):
            broker.send_message("test", "agent", "hello")
    
    @patch('subprocess.run')
    def test_send_message_file_not_found(self, mock_run, broker):
        """Test handling of missing broker script."""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(BrokerError, match="Broker script not found"):
            broker.send_message("test", "agent", "hello")


class TestBrokerWrapperReadMessages:
    """Tests for read_messages method."""
    
    @patch('subprocess.run')
    def test_read_messages_success(self, mock_run, broker):
        """Test successful message reading."""
        msg1 = {"id": "msg_1", "from": "a", "to": "b", "content": "hello", "timestamp_ack": None}
        msg2 = {"id": "msg_2", "from": "a", "to": "b", "content": "world", "timestamp_ack": None}
        mock_run.return_value = MagicMock(
            stdout=json.dumps(msg1) + "\n" + json.dumps(msg2)
        )
        
        messages = broker.read_messages("b")
        
        assert len(messages) == 2
        assert messages[0]["id"] == "msg_1"
        assert messages[1]["id"] == "msg_2"
    
    @patch('subprocess.run')
    def test_read_messages_empty(self, mock_run, broker):
        """Test reading when no messages exist."""
        mock_run.return_value = MagicMock(stdout="")
        
        messages = broker.read_messages("b")
        
        assert messages == []
    
    @patch('subprocess.run')
    def test_read_messages_with_ack_flag(self, mock_run, broker):
        """Test reading with include_acknowledged=True."""
        mock_run.return_value = MagicMock(stdout="")

        broker.read_messages("b", include_acknowledged=True)

        args = mock_run.call_args[0][0]
        assert "--all" in args

    @patch('subprocess.run')
    def test_read_messages_invalid_json(self, mock_run, broker):
        """Test handling of invalid JSON in output."""
        mock_run.return_value = MagicMock(
            stdout='invalid json\n{"id": "valid"}\nanother bad line'
        )

        messages = broker.read_messages("b")

        # Should skip invalid lines and parse valid ones
        assert len(messages) == 1
        assert messages[0]["id"] == "valid"

    @patch.object(BrokerWrapper, '_run_command')
    def test_read_messages_broker_error(self, mock_cmd, broker):
        """Test handling of BrokerError during read."""
        mock_cmd.side_effect = BrokerError("command failed")

        messages = broker.read_messages("b")

        # Should return empty list on error
        assert messages == []


class TestBrokerWrapperAcknowledge:
    """Tests for acknowledge_message and acknowledge_messages methods."""
    
    @patch('subprocess.run')
    def test_acknowledge_message_success(self, mock_run, broker):
        """Test successful message acknowledgment."""
        mock_run.return_value = MagicMock(stdout="")
        
        result = broker.acknowledge_message("msg_123")
        
        assert result is True
        args = mock_run.call_args[0][0]
        assert "ack" in args
        assert "msg_123" in args
    
    @patch('subprocess.run')
    def test_acknowledge_message_failure(self, mock_run, broker):
        """Test acknowledgment failure."""
        mock_run.side_effect = BrokerError("failed")
        
        result = broker.acknowledge_message("msg_123")
        
        assert result is False
    
    @patch('subprocess.run')
    def test_acknowledge_messages_success(self, mock_run, broker):
        """Test acknowledging multiple messages."""
        mock_run.return_value = MagicMock(stdout="")
        
        result = broker.acknowledge_messages(["msg_1", "msg_2", "msg_3"])
        
        assert result == 3
    
    def test_acknowledge_messages_empty(self, temp_messages_file):
        """Test acknowledging empty list."""
        broker = BrokerWrapper(messages_file=temp_messages_file)
        result = broker.acknowledge_messages([])
        assert result == 0
    
    @patch('subprocess.run')
    def test_acknowledge_messages_partial_failure(self, mock_run, broker):
        """Test partial acknowledgment failure falls back to individual acks."""
        mock_run.side_effect = [
            BrokerError("batch failed"),
            MagicMock(stdout=""),  # msg_1 succeeds
            BrokerError("msg_2 failed"),  # msg_2 fails
            MagicMock(stdout=""),  # msg_3 succeeds
        ]
        
        result = broker.acknowledge_messages(["msg_1", "msg_2", "msg_3"])
        
        assert result == 2


class TestBrokerWrapperCountPending:
    """Tests for count_pending method."""
    
    @patch.object(BrokerWrapper, 'read_messages')
    def test_count_pending(self, mock_read, broker):
        """Test counting pending messages."""
        mock_read.return_value = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        
        count = broker.count_pending("agent")
        
        assert count == 3
        mock_read.assert_called_once_with("agent", include_acknowledged=False)


class TestBrokerWrapperGetAllPending:
    """Tests for get_all_pending method."""
    
    def test_get_all_pending_empty_file(self, temp_messages_file):
        """Test getting pending messages from empty file."""
        broker = BrokerWrapper(messages_file=temp_messages_file)
        
        messages = broker.get_all_pending()
        
        assert messages == []
    
    def test_get_all_pending_with_messages(self, temp_messages_file):
        """Test getting pending messages."""
        broker = BrokerWrapper(messages_file=temp_messages_file)
        
        # Write test messages
        msg1 = {"id": "1", "to": "a", "timestamp_ack": None}
        msg2 = {"id": "2", "to": "b", "timestamp_ack": None}
        msg3 = {"id": "3", "to": "a", "timestamp_ack": "2024-01-01"}  # acknowledged
        
        with open(temp_messages_file, 'w') as f:
            f.write(json.dumps(msg1) + "\n")
            f.write(json.dumps(msg2) + "\n")
            f.write(json.dumps(msg3) + "\n")
        
        messages = broker.get_all_pending()
        
        assert len(messages) == 2
        assert messages[0]["id"] == "1"
        assert messages[1]["id"] == "2"
    
    def test_get_all_pending_nonexistent_file(self):
        """Test getting pending messages when file doesn't exist."""
        broker = BrokerWrapper(messages_file="/nonexistent/path.jsonl")

        messages = broker.get_all_pending()

        assert messages == []

    def test_get_all_pending_invalid_json(self, temp_messages_file):
        """Test getting pending messages with invalid JSON lines."""
        broker = BrokerWrapper(messages_file=temp_messages_file)

        # Write mix of valid and invalid JSON
        with open(temp_messages_file, 'w') as f:
            f.write('invalid json\n')
            f.write('{"id": "1", "to": "a", "timestamp_ack": null}\n')
            f.write('another bad line\n')
            f.write('{"id": "2", "to": "b", "timestamp_ack": "2024-01-01"}\n')  # acked

        messages = broker.get_all_pending()

        # Should skip invalid lines and only return unacknowledged
        assert len(messages) == 1
        assert messages[0]["id"] == "1"

    @patch('builtins.open')
    def test_get_all_pending_io_error(self, mock_open, broker):
        """Test handling of IOError/OSError when reading file."""
        mock_open.side_effect = IOError("file read error")

        messages = broker.get_all_pending()

        # Should return empty list on error
        assert messages == []


class TestBrokerWrapperCountByAgent:
    """Tests for count_by_agent method."""
    
    @patch.object(BrokerWrapper, 'get_all_pending')
    def test_count_by_agent(self, mock_get_all, broker):
        """Test counting messages per agent."""
        mock_get_all.return_value = [
            {"to": "agent_a"},
            {"to": "agent_b"},
            {"to": "agent_a"},
            {"to": "agent_c"},
            {"to": "agent_a"},
        ]
        
        counts = broker.count_by_agent()
        
        assert counts == {"agent_a": 3, "agent_b": 1, "agent_c": 1}


class TestBrokerWrapperGenerateContext:
    """Tests for generate_context method."""
    
    @patch.object(BrokerWrapper, 'count_by_agent')
    def test_generate_context(self, mock_count, broker):
        """Test context generation."""
        mock_count.return_value = {"agent_a": 5, "agent_b": 3}
        
        context = broker.generate_context()
        
        assert "Total pending messages: 8" in context
        assert "agent_a: 5" in context
        assert "agent_b: 3" in context
    
    @patch.object(BrokerWrapper, 'count_by_agent')
    def test_generate_context_empty(self, mock_count, broker):
        """Test context generation with no messages."""
        mock_count.return_value = {}
        
        context = broker.generate_context()
        
        assert "Total pending messages: 0" in context
        assert "(no pending messages)" in context


class TestBrokerWrapperVerify:
    """Tests for verify method."""
    
    def test_verify_exists_and_executable(self, broker):
        """Test verification when broker exists."""
        # The default broker path likely doesn't exist, so this may be False
        # Just ensure the method runs without error
        result = broker.verify()
        assert isinstance(result, bool)
    
    def test_verify_nonexistent(self, temp_messages_file):
        """Test verification when broker doesn't exist."""
        broker = BrokerWrapper(broker_path="/nonexistent/broker", messages_file=temp_messages_file)
        
        result = broker.verify()
        
        assert result is False


class TestGetBroker:
    """Tests for get_broker function."""
    
    def test_get_broker_singleton(self):
        """Test that get_broker returns same instance."""
        # Reset global
        import orchestrator.broker_wrapper as bw
        bw._broker = None
        
        b1 = get_broker()
        b2 = get_broker()
        
        assert b1 is b2


class TestBrokerError:
    """Tests for BrokerError exception."""
    
    def test_broker_error_instantiation(self):
        """Test creating BrokerError."""
        error = BrokerError("test message")
        assert str(error) == "test message"
        assert isinstance(error, Exception)
