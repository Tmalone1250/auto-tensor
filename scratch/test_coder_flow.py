import os
import sys
import json
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock health_check BEFORE importing coder
with patch('core.health_check.governor_gate', return_value=True):
    import agents.coder as coder
    
    # Also mock executor to avoid running actual long build commands in this environment
    # if the repo doesn't exist. We want to test the FLOW.
    with patch('agents.coder.run_wsl_in_workspace') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Build SUCCESS", stderr="")
        
        # Also mock LLM to avoid API calls during a quick logic test
        with patch('agents.coder.LlmClient') as mock_llm:
            instance = mock_llm.return_value
            instance.generate.return_value = "Verified. The delta shows success."
            
            # Ensure mission_parameters.json exists
            params = {
                "mission_id": "TEST-001",
                "target_repo": "test/repo",
                "strategy": "Test strategy",
                "repro_cmd": "echo repro",
                "fix_cmd": "echo fix"
            }
            os.makedirs("logs", exist_ok=True)
            with open("logs/mission_parameters.json", "w") as f:
                json.dump(params, f)
            
            print("--- RUNNING MOCKED CODER TEST ---")
            coder.execute_mission()
            print("--- TEST COMPLETE ---")
