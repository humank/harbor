"""Domain exceptions for Harbor services."""


class HarborError(Exception):
    """Base exception."""


class AgentNotFoundError(HarborError):
    """Agent does not exist."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent {agent_id} not found")
        self.agent_id = agent_id


class InvalidLifecycleTransitionError(HarborError):
    """Lifecycle state transition is not allowed."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition from {current} to {target}")
        self.current = current
        self.target = target


class InsufficientApprovalsError(HarborError):
    """Not enough approvals for the transition."""


class DuplicateAgentError(HarborError):
    """Agent with this ID already exists."""

    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent {agent_id} already exists")
        self.agent_id = agent_id


class PolicyViolationError(HarborError):
    """A governance policy was violated."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class TenantMismatchError(HarborError):
    """Caller's tenant does not match the resource's tenant."""
