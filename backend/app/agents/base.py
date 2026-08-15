from abc import ABC, abstractmethod

from app.agents.state import AgentState


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        ...

    def __call__(self, state: AgentState) -> AgentState:
        return self.run(state)
