import unittest

from noesis_harness.model_selector import select_model
from noesis_harness.ui_assets import CONTROL_PLANE_HTML


RECORDS = (
    {"id": "basic", "provider": "ollama", "status": "ready", "capabilities": {"tools": False, "vision": False, "structured_output": False}},
    {"id": "tools-model", "provider": "vllm", "status": "ready", "capabilities": {"tools": True, "vision": False, "structured_output": True}},
    {"id": "offline", "provider": "ollama", "status": "unavailable", "capabilities": {"tools": True}},
)


class ModelSelectorTests(unittest.TestCase):
    def test_selects_model_that_satisfies_required_capabilities(self):
        result = select_model(RECORDS, ("tools", "structured_output"))
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.model_id, "tools-model")
        self.assertEqual(result.missing, ())

    def test_preferred_provider_is_deterministic_tiebreaker(self):
        records = RECORDS + ({"id": "tools-local", "provider": "ollama", "status": "ready", "capabilities": {"tools": True}},)
        result = select_model(records, ("tools",), preferred_provider="ollama")
        self.assertEqual(result.model_id, "tools-local")

    def test_missing_capability_is_degraded_not_fake_ready(self):
        result = select_model(RECORDS, ("vision",))
        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.reason, "required_capabilities_unavailable")
        self.assertEqual(result.missing, ("vision",))

    def test_unknown_requirement_and_empty_records_fail_soft(self):
        self.assertEqual(select_model(RECORDS, ("execute_code",)).status, "incompatible")
        self.assertEqual(select_model((), ("tools",)).status, "unavailable")

    def test_ui_exposes_capabilities_and_keeps_invocation_disabled(self):
        self.assertIn("Models & capabilities", CONTROL_PLANE_HTML)
        self.assertIn("Invoke disabled", CONTROL_PLANE_HTML)
        self.assertIn("tools", CONTROL_PLANE_HTML)
        self.assertNotIn("/chat/completions", CONTROL_PLANE_HTML)


if __name__ == "__main__":
    unittest.main()
