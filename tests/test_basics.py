import pytest
from orchestrator.service import OrchestrationService
from orchestrator.agents import registry
from orchestrator.config import config

def test_available_cli_agents():
    service = OrchestrationService()
    # At least gemini should be available in this environment
    assert len(service.available_cli_agents) > 0

def test_agent_rotation():
    service = OrchestrationService()
    if not service.available_cli_agents:
        pytest.skip("No CLI agents available")
    
    agent1 = service.get_next_cli_agent(1)
    agent2 = service.get_next_cli_agent(2)
    
    assert agent1 is not None
    if len(service.available_cli_agents) > 1:
        assert agent1 != agent2
    else:
        assert agent1 == agent2

def test_registry():
    assert registry.get_agent("Orchestrator") is not None
    assert registry.get_agent("Requirements Analyst") is not None
    assert registry.get_agent("Unknown") is None
