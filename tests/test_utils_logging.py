"""Tests for logging utility functions."""
from unittest.mock import patch
from orchestrator.utils import (
    log_agent_activation,
    log_messages_received,
    log_message_sent,
    log_messages_acknowledged
)


class TestLoggingFunctions:
    """Tests for message logging functions."""

    @patch('orchestrator.utils.print_info')
    def test_log_agent_activation(self, mock_print):
        """Test logging agent activation."""
        log_agent_activation("Developer", 5)
        mock_print.assert_called_once_with(
            "[ACTIVATION] Developer selected (5 pending messages)"
        )

    @patch('orchestrator.utils.print_info')
    def test_log_messages_received_with_messages(self, mock_print):
        """Test logging messages received (with messages)."""
        log_messages_received("Developer", 3)
        mock_print.assert_called_once_with(
            "[RECEIVED] Developer: 3 message(s) in context"
        )

    @patch('orchestrator.utils.print_info')
    def test_log_messages_received_no_messages(self, mock_print):
        """Test logging messages received (no messages)."""
        log_messages_received("Developer", 0)
        mock_print.assert_called_once_with(
            "[RECEIVED] Developer: No messages in context"
        )

    @patch('orchestrator.utils.print_info')
    def test_log_message_sent_short_content(self, mock_print):
        """Test logging message sent (short content)."""
        log_message_sent("Developer", "Tester", "Code ready for testing")
        mock_print.assert_called_once_with(
            "[SENT] Developer->Tester: Code ready for testing"
        )

    @patch('orchestrator.utils.print_info')
    def test_log_message_sent_long_content(self, mock_print):
        """Test logging message sent (long content truncated)."""
        long_content = "This is a very long message that should be truncated for display purposes in the logging output"
        log_message_sent("Developer", "Tester", long_content)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[SENT] Developer->Tester:" in call_args
        assert "..." in call_args

    @patch('orchestrator.utils.print_info')
    def test_log_messages_acknowledged_with_ids(self, mock_print):
        """Test logging messages acknowledged (with IDs)."""
        log_messages_acknowledged("Developer", ["beads-123", "beads-124"])
        mock_print.assert_called_once_with(
            "[ACKNOWLEDGED] Developer marked read: beads-123, beads-124"
        )

    @patch('orchestrator.utils.print_info')
    def test_log_messages_acknowledged_many_ids(self, mock_print):
        """Test logging messages acknowledged (many IDs truncated)."""
        ids = ["beads-1", "beads-2", "beads-3", "beads-4", "beads-5", "beads-6"]
        log_messages_acknowledged("Developer", ids)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[ACKNOWLEDGED] Developer marked read:" in call_args
        assert "(+1 more)" in call_args

    @patch('orchestrator.utils.print_info')
    def test_log_messages_acknowledged_no_ids(self, mock_print):
        """Test logging messages acknowledged (no IDs)."""
        log_messages_acknowledged("Developer", [])
        mock_print.assert_called_once_with(
            "[ACKNOWLEDGED] Developer: No messages marked as read"
        )
