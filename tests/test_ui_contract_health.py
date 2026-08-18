import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from noesis_harness.health_server import HealthServer
from noesis_harness.admin_migration import OperatorMigrationModeSource, verify_signed_mode_change_receipt
from noesis_harness.ui_contract import CONTRACT_VERSION, UIContractError, failure, health_payload, model_payload, success


class UIContractTests(unittest.TestCase):
    def test_success_redacts_secrets_and_is_deterministic(self):
        envelope = success({"model": "local", "api_key": "secret-value", "nested": {"password": "hidden"}}, request_id="fixed")
        payload = envelope.to_dict()
        self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
        self.assertEqual(payload["data"]["api_key"], "[REDACTED]")
        self.assertEqual(payload["data"]["nested"]["password"], "[REDACTED]")
        self.assertEqual(envelope.to_json(), envelope.to_json())
        self.assertNotIn("secret-value", envelope.to_json())

    def test_health_degraded_when_optional_capabilities_are_unavailable(self):
        envelope = health_payload(
            runtime_version="0.1",
            readiness="ready",
            binding="127.0.0.1:0",
            capabilities={"ui_contract": "ready", "hermes_adapter": "unavailable"},
            unavailable_reasons=("hermes_adapter_unavailable",),
        )
        self.assertEqual(envelope.status, "degraded")
        self.assertEqual(envelope.data["readiness"], "ready")

    def test_models_require_id_provider_and_valid_status(self):
        envelope = model_payload(({"id": "m", "provider": "ollama", "capabilities": {"tools": False}},))
        self.assertEqual(envelope.data["models"][0]["id"], "m")
        with self.assertRaises(UIContractError):
            model_payload(({"provider": "ollama"},))
        with self.assertRaises(UIContractError):
            success(status="not-a-status")
        with self.assertRaises(UIContractError):
            failure("ready", "bad", "bad")


class HealthServerTests(unittest.TestCase):
    def _request(self, method, path):
        request = urllib.request.Request(path, method=method)
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            error.close()
            return error.code, payload

    def test_loopback_health_response_and_clean_shutdown(self):
        server = HealthServer(runtime_version="test", port=0)
        address = server.start()
        try:
            self.assertEqual(address[0], "127.0.0.1")
            code, payload = self._request("GET", f"http://{address[0]}:{address[1]}/health")
            self.assertEqual(code, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
            self.assertEqual(payload["data"]["readiness"], "ready")
        finally:
            server.stop()
        self.assertEqual(server._thread, None)

    def test_operator_owned_migration_readiness_is_exposed_at_startup(self):
        source = OperatorMigrationModeSource('/tmp/noesis-test-migration-source-' + str(time.time_ns()), operator_ids=('operator-1',), signing_key=b'readiness-signing-key')
        server = HealthServer(port=0, migration_mode_source=source)
        self.assertEqual(server._migration_readiness_snapshot()['mode'], 'legacy')
        source.set_mode('dual_read', operator_id='operator-1', reason='operator verification')
        self.assertEqual(server._migration_readiness_snapshot()['status'], 'dual_read')
        with server:
            base = f'http://{server.address[0]}:{server.address[1]}'
            code, payload = self._request('GET', base + '/api/readiness')
            self.assertEqual(code, 200)
            readiness = payload['data']['migration_readiness']
            self.assertEqual(readiness['mode'], 'dual_read')
            self.assertFalse(readiness['blocked'])
            self.assertTrue(readiness['rollback_available'])
        source.rollback(operator_id='operator-1', reason='restore legacy default')
        self.assertEqual(source.readiness()['mode'], 'legacy')
        self.assertFalse(source.readiness()['rollback_available'])

    def test_authenticated_mode_change_returns_signed_receipt(self):
        key = b'ui-migration-signing-key'
        source = OperatorMigrationModeSource(tempfile.mktemp(), operator_ids=('operator-1',), signing_key=key)
        server = HealthServer(port=0, migration_mode_source=source, migration_mode_change_handler=source.handle_action, operator_id='operator-1', operator_session_id='operator-session', operator_scopes=('admin:migration',))
        payload = {'schema_version': 'noesis.migration-mode-action.v1', 'action_id': 'ui-mode-action-1', 'action': 'set_mode', 'mode': 'dual_read', 'operator_id': 'operator-1', 'reason': 'operator readiness test'}
        with server:
            base = f'http://{server.address[0]}:{server.address[1]}'
            request = urllib.request.Request(base + '/api/admin/migration-mode', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(request, timeout=2) as response:
                result = json.loads(response.read().decode('utf-8'))
            receipt = result['data']['result']
            self.assertTrue(verify_signed_mode_change_receipt(receipt, key))
            self.assertEqual(receipt['mode'], 'dual_read')
            readiness_code, readiness_payload = self._request('GET', base + '/api/readiness')
            self.assertEqual(readiness_code, 200)
            self.assertEqual(readiness_payload['data']['migration_readiness']['mode'], 'dual_read')
        tampered = dict(receipt)
        tampered['mode'] = 'sqlite'
        self.assertFalse(verify_signed_mode_change_receipt(tampered, key))

    def test_mode_change_requires_authenticated_operator_context(self):
        source = OperatorMigrationModeSource(tempfile.mktemp(), signing_key=b'ui-migration-signing-key')
        server = HealthServer(port=0, migration_mode_source=source, migration_mode_change_handler=source.handle_action)
        payload = {'schema_version': 'noesis.migration-mode-action.v1', 'action_id': 'ui-mode-action-denied', 'action': 'set_mode', 'mode': 'dual_read', 'operator_id': 'operator-1', 'reason': 'denied test'}
        with server:
            request = urllib.request.Request(f'http://{server.address[0]}:{server.address[1]}/api/admin/migration-mode', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=2)
            error = caught.exception
            try:
                body = json.loads(error.read().decode('utf-8'))
            finally:
                error.close()
            self.assertEqual(error.code, 403)
            self.assertEqual(body['error']['code'], 'operator_context_unavailable')

    def test_readiness_provider_failure_is_blocked_and_health_is_not_ready(self):
        server = HealthServer(port=0, migration_readiness_provider=lambda: (_ for _ in ()).throw(RuntimeError('broken')))
        readiness = server._migration_readiness_snapshot()
        self.assertEqual(readiness['mode'], 'blocked')
        self.assertTrue(readiness['blocked'])
        with server:
            code, payload = self._request('GET', f'http://{server.address[0]}:{server.address[1]}/health')
            self.assertEqual(code, 200)
            self.assertEqual(payload['status'], 'unavailable')
            self.assertEqual(payload['data']['readiness'], 'unavailable')

    def test_read_only_and_unknown_path_fail_soft(self):
        with HealthServer(port=0) as server:
            address = server.address
            code, payload = self._request("POST", f"http://{address[0]}:{address[1]}/health")
            self.assertEqual(code, 405)
            self.assertEqual(payload["status"], "denied")
            code, payload = self._request("GET", f"http://{address[0]}:{address[1]}/not-found")
            self.assertEqual(code, 404)
            self.assertEqual(payload["status"], "invalid_request")

    def test_operator_snapshot_is_bounded_redacted_and_read_only(self):
        server = HealthServer(port=0, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("telemetry:read",))
        server.set_telemetry(streams=({"stream_id": "s-1", "authorization": "secret"},), child_runtimes=({"runtime_id": "child-1", "state": "running"},))
        snapshot = server.operator_snapshot()
        self.assertEqual(snapshot["schema_version"], "noesis.operator-snapshot.v1")
        self.assertEqual(snapshot["execution_claim"], "read_only_snapshot")
        self.assertTrue(snapshot["operator_context"]["configured"])
        self.assertEqual(snapshot["telemetry"]["streams"][0]["authorization"], "[REDACTED]")
        self.assertEqual(snapshot["health"]["contract_version"], CONTRACT_VERSION)
        self.assertIn("migration_readiness", snapshot["telemetry"])

    def test_telemetry_snapshot_child_runtime_and_sse_are_read_only(self):
        server = HealthServer(port=0)
        server.set_telemetry(
            streams=({"stream_id": "s-1", "state": "active", "api_key": "hidden"},),
            child_runtimes=({"runtime_id": "child-1", "state": "running", "pid": 123},),
            counters={"events": 4},
        )
        with server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            code, payload = self._request("GET", base + "/api/telemetry")
            self.assertEqual(code, 200)
            self.assertEqual(payload["data"]["telemetry"]["counters"]["active_streams"], 1)
            self.assertEqual(payload["data"]["telemetry"]["streams"][0]["api_key"], "[REDACTED]")
            self.assertEqual(payload["data"]["telemetry"]["migration_readiness"]["mode"], "legacy")
            code, child_payload = self._request("GET", base + "/api/child-runtimes")
            self.assertEqual(code, 200)
            self.assertEqual(child_payload["data"]["telemetry"]["child_runtimes"][0]["runtime_id"], "child-1")
            code, snapshot_payload = self._request("GET", base + "/api/operator/snapshot")
            self.assertEqual(code, 200)
            self.assertEqual(snapshot_payload["data"]["schema_version"], "noesis.operator-snapshot.v1")
            self.assertEqual(snapshot_payload["data"]["execution_claim"], "read_only_snapshot")
            request = urllib.request.Request(base + "/api/telemetry/events", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.headers["Content-Type"], "text/event-stream; charset=utf-8")
                self.assertIn("event: telemetry", body)
                self.assertIn('"runtime_id":"child-1"', body)
                self.assertIn('"migration_readiness"', body)
                self.assertNotIn("hidden", body)

    def test_operator_session_and_admin_policy_endpoints_require_explicit_handlers(self):
        session_payload = {"schema_version": "noesis.operator-session-action.v1", "action_id": "session-action", "action": "open", "operator_id": "operator-1", "session_id": "session-target", "ttl_seconds": 60, "scopes": ["promotion:review"]}
        admin_payload = {"schema_version": "noesis.administrative-policy.v1", "action": "grant_reviewer", "operator_id": "reviewer-1", "session_id": "session-target", "scopes": ["promotion:review"]}
        with HealthServer(port=0) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            for path, payload in (("/api/operator-sessions", session_payload), ("/api/admin/reviewer-policy", admin_payload)):
                request = urllib.request.Request(base + path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(request, timeout=2)
                error = context.exception
                try:
                    body = json.loads(error.read().decode("utf-8"))
                finally:
                    error.close()
                self.assertEqual(error.code, 405)
                self.assertEqual(body["status"], "denied")

        calls = []
        with HealthServer(port=0, operator_id="operator-1", operator_session_id="session-admin", operator_scopes=("admin:reviewers",), operator_session_action_handler=lambda action, auth: calls.append(("session", action.to_mapping(), auth.operator_id)) or {"status": "queued"}, administrative_policy_handler=lambda payload, auth: calls.append(("admin", payload, auth.operator_id)) or {"status": "queued"}) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            for path, payload in (("/api/operator-sessions", session_payload), ("/api/admin/reviewer-policy", admin_payload)):
                request = urllib.request.Request(base + path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=2) as response:
                    self.assertEqual(response.status, 202)
                    body = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(body["data"]["result"]["status"], "queued")
        self.assertEqual([item[0] for item in calls], ["session", "admin"])

    def test_operator_promotion_action_requires_handler_and_returns_contract(self):
        action_payload = {"schema_version": "noesis.promotion-approval.v1", "action_id": "action-1", "action": "approve", "proposal_id": "proposal-1", "operator_id": "operator-1"}
        with HealthServer(port=0) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            request = urllib.request.Request(base + "/api/promotion-actions", data=json.dumps(action_payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(request, timeout=2)
            error = context.exception
            try:
                payload = json.loads(error.read().decode("utf-8"))
            finally:
                error.close()
            self.assertEqual(error.code, 405)
            self.assertEqual(payload["error"]["code"], "promotion_actions_unavailable")

        handled = []
        with HealthServer(port=0, promotion_action_handler=lambda action, context: handled.append((action.to_mapping(), context)) or {"status": "queued"}, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("promotion:approve",)) as server:
            base = f"http://{server.address[0]}:{server.address[1]}"
            request = urllib.request.Request(base + "/api/promotion-actions", data=json.dumps(action_payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 202)
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["data"]["action"]["proposal_id"], "proposal-1")
                self.assertEqual(payload["data"]["result"]["status"], "queued")
        self.assertEqual(handled[0][0]["action"], "approve")
        self.assertEqual(handled[0][1].operator_id, "operator-1")
        self.assertEqual(handled[0][1].session_id, "session-1")

    def test_duplicate_start_and_invalid_binding_are_safe(self):
        with HealthServer(port=0) as server:
            first = server.start()
            second = server.start()
            self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0")
        with self.assertRaises(ValueError):
            HealthServer(max_request_bytes=128)


if __name__ == "__main__":
    unittest.main()
