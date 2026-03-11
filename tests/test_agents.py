from unittest.mock import patch, MagicMock
import subprocess
import pytest
from orchestrator.agents import registry, Agent, RequirementsAnalyst

def test_agent_registry():
    assert registry.get_agent("analyst") is not None
    assert registry.get_agent("Architect") is not None
    assert registry.get_agent("developer") is not None
    assert registry.get_agent("tester") is not None
    assert registry.get_agent("deployer") is not None
    assert registry.get_agent("GitMaintainer") is not None
    
    # Check if they return the same object where applicable
    assert registry.get_agent("Architect") == registry.get_agent("Designer")

def test_agent_call_success():
    agent = RequirementsAnalyst()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="Agent Output", returncode=0)
        result = agent.call_agent("gemini", "prompt", "context", 1)
        assert result == "Agent Output"

def test_agent_call_failure():
    agent = RequirementsAnalyst()
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["gemini"], stderr="Error")
        result = agent.call_agent("gemini", "prompt", "context", 1)
        assert "ERROR: Error" in result

def test_all_agent_prompts():
    # Test that all registered agents return a non-empty prompt
    for agent_name in registry.list_agents():
        agent = registry.get_agent(agent_name)
        prompt = agent.get_prompt("some context")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "AVAILABLE AGENTS" in prompt
