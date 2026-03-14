"""Tests for the orchestration service module."""

from unittest.mock import patch, MagicMock, PropertyMock
import subprocess
import pytest
import os
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
    """Create an OrchestrationService instance with mocked broker."""
    with patch('shutil.which', return_value='/usr/bin/gemini'):
        return OrchestrationService(broker=mock_broker)


class TestServiceInit:
    """Tests for service initialization."""
    
    def test_get_available_cli_agents_none(self):
        with patch('shutil.which', return_value=None):
            service = OrchestrationService()
            assert service.available_cli_agents == []
    
    def test_get_available_cli_agents_some(self):
        with patch('shutil.which', side_effect=lambda x: '/bin/' + x if x in ['gemini', 'qwen'] else None):
            service = OrchestrationService()
            assert len(service.available_cli_agents) == 2
            assert 'gemini' in service.available_cli_agents
            assert 'qwen' in service.available_cli_agents


class TestVerifyTools:
    """Tests for verify_tools method."""
    
    def test_verify_tools(self, mock_broker):
        with patch('shutil.which', return_value='/usr/bin/tool'):
            service = OrchestrationService(broker=mock_broker)
            assert service.verify_tools() is True
        
        with patch('shutil.which', return_value=None):
            service = OrchestrationService(broker=mock_broker)
            assert service.verify_tools() is False


class TestVerifyGitRepo:
    """Tests for verify_git_repo method."""
    
    def test_verify_git_repo(self, service):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert service.verify_git_repo() is True
            
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            assert service.verify_git_repo() is False


class TestVerifySpecsFile:
    """Tests for verify_specs_file method."""
    
    def test_verify_specs_file(self, service):
        with patch('os.path.exists', return_value=True):
            assert service.verify_specs_file() is True
        
        with patch('os.path.exists', return_value=False), \
             patch('orchestrator.service.OrchestrationService.create_specs_template') as mock_create:
            assert service.verify_specs_file() is True
            mock_create.assert_called_once()


class TestInitializeBeads:
    """Tests for initialize_beads method (verifies broker)."""
    
    def test_initialize_beads_success(self, service):
        service.broker.verify.return_value = True
        assert service.initialize_beads() is True
    
    def test_initialize_beads_failure(self, service):
        service.broker.verify.return_value = False
        assert service.initialize_beads() is False


class TestBootstrapMessages:
    """Tests for create_bootstrap_messages method."""
    
    def test_create_bootstrap_messages(self, service):
        service.create_bootstrap_messages()
        
        # Should send one message to each agent role
        assert service.broker.send_message.call_count == len(AGENT_ROLE_ORDER)


class TestCountPendingMessages:
    """Tests for count_pending_messages method."""
    
    def test_count_pending_messages(self, service):
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "a"},
            {"id": "2", "to": "b"},
            {"id": "3", "to": "a"},
        ]
        
        assert service.count_pending_messages() == 3
    
    def test_count_pending_messages_empty(self, service):
        service.broker.get_all_pending.return_value = []
        assert service.count_pending_messages() == 0


class TestCountMessagesForAgent:
    """Tests for count_messages_for_agent method."""
    
    def test_count_messages_for_agent(self, service):
        service.broker.count_pending.return_value = 5
        assert service.count_messages_for_agent("Developer") == 5
        service.broker.count_pending.assert_called_with("Developer")


class TestGetPendingMessagesByAgent:
    """Tests for get_pending_messages_by_agent method."""
    
    def test_get_pending_messages_by_agent(self, service):
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "Developer", "from": "Architect"},
            {"id": "2", "to": "Tester", "from": "Developer"},
            {"id": "3", "to": "Developer", "from": "System"},
        ]
        
        result = service.get_pending_messages_by_agent()
        
        assert len(result["Developer"]) == 2
        assert len(result["Tester"]) == 1
    
    def test_get_pending_messages_by_agent_empty(self, service):
        service.broker.get_all_pending.return_value = []
        result = service.get_pending_messages_by_agent()
        assert result == {}


class TestSelectAgentByMessages:
    """Tests for select_agent_by_messages method."""
    
    def test_select_agent_by_messages(self, service):
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "Developer"},
            {"id": "2", "to": "Developer"},
            {"id": "3", "to": "Tester"},
        ]
        
        agent = service.select_agent_by_messages()
        assert agent == "Developer"
    
    def test_select_agent_by_messages_tie_break(self, service):
        # Equal messages, should use role order
        service.broker.get_all_pending.return_value = [
            {"id": "1", "to": "Tester"},
            {"id": "2", "to": "Developer"},
        ]
        
        agent = service.select_agent_by_messages()
        # Requirements Analyst comes first in role order
        assert agent == "Developer"  # Developer comes before Tester
    
    def test_select_agent_by_messages_empty(self, service):
        service.broker.get_all_pending.return_value = []
        assert service.select_agent_by_messages() is None


class TestCommitChanges:
    """Tests for commit_changes method."""
    
    def test_commit_changes_with_changes(self, service):
        with patch('subprocess.run') as mock_run:
            # Changes exist
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=1),  # git diff (means changes)
                MagicMock(returncode=0)   # git commit
            ]
            assert service.commit_changes("Agent", "msg") is True
    
    def test_commit_changes_no_changes(self, service):
        with patch('subprocess.run') as mock_run:
            # No changes
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=0)   # git diff (no changes)
            ]
            assert service.commit_changes("Agent", "msg") is True
    
    def test_commit_changes_exception(self, service):
        with patch('subprocess.run', side_effect=Exception("error")):
            assert service.commit_changes("Agent", "msg") is False


class TestGitUtils:
    """Tests for git utility methods."""
    
    def test_get_git_status(self, service):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=" M file.py\n")
            assert "file.py" in service.get_git_status()
    
    def test_get_git_status_error(self, service):
        with patch('subprocess.run', side_effect=Exception("error")):
            assert "Error" in service.get_git_status()
    
    def test_get_git_log(self, service):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="abc123 Commit message\n")
            assert "abc123" in service.get_git_log()
    
    def test_get_git_log_error(self, service):
        with patch('subprocess.run', side_effect=Exception("error")):
            assert "Error" in service.get_git_log()


class TestBuildContext:
    """Tests for build_context method."""

    def test_build_context(self, service):
        with patch.object(service, 'get_git_status', return_value="status"), \
             patch.object(service, 'get_git_log', return_value="log"), \
             patch.object(service.broker, 'generate_context', return_value="broker_ctx"):
            ctx = service.build_context("Agent", iteration=5)
            assert "status" in ctx
            assert "log" in ctx
            assert "broker_ctx" in ctx
            assert "=== ITERATION ===" in ctx
            assert "5" in ctx
            # Should NOT include messages (agents read their own)
            assert "INTER-AGENT MESSAGES" not in ctx


class TestCallAgentWithRetry:
    """Tests for call_agent_with_retry method."""
    
    def test_success(self, service):
        service.available_cli_agents = ['gemini']
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Agent output"
        
        with patch('subprocess.run', return_value=mock_process):
            result = service.call_agent_with_retry("Developer", "prompt", "context", 1)
            assert result == "Agent output"
    
    def test_all_fails(self, service):
        with patch('subprocess.run') as mock_run, patch('time.sleep'):
            mock_run.return_value = MagicMock(returncode=1, stdout="fail")
            res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
            assert res is None
    
    def test_timeout(self, service):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(["agent"], 10)), \
             patch('time.sleep'):
            res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
            assert res is None
    
    def test_exception(self, service):
        with patch('subprocess.run', side_effect=Exception("error")), \
             patch('time.sleep'):
            res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
            assert res is None


class TestActivateAgent:
    """Tests for activate_agent method."""
    
    def test_success(self, service):
        with patch.object(service, 'build_context', return_value="context"):
            with patch.object(service, 'call_agent_with_retry', return_value="output"):
                result = service.activate_agent("Developer", 1)
                assert result == "output"
    
    def test_unknown_agent(self, service):
        assert service.activate_agent("Unknown Agent", 1) is None


class TestGetNextCliAgent:
    """Tests for get_next_cli_agent method."""
    
    def test_rotation(self, service):
        service.available_cli_agents = ['gemini', 'qwen']
        
        assert service.get_next_cli_agent(1) == 'gemini'
        assert service.get_next_cli_agent(2) == 'qwen'
        assert service.get_next_cli_agent(3) == 'gemini'  # Wraps around
    
    def test_empty(self, service):
        service.available_cli_agents = []
        assert service.get_next_cli_agent(1) is None


class TestGetBeadsState:
    """Tests for get_beads_state method."""

    def test_with_messages(self, service):
        service.broker.count_by_agent.return_value = {"Developer": 3, "Tester": 1}
        state = service.get_beads_state()
        assert "Developer" in state
        assert "Tester" in state

    def test_empty(self, service):
        service.broker.count_by_agent.return_value = {}
        assert "No pending messages" in service.get_beads_state()


class TestCreateSpecsTemplate:
    """Tests for create_specs_template method."""

    def test_create_specs_template(self, service):
        """Test specs template creation."""
        with patch('builtins.open', __enter__=lambda *args: None, __exit__=lambda *args: None):
            service.create_specs_template()


class TestCallAgentWithRetryTimeout:
    """Tests for call_agent_with_retry timeout handling."""

    def test_timeout_with_int_config(self, mock_broker):
        """Test timeout handling when timeout is an int (not string)."""
        with patch('orchestrator.service.config') as mock_config:
            mock_config.agent_timeout_limit = 1200  # int, not "1200s"
            mock_config.max_retries = 1
            
            with patch('shutil.which', return_value='/usr/bin/gemini'):
                service = OrchestrationService(broker=mock_broker)
                service.available_cli_agents = ['gemini']
                
                with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(["agent"], 1200)), \
                     patch('time.sleep'):
                    res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
                    assert res is None

    def test_no_cli_agents_available(self, service):
        """Test call_agent_with_retry when no CLI agents available."""
        service.available_cli_agents = []
        
        with patch('time.sleep'):
            res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
            assert res is None
