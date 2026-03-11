from unittest.mock import patch, MagicMock
import subprocess
import pytest
import os
from orchestrator.service import OrchestrationService

@pytest.fixture
def service():
    with patch('shutil.which', return_value='/usr/bin/gemini'):
        return OrchestrationService()

def test_get_available_cli_agents_none():
    with patch('shutil.which', return_value=None):
        service = OrchestrationService()
        assert service.available_cli_agents == []

def test_verify_tools(service):
    with patch('shutil.which', return_value='/usr/bin/tool'):
        assert service.verify_tools() is True
    
    with patch('shutil.which', return_value=None):
        assert service.verify_tools() is False

def test_verify_git_repo(service):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert service.verify_git_repo() is True
        
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert service.verify_git_repo() is False

def test_verify_specs_file(service):
    with patch('os.path.exists', return_value=True):
        assert service.verify_specs_file() is True
        
    with patch('os.path.exists', return_value=False), patch('orchestrator.service.OrchestrationService.create_specs_template') as mock_create:
        assert service.verify_specs_file() is True
        mock_create.assert_called_once()

def test_initialize_beads(service):
    with patch('subprocess.run') as mock_run:
        # Already initialized
        mock_run.return_value = MagicMock(returncode=0, stdout="some issues")
        assert service.initialize_beads() is True
        
        # Not initialized
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""), # bd list fails
            MagicMock(returncode=0), # bd init
            MagicMock(returncode=0)  # bd create
        ]
        assert service.initialize_beads() is True
        
        # Exception
        mock_run.side_effect = Exception("error")
        assert service.initialize_beads() is False

def test_check_for_blockers(service):
    with patch('orchestrator.service.OrchestrationService.get_beads_state', return_value="BLOCKER: something"):
        assert service.check_for_blockers() is True
    
    with patch('orchestrator.service.OrchestrationService.get_beads_state', return_value="all good"):
        assert service.check_for_blockers() is False

def test_messaging(service):
    with patch('orchestrator.service.beads.send_message') as mock_send:
        assert service.send_message("A", "B", "msg") is True
    
    with patch('orchestrator.service.beads.send_message', side_effect=Exception("error")):
        assert service.send_message("A", "B", "msg") is False

    with patch('orchestrator.service.beads.list_issues', return_value="MESSAGE: A→B: hello\nMESSAGE: B→[All]: hi"):
        assert "hello" in service.get_messages_for_agent("B")
        assert "hi" in service.get_messages_for_agent("B")
        assert "hello" in service.get_messages_from_agent("A")

def test_mark_message_read(service):
    with patch('orchestrator.service.beads.close_issue') as mock_close:
        assert service.mark_message_read("123") is True
    
    with patch('orchestrator.service.beads.close_issue', side_effect=Exception("error")):
        assert service.mark_message_read("123") is False

def test_commit_changes(service):
    with patch('subprocess.run') as mock_run:
        # Changes exist
        mock_run.side_effect = [
            MagicMock(returncode=0), # git add
            MagicMock(returncode=1), # git diff (means changes)
            MagicMock(returncode=0)  # git commit
        ]
        assert service.commit_changes("Agent", "msg") is True
        
        # No changes
        mock_run.side_effect = [
            MagicMock(returncode=0), # git add
            MagicMock(returncode=0)  # git diff (no changes)
        ]
        assert service.commit_changes("Agent", "msg") is True
        
        # Exception
        mock_run.side_effect = Exception("error")
        assert service.commit_changes("Agent", "msg") is False

def test_git_utils_error(service):
    with patch('subprocess.run', side_effect=Exception("error")):
        assert "Error" in service.get_git_status()
        assert "Error" in service.get_git_log()
        assert "Error" in service.get_beads_prime()

def test_build_context(service):
    with patch('orchestrator.service.OrchestrationService.get_beads_state', return_value="state"), \
         patch('orchestrator.service.OrchestrationService.get_git_status', return_value="status"), \
         patch('orchestrator.service.OrchestrationService.get_git_log', return_value="log"), \
         patch('orchestrator.service.OrchestrationService.get_beads_prime', return_value="prime"), \
         patch('orchestrator.service.OrchestrationService.get_messages_for_agent', return_value="msgs"):
        ctx = service.build_context("Agent")
        assert "state" in ctx
        assert "status" in ctx
        assert "log" in ctx
        assert "prime" in ctx
        assert "msgs" in ctx

def test_call_agent_with_retry_all_fails(service):
    with patch('subprocess.run') as mock_run, patch('time.sleep'):
        mock_run.return_value = MagicMock(returncode=1, stdout="fail")
        res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
        assert res is None

def test_call_agent_with_retry_timeout(service):
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(["agent"], 10)), patch('time.sleep'):
        res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
        assert res is None

def test_call_agent_with_retry_exception(service):
    with patch('subprocess.run', side_effect=Exception("error")), patch('time.sleep'):
        res = service.call_agent_with_retry("Analyst", "prompt", "context", 1)
        assert res is None

def test_activate_agent_unknown(service):
    assert service.activate_agent("Unknown Agent", 1) is None
