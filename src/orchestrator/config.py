from typing import Dict, List
from pydantic import BaseModel, Field

class OrchestratorConfig(BaseModel):
    max_retries: int = 3
    max_iterations: int = 24
    agent_timeout_limit: str = "1200s"
    
    agents: List[str] = ["opencode", "gemini", "qwen", "cline", "codex"]
    agent_flags: Dict[str, str] = {
        "opencode": "run",
        "gemini": "-y -p",
        "qwen": "-y",
        "cline": "-a -y",
        "codex": "--full-auto exec --skip-git-repo-check",
    }
    
    required_tools: List[str] = ["git", "bd", "jq"]

# Default configuration instance
config = OrchestratorConfig()
