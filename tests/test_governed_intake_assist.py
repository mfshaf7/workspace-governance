from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def load_module(name: str, path: Path):
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assist = load_module("governed_intake_assist", SCRIPTS_ROOT / "governed_intake_assist.py")
scaffold = load_module("scaffold_intake", SCRIPTS_ROOT / "scaffold_intake.py")


def suggestion(**overrides) -> dict:
    value = {
        "profile_id": "intake-classifier-v1",
        "policy_status": "active",
        "policy_decision": "allow",
        "decision_id": "intake-test-1",
        "generated_at": "2026-08-20T12:00:00Z",
        "confidence": "medium",
        "caller_id": "workspace-governance/intake-assist",
        "invocation_path": "governed-ai-gateway",
        "suggested_decision": "proposed",
        "audit_ref": "local-ledger:test-audit",
    }
    value.update(overrides)
    return value


def artifact(value: dict | None = None) -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "governed_intake_suggestion_candidate",
        "status": "awaiting-operator-decision",
        "captured_at": "2026-08-20T12:00:01Z",
        "input_digest": "sha256:" + "a" * 64,
        "initiating_operator_id": "operator:test",
        "suggestion": value or suggestion(),
    }


class GatewayHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_body = suggestion()
    received = None

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        type(self).received = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps(type(self).response_body).encode("utf-8")
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class GovernedIntakeAssistTests(unittest.TestCase):
    def setUp(self) -> None:
        GatewayHandler.response_status = 200
        GatewayHandler.response_body = suggestion()
        GatewayHandler.received = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_gateway_url_rejects_remote_plaintext(self) -> None:
        self.assertEqual(
            assist.validate_gateway_url("http://127.0.0.1:18290/"),
            "http://127.0.0.1:18290",
        )
        with self.assertRaisesRegex(assist.IntakeAssistError, "loopback"):
            assist.validate_gateway_url("http://gateway.example.test")
        self.assertEqual(
            assist.validate_gateway_url("https://gateway.example.test/"),
            "https://gateway.example.test",
        )

    def test_gateway_invocation_returns_structured_suggestion(self) -> None:
        payload = {"profile_id": "intake-classifier-v1"}
        result = assist.invoke_gateway(
            f"http://127.0.0.1:{self.server.server_port}",
            payload,
            2,
        )

        self.assertEqual(result, suggestion())
        self.assertEqual(GatewayHandler.received, payload)

    def test_gateway_denial_fails_closed(self) -> None:
        GatewayHandler.response_status = 403
        GatewayHandler.response_body = {
            "policy_decision": "deny",
            "reasons": ["caller-not-allowed"],
        }

        with self.assertRaisesRegex(assist.IntakeAssistError, "caller-not-allowed"):
            assist.invoke_gateway(
                f"http://127.0.0.1:{self.server.server_port}",
                {"profile_id": "intake-classifier-v1"},
                2,
            )

    def test_candidate_validation_rejects_identity_mismatch(self) -> None:
        contract = {
            "consumer": {
                "caller_id": "workspace-governance/intake-assist",
                "profile_id": "intake-classifier-v1",
                "invocation_path": "governed-ai-gateway",
                "suggestion_candidate_schema_ref": {
                    "repo": "workspace-governance",
                    "path": "contracts/schemas/intake-ai-suggestion-candidate.schema.json",
                },
            }
        }
        assist.validate_suggestion(REPO_ROOT, contract, suggestion(), "intake-test-1")
        with self.assertRaisesRegex(assist.IntakeAssistError, "identity mismatch"):
            assist.validate_suggestion(
                REPO_ROOT,
                contract,
                suggestion(caller_id="unapproved/consumer"),
                "intake-test-1",
            )

    def test_candidate_artifact_keeps_only_input_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "candidate.json"
            assist.write_candidate(REPO_ROOT, output, suggestion(), "private intake note", "operator:test")
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotIn("private intake note", json.dumps(payload))
        self.assertRegex(payload["input_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(payload["suggestion"]["audit_ref"], "local-ledger:test-audit")

    def test_candidate_output_is_confined_to_local_artifact_root(self) -> None:
        expected = REPO_ROOT / ".art" / "intake-assist" / "candidate.json"
        self.assertEqual(
            assist.resolve_candidate_output(REPO_ROOT, Path(".art/intake-assist/candidate.json")),
            expected,
        )
        with self.assertRaisesRegex(assist.IntakeAssistError, "must stay under"):
            assist.resolve_candidate_output(REPO_ROOT, Path("contracts/intake-register.yaml"))

    def test_scaffold_accepts_gateway_candidate_only_after_explicit_operator_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_path = Path(temp_dir) / "candidate.json"
            candidate_path.write_text(json.dumps(artifact()), encoding="utf-8")
            args = argparse.Namespace(
                acceptance_state="accepted",
                accepted_at="2026-08-20T12:05:00Z",
                accepted_by="operator:test",
                ai_suggestion_file=candidate_path,
                decision_source="ai-suggested",
                governed_intake_assist={
                    "activation_state": {
                        "source_contract_status": "active",
                        "live_consumption_allowed": True,
                    },
                    "consumer": {
                        "caller_id": "workspace-governance/intake-assist",
                        "profile_id": "intake-classifier-v1",
                        "invocation_path": "governed-ai-gateway",
                    }
                },
                operator_decision="proposed",
                override_reason=None,
                repo_root=REPO_ROOT,
                status="proposed",
                used_ai_decision_ids=set(),
            )
            accepted = scaffold.build_ai_suggestion(args)

        self.assertEqual(accepted["decision_id"], "intake-test-1")
        self.assertEqual(accepted["audit_ref"], "local-ledger:test-audit")
        self.assertEqual(accepted["acceptance_state"], "accepted")
        self.assertNotIn("policy_decision", accepted)

    def test_scaffold_rejects_override_without_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_path = Path(temp_dir) / "candidate.json"
            candidate_path.write_text(json.dumps(artifact()), encoding="utf-8")
            args = argparse.Namespace(
                acceptance_state="overridden",
                accepted_at="2026-08-20T12:05:00Z",
                accepted_by="operator:test",
                ai_suggestion_file=candidate_path,
                decision_source="ai-suggested",
                governed_intake_assist={
                    "activation_state": {
                        "source_contract_status": "active",
                        "live_consumption_allowed": True,
                    },
                    "consumer": {
                        "caller_id": "workspace-governance/intake-assist",
                        "profile_id": "intake-classifier-v1",
                        "invocation_path": "governed-ai-gateway",
                    }
                },
                operator_decision="out-of-scope",
                override_reason=None,
                repo_root=REPO_ROOT,
                status="out-of-scope",
                used_ai_decision_ids=set(),
            )
            with self.assertRaisesRegex(SystemExit, "override-reason"):
                scaffold.build_ai_suggestion(args)

    def test_scaffold_rejects_replayed_decision_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_path = Path(temp_dir) / "candidate.json"
            candidate_path.write_text(json.dumps(artifact()), encoding="utf-8")
            args = argparse.Namespace(
                acceptance_state="accepted",
                accepted_at="2026-08-20T12:05:00Z",
                accepted_by="operator:test",
                ai_suggestion_file=candidate_path,
                decision_source="ai-suggested",
                governed_intake_assist={
                    "activation_state": {
                        "source_contract_status": "active",
                        "live_consumption_allowed": True,
                    },
                    "consumer": {
                        "caller_id": "workspace-governance/intake-assist",
                        "profile_id": "intake-classifier-v1",
                        "invocation_path": "governed-ai-gateway",
                    },
                },
                operator_decision="proposed",
                override_reason=None,
                repo_root=REPO_ROOT,
                status="proposed",
                used_ai_decision_ids={"intake-test-1"},
            )
            with self.assertRaisesRegex(SystemExit, "already been applied"):
                scaffold.build_ai_suggestion(args)


if __name__ == "__main__":
    unittest.main()
