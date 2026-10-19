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
from .execution_assurance import ASSURANCE_SCHEMA, AssuranceError, ExecutionReceipt, ExecutionReceiptStore, ExecutionRecoveryStore, artifact_manifest, build_artifact_diff_from_manifests, build_artifact_diff, create_receipt, validate_receipt_transition, validate_receipt_chain, verify_receipt
from .execution_recovery import RECOVERY_ACTION_SCHEMA, ExecutionRecoveryAction, ExecutionRecoveryError, ExecutionRecoveryExecutor
from .multi_agent_workflow import WORK_PRODUCT_SCHEMA, MultiAgentWorkProductLoop, WorkProductEnvelope, WorkProductError
from .work_product_benchmark import WorkProductBenchmarkError, WorkProductBenchmarkEvaluator, WorkProductMetrics, WorkProductOutcome
from .multi_agent_benchmark import DurableWorkloadAggregator, MultiAgentBenchmarkError, MultiAgentWorkloadRunner, RepeatedWorkloadReport, WorkloadCase, WorkloadRun
from .isolation_holdouts import ActiveDelegationLeakageSuite
from .memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore, MemoryComparisonReport, MemoryQualityCase, MemoryQualityError, MemoryQualityEvaluator, MemoryQualityMetrics, MemoryQualityOutcome, MemoryTrajectoryStep, MultiSessionMemoryQualityReport, RealMemoryReuseStressReport, build_long_context_cases, compare_baseline_nextgen, run_real_memory_reuse_stress
from .native_parity import NATIVE_PARITY_SCHEMA, NativeParityEvidence, operator_bundle, prepare_native_evidence, validate_native_artifacts
from .delegated_resume import SCHEMA_VERSION as DELEGATED_RESUME_SCHEMA, DelegationIdentity, DelegationSnapshot, DelegatedResumeError, DelegatedResumeStore
from .delegated_resume_action import SCHEMA_VERSION as DELEGATED_RESUME_ACTION_SCHEMA, DelegatedResumeAction, DelegatedResumeActionReceipt, DelegatedResumeActionError, DelegatedResumeActionExecutor, bridge_resume_callback, bridge_runtime_resume_callback
from .signed_evidence_aggregator import SCHEMA_VERSION as SIGNED_EVIDENCE_AGGREGATE_SCHEMA, AggregateEvidence, SignedEvidenceAggregationError, SignedEvidenceAggregator, sign_evidence, verify_evidence
from .report_bundle import SCHEMA_VERSION as SIGNED_REPORT_BUNDLE_SCHEMA, SCHEMA_VERSION_WITH_RECEIPTS as SIGNED_REPORT_BUNDLE_WITH_RECEIPTS_SCHEMA, DOMAINS as SIGNED_REPORT_BUNDLE_DOMAINS, RECEIPT_DOMAIN as SIGNED_REPORT_BUNDLE_RECEIPT_DOMAIN, DOMAINS_WITH_RECEIPTS as SIGNED_REPORT_BUNDLE_DOMAINS_WITH_RECEIPTS, build_report_bundle, verify_report_bundle
from .report_export_action import SCHEMA_VERSION as REPORT_EXPORT_ACTION_SCHEMA, RECEIPT_SCHEMA as REPORT_EXPORT_RECEIPT_SCHEMA, LIFECYCLE_SCHEMA as REPORT_EXPORT_LIFECYCLE_SCHEMA, REQUIRED_SCOPE as REPORT_EXPORT_REQUIRED_SCOPE, ReportExportAction, ReportExportActionError, ReportExportActionExecutor
from .report_export_lifecycle import lifecycle_audit_only_projection, lifecycle_audit_readiness, verify_lifecycle_events, verify_lifecycle_file
from .lifecycle_audit_ingestion import LifecycleAuditIngestionAdapter, LifecycleAuditIngestionError, build_healthserver_wiring, verify_ingestion_receipt, verify_ingestion_receipt_audit
from .evidence_projection import EVIDENCE_PROJECTION_SCHEMA, load_memory_quality_digests, load_workload_evidence, project_evidence

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
    "COMMANDS", "TASK_SESSION_SCHEMA_VERSION", "SessionRecord", "TaskRecord", "TaskSessionError", "TaskSessionStore", "STREAM_SCHEMA", "MAX_EVENT_BYTES", "CancellationToken", "SessionEventBuffer", "StreamContractError", "StreamEvent", "TaskExecutionBridge", "TaskExecutionBridgeError", "TaskExecutionReport", "TaskExecutionRequest", "ChildExecutionError", "ChildExecutionRuntime", "ExecutionRequest", "ExecutionResult", "ASSURANCE_SCHEMA", "AssuranceError", "ExecutionReceipt", "ExecutionReceiptStore", "ExecutionRecoveryStore", "artifact_manifest", "build_artifact_diff_from_manifests", "build_artifact_diff", "create_receipt", "validate_receipt_transition", "validate_receipt_chain", "verify_receipt", "RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor", "WORK_PRODUCT_SCHEMA", "MultiAgentWorkProductLoop", "WorkProductEnvelope", "WorkProductError", "WorkProductBenchmarkError", "WorkProductBenchmarkEvaluator", "WorkProductMetrics", "WorkProductOutcome", "DurableWorkloadAggregator", "MultiAgentBenchmarkError", "MultiAgentWorkloadRunner", "RepeatedWorkloadReport", "WorkloadCase", "WorkloadRun", "ActiveDelegationLeakageSuite", "DurableMemoryQualityAdapter", "DurableMemoryQualityTraceStore", "MemoryComparisonReport", "MemoryQualityCase", "MemoryQualityError", "MemoryQualityEvaluator", "MemoryQualityMetrics", "MemoryQualityOutcome", "MemoryTrajectoryStep", "MultiSessionMemoryQualityReport", "RealMemoryReuseStressReport", "build_long_context_cases", "compare_baseline_nextgen", "run_real_memory_reuse_stress", "NATIVE_PARITY_SCHEMA", "NativeParityEvidence", "operator_bundle", "prepare_native_evidence", "validate_native_artifacts", "DELEGATED_RESUME_SCHEMA", "DelegationIdentity", "DelegationSnapshot", "DelegatedResumeError", "DelegatedResumeStore", "DELEGATED_RESUME_ACTION_SCHEMA", "DelegatedResumeAction", "DelegatedResumeActionReceipt", "DelegatedResumeActionError", "DelegatedResumeActionExecutor", "bridge_resume_callback", "bridge_runtime_resume_callback", "SIGNED_EVIDENCE_AGGREGATE_SCHEMA", "AggregateEvidence", "SignedEvidenceAggregationError", "SignedEvidenceAggregator", "sign_evidence", "verify_evidence", "SIGNED_REPORT_BUNDLE_SCHEMA", "SIGNED_REPORT_BUNDLE_WITH_RECEIPTS_SCHEMA", "SIGNED_REPORT_BUNDLE_DOMAINS", "SIGNED_REPORT_BUNDLE_RECEIPT_DOMAIN", "SIGNED_REPORT_BUNDLE_DOMAINS_WITH_RECEIPTS", "build_report_bundle", "verify_report_bundle",
 "REPORT_EXPORT_ACTION_SCHEMA", "REPORT_EXPORT_RECEIPT_SCHEMA", "REPORT_EXPORT_LIFECYCLE_SCHEMA", "REPORT_EXPORT_REQUIRED_SCOPE", "ReportExportAction", "ReportExportActionError", "ReportExportActionExecutor", "verify_lifecycle_events", "verify_lifecycle_file", "lifecycle_audit_only_projection", "lifecycle_audit_readiness", "LifecycleAuditIngestionAdapter", "LifecycleAuditIngestionError", "build_healthserver_wiring", "verify_ingestion_receipt", "verify_ingestion_receipt_audit", "EVIDENCE_PROJECTION_SCHEMA", "load_workload_evidence", "load_memory_quality_digests", "project_evidence",
]

__version__ = "0.6.0"

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
from .turn_checkpoint import SCHEMA as TURN_CHECKPOINT_SCHEMA, TurnCheckpoint, TurnCheckpointError, DurableTurnCheckpointStore
from .delegation import SCHEMA as DELEGATION_SCHEMA, DelegationRequest, DelegationReceipt, DelegationError, DelegationCoordinator
from .promotion_integration import EvaluatorSpec, EvaluatorRegistry, PromotionTelemetry, RuntimePolicySimulator, OwnershipPolicySimulator, OperatorSessionRegistry, ReviewerAuthorizationStore, OperatorAuthContext, PromotionApprovalAction, PromotionActionReceipt, PromotionActionExecutor, SignedMutationReceipt, verify_signed_mutation_receipt, CoordinatedMutationJournal, OperatorSessionAction, OperatorSessionActionExecutor, AdministrativePolicyStore, PolicySimulation, PromotionEventBridge, PromotionIntegration, ProductionLearningLifecycle
from .admin_state_sqlite import SQLiteAdminStateError, SQLiteAdministrativeBackend
from .admin_migration import MIGRATION_SCHEMA, AdministrativeMigrationError, OperatorMigrationModeSource, verify_signed_mode_change_receipt, MigrationCheck, AdministrativeActionRouter, AdministrativeMigrationAdapter
from .external_identity import SCHEMA_VERSION as EXTERNAL_IDENTITY_SCHEMA, ExternalIdentityPreparationError, PreparedExternalIdentity, ExternalIdentityPreparation
from .metadata_translator import MetadataTranslationError, TranslationResult, translate_metadata
from .portable_launcher import PortableLayout, PortableLaunchError, resolve_layout, startup_probe
from .bridge_integration import BridgeIntegrationCoordinator, BridgeIntegrationError, IntegrationRecord
from .gateway_fixture import GatewayFixture, GatewayFixtureError
from .sandbox_backend import BackendConformanceResult, SandboxBackend, inspect_backend, run_conformance
from .sandbox_bwrap import BubblewrapBackend, SandboxResult, SandboxUnavailable
from .sandbox_macos import MacOSSandboxBackend
from .sandbox_windows import WindowsSandboxBackend
from .process_control import terminate_process_tree
from .workspaces import MergeAuthorization, PatchReviewStore
__all__.extend(["CONTRACT_VERSION", "UIContractError", "UIEnvelope", "failure", "health_payload", "model_payload", "new_request_id", "success", "HealthServer", "CAPABILITY_KEYS", "ModelDescriptor", "ProviderAdapterSpec", "ProviderDescriptor", "ProviderRegistry", "ProviderRegistryError", "SUPPORTED_PROVIDER_KINDS", "adapter_spec", "BridgeCandidate", "BridgeDiscovery", "BridgeStatus", "ChildRuntimeSupervisor", "RuntimeStatus", "UserDataPaths", "user_data_paths", "HERMES_FORBIDDEN_SCOPE_PREFIXES", "HERMES_SUPPORTED_SCOPES", "HermesGatewayAdapter", "HermesGatewayConfig", "HermesGatewayError", "CompatibilityResult", "DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES", "DeepSeekHarnessAdapter", "DeepSeekHarnessConfig", "DeepSeekHarnessError", "SelectionResult", "select_model", "ALLOWED_CAPABILITIES", "ALLOWED_PLATFORMS", "MANIFEST_FILENAME", "MANIFEST_FORMAT_VERSION", "SkillManifest", "SkillManifestError", "digest_files", "ImportAssessment", "SafeSkillImport", "SkillImportError", "SkillStore", "SkillStoreError", "SkillDescriptor", "SkillDiscoveryError", "discover_skills", "ExperienceRecord", "ExperienceReuseError", "ExperienceReuseSelector", "ReuseDecision", "ExperienceReceipt", "HoldoutEvaluation", "PromotionProposal", "LearningPromotionError", "DurablePromotionState", "LearningPromotionPipeline", "TURN_CHECKPOINT_SCHEMA", "TurnCheckpoint", "TurnCheckpointError", "DurableTurnCheckpointStore", "DELEGATION_SCHEMA", "DelegationRequest", "DelegationReceipt", "DelegationError", "DelegationCoordinator", "EvaluatorSpec", "EvaluatorRegistry", "PromotionTelemetry", "RuntimePolicySimulator", "OwnershipPolicySimulator", "OperatorSessionRegistry", "ReviewerAuthorizationStore", "OperatorAuthContext", "PromotionApprovalAction", "PromotionActionReceipt", "PromotionActionExecutor", "SignedMutationReceipt", "verify_signed_mutation_receipt", "CoordinatedMutationJournal", "OperatorSessionAction", "OperatorSessionActionExecutor", "AdministrativePolicyStore", "SQLiteAdminStateError", "SQLiteAdministrativeBackend", "MIGRATION_SCHEMA", "AdministrativeMigrationError", "OperatorMigrationModeSource", "verify_signed_mode_change_receipt", "MigrationCheck", "AdministrativeActionRouter", "AdministrativeMigrationAdapter", "EXTERNAL_IDENTITY_SCHEMA", "ExternalIdentityPreparationError", "PreparedExternalIdentity", "ExternalIdentityPreparation", "PolicySimulation", "PromotionEventBridge", "PromotionIntegration", "ProductionLearningLifecycle", "MetadataTranslationError", "TranslationResult", "translate_metadata", "PortableLayout", "PortableLaunchError", "resolve_layout", "startup_probe", "BridgeIntegrationCoordinator", "BridgeIntegrationError", "IntegrationRecord", "GatewayFixture", "GatewayFixtureError", "MergeAuthorization", "PatchReviewStore", "BackendConformanceResult", "SandboxBackend", "inspect_backend", "run_conformance", "BubblewrapBackend", "SandboxResult", "SandboxUnavailable", "MacOSSandboxBackend", "terminate_process_tree"])
__all__.extend(["WindowsSandboxBackend"])

# 0.6 integration batch: session-source indexing, retrieval, memory records and
# governance patterns ported from deja-vu (Go), harness-books, claude-code-book,
# wshobson/agents (Python) and qm (TypeScript). Clean-room reimplementations,
# no upstream code vendored. Provenance: docs/SESSION_INDEX_AND_GOVERNANCE.md,
# docs/third_party_provenance.json.
from .session_sources import FileKind, HarnessSpec, SessionSourceRegistry, kind_for_path, register_harness
from .inverted_index import InvertedIndex, decode_postings, encode_postings
from .inverted_index import bucket as index_bucket
from .inverted_index import bm25_score as index_bm25_score
from .inverted_index import tokenize as index_tokenize
from .retrieval_ladder import Hit, SearchTier, damerau_levenshtein, freshness_decay, rank_with_relevance_tail, search_tiered, trim_to_budget
from .retrieval_ladder import bm25_score as ladder_bm25_score
from .retrieval_ladder import tokenize as query_tokenize
from .untrusted_frame import FRAME_CLOSE, FRAME_OPEN, FRAME_TAG, UNTRUSTED_NOTICE, frame_untrusted, is_framed, neutralize_markers
from .authorization_gate import AuthorizationGate, Decision, RiskTier, Rule, pattern_matches
from .ledger_closure import LedgerClosure, LedgerError, closure_summary
from .circuit_breaker import CircuitBreaker, CircuitState, GuardedRecovery, RecoveryLadder
from .memory_index import ENTRY_MAX_CHARS, MAX_ENTRYPOINT_BYTES, MAX_ENTRYPOINT_LINES, MemoryIndex, MemoryRecord, MemoryRecordError, MemoryType, parse_record, render_record, safe_memory_path
from .frontmatter import FrontmatterError, parse_frontmatter, render_frontmatter, yaml_scalar
from .frontmatter import roundtrip as frontmatter_roundtrip
from .composite_score import Composite, Confidence, LAYER_BLENDS, Layer, Signal, confidence_from_layers, grade_for, score_composite
from .registry_reconcile import Finding, Severity, prune_plan, reconcile_directories, reconcile_registry
from .registry_reconcile import summarize as summarize_findings
from .scope_id import SCOPE_KINDS, ScopeError, WorkspaceLayer, conversation_scope, format_scope, is_cross_scope, is_entitled, layered_workspace, parse_scope, personal_scope, scope_key
__all__.extend([
    "FileKind", "HarnessSpec", "SessionSourceRegistry", "kind_for_path", "register_harness",
    "InvertedIndex", "decode_postings", "encode_postings", "index_bucket", "index_bm25_score", "index_tokenize",
    "Hit", "SearchTier", "damerau_levenshtein", "freshness_decay", "rank_with_relevance_tail", "search_tiered", "trim_to_budget", "ladder_bm25_score", "query_tokenize",
    "FRAME_CLOSE", "FRAME_OPEN", "FRAME_TAG", "UNTRUSTED_NOTICE", "frame_untrusted", "is_framed", "neutralize_markers",
    "AuthorizationGate", "Decision", "RiskTier", "Rule", "pattern_matches",
    "LedgerClosure", "LedgerError", "closure_summary",
    "CircuitBreaker", "CircuitState", "GuardedRecovery", "RecoveryLadder",
    "ENTRY_MAX_CHARS", "MAX_ENTRYPOINT_BYTES", "MAX_ENTRYPOINT_LINES", "MemoryIndex", "MemoryRecord", "MemoryRecordError", "MemoryType", "parse_record", "render_record", "safe_memory_path",
    "FrontmatterError", "parse_frontmatter", "render_frontmatter", "yaml_scalar", "frontmatter_roundtrip",
    "Composite", "Confidence", "LAYER_BLENDS", "Layer", "Signal", "confidence_from_layers", "grade_for", "score_composite",
    "Finding", "Severity", "prune_plan", "reconcile_directories", "reconcile_registry", "summarize_findings",
    "SCOPE_KINDS", "ScopeError", "WorkspaceLayer", "conversation_scope", "format_scope", "is_cross_scope", "is_entitled", "layered_workspace", "parse_scope", "personal_scope", "scope_key",
])

# 0.6 integration batch, wave 2: loop/knowledge state, session sync, retrieval
# plumbing, authority and scoring primitives ported from deja-vu, harness-books,
# claude-code-book, wshobson/agents, qm and AI-Builder-Club/skills.
from .observation_log import LOG_PREFIX, TIMELINE_HEADING, ObservationLog, content_key
from .completion_sentinel import DONE_SUFFIX, LEASE_SUFFIX, READY_SUFFIX, RESULT_SUFFIX, ResourceLease, SentinelTimeout, StepMarker, TurnSentinel
from .source_refresh import MANIFEST_VERSION, FileState, ManifestCache, RefreshPlan, plan_all, plan_refresh, prefix_sample
from .source_refresh import observe as observe_file
from .sync_watermark import DedupeLedger, ExportBatch, PeerWatermarks, SyncExchange, export_since, imported_id, record_identity, watermark_key
from .atomic_write import AtomicWriteError, atomic_append_line, atomic_write_bytes, atomic_write_text, prune_temp_files, unique_temp_name
from .atomic_write import read_text as atomic_read_text
from .tool_dialect import CANONICAL_KEYS, DEFAULT_DIALECT_NAME, DIALECTS, ToolDialect, denormalize_tool_args, dialect_for, dialects, normalize_tool_args, tool_name_for
from .parallel_parse import DEFAULT_WORKER_CAP, ParseFailure, bounded_fanout, ordered_fanout, parse_files_parallel
from .fork_isolation import CacheSafeSnapshot, ChildScope, ForkCoordinator, ForkError
from .fork_isolation import Status as ForkStatus
from .fork_isolation import canonical_digest as fork_canonical_digest
from .instruction_layers import PRECEDENCE, InstructionFragment, InstructionStack, LayerSource, assert_no_replacement
from .hook_engine import Hook, HookBudgetError, HookEngine, HookEvent, HookResult
from .extraction_queue import ExtractionCoordinator, ExtractionWorker
from .shared_board import SharedBoard, TaskNotification, WriteConflict, safe_name
from .shared_board import Confidence as BoardConfidence
from .projection_adapters import AdapterRegistry, Consumer, JsonAdapter, MarkdownAdapter, TomlAdapter, VALID_SEVERITIES, default_registry, emit_all, slugify
from .projection_adapters import Finding as ProjectionFinding
from .projection_adapters import canonical_digest as projection_canonical_digest
from .elo_rank import DEFAULT_RATING, K_FACTOR, BootstrapCI, ConfidenceTier, EloTable, GoldCorpus, Match, bootstrap_ci, expected_score, select_references, update_ratings
from .namespace_registry import ALLOWED_RE, MAX_NAME_LEN, SEPARATOR, NamespaceError, NamespaceRegistry, qualified, sanitize
from .blob_store import BlobStore, BlobStoreError, digest_bytes, sha256_shard
from .acl_store import AclError, AclStore, Grant, Membership, MembershipAcl, Permission
from .capability_token import Capability, TokenError, b64d, b64e, canonical_bytes, capability_grants, mint_capability, verify_capability
from .leader_lease import KeyedQueue, LeaderLease, LeaseError, Sweeper
from .memory_revisions import MemoryRevisions, Revision, RevisionConflict, mark_untrusted, read_revision_log
from .memory_revisions import SCHEMA_VERSION as MEMORY_REVISIONS_SCHEMA_VERSION
from .loop_contract import Cadence, GateCondition, LoopContract, LoopRegistry, LoopStatus, kebab_case
from .verification_ledger import DEFAULT_MARKER, SECONDS_PER_DAY, AppliedChange, FixLoop, MarkerGuard, VerificationLedger
from .verification_ledger import LedgerError as VerificationLedgerError
from .metrics_collector import MetricCollector, MetricError, MetricPoint, MetricReport, build_report, safe_series
from .loop_state import LoopState, LoopStateError, LoopStateStore, Understanding
from .lesson_cue import CueDecision, CueMatch, CueSelector, Lesson, LessonCueError, LessonJournal, LessonJournalConflict, LessonRecord
from .lesson_cue import SCHEMA_VERSION as LESSON_CUE_SCHEMA_VERSION
from .lesson_cue import STATUS_ACTIVE, STATUS_CANDIDATE, STATUS_RETIRED, STATUS_SUPERSEDED
from .lesson_cue import build_lesson, cue_score, extract_lesson, match_tier, meaningful_tokens, normalize_domain
from .domain_library import DomainLibrary, DomainLibraryError, DomainLibraryRoot, LibraryEntry, LibraryReport, domain_dir, publish_lesson, slug
from .domain_library import SCHEMA_VERSION as DOMAIN_LIBRARY_SCHEMA_VERSION
from .blind_select import BlindSelectError, Candidate, Contrast, Selection, SelectionTask, anonym_id, assign_ids, build_contrast, render_pool, reverse_ids, run_selection, trivial_selection, write_candidates
from .blind_select import SCHEMA_VERSION as BLIND_SELECT_SCHEMA_VERSION
from .budget import BudgetIdentityError, RunEntry, RunLedger, expected_rollouts, expected_sessions
from .forget import ERASED_MARKER, REASONS, REASON_LEGAL_REQUEST, REASON_RETENTION, REASON_USER_REQUEST, CipherCapability, ForgetError, ForgetReceipt, Forger, Predicate, ReceiptLog, ResidueReport, StoreResult, build_predicate, cipher_capability, content_digest, fsync_paths, harden_sqlite, normalize, scan_raw_bytes, scrub_sidecars, sqlite_sidecars, sweep as forget_sweep
from .aead import AuthenticationError, AeadError, aead_decrypt, aead_encrypt, selftest as aead_selftest
from .aead import SCHEMA_VERSION as AEAD_SCHEMA_VERSION
from .cell_cipher import Cell, CellCipher, CellCipherError, ErasureReceipt, KeyDestroyed, KeyStore, ReceiptJournal
from .cell_cipher import CELL_ERASED, CELL_SEALED, ERASURE_ACCESS_CONTROL, ERASURE_CRYPTOGRAPHIC
from .cell_cipher import SCHEMA_VERSION as CELL_CIPHER_SCHEMA_VERSION
from .forget import SCHEMA_VERSION as FORGET_SCHEMA_VERSION
__all__.extend([
    "LOG_PREFIX", "TIMELINE_HEADING", "ObservationLog", "content_key",
    "DONE_SUFFIX", "LEASE_SUFFIX", "READY_SUFFIX", "RESULT_SUFFIX", "ResourceLease", "SentinelTimeout", "StepMarker", "TurnSentinel",
    "MANIFEST_VERSION", "FileState", "ManifestCache", "RefreshPlan", "plan_all", "plan_refresh", "prefix_sample", "observe_file",
    "DedupeLedger", "ExportBatch", "PeerWatermarks", "SyncExchange", "export_since", "imported_id", "record_identity", "watermark_key",
    "AtomicWriteError", "atomic_append_line", "atomic_write_bytes", "atomic_write_text", "prune_temp_files", "unique_temp_name", "atomic_read_text",
    "CANONICAL_KEYS", "DEFAULT_DIALECT_NAME", "DIALECTS", "ToolDialect", "denormalize_tool_args", "dialect_for", "dialects", "normalize_tool_args", "tool_name_for",
    "DEFAULT_WORKER_CAP", "ParseFailure", "bounded_fanout", "ordered_fanout", "parse_files_parallel",
    "CacheSafeSnapshot", "ChildScope", "ForkCoordinator", "ForkError", "ForkStatus", "fork_canonical_digest",
    "PRECEDENCE", "InstructionFragment", "InstructionStack", "LayerSource", "assert_no_replacement",
    "Hook", "HookBudgetError", "HookEngine", "HookEvent", "HookResult",
    "ExtractionCoordinator", "ExtractionWorker",
    "SharedBoard", "TaskNotification", "WriteConflict", "safe_name", "BoardConfidence",
    "AdapterRegistry", "Consumer", "JsonAdapter", "MarkdownAdapter", "TomlAdapter", "VALID_SEVERITIES", "default_registry", "emit_all", "slugify", "ProjectionFinding", "projection_canonical_digest",
    "DEFAULT_RATING", "K_FACTOR", "BootstrapCI", "ConfidenceTier", "EloTable", "GoldCorpus", "Match", "bootstrap_ci", "expected_score", "select_references", "update_ratings",
    "ALLOWED_RE", "MAX_NAME_LEN", "SEPARATOR", "NamespaceError", "NamespaceRegistry", "qualified", "sanitize",
    "BlobStore", "BlobStoreError", "digest_bytes", "sha256_shard",
    "AclError", "AclStore", "Grant", "Membership", "MembershipAcl", "Permission",
    "Capability", "TokenError", "b64d", "b64e", "canonical_bytes", "capability_grants", "mint_capability", "verify_capability",
    "KeyedQueue", "LeaderLease", "LeaseError", "Sweeper",
    "MemoryRevisions", "Revision", "RevisionConflict", "mark_untrusted", "read_revision_log", "MEMORY_REVISIONS_SCHEMA_VERSION",
    "Cadence", "GateCondition", "LoopContract", "LoopRegistry", "LoopStatus", "kebab_case",
    "DEFAULT_MARKER", "SECONDS_PER_DAY", "AppliedChange", "FixLoop", "MarkerGuard", "VerificationLedger", "VerificationLedgerError",
    "MetricCollector", "MetricError", "MetricPoint", "MetricReport", "build_report", "safe_series",
    "LoopState", "LoopStateError", "LoopStateStore", "Understanding",
    "CueDecision", "CueMatch", "CueSelector", "Lesson", "LessonCueError", "LessonJournal", "LessonJournalConflict", "LessonRecord",
    "LESSON_CUE_SCHEMA_VERSION", "STATUS_ACTIVE", "STATUS_CANDIDATE", "STATUS_RETIRED", "STATUS_SUPERSEDED",
    "build_lesson", "cue_score", "extract_lesson", "match_tier", "meaningful_tokens", "normalize_domain",
    "DomainLibrary", "DomainLibraryError", "DomainLibraryRoot", "LibraryEntry", "LibraryReport", "domain_dir", "publish_lesson", "slug",
    "DOMAIN_LIBRARY_SCHEMA_VERSION",
    "BlindSelectError", "Candidate", "Contrast", "Selection", "SelectionTask", "anonym_id", "assign_ids", "build_contrast", "render_pool", "reverse_ids", "run_selection", "trivial_selection", "write_candidates",
    "BLIND_SELECT_SCHEMA_VERSION",
    "BudgetIdentityError", "RunEntry", "RunLedger", "expected_rollouts", "expected_sessions",
    "ERASED_MARKER", "REASONS", "REASON_LEGAL_REQUEST", "REASON_RETENTION", "REASON_USER_REQUEST",
    "ForgetError", "ForgetReceipt", "Forger", "Predicate", "ReceiptLog", "ResidueReport", "StoreResult",
    "build_predicate", "content_digest", "normalize", "forget_sweep", "FORGET_SCHEMA_VERSION",
    "CipherCapability", "cipher_capability",
    "harden_sqlite", "scan_raw_bytes", "scrub_sidecars", "sqlite_sidecars", "fsync_paths",
    "AuthenticationError", "AeadError", "aead_decrypt", "aead_encrypt", "aead_selftest", "AEAD_SCHEMA_VERSION",
    "Cell", "CellCipher", "CellCipherError", "ErasureReceipt", "KeyDestroyed", "KeyStore", "ReceiptJournal",
    "CELL_ERASED", "CELL_SEALED", "ERASURE_ACCESS_CONTROL", "ERASURE_CRYPTOGRAPHIC", "CELL_CIPHER_SCHEMA_VERSION",
])
