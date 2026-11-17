"""End-to-end governed multi-agent work-product workflow."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .event_store import EventStore
from .multi_agent_runtime import MultiAgentCoordinator, MultiAgentError
from .work_product_benchmark import WorkProductBenchmarkError, WorkProductCommitMarker, WorkProductCommitMarkerLedger
from .workspaces import MergeAuthorization, WorkspaceError

WORK_PRODUCT_SCHEMA = "noesis.multi-agent-work-product.v1"


class WorkProductError(ValueError):
    """Raised when a delegated work product violates workflow policy."""


@dataclass(frozen=True)
class WorkProductEnvelope:
    task_id: str
    agent_id: str
    workspace_id: str
    base_snapshot_id: str
    head_snapshot_id: str
    summary: str
    artifact_digest: str
    result_type: str = "workspace_patch"
    schema_version: str = WORK_PRODUCT_SCHEMA

    def __post_init__(self) -> None:
        for value, field in ((self.task_id, "task_id"), (self.agent_id, "agent_id"), (self.workspace_id, "workspace_id"), (self.base_snapshot_id, "base_snapshot_id"), (self.head_snapshot_id, "head_snapshot_id"), (self.artifact_digest, "artifact_digest")):
            if not value:
                raise WorkProductError(field + "_required")
        if self.schema_version != WORK_PRODUCT_SCHEMA:
            raise WorkProductError("unsupported_work_product_schema")
        if self.result_type not in {"workspace_patch", "analysis", "test_report"}:
            raise WorkProductError("unsupported_result_type")

    @property
    def product_id(self) -> str:
        raw = json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "product:" + hashlib.sha256(raw).hexdigest()[:32]

    def to_mapping(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "task_id": self.task_id, "agent_id": self.agent_id, "workspace_id": self.workspace_id, "base_snapshot_id": self.base_snapshot_id, "head_snapshot_id": self.head_snapshot_id, "summary": self.summary[:4096], "artifact_digest": self.artifact_digest, "result_type": self.result_type}


class MultiAgentWorkProductLoop:
    """Coordinate delegated products without implicit merge or cross-agent access."""
    def __init__(self, coordinator: MultiAgentCoordinator, event_path: str, marker_ledger: WorkProductCommitMarkerLedger | None = None):
        self.coordinator = coordinator
        self.events = EventStore(event_path)
        self.marker_ledger = marker_ledger

    def _existing(self, product_id: str, event_type: str | None = None) -> Mapping[str, Any] | None:
        for event in self.events.iter_events():
            if event_type is not None and event.get("type") != event_type:
                continue
            payload = event.get("payload") or {}
            if payload.get("product_id") == product_id:
                return dict(payload)
        return None

    @staticmethod
    def _execution_evidence(execution_result: Any) -> Mapping[str, Any]:
        if isinstance(execution_result, Mapping):
            status = execution_result.get("status", "completed")
            request_id = str(execution_result.get("request_id", ""))
            receipt_id = str(execution_result.get("receipt_id", ""))
            outcome = str(execution_result.get("outcome", ""))
            sandboxed = bool(execution_result.get("sandboxed", False))
        else:
            status = getattr(execution_result, "status", "")
            receipt = getattr(execution_result, "receipt", None)
            request_id = str(getattr(execution_result, "request_id", ""))
            receipt_id = str(getattr(receipt, "receipt_id", ""))
            outcome = str(getattr(receipt, "outcome", ""))
            sandboxed = bool(getattr(execution_result, "sandboxed", False))
        if status != "completed":
            raise WorkProductError("delegated_execution_not_completed")
        if outcome != "committed" or not receipt_id:
            raise WorkProductError("signed_execution_receipt_required")
        if not request_id:
            raise WorkProductError("execution_identity_required")
        return {"request_id": request_id, "receipt_id": receipt_id, "outcome": "committed", "sandboxed": sandboxed}

    def execute_and_submit(self, *, runtime: Any, request: Any, task_id: str, agent_id: str, base_snapshot_id: str, head_snapshot_id: str, summary: str = "", result_type: str = "workspace_patch") -> WorkProductEnvelope | Mapping[str, Any]:
        claim = self.coordinator._claims.get(task_id)
        if claim is None or claim.agent_id != agent_id:
            raise WorkProductError("claim_owner_required")
        request_workspace = Path(str(getattr(request, "workspace", ""))).expanduser().resolve()
        claimed_workspace = self.coordinator.workspaces.path(claim.workspace_id).resolve()
        if request_workspace != claimed_workspace:
            raise WorkProductError("execution_workspace_mismatch")
        runner = getattr(runtime, "run", None)
        if not callable(runner):
            raise WorkProductError("execution_runtime_required")
        result = runner(request)
        execution = self._execution_evidence(result)
        receipt_store = getattr(runtime, "receipt_store", None)
        if receipt_store is None or not callable(getattr(receipt_store, "get", None)):
            raise WorkProductError("execution_receipt_store_required")
        stored_receipt = receipt_store.get(execution["receipt_id"])
        if stored_receipt is None or str(getattr(stored_receipt, "receipt_id", "")) != execution["receipt_id"] or str(getattr(stored_receipt, "outcome", "")) != "committed":
            raise WorkProductError("execution_receipt_not_verified")
        return self.submit(task_id=task_id, agent_id=agent_id, base_snapshot_id=base_snapshot_id, head_snapshot_id=head_snapshot_id, summary=summary, result_type=result_type, execution_evidence=execution)

    def submit(self, *, task_id: str, agent_id: str, base_snapshot_id: str, head_snapshot_id: str, summary: str = "", artifact_digest: str = "", result_type: str = "workspace_patch", execution_evidence: Mapping[str, Any] | None = None) -> WorkProductEnvelope | Mapping[str, Any]:
        claim = self.coordinator._claims.get(task_id)
        if claim is None or claim.agent_id != agent_id:
            raise WorkProductError("claim_owner_required")
        if claim.workspace_id != self.coordinator.workspaces.get_snapshot(head_snapshot_id).workspace_id:
            raise WorkProductError("work_product_workspace_mismatch")
        base = self.coordinator.workspaces.get_snapshot(base_snapshot_id)
        head = self.coordinator.workspaces.get_snapshot(head_snapshot_id)
        if base.workspace_id != claim.workspace_id or head.workspace_id != claim.workspace_id:
            raise WorkProductError("work_product_workspace_mismatch")
        if head.parent_snapshot_id != base.snapshot_id:
            raise WorkProductError("work_product_base_mismatch")
        if not artifact_digest:
            artifact_digest = "sha256:" + hashlib.sha256(json.dumps([entry.as_dict() for entry in head.files], sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        execution = None if execution_evidence is None else dict(self._execution_evidence(execution_evidence))
        envelope = WorkProductEnvelope(task_id, agent_id, claim.workspace_id, base_snapshot_id, head_snapshot_id, str(summary)[:4096], artifact_digest, result_type)
        existing = self._existing(envelope.product_id, "work_product_submitted")
        if existing is not None:
            return existing
        self.coordinator.complete_for_review(task_id, agent_id, summary)
        payload = {"schema_version": WORK_PRODUCT_SCHEMA, "product_id": envelope.product_id, **envelope.to_mapping(), "status": "needs_review"}
        if execution is not None:
            payload["execution"] = execution
        self.events.append("work_product_submitted", payload, event_id="work-product-submit:" + envelope.product_id)
        return envelope

    def review(self, envelope: WorkProductEnvelope, *, reviewer_id: str, decision: str, current_base_snapshot_id: str) -> Mapping[str, Any]:
        if reviewer_id == envelope.agent_id:
            raise WorkProductError("independent_reviewer_required")
        if reviewer_id not in self.coordinator._agents:
            raise WorkProductError("reviewer_not_registered")
        if decision not in {"approved", "rejected"}:
            raise WorkProductError("invalid_work_product_review")
        existing = self._existing(envelope.product_id, "work_product_reviewed")
        if existing is not None:
            if existing.get("reviewer_id") == reviewer_id and existing.get("decision") == decision:
                return {"status": "replayed", "result": existing}
            raise WorkProductError("work_product_review_conflict")
        proposal = self.coordinator.workspaces.propose_patch(envelope.base_snapshot_id, envelope.head_snapshot_id)
        reviewed = self.coordinator.workspaces.review(proposal, decision)
        payload: dict[str, Any] = {"schema_version": WORK_PRODUCT_SCHEMA, "product_id": envelope.product_id, "task_id": envelope.task_id, "reviewer_id": reviewer_id, "decision": decision, "proposal_id": reviewed.proposal_id, "current_base_snapshot_id": current_base_snapshot_id, "status": decision}
        if decision == "approved":
            try:
                authorization = self.coordinator.workspaces.authorize_merge(reviewed, reviewer=reviewer_id, current_base_snapshot_id=current_base_snapshot_id)
            except WorkspaceError as exc:
                raise WorkProductError(str(exc)) from exc
            payload["authorization_digest"] = authorization.authorization_digest
            payload["merge_authorized"] = True
        else:
            payload["merge_authorized"] = False
        self.events.append("work_product_reviewed", payload, event_id="work-product-review:" + envelope.product_id)
        return payload

    def commit(self, envelope: WorkProductEnvelope, *, authorization: MergeAuthorization) -> Mapping[str, Any]:
        if authorization.proposal_id == "" or authorization.workspace_id != envelope.workspace_id or authorization.base_snapshot_id != envelope.base_snapshot_id or authorization.head_snapshot_id != envelope.head_snapshot_id:
            raise WorkProductError("merge_authorization_mismatch")
        existing = self._existing(envelope.product_id, "work_product_committed")
        if existing is not None:
            return {"status": "replayed", "result": existing}
        reviews = [event.get("payload") or {} for event in self.events.iter_events() if event.get("type") == "work_product_reviewed" and (event.get("payload") or {}).get("product_id") == envelope.product_id]
        if not reviews or not reviews[-1].get("merge_authorized") or reviews[-1].get("proposal_id") != authorization.proposal_id:
            raise WorkProductError("merge_authorization_required")
        task = self.coordinator.tasks.task(envelope.task_id)
        if task.state != "review":
            raise WorkProductError("task_not_in_review")
        if self.marker_ledger is not None:
            marker = WorkProductCommitMarker(envelope.product_id, envelope.task_id, envelope.agent_id, envelope.workspace_id, envelope.base_snapshot_id, envelope.head_snapshot_id, envelope.artifact_digest, authorization.authorization_digest)
            try:
                self.marker_ledger.record(marker)
            except WorkProductBenchmarkError as exc:
                raise WorkProductError(str(exc)) from exc
        self.coordinator.tasks.transition_task(envelope.task_id, "committed", reason="work_product_committed")
        payload = {"schema_version": WORK_PRODUCT_SCHEMA, "product_id": envelope.product_id, "task_id": envelope.task_id, "authorization_digest": authorization.authorization_digest, "status": "committed", "files_applied": False}
        self.events.append("work_product_committed", payload, event_id="work-product-commit:" + envelope.product_id)
        return payload

    def resume(self, session_id: str) -> Mapping[str, Any]:
        view = self.coordinator.resume(session_id)
        products = tuple(event.get("payload") or {} for event in self.events.iter_events() if (event.get("payload") or {}).get("task_id") in {task.task_id for task in view["tasks"]})
        result: dict[str, Any] = {**view, "work_products": products}
        if self.marker_ledger is not None:
            markers = self.marker_ledger.markers()
            result["commit_markers"] = {"count": len(markers), "last_marker_id": markers[-1].marker_id if markers else None}
        return result


__all__ = ["WORK_PRODUCT_SCHEMA", "WorkProductEnvelope", "WorkProductError", "MultiAgentWorkProductLoop"]
