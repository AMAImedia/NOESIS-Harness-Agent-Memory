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
from .parallel_agent import AgentLane, AgentLaneContext, AgentLaneResult, ALWAYS_DENIED_CAPABILITIES, CancellationToken as ParallelCancellationToken, ParallelExecutionError, SAFE_CAPABILITIES, SafeParallelExecutor
from .task_session_api import COMMANDS, SCHEMA_VERSION as TASK_SESSION_SCHEMA_VERSION, SessionRecord, TaskRecord, TaskSessionError, TaskSessionStore
from .session_stream import STREAM_SCHEMA, MAX_EVENT_BYTES, CancellationToken, SessionEventBuffer, StreamContractError, StreamEvent
from .execution_bridge import TaskExecutionBridge, TaskExecutionBridgeError, TaskExecutionReport, TaskExecutionRequest
from .child_execution import ChildExecutionError, ChildExecutionRuntime, ExecutionRequest, ExecutionResult
from .execution_assurance import ASSURANCE_SCHEMA, AssuranceError, ExecutionReceipt, ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt, verify_receipt
from .execution_recovery import RECOVERY_ACTION_SCHEMA, ExecutionRecoveryAction, ExecutionRecoveryError, ExecutionRecoveryExecutor
from .multi_agent_workflow import WORK_PRODUCT_SCHEMA, MultiAgentWorkProductLoop, WorkProductEnvelope, WorkProductError
from .work_product_benchmark import WorkProductBenchmarkError, WorkProductBenchmarkEvaluator, WorkProductMetrics, WorkProductOutcome
from .multi_agent_benchmark import DurableWorkloadAggregator, MultiAgentBenchmarkError, MultiAgentWorkloadRunner, RepeatedWorkloadReport, WorkloadCase, WorkloadRun
from .isolation_holdouts import ActiveDelegationLeakageSuite
from .memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore, MemoryComparisonReport, MemoryQualityCase, MemoryQualityError, MemoryQualityEvaluator, MemoryQualityMetrics, MemoryQualityOutcome, MemoryTrajectoryStep, MultiSessionMemoryQualityReport, build_long_context_cases, compare_baseline_nextgen
from .native_parity import NATIVE_PARITY_SCHEMA, NativeParityEvidence, operator_bundle, prepare_native_evidence, validate_native_artifacts
from .delegated_resume import SCHEMA_VERSION as DELEGATED_RESUME_SCHEMA, DelegationIdentity, DelegationSnapshot, DelegatedResumeError, DelegatedResumeStore
from .delegated_resume_action import SCHEMA_VERSION as DELEGATED_RESUME_ACTION_SCHEMA, DelegatedResumeAction, DelegatedResumeActionReceipt, DelegatedResumeActionError, DelegatedResumeActionExecutor, bridge_resume_callback, bridge_runtime_resume_callback
from .signed_evidence_aggregator import SCHEMA_VERSION as SIGNED_EVIDENCE_AGGREGATE_SCHEMA, AggregateEvidence, SignedEvidenceAggregationError, SignedEvidenceAggregator, sign_evidence, verify_evidence
from .report_bundle import SCHEMA_VERSION as SIGNED_REPORT_BUNDLE_SCHEMA, SCHEMA_VERSION_WITH_RECEIPTS as SIGNED_REPORT_BUNDLE_WITH_RECEIPTS_SCHEMA, DOMAINS as SIGNED_REPORT_BUNDLE_DOMAINS, RECEIPT_DOMAIN as SIGNED_REPORT_BUNDLE_RECEIPT_DOMAIN, DOMAINS_WITH_RECEIPTS as SIGNED_REPORT_BUNDLE_DOMAINS_WITH_RECEIPTS, build_report_bundle, verify_report_bundle
from .report_export_action import SCHEMA_VERSION as REPORT_EXPORT_ACTION_SCHEMA, RECEIPT_SCHEMA as REPORT_EXPORT_RECEIPT_SCHEMA, LIFECYCLE_SCHEMA as REPORT_EXPORT_LIFECYCLE_SCHEMA, REQUIRED_SCOPE as REPORT_EXPORT_REQUIRED_SCOPE, ReportExportAction, ReportExportActionError, ReportExportActionExecutor
from .report_export_lifecycle import lifecycle_audit_only_projection, lifecycle_audit_readiness, verify_lifecycle_events, verify_lifecycle_file
from .lifecycle_audit_ingestion import LifecycleAuditIngestionAdapter, LifecycleAuditIngestionError, build_healthserver_wiring, verify_ingestion_receipt, verify_ingestion_receipt_audit

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
    "AgentLane", "AgentLaneContext", "AgentLaneResult", "ALWAYS_DENIED_CAPABILITIES", "ParallelCancellationToken", "ParallelExecutionError", "SAFE_CAPABILITIES", "SafeParallelExecutor",
    "COMMANDS", "TASK_SESSION_SCHEMA_VERSION", "SessionRecord", "TaskRecord", "TaskSessionError", "TaskSessionStore", "STREAM_SCHEMA", "MAX_EVENT_BYTES", "CancellationToken", "SessionEventBuffer", "StreamContractError", "StreamEvent", "TaskExecutionBridge", "TaskExecutionBridgeError", "TaskExecutionReport", "TaskExecutionRequest", "ChildExecutionError", "ChildExecutionRuntime", "ExecutionRequest", "ExecutionResult", "ASSURANCE_SCHEMA", "AssuranceError", "ExecutionReceipt", "ExecutionReceiptStore", "ExecutionRecoveryStore", "create_receipt", "verify_receipt", "RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor", "WORK_PRODUCT_SCHEMA", "MultiAgentWorkProductLoop", "WorkProductEnvelope", "WorkProductError", "WorkProductBenchmarkError", "WorkProductBenchmarkEvaluator", "WorkProductMetrics", "WorkProductOutcome", "DurableWorkloadAggregator", "MultiAgentBenchmarkError", "MultiAgentWorkloadRunner", "RepeatedWorkloadReport", "WorkloadCase", "WorkloadRun", "ActiveDelegationLeakageSuite", "DurableMemoryQualityAdapter", "DurableMemoryQualityTraceStore", "MemoryComparisonReport", "MemoryQualityCase", "MemoryQualityError", "MemoryQualityEvaluator", "MemoryQualityMetrics", "MemoryQualityOutcome", "MemoryTrajectoryStep", "MultiSessionMemoryQualityReport", "build_long_context_cases", "compare_baseline_nextgen", "NATIVE_PARITY_SCHEMA", "NativeParityEvidence", "operator_bundle", "prepare_native_evidence", "validate_native_artifacts", "DELEGATED_RESUME_SCHEMA", "DelegationIdentity", "DelegationSnapshot", "DelegatedResumeError", "DelegatedResumeStore", "DELEGATED_RESUME_ACTION_SCHEMA", "DelegatedResumeAction", "DelegatedResumeActionReceipt", "DelegatedResumeActionError", "DelegatedResumeActionExecutor", "bridge_resume_callback", "bridge_runtime_resume_callback", "SIGNED_EVIDENCE_AGGREGATE_SCHEMA", "AggregateEvidence", "SignedEvidenceAggregationError", "SignedEvidenceAggregator", "sign_evidence", "verify_evidence", "SIGNED_REPORT_BUNDLE_SCHEMA", "SIGNED_REPORT_BUNDLE_WITH_RECEIPTS_SCHEMA", "SIGNED_REPORT_BUNDLE_DOMAINS", "SIGNED_REPORT_BUNDLE_RECEIPT_DOMAIN", "SIGNED_REPORT_BUNDLE_DOMAINS_WITH_RECEIPTS", "build_report_bundle", "verify_report_bundle",
 "REPORT_EXPORT_ACTION_SCHEMA", "REPORT_EXPORT_RECEIPT_SCHEMA", "REPORT_EXPORT_LIFECYCLE_SCHEMA", "REPORT_EXPORT_REQUIRED_SCOPE", "ReportExportAction", "ReportExportActionError", "ReportExportActionExecutor", "verify_lifecycle_events", "verify_lifecycle_file", "lifecycle_audit_only_projection", "lifecycle_audit_readiness", "LifecycleAuditIngestionAdapter", "LifecycleAuditIngestionError", "build_healthserver_wiring", "verify_ingestion_receipt", "verify_ingestion_receipt_audit",
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
from .skill_manifest import ALLOWED_CAPABILITIES, ALLOWED_PLATFORMS, MANIFEST_FILENAME, MANIFEST_FORMAT_VERSION, SkillManifest, SkillManifestError, digest_files
from .skill_import import ImportAssessment, SafeSkillImport, SkillImportError
from .skill_store import SkillStore, SkillStoreError
from .skill_discovery import SkillDescriptor, SkillDiscoveryError, discover as discover_skills
from .experience_reuse import ExperienceRecord, ExperienceReuseError, ExperienceReuseSelector, ReuseDecision
from .learning_promotion import ExperienceReceipt, HoldoutEvaluation, PromotionProposal, LearningPromotionError, DurablePromotionState, LearningPromotionPipeline
from .promotion_integration import EvaluatorSpec, EvaluatorRegistry, PromotionTelemetry, RuntimePolicySimulator, OwnershipPolicySimulator, OperatorSessionRegistry, ReviewerAuthorizationStore, OperatorAuthContext, PromotionApprovalAction, PromotionActionReceipt, PromotionActionExecutor, SignedMutationReceipt, verify_signed_mutation_receipt, CoordinatedMutationJournal, OperatorSessionAction, OperatorSessionActionExecutor, AdministrativePolicyStore, PolicySimulation, PromotionEventBridge, PromotionIntegration, ProductionLearningLifecycle
from .admin_state_sqlite import SQLiteAdminStateError, SQLiteAdministrativeBackend
from .admin_migration import MIGRATION_SCHEMA, AdministrativeMigrationError, OperatorMigrationModeSource, verify_signed_mode_change_receipt, MigrationCheck, AdministrativeActionRouter, AdministrativeMigrationAdapter
from .metadata_translator import MetadataTranslationError, TranslationResult, translate_metadata
from .portable_launcher import PortableLayout, PortableLaunchError, resolve_layout, startup_probe
from .bridge_integration import BridgeIntegrationCoordinator, BridgeIntegrationError, IntegrationRecord
from .gateway_fixture import GatewayFixture, GatewayFixtureError
from .sandbox_backend import BackendConformanceResult, SandboxBackend, inspect_backend, run_conformance
from .sandbox_bwrap import BubblewrapBackend, SandboxResult, SandboxUnavailable
from .sandbox_macos import MacOSSandboxBackend
from .process_control import terminate_process_tree
from .workspaces import MergeAuthorization, PatchReviewStore
__all__.extend(["CONTRACT_VERSION", "UIContractError", "UIEnvelope", "failure", "health_payload", "model_payload", "new_request_id", "success", "HealthServer", "CAPABILITY_KEYS", "ModelDescriptor", "ProviderAdapterSpec", "ProviderDescriptor", "ProviderRegistry", "ProviderRegistryError", "SUPPORTED_PROVIDER_KINDS", "adapter_spec", "BridgeCandidate", "BridgeDiscovery", "BridgeStatus", "ChildRuntimeSupervisor", "RuntimeStatus", "UserDataPaths", "user_data_paths", "HERMES_FORBIDDEN_SCOPE_PREFIXES", "HERMES_SUPPORTED_SCOPES", "HermesGatewayAdapter", "HermesGatewayConfig", "HermesGatewayError", "CompatibilityResult", "DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES", "DeepSeekHarnessAdapter", "DeepSeekHarnessConfig", "DeepSeekHarnessError", "SelectionResult", "select_model", "ALLOWED_CAPABILITIES", "ALLOWED_PLATFORMS", "MANIFEST_FILENAME", "MANIFEST_FORMAT_VERSION", "SkillManifest", "SkillManifestError", "digest_files", "ImportAssessment", "SafeSkillImport", "SkillImportError", "SkillStore", "SkillStoreError", "SkillDescriptor", "SkillDiscoveryError", "discover_skills", "ExperienceRecord", "ExperienceReuseError", "ExperienceReuseSelector", "ReuseDecision", "ExperienceReceipt", "HoldoutEvaluation", "PromotionProposal", "LearningPromotionError", "DurablePromotionState", "LearningPromotionPipeline", "EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "RuntimePolicySimulator", "OwnershipPolicySimulator", "OperatorSessionRegistry", "ReviewerAuthorizationStore", "OperatorAuthContext", "PromotionApprovalAction", "PromotionActionReceipt", "PromotionActionExecutor", "SignedMutationReceipt", "verify_signed_mutation_receipt", "CoordinatedMutationJournal", "OperatorSessionAction", "OperatorSessionActionExecutor", "AdministrativePolicyStore", "SQLiteAdminStateError", "SQLiteAdministrativeBackend", "MIGRATION_SCHEMA", "AdministrativeMigrationError", "OperatorMigrationModeSource", "verify_signed_mode_change_receipt", "MigrationCheck", "AdministrativeActionRouter", "AdministrativeMigrationAdapter", "PolicySimulation", "PromotionEventBridge", "PromotionIntegration", "ProductionLearningLifecycle", "MetadataTranslationError", "TranslationResult", "translate_metadata", "PortableLayout", "PortableLaunchError", "resolve_layout", "startup_probe", "BridgeIntegrationCoordinator", "BridgeIntegrationError", "IntegrationRecord", "GatewayFixture", "GatewayFixtureError", "MergeAuthorization", "PatchReviewStore", "BackendConformanceResult", "SandboxBackend", "inspect_backend", "run_conformance", "BubblewrapBackend", "SandboxResult", "SandboxUnavailable", "MacOSSandboxBackend", "terminate_process_tree"])
