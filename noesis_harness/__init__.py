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
__all__.extend(["BestStateStore", "CandidateDecision", "DecisionStatus", "RecoveryResult", "RecoveryStatus", "StateRecord"])
