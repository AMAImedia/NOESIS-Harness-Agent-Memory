"""Portable launch boundary for Windows/macOS NOESIS distributions.

Patterns are borrowed from portable application layouts, Windows command
launchers, NOESIS user-data separation, and the read-only control plane. The
launcher starts only the local HealthServer; it does not install packages,
invoke models, execute skill entrypoints, or require Node/npm.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from .admin_migration import OperatorMigrationModeSource
from .admin_state_sqlite import SQLiteAdministrativeBackend
from .health_server import HealthServer
from .learning_promotion import LearningPromotionPipeline
from .promotion_integration import AdministrativePolicyStore, CoordinatedMutationJournal, EvaluatorRegistry, OperatorSessionAction, OperatorSessionActionExecutor, OperatorAuthContext, OperatorSessionRegistry, OwnershipPolicySimulator, ProductionLearningLifecycle, PromotionActionExecutor, PromotionEventBridge, PromotionIntegration, ReviewerAuthorizationStore
from .provider_registry import ProviderRegistry
from .task_session_api import TaskSessionStore
from .user_data import user_data_paths


class PortableLaunchError(ValueError):
    """Raised when portable install/data boundaries are unsafe."""


@dataclass(frozen=True)
class PortableLayout:
    install_root: Path
    data_root: Path
    runtime_root: Path
    logs_root: Path

    def ensure(self) -> "PortableLayout":
        for path in (self.install_root, self.data_root, self.runtime_root, self.logs_root):
            path.mkdir(parents=True, exist_ok=True)
        return self


def resolve_layout(install_root: str, data_root: Optional[str] = None, env: Optional[Mapping[str, str]] = None, platform: Optional[str] = None, home: Optional[str] = None) -> PortableLayout:
    install = Path(install_root).expanduser().resolve()
    if not install.is_dir() and install.exists():
        raise PortableLaunchError("install_root must be a directory")
    environment = dict(os.environ if env is None else env)
    selected = data_root or environment.get("NOESIS_HOME")
    if selected:
        data = Path(selected).expanduser().resolve()
    elif platform in {"darwin", "win32"}:
        data = user_data_paths(env=environment, platform=platform, home=home, create=False).root
    else:
        data = install / "data"
    if data == install or install in data.parents:
        # install/data is permitted for a self-contained USB layout; code and data remain separate.
        if data == install:
            raise PortableLaunchError("data_root must be separate from install_root")
    runtime = data / "runtime"
    logs = data / "logs"
    return PortableLayout(install, data, runtime, logs)


def startup_probe(layout: PortableLayout, *, host: str = "127.0.0.1", port: int = 0) -> Tuple[str, int]:
    """Start/stop a read-only server and verify the persistent data boundary."""
    layout.ensure()
    sentinel = layout.data_root / "state" / "portable-startup.sentinel"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("noesis-portable-started\n", encoding="utf-8")
    session_store = TaskSessionStore(str(layout.data_root / "state" / "session_events.jsonl"))
    with HealthServer(host=host, port=port, provider_registry=ProviderRegistry(), session_store=session_store) as server:
        address = server.address
    if not sentinel.is_file() or sentinel.read_text(encoding="utf-8") != "noesis-portable-started\n":
        raise PortableLaunchError("data-preservation sentinel missing")
    return address


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run NOESIS portable local-first agent control plane")
    parser.add_argument("--install-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    layout = resolve_layout(args.install_root, args.data_root)
    layout.ensure()
    session_store = TaskSessionStore(str(layout.data_root / "state" / "session_events.jsonl"))
    signing_key = os.environ.get("NOESIS_MIGRATION_SIGNING_KEY", "").encode("utf-8")
    operator_id = os.environ.get("NOESIS_OPERATOR_ID")
    operator_session_id = os.environ.get("NOESIS_OPERATOR_SESSION_ID")
    migration_source = None
    migration_backend = None
    promotion_lifecycle = None
    promotion_integration = None
    operator_session_action_handler = None
    administrative_policy_handler = None
    if len(signing_key) >= 16:
        state_root = layout.data_root / "state"
        state_root.mkdir(parents=True, exist_ok=True)
        migration_backend = SQLiteAdministrativeBackend(str(state_root / "admin.sqlite3"), signing_key=signing_key, admin_ids=(operator_id,) if operator_id else ())
        migration_source = OperatorMigrationModeSource(str(state_root / "migration_mode.jsonl"), operator_ids=(operator_id,) if operator_id else (), signing_key=signing_key, audit_backend=migration_backend)
        promotion_pipeline = LearningPromotionPipeline(str(state_root / "learning"), signing_key)
        promotion_integration = PromotionIntegration(promotion_pipeline, registry=EvaluatorRegistry(state=promotion_pipeline.durable_state))
        reviewer_store = ReviewerAuthorizationStore(str(state_root / "reviewer_events.jsonl"))
        session_registry = OperatorSessionRegistry(str(state_root / "operator_sessions.jsonl"))
        mutation_journal = CoordinatedMutationJournal(str(state_root / "admin_mutations.jsonl"))
        session_action_executor = OperatorSessionActionExecutor(session_registry, str(state_root / "operator_session_actions.jsonl"), signing_key=signing_key, journal=mutation_journal)
        operator_session_action_handler = session_action_executor.handle
        administrative_policy = AdministrativePolicyStore(str(state_root / "admin_policy.jsonl"), reviewer_store, session_registry, admin_ids=(operator_id,) if operator_id else (), signing_key=signing_key, journal=mutation_journal)
        def administrative_policy_handler(payload, context):
            action = str(payload.get("action", "")) if isinstance(payload, Mapping) else ""
            if action == "grant_reviewer":
                return administrative_policy.grant_reviewer(context, str(payload.get("operator_id", "")), str(payload.get("session_id", "")), tuple(str(item) for item in payload.get("scopes", ())))
            if action == "revoke_reviewer":
                return administrative_policy.revoke_reviewer(context, str(payload.get("operator_id", "")), str(payload.get("session_id", "")))
            raise PortableLaunchError("unsupported_administrative_policy_action")
        action_executor = PromotionActionExecutor(promotion_integration, str(state_root / "promotion_actions.jsonl"), reviewer_store=reviewer_store, session_registry=session_registry)
        runtime_policy = OwnershipPolicySimulator(session_store, lambda task_id: session_store.task(task_id).owner, scope_prefix="session:")
        promotion_lifecycle = ProductionLearningLifecycle(task_store=session_store, event_bridge=PromotionEventBridge(promotion_integration, str(state_root / "promotion_bridge.jsonl")), policy_simulator=runtime_policy.simulate, action_executor=action_executor)
    server = HealthServer(host=args.host, port=args.port, provider_registry=ProviderRegistry(), session_store=session_store, promotion_telemetry=promotion_integration if promotion_integration else None, promotion_action_handler=promotion_lifecycle.handle_operator_action if promotion_lifecycle else None, operator_session_action_handler=operator_session_action_handler, administrative_policy_handler=administrative_policy_handler, migration_mode_source=migration_source, migration_audit_provider=migration_source.mode_audit if migration_source else None, migration_mode_change_handler=migration_source.handle_action if migration_source else None, operator_id=operator_id, operator_session_id=operator_session_id, operator_scopes=("admin:migration", "admin:session", "admin:reviewers", "promotion:review") if operator_id and operator_session_id else ())
    server.start()
    print("NOESIS portable control plane listening at http://%s:%d" % server.address, flush=True)
    print("Install root: %s" % layout.install_root, flush=True)
    print("Data root: %s" % layout.data_root, flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        server.stop()


__all__ = ["PortableLayout", "PortableLaunchError", "resolve_layout", "startup_probe", "main"]
