"""Tests for message-driven system functionality."""
from unittest.mock import patch, MagicMock
import pytest
from orchestrator.service import OrchestrationService, AGENT_ROLE_ORDER


@pytest.fixture
def service():
    """Create a service instance with mocked CLI agents."""
    with patch('orchestrator.service.OrchestrationService._get_available_cli_agents', return_value=[]):
        return OrchestrationService()


class TestBootstrapMessages:
    """Tests for create_bootstrap_messages()."""

    def test_create_bootstrap_messages(self, service):
        """Test that bootstrap messages are created for all agents."""
        with patch('orchestrator.service.beads.send_message') as mock_send:
            service.create_bootstrap_messages()
            
            # Should send to all agents in AGENT_ROLE_ORDER
            assert mock_send.call_count == len(AGENT_ROLE_ORDER)
            
            # Check first call (System → Requirements Analyst)
            first_call = mock_send.call_args_list[0]
            assert first_call[0][0] == "System"
            assert first_call[0][1] == "Requirements Analyst"
            assert "Bootstrap message" in first_call[0][2]

    def test_create_bootstrap_messages_handles_exception(self, service):
        """Test that exceptions during bootstrap are handled gracefully."""
        with patch('orchestrator.service.beads.send_message', side_effect=Exception("error")):
            # Should not raise, just log warnings
            service.create_bootstrap_messages()


class TestCountPendingMessages:
    """Tests for count_pending_messages()."""

    def test_count_pending_messages(self, service):
        """Test counting pending MESSAGE: beads."""
        mock_result = MagicMock()
        mock_result.stdout = "beads-123 | MESSAGE: A→B: hello\nbeads-124 | TASK: something\nbeads-125 | MESSAGE: C→D: world\n"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_pending_messages()
            assert count == 2  # Only MESSAGE: beads

    def test_count_pending_messages_empty(self, service):
        """Test counting with no pending messages."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_pending_messages()
            assert count == 0

    def test_count_pending_messages_exception(self, service):
        """Test that exceptions are handled gracefully."""
        with patch('subprocess.run', side_effect=Exception("error")):
            count = service.count_pending_messages()
            assert count == 0


class TestGetPendingMessagesByAgent:
    """Tests for get_pending_messages_by_agent()."""

    def test_get_pending_messages_by_agent(self, service):
        """Test grouping pending messages by target agent."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→Developer: hello\n"
            "○ orchestrator-124 ● P3 MESSAGE: B→Developer: world\n"
            "○ orchestrator-125 ● P3 MESSAGE: C→Tester: test this\n"
        )
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            result = service.get_pending_messages_by_agent()

            assert "Developer" in result
            assert "Tester" in result
            assert len(result["Developer"]) == 2
            assert len(result["Tester"]) == 1
            assert result["Developer"][0]["id"] == "orchestrator-123"

    def test_get_pending_messages_by_agent_empty(self, service):
        """Test with no pending messages."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = service.get_pending_messages_by_agent()
            assert result == {}

    def test_get_pending_messages_by_agent_exception(self, service):
        """Test that exceptions are handled gracefully."""
        with patch('subprocess.run', side_effect=Exception("error")):
            result = service.get_pending_messages_by_agent()
            assert result == {}


class TestSelectAgentByMessages:
    """Tests for select_agent_by_messages()."""

    def test_select_agent_most_messages(self, service):
        """Test selecting agent with most pending messages."""
        mock_data = {
            "Developer": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "Tester": [{"id": "4"}, {"id": "5"}],
            "Requirements Analyst": [{"id": "6"}],
        }
        
        with patch.object(service, 'get_pending_messages_by_agent', return_value=mock_data):
            agent = service.select_agent_by_messages()
            assert agent == "Developer"

    def test_select_agent_tie_breaker(self, service):
        """Test tie-breaking by role order."""
        mock_data = {
            "Developer": [{"id": "1"}],
            "Tester": [{"id": "2"}],
            "Requirements Analyst": [{"id": "3"}],
        }
        
        with patch.object(service, 'get_pending_messages_by_agent', return_value=mock_data):
            agent = service.select_agent_by_messages()
            # Requirements Analyst comes first in AGENT_ROLE_ORDER
            assert agent == "Requirements Analyst"

    def test_select_agent_no_messages(self, service):
        """Test with no pending messages."""
        with patch.object(service, 'get_pending_messages_by_agent', return_value={}):
            agent = service.select_agent_by_messages()
            assert agent is None

    def test_select_agent_fallback(self, service):
        """Test fallback when no agent from ORDER has messages."""
        mock_data = {
            "UnknownAgent": [{"id": "1"}],
        }
        
        with patch.object(service, 'get_pending_messages_by_agent', return_value=mock_data):
            agent = service.select_agent_by_messages()
            assert agent == "UnknownAgent"


class TestRegisterMessage:
    """Tests for register_message()."""

    def test_register_message(self, service):
        """Test registering a new message."""
        with patch.object(service, 'send_message', return_value=True) as mock_send:
            result = service.register_message("A", "B", "content")
            assert result is True
            mock_send.assert_called_once_with("A", "B", "content")


class TestAgentRoleOrder:
    """Tests for AGENT_ROLE_ORDER constant."""

    def test_agent_role_order_contains_all_agents(self):
        """Test that role order contains all expected agents."""
        expected_agents = [
            "Requirements Analyst",
            "Architect/Designer",
            "Developer",
            "Tester",
            "Deployer",
            "Maintainer/Reviewer",
            "Refiner",
            "Git Maintainer",
            "Documentation Specialist"
        ]
        
        for agent in expected_agents:
            assert agent in AGENT_ROLE_ORDER

    def test_agent_role_order_no_duplicates(self):
        """Test that there are no duplicate agents in the order."""
        assert len(AGENT_ROLE_ORDER) == len(set(AGENT_ROLE_ORDER))


class TestCountMessagesForAgent:
    """Tests for count_messages_for_agent()."""

    def test_count_messages_for_agent(self, service):
        """Test counting messages for a specific agent."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→Developer: hello\n"
            "○ orchestrator-124 ● P3 MESSAGE: B→Developer: world\n"
            "○ orchestrator-125 ● P3 MESSAGE: C→Tester: test\n"
        )
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            count = service.count_messages_for_agent("Developer")
            assert count == 2

    def test_count_messages_for_agent_with_all(self, service):
        """Test counting messages includes →[All] messages."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→[All]: announcement\n"
        )
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            count = service.count_messages_for_agent("Developer")
            assert count == 1

    def test_count_messages_for_agent_empty(self, service):
        """Test counting with no messages for agent."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_messages_for_agent("Developer")
            assert count == 0

    def test_count_messages_for_agent_exception(self, service):
        """Test that exceptions are handled gracefully."""
        with patch('subprocess.run', side_effect=Exception("error")):
            count = service.count_messages_for_agent("Developer")
            assert count == 0


class TestBdListParsingEdgeCases:
    """Edge case tests for bd list output parsing."""

    def test_count_pending_messages_with_all_messages(self, service):
        """Test counting includes [All] messages."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→[All]: announcement\n"
            "○ orchestrator-124 ● P3 MESSAGE: B→C: direct message\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_pending_messages()
            assert count == 2

    def test_count_pending_messages_malformed_lines(self, service):
        """Test handling of malformed output lines."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→B: valid\n"
            "Some random line without MESSAGE\n"
            "○ orchestrator-124 ● P3 MESSAGE: incomplete\n"
            "○ malformed line\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_pending_messages()
            assert count == 2  # Lines with MESSAGE: keyword

    def test_get_messages_different_status_symbols(self, service):
        """Test parsing with different status symbols."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→B: open message\n"
            "✓ orchestrator-124 ● P3 MESSAGE: C→B: closed but open task\n"
            "◐ orchestrator-125 ● P3 MESSAGE: D→B: in progress\n"
            "● orchestrator-126 ● P3 MESSAGE: E→B: blocked\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            messages = service.get_messages_for_agent("B")
            assert "open message" in messages
            assert "closed but open task" in messages
            assert "in progress" in messages
            assert "blocked" in messages

    def test_get_pending_messages_malformed_lines(self, service):
        """Test handling malformed lines in get_pending_messages_by_agent."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→Developer: valid\n"
            "malformed line without proper format\n"
            "○ orchestrator-124 ● P3 MESSAGE: no arrow in message\n"
            "○ orchestrator-125 ● P3 MESSAGE: B→Tester: also valid\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            result = service.get_pending_messages_by_agent()
            assert "Developer" in result
            assert "Tester" in result
            assert len(result) == 2

    def test_count_messages_mixed_all_and_targeted(self, service):
        """Test counting with mixed [All] and targeted messages."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→[All]: announcement 1\n"
            "○ orchestrator-124 ● P3 MESSAGE: B→Developer: specific\n"
            "○ orchestrator-125 ● P3 MESSAGE: C→[All]: announcement 2\n"
            "○ orchestrator-126 ● P3 MESSAGE: D→Developer: another specific\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_messages_for_agent("Developer")
            assert count == 4  # 2 targeted + 2 [All]

    def test_get_messages_special_characters_in_agent_names(self, service):
        """Test parsing with special characters in agent names."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: AI-Agent→Developer: message\n"
            "○ orchestrator-124 ● P3 MESSAGE: Dev_Ops→[All]: update\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            messages = service.get_messages_for_agent("Developer")
            assert "message" in messages
            assert "update" in messages

    def test_get_pending_messages_by_agent_with_all(self, service):
        """Test [All] messages are grouped correctly."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→[All]: broadcast\n"
            "○ orchestrator-124 ● P3 MESSAGE: B→Developer: specific\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            result = service.get_pending_messages_by_agent()
            assert "All" in result  # Regex extracts 'All' from '[All]'
            assert "Developer" in result
            assert len(result["All"]) == 1
            assert len(result["Developer"]) == 1

    def test_count_pending_messages_updated_format(self, service):
        """Test count_pending_messages with realistic human-readable format."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "○ orchestrator-123 ● P3 MESSAGE: A→B: hello\n"
            "○ orchestrator-124 ● P2 task Regular task\n"
            "○ orchestrator-125 ● P3 MESSAGE: C→D: world\n"
            "✓ orchestrator-126 ● P1 MESSAGE: E→F: done but still open\n"
        )
        with patch('subprocess.run', return_value=mock_result):
            count = service.count_pending_messages()
            assert count == 3  # Only MESSAGE: lines
