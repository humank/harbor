"""Shared FastAPI dependencies — stores, services, auth."""

from harbor.audit.service import AuditService
from harbor.auth.service import AuthContext, get_auth_context, require_role
from harbor.discovery.service import DiscoveryService
from harbor.events.emitter import EventEmitter
from harbor.health.service import HealthService
from harbor.policy.service import PolicyService
from harbor.registry.service import RegistryService
from harbor.store.agent_store import AgentStore
from harbor.store.audit_store import AuditStore
from harbor.store.health_store import HealthStore
from harbor.store.policy_store import PolicyStore
from harbor.store.version_store import VersionStore


class Services:
    """Container for all wired services. Created once in main.py."""

    def __init__(
        self,
        agent_store: AgentStore | None = None,
        audit_store: AuditStore | None = None,
        health_store: HealthStore | None = None,
        policy_store: PolicyStore | None = None,
        version_store: VersionStore | None = None,
        events: EventEmitter | None = None,
    ) -> None:
        self.agent_store = agent_store or AgentStore()
        self.audit_store = audit_store or AuditStore()
        self.health_store = health_store or HealthStore()
        self.policy_store = policy_store or PolicyStore()
        self.version_store = version_store or VersionStore()
        self.events = events or EventEmitter()

        self.registry = RegistryService(
            self.agent_store, self.audit_store, self.version_store, self.events,
        )
        self.discovery = DiscoveryService(self.agent_store)
        self.health = HealthService(self.agent_store, self.health_store)
        self.audit = AuditService(self.audit_store)
        self.policy = PolicyService(self.policy_store, self.audit_store, self.events)


__all__ = ["AuthContext", "Services", "get_auth_context", "require_role"]
