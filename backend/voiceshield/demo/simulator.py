"""Demo scenario simulator interface (C-51)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ScenarioEngine(ABC):
    """Abstract interface for demo fixture playback and simulated scenario execution."""

    @abstractmethod
    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List available frozen demo scenarios."""
        raise NotImplementedError("ScenarioEngine.list_scenarios is not implemented yet")

    @abstractmethod
    async def start_scenario(self, scenario_id: str) -> str:
        """Start a session initialized with the specified scenario fixture."""
        raise NotImplementedError("ScenarioEngine.start_scenario is not implemented yet")
