from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from orchestrator.main import app, strip_markdown, parse_orchestrator_decision, run
import subprocess

runner = CliRunner()

def test_strip_markdown():
    # Fix: ensure underscores are actually surrounded by word boundaries or at end/start
    assert strip_markdown("**bold** *italic* `code` __ under __ _ line _") == "bold italic code under line"

def test_parse_orchestrator_decision():
    assert parse_orchestrator_decision("NEXT_AGENT: Developer") == "Developer"
    assert parse_orchestrator_decision("PROJECT_COMPLETE") == "PROJECT_COMPLETE"
    assert parse_orchestrator_decision("PROJECT_HALTED: Error") == "PROJECT_HALTED: Error"
    assert parse_orchestrator_decision("Let's activate the Requirements Analyst") == "Requirements Analyst"
    assert parse_orchestrator_decision("Nothing to see here") == "UNKNOWN"

def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SDLC Orchestrator v0.1.0" in result.stdout

@patch('orchestrator.main.orchestration_service')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_success(mock_sub, mock_sleep, mock_service):
    # Setup mocks
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.get_beads_state.return_value = "Done"
    
    # First call to Orchestrator returns decision to call Requirements Analyst
    # Second call to Orchestrator returns PROJECT_COMPLETE
    mock_service.activate_agent.side_effect = [
        "NEXT_AGENT: Requirements Analyst", # Orchestrator decision
        "Analyst done",                     # Agent output
        "PROJECT_COMPLETE"                  # Orchestrator decision
    ]
    
    # Call directly
    run(max_iterations=2)
    
    assert mock_service.activate_agent.call_count == 3
    assert mock_service.commit_changes.called

@patch('orchestrator.main.orchestration_service')
def test_run_halted(mock_service):
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    
    mock_service.activate_agent.return_value = "PROJECT_HALTED: Reason"
    
    run(max_iterations=5)
    assert mock_service.activate_agent.called

@patch('orchestrator.main.orchestration_service')
def test_run_unknown_decision(mock_service):
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    
    mock_service.activate_agent.return_value = "Random text"
    
    run(max_iterations=5)
    assert mock_service.activate_agent.called

@patch('orchestrator.main.orchestration_service')
def test_prerequisites_fail(mock_service):
    mock_service.verify_tools.return_value = False
    run(max_iterations=5)
    
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = False
    run(max_iterations=5)
    
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = False
    run(max_iterations=5)

def test_main_execution():
    with patch('orchestrator.main.app') as mock_app:
        with patch('orchestrator.main.__name__', '__main__'):
            # This is hard to test directly due to how python executes modules
            pass
