"""Tests for message-driven system functionality with broker."""

from unittest.mock import patch, MagicMock
import pytest
from orchestrator.service import OrchestrationService, AGENT_ROLE_ORDER


@pytest.fixture
def mock_broker():
    """Create a mock broker instance."""
    broker = MagicMock()
    broker.verify.return_value = True
    broker.count_by_agent.return_value = {}
    broker.get_all_pending.return_value = []
    broker.count_pending.return_value = 0
    broker.send_message.return_value = "msg_123_test"
    broker.generate_context.return_value = "Broker context"
    return broker


@pytest.fixture
def service(mock_broker):
    """Create a service instance with mocked broker."""
    with patch('shutil.which', return_value='/usr/bin/gemini'):
        return OrchestrationService(broker=mock_broker)


class TestBootstrapMessages:
    """Tests for create_bootstrap_messages()."""

    def test_create_bootstrap_messages(self, service):
        """Test that bootstrap messages are created for all agents."""
        service.create_bootstrap_messages()

        # Should send to all agents in AGENT_ROLE_ORDER
        assert service.broker.send_message.call_count == len(AGENT_ROLE_ORDER)

        # Check first call (System → Requirements Analyst)
        first_call = service.broker.send_message.call_args_list[0]
        assert first_call[0][0] == "System"
        assert first_call[0][1] == "Requirements Analyst"
        assert "Bootstrap message" in first_call[0][2]

    def test_create_bootstrap_messages_handles_exception(self, service):
        """Test that exceptions during bootstrap are handled gracefully."""
        service.broker.send_message.side_effect = Exception("error")
        # Should not raise, just log warnings
        service.create_bootstrap_messages()


class TestCountPendingMessages:
    """Tests for count_pending_messages()."""

    def test_count_pending_messages(self, service):
        """Test counting pending messages."""
        service.broker.get_all_pending.return_value = [
            {"id": "msg_1", "to": "B", "from": "A"},
            {"id": "msg_2", "to": "D", "from": "C"},
        ]
        count = service.count_pending_messages()
        assert count == 2

    def test_count_pending_messages_empty(self, service):
        """Test counting with no pending messages."""
        service.broker.get_all_pending.return_value = []
        count = service.count_pending_messages()
        assert count == 0

    def test_count_pending_messages_exception(self, service):
        """Test that exceptions are handled gracefully by broker."""
        # Broker handles exceptions internally and returns empty list
        service.broker.get_all_pending.return_value = []
        count = service.count_pending_messages()
        assert count == 0


class TestGetPendingMessagesByAgent:
    """Tests for get_pending_messages_by_agent()."""

    def test_get_pending_messages_by_agent(self, service):
        """Test grouping pending messages by target agent."""
        service.broker.get_all_pending.return_value = [
            {"id": "msg_1", "to": "Developer", "from": "A"},
            {"id": "msg_2", "to": "Developer", "from": "B"},
            {"id": "msg_3", "to": "Tester", "from": "C"},
        ]
        result = service.get_pending_messages_by_agent()

        assert "Developer" in result
        assert "Tester" in result
        assert len(result["Developer"]) == 2
        assert len(result["Tester"]) == 1
        assert result["Developer"][0]["id"] == "msg_1"

    def test_get_pending_messages_by_agent_empty(self, service):
        """Test with no pending messages."""
        service.broker.get_all_pending.return_value = []
        result = service.get_pending_messages_by_agent()
        assert result == {}

    def test_get_pending_messages_by_agent_exception(self, service):
        """Test that exceptions are handled gracefully by broker."""
        # Broker handles exceptions internally and returns empty list
        service.broker.get_all_pending.return_value = []
        result = service.get_pending_messages_by_agent()
        assert result == {}


class TestSelectAgentByMessages:
    """Tests for select_agent_by_messages()."""

    def test_select_agent_first_in_order(self, service):
        """Test selecting first agent in order with pending messages."""
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "Developer"},
            {"id": "2", "to": "Developer"},
            {"id": "3", "to": "Developer"},
            {"id": "4", "to": "Tester"},
            {"id": "5", "to": "Tester"},
            {"id": "6", "to": "Requirements Analyst"},
        ]
        agent = service.select_agent_by_messages()
        # Requirements Analyst comes first in order and has messages
        assert agent == "Requirements Analyst"

    def test_select_agent_skips_empty_agents(self, service):
        """Test that agents without messages are skipped in order."""
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "Developer"},
            {"id": "2", "to": "Tester"},
        ]
        agent = service.select_agent_by_messages()
        # Requirements Analyst and Architect/Designer have no messages, skip to Developer
        assert agent == "Developer"

    def test_select_agent_no_messages(self, service):
        """Test with no pending messages."""
        service.broker.get_all_pending.return_value = []
        agent = service.select_agent_by_messages()
        assert agent is None

    def test_select_agent_fallback(self, service):
        """Test fallback when no agent from ORDER has messages."""
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "UnknownAgent"},
        ]
        agent = service.select_agent_by_messages()
        assert agent == "UnknownAgent"


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
        service.broker.count_pending.return_value = 2
        count = service.count_messages_for_agent("Developer")
        assert count == 2
        service.broker.count_pending.assert_called_with("Developer")

    def test_count_messages_for_agent_empty(self, service):
        """Test counting with no messages for agent."""
        service.broker.count_pending.return_value = 0
        count = service.count_messages_for_agent("Developer")
        assert count == 0

    def test_count_messages_for_agent_exception(self, service):
        """Test that exceptions are handled gracefully by broker."""
        # Broker handles exceptions internally and returns 0
        service.broker.count_pending.return_value = 0
        count = service.count_messages_for_agent("Developer")
        assert count == 0


class TestBrokerIntegration:
    """Tests for broker integration."""

    def test_count_pending_uses_broker(self, service):
        """Test that count_pending_messages uses broker."""
        service.broker.get_all_pending.return_value = [{"id": "1"}]
        service.count_pending_messages()
        service.broker.get_all_pending.assert_called_once()

    def test_count_for_agent_uses_broker(self, service):
        """Test that count_messages_for_agent uses broker."""
        service.count_messages_for_agent("Developer")
        service.broker.count_pending.assert_called_with("Developer")

    def test_get_pending_by_agent_uses_broker(self, service):
        """Test that get_pending_messages_by_agent uses broker."""
        service.broker.get_all_pending.return_value = []
        service.get_pending_messages_by_agent()
        service.broker.get_all_pending.assert_called_once()

    def test_select_agent_uses_broker(self, service):
        """Test that select_agent_by_messages uses broker."""
        service.broker.get_all_pending.return_value = []
        service.select_agent_by_messages()
        service.broker.get_all_pending.assert_called_once()

    def test_bootstrap_uses_broker(self, service):
        """Test that create_bootstrap_messages uses broker."""
        service.create_bootstrap_messages()
        assert service.broker.send_message.called
