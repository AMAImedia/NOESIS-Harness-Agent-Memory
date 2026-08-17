"""noesis_harness/__init__.py

NOESIS Harness Agent Memory — a local-first agent framework core.

Three primitives, zero cloud, zero API keys:
  - event_store   : append-only event log + deterministic projection
  - memory        : four-tier persistent memory (working/episodic/semantic/procedural)
  - coordination  : leases + signals + actions (agents never overlap)

"Selling point": agents that don't forget, don't loop, and don't step on each
other — on your laptop, for free.
"""

from .event_store import EventStore, project_chain
from .memory import Memory
from .coordination import Leases, Signals, Actions
from .privacy import PrivacyFilter
from .snapshot import export_snapshot, import_snapshot
from .consolidate import ConsolidationWorker
from .procedures import ProcedureRunner, parse_procedure
from .mesh import Mesh, serve_mesh
from .inspect_ui import InspectUI
from .trace import AgentTrace, HybridJudge
from .queue import DurableQueue
from .loop_guard import LoopGuard
from .graph import MemoryGraph
from .budget import Budget
from .hitl import HitlGate
from .scope import ScopedMemory
from .vfs import ContextVfs, uri as vfs_uri, parse_uri
from .session import extract_session
from .mcp_stdio import McpServer
from .context_pack import ContextPack, estimate_tokens
from .agent_loop import AgentLoop

__all__ = [
    "EventStore", "project_chain",
    "Memory",
    "Leases", "Signals", "Actions",
    "PrivacyFilter",
    "export_snapshot", "import_snapshot",
    "ConsolidationWorker",
    "ProcedureRunner", "parse_procedure",
    "Mesh", "serve_mesh",
    "InspectUI",
    "AgentTrace", "HybridJudge",
    "DurableQueue", "LoopGuard",
    "MemoryGraph", "Budget", "HitlGate", "ScopedMemory",
    "ContextVfs", "vfs_uri", "parse_uri",
    "extract_session", "McpServer",
    "ContextPack", "estimate_tokens", "AgentLoop",
]

__version__ = "0.5.0"

from .nextgen import AuditChain, AgentManifest, CapabilityDenied, CapabilityManifest, ContextManager, DurableCommandLedger, IsolationBroker, ResultEnvelope, RunEnvelope
from .governance import ActionRequest, DAGPlanner, ExecutionLadder, Gatekeeper, SkillGate, VaultNote, VaultProjector
__all__.extend(["AuditChain", "AgentManifest", "CapabilityDenied", "CapabilityManifest", "ContextManager", "DurableCommandLedger", "IsolationBroker", "ResultEnvelope", "RunEnvelope", "ActionRequest", "DAGPlanner", "ExecutionLadder", "Gatekeeper", "SkillGate", "VaultNote", "VaultProjector"])

from .fibers import FiberInterrupted, FiberRecord, FiberStore
from .evidence import EvidenceFact, EvidenceStore
from .security import ExecutionPlan, LocalExecutionContract, SecurityFinding, SecurityScanner, safe_path
__all__.extend(["FiberInterrupted", "FiberRecord", "FiberStore", "EvidenceFact", "EvidenceStore", "ExecutionPlan", "LocalExecutionContract", "SecurityFinding", "SecurityScanner", "safe_path"])

from .orchestration import WorkClaim, WorkCoordinator
__all__.extend(["WorkClaim", "WorkCoordinator"])

from .context_engine import ContextAssembly, ContextItem, BudgetedContextAssembler
__all__.extend(["ContextAssembly", "ContextItem", "BudgetedContextAssembler"])

from .best_state import BestStateStore, CandidateDecision, DecisionStatus, RecoveryResult, RecoveryStatus, StateRecord
from .recovery import DurableRecoveryReport, RecoveryCoordinator
__all__.extend(["BestStateStore", "CandidateDecision", "DecisionStatus", "RecoveryResult", "RecoveryStatus", "StateRecord", "DurableRecoveryReport", "RecoveryCoordinator"])
from .trajectory_eval import TrajectoryCheckpoint, TrajectoryEvaluator, TrajectoryMetrics, peak_retention
__all__.extend(["TrajectoryCheckpoint", "TrajectoryEvaluator", "TrajectoryMetrics", "peak_retention"])
from .memory_ab import ControlledMemoryEvaluator, MemoryABCase, MemoryABOutcome
__all__.extend(["ControlledMemoryEvaluator", "MemoryABCase", "MemoryABOutcome"])
from .security_holdouts import DEFAULT_HOLDOUTS, SecurityHoldoutCase, SecurityHoldoutResult, SecurityHoldoutSuite
__all__.extend(["DEFAULT_HOLDOUTS", "SecurityHoldoutCase", "SecurityHoldoutResult", "SecurityHoldoutSuite"])
from .coding_adapter import CodingSuiteSummary, CodingVerification, PINNED_TASKS, PinnedCodingTask, PinnedCodingTaskAdapter
from .isolation_holdouts import CrossAgentLeakageSuite, IsolationHoldoutResult
__all__.extend(["CodingSuiteSummary", "CodingVerification", "PINNED_TASKS", "PinnedCodingTask", "PinnedCodingTaskAdapter", "CrossAgentLeakageSuite", "IsolationHoldoutResult"])
from .ui_contract import CONTRACT_VERSION, UIContractError, UIEnvelope, failure, health_payload, model_payload, new_request_id, success
from .health_server import HealthServer
from .provider_registry import CAPABILITY_KEYS, ModelDescriptor, ProviderAdapterSpec, ProviderDescriptor, ProviderRegistry, ProviderRegistryError, SUPPORTED_PROVIDER_KINDS, adapter_spec
from .bridge_discovery import BridgeCandidate, BridgeDiscovery, BridgeStatus
from .runtime_supervisor import ChildRuntimeSupervisor, RuntimeStatus
from .user_data import UserDataPaths, user_data_paths
from .hermes_gateway import HERMES_FORBIDDEN_SCOPE_PREFIXES, HERMES_SUPPORTED_SCOPES, HermesGatewayAdapter, HermesGatewayConfig, HermesGatewayError
from .deepseek_harness import CompatibilityResult, DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES, DeepSeekHarnessAdapter, DeepSeekHarnessConfig, DeepSeekHarnessError
from .model_selector import SelectionResult, select_model
__all__.extend(["CONTRACT_VERSION", "UIContractError", "UIEnvelope", "failure", "health_payload", "model_payload", "new_request_id", "success", "HealthServer", "CAPABILITY_KEYS", "ModelDescriptor", "ProviderAdapterSpec", "ProviderDescriptor", "ProviderRegistry", "ProviderRegistryError", "SUPPORTED_PROVIDER_KINDS", "adapter_spec", "BridgeCandidate", "BridgeDiscovery", "BridgeStatus", "ChildRuntimeSupervisor", "RuntimeStatus", "UserDataPaths", "user_data_paths", "HERMES_FORBIDDEN_SCOPE_PREFIXES", "HERMES_SUPPORTED_SCOPES", "HermesGatewayAdapter", "HermesGatewayConfig", "HermesGatewayError", "CompatibilityResult", "DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES", "DeepSeekHarnessAdapter", "DeepSeekHarnessConfig", "DeepSeekHarnessError", "SelectionResult", "select_model"])
