import concurrent.futures
from dataclasses import replace
import json
from pathlib import Path
import sys
import threading
import unittest
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_support import (
    CloudflareWorkersAI, LocalModelProvider, Limits, MAX_OUTPUT_BYTES, MAX_OUTPUT_TOKENS,
    MAX_PROMPT_BYTES, MODEL, Principal, ProviderResult, RuntimeControls,
    SupportService, SYSTEM_PROMPT,
)


class LocalAuthenticator:
    """Runtime-generated local fixtures; no issued or committed credentials."""

    def __init__(self):
        self.authorization = "Bearer " + str(uuid4())
        self.principal = Principal(
            str(uuid4()), "niknolig", frozenset({"ai:support", "ai:electro-engel"}),
            2000.0, True,
        )

    def authenticate(self, authorization):
        return self.principal if authorization == self.authorization else None


class LocalProvider:
    provider_id = "local-mock"

    def __init__(self):
        self.calls = []
        self.result = ProviderResult("Local mock reply.", 12, 6)
        self.error = None
        self.entered = None
        self.release = None

    def generate(self, prompt):
        self.calls.append(prompt)
        if self.entered:
            self.entered.set()
            if not self.release.wait(3):
                raise TimeoutError("Local mock did not release")
        if self.error:
            raise self.error
        return self.result


class LocalAudit:
    def __init__(self):
        self.events = []
        self.fail_at = None
        self.hook = None
        self.lock = threading.Lock()

    def write(self, event):
        with self.lock:
            if len(self.events) == self.fail_at:
                raise RuntimeError("Private audit exception")
            self.events.append(dict(event))
        if self.hook:
            self.hook()


def local_service(**kwargs):
    auth = LocalAuthenticator()
    provider = LocalProvider()
    audit = LocalAudit()
    controls = RuntimeControls()
    controls.configure(enabled=True, provider_approved=True, cost_approved=True)
    service = SupportService(
        authenticator=auth, provider=provider, audit=audit,
        controls=controls, clock=lambda: 1000.0, **kwargs,
    )
    return service, auth, provider, audit


def payload(**changes):
    return {"app": "niknolig", "feature": "support", "prompt": "Local support question.",
            **changes}


class SupportServiceTests(unittest.TestCase):
    def setUp(self):
        self.service, self.auth, self.provider, self.audit = local_service()

    def invoke(self, body=None):
        return self.service.handle(
            self.auth.authorization, payload() if body is None else body
        )

    def test_default_service_is_disabled_even_with_authorization(self):
        status, result = SupportService().handle(self.auth.authorization, payload())
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", result["error"]["code"])
        self.assertTrue(result["error"]["escalationRequired"])

    def test_default_authenticator_rejects_everything_when_gates_are_open(self):
        self.service.authenticator = SupportService().authenticator
        self.assertEqual(401, self.invoke()[0])
        self.assertFalse(self.provider.calls)

    def test_each_gate_offline_and_kill_switch_prevent_dispatch(self):
        configurations = [
            {}, {"enabled": True}, {"enabled": True, "provider_approved": True},
            {"enabled": True, "cost_approved": True},
            {"enabled": True, "provider_approved": True, "cost_approved": True,
             "offline": True},
            {"enabled": True, "provider_approved": True, "cost_approved": True,
             "killed": True},
        ]
        for config in configurations:
            with self.subTest(config=config):
                self.service.controls.configure(**config)
                self.assertEqual(503, self.invoke()[0])
        self.assertFalse(self.provider.calls)
        self.assertFalse(self.audit.events)

    def test_controls_reject_truthy_non_boolean_flags(self):
        for flag in ("enabled", "provider_approved", "cost_approved", "offline", "killed"):
            for value in ("true", 1, 0, -1, None):
                with self.subTest(flag=flag, value=value), self.assertRaises(ValueError):
                    self.service.controls.configure(**{flag: value})

    def test_kill_after_audit_still_prevents_dispatch(self):
        self.audit.hook = lambda: self.service.controls.configure(killed=True)
        status, body = self.invoke()
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", body["error"]["code"])
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertFalse(self.provider.calls)

    def test_gate_closure_after_provider_withholds_text_and_escalates(self):
        generate = self.provider.generate

        def generate_then_kill(prompt):
            result = generate(prompt)
            self.service.controls.configure(killed=True)
            return result

        self.provider.generate = generate_then_kill
        status, body = self.invoke()
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", body["error"]["code"])
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertNotIn(self.provider.result.text, json.dumps(body))
        self.assertEqual(["reserved", "ai_disabled"],
                         [event["outcome"] for event in self.audit.events])

    def test_gate_closure_in_final_audit_hook_withholds_text(self):
        def kill_after_completion():
            if self.audit.events[-1]["outcome"] == "completed":
                self.service.controls.configure(killed=True)

        self.audit.hook = kill_after_completion
        status, body = self.invoke()
        self.assertEqual(503, status)
        self.assertEqual("AI_DISABLED", body["error"]["code"])
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertNotIn(self.provider.result.text, json.dumps(body))
        self.assertEqual("ai_disabled", self.audit.events[-1]["outcome"])

    def test_success_is_untrusted_plain_text_and_audit_is_redacted(self):
        private_prompt = str(uuid4())
        self.provider.result = ProviderResult("<script>tool()</script>", 10, 10)
        status, body = self.invoke(payload(prompt=private_prompt))
        self.assertEqual(200, status)
        self.assertEqual("text/plain", body["contentType"])
        self.assertTrue(body["untrusted"])
        self.assertFalse(body["escalationRequired"])
        self.assertEqual("<script>tool()</script>", body["text"])
        self.assertNotIn("tools", body)
        self.assertEqual(["reserved", "completed"],
                         [e["outcome"] for e in self.audit.events])
        encoded = json.dumps(self.audit.events)
        for private in (private_prompt, self.auth.authorization,
                        self.auth.principal.subject, body["text"]):
            self.assertNotIn(private, encoded)
        allowed = {"requestId", "app", "feature", "provider", "model", "outcome",
                   "reservedTokens", "inputTokens", "outputTokens"}
        self.assertTrue(all(set(e) <= allowed for e in self.audit.events))

    def test_local_model_adapter_uses_fixed_bounded_runtime_parameters(self):
        class Runtime:
            def __init__(self):
                self.calls = []

            def generate(self, prompt, *, max_tokens, timeout_seconds):
                self.calls.append((prompt, max_tokens, timeout_seconds))
                return ProviderResult("Local inference.", 10, 4)

        runtime = Runtime()
        provider = LocalModelProvider(model_id="local/approved-model-q4", runtime=runtime)
        self.service.provider = provider
        status, response = self.invoke()
        self.assertEqual(200, status)
        self.assertEqual("Local inference.", response["text"])
        self.assertEqual(
            [("Local support question.", MAX_OUTPUT_TOKENS, 5.0)], runtime.calls
        )
        self.assertEqual("local/approved-model-q4", self.audit.events[0]["model"])

    def test_principal_validation_denies_before_quotas(self):
        original = self.auth.principal
        invalid = [
            None, replace(original, active=False), replace(original, active=1),
            replace(original, expires_at=1000), replace(original, expires_at=float("nan")),
            replace(original, expires_at=float("inf")), replace(original, expires_at=True),
            replace(original, app="other"), replace(original, app=[]),
            replace(original, subject=""), replace(original, subject="s" * 129),
            replace(original, permissions={"ai:support"}),
            replace(original, permissions=frozenset({1})),
        ]
        for principal in invalid:
            with self.subTest(principal=principal):
                self.auth.principal = principal
                self.assertEqual(401, self.invoke()[0])
        self.assertFalse(self.provider.calls)
        self.assertFalse(self.service.quotas._rates)

    def test_auth_exception_is_generic_and_does_not_dispatch(self):
        class BrokenAuth:
            def authenticate(self, authorization):
                raise RuntimeError(authorization)
        self.service.authenticator = BrokenAuth()
        status, body = self.invoke()
        self.assertEqual(401, status)
        self.assertNotIn(self.auth.authorization, json.dumps(body))
        self.assertFalse(self.provider.calls)

    def test_wrong_credentials_rejected(self):
        self.assertEqual(401, self.service.handle(None, payload())[0])
        self.assertEqual(401, self.service.handle(str(uuid4()), payload())[0])
        self.assertFalse(self.service.handle(None, payload())[1]["error"]["escalationRequired"])

    def test_cross_app_permission_and_engel_boundaries(self):
        self.assertEqual(403, self.invoke(payload(app="niknolig-defense"))[0])
        self.auth.principal = replace(self.auth.principal, permissions=frozenset())
        self.assertEqual(403, self.invoke()[0])
        self.auth.principal = replace(
            self.auth.principal, app="niknolig-defense",
            permissions=frozenset({"ai:support", "ai:electro-engel"}),
        )
        status, response = self.invoke(
            payload(app="niknolig-defense", feature="electro-engel"))
        self.assertEqual(200, status)
        self.assertEqual("niknolig-defense", response["app"])
        self.assertEqual("electro-engel", response["feature"])
        self.auth.principal = replace(
            self.auth.principal, app="niknolig",
            permissions=frozenset({"ai:support", "ai:electro-engel"}),
        )
        self.assertEqual(403, self.invoke(
            payload(app="niknolig-defense", feature="electro-engel"))[0])
        self.assertEqual(["Local support question."], self.provider.calls)
        self.auth.principal = replace(
            self.auth.principal, app="niknolig-defense",
            permissions=frozenset({"ai:support", "ai:electro-engel"}),
        )
        self.assertEqual(200, self.invoke(payload(app="niknolig-defense"))[0])
        self.auth.principal = replace(
            self.auth.principal, app="niknolig",
            permissions=frozenset({"ai:support", "ai:electro-engel"}),
        )
        self.assertEqual(200, self.invoke(payload(feature="electro-engel"))[0])
        self.assertEqual(
            ["Local support question."] * 3,
            self.provider.calls,
        )

    def test_untrusted_fields_types_unicode_and_size_are_rejected(self):
        cases = [
            [], "text", 1, {}, {**payload(), "provider": "caller"},
            {**payload(), "model": "caller"}, {**payload(), "url": "caller"},
            {**payload(), "apiKey": str(uuid4())}, {**payload(), "tools": []},
            payload(app=[]), payload(feature=None), payload(prompt=3),
            payload(app="other"), payload(feature="other"),
            payload(prompt=""), payload(prompt=" \n\t"),
            payload(prompt="x" * (MAX_PROMPT_BYTES + 1)),
            payload(prompt="é" * (MAX_PROMPT_BYTES // 2 + 1)),
            payload(prompt="\ud800"),
        ]
        for case in cases:
            with self.subTest(case=repr(case)[:100]):
                self.assertEqual(400, self.invoke(case)[0])
        self.assertFalse(self.provider.calls)

    def test_maximum_utf8_prompt_is_accepted(self):
        self.assertEqual(200, self.invoke(payload(prompt="é" * 1024))[0])

    def test_unapproved_provider_label_is_not_dispatched_or_audited(self):
        self.provider.provider_id = "caller-selected"
        self.assertEqual(503, self.invoke()[0])
        self.assertFalse(self.provider.calls)
        self.assertFalse(self.audit.events)

    def test_missing_or_failed_initial_audit_prevents_provider(self):
        self.audit.fail_at = 0
        self.assertEqual("AUDIT_UNAVAILABLE", self.invoke()[1]["error"]["code"])
        self.assertFalse(self.provider.calls)
        self.service.audit = SupportService().audit
        self.assertEqual(503, self.invoke()[0])
        self.assertFalse(self.provider.calls)

    def test_final_audit_failure_withholds_answer_and_escalates(self):
        self.audit.fail_at = 1
        status, body = self.invoke()
        self.assertEqual(503, status)
        self.assertEqual("AUDIT_UNAVAILABLE", body["error"]["code"])
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertNotIn(self.provider.result.text, json.dumps(body))
        self.assertEqual(1, len(self.provider.calls))

    def test_provider_errors_are_generic_escalated_and_consume_reservations(self):
        for exception in (TimeoutError, ConnectionError, RuntimeError):
            with self.subTest(exception=exception):
                service, auth, provider, audit = local_service(
                    limits=Limits(app_daily_calls=1))
                private = str(uuid4())
                provider.error = exception(private)
                status, body = service.handle(auth.authorization, payload())
                self.assertEqual(503, status)
                self.assertTrue(body["error"]["escalationRequired"])
                self.assertNotIn(private, json.dumps(body) + json.dumps(audit.events))
                self.assertEqual("provider_unavailable", audit.events[-1]["outcome"])
                self.assertEqual(429, service.handle(auth.authorization, payload())[0])
                self.assertFalse(service.handle(auth.authorization, payload())[1]["error"][
                    "escalationRequired"])
                self.assertEqual(1, len(provider.calls))

    def test_invalid_or_uncertain_output_never_escapes(self):
        cases = [
            None, {"text": "unexpected"}, ProviderResult("", 1, 1),
            ProviderResult(" ", 1, 1), ProviderResult([], 1, 1),
            ProviderResult("x" * (MAX_OUTPUT_BYTES + 1), 1, 1),
            ProviderResult("é" * 513, 1, 1), ProviderResult("\ud800", 1, 1),
            ProviderResult("ok", True, 1), ProviderResult("ok", 1, False),
            ProviderResult("ok", -1, 1), ProviderResult("ok", 99999, 1),
            ProviderResult("ok", 1, MAX_OUTPUT_TOKENS + 1),
        ]
        for result in cases:
            with self.subTest(result=repr(result)[:100]):
                service, auth, provider, _ = local_service()
                provider.result = result
                status, body = service.handle(auth.authorization, payload())
                self.assertEqual(503, status)
                self.assertTrue(body["error"]["escalationRequired"])

    def test_boundary_output_is_accepted(self):
        self.provider.result = ProviderResult("x" * MAX_OUTPUT_BYTES, 1, MAX_OUTPUT_TOKENS)
        self.assertEqual(200, self.invoke()[0])

    def test_auth_failures_do_not_consume_rate_limit(self):
        service, auth, provider, _ = local_service(limits=Limits(calls_per_minute=1))
        for _ in range(4):
            self.assertEqual(401, service.handle(None, payload())[0])
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        self.assertEqual(1, len(provider.calls))

    def test_rate_window_recovers_but_budget_does_not_refund_success(self):
        service, auth, provider, _ = local_service(limits=Limits(calls_per_minute=1))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        used = service.quotas._apps["niknolig"][0]
        self.assertGreater(used, provider.result.input_tokens + provider.result.output_tokens)
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        service.clock = lambda: 1060
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        self.assertEqual(2 * used, service.quotas._apps["niknolig"][0])

    def test_out_of_order_timestamps_do_not_reopen_the_rate_limit(self):
        service, auth, _, _ = local_service()
        timestamps = iter((60.01, 59.99, 60.02, 60.02, 60.02, 60.02, 60.02))
        service.clock = lambda: next(timestamps)

        statuses = [
            service.handle(auth.authorization, payload())[0]
            for _ in range(7)
        ]

        self.assertEqual([200, 200, 200, 200, 200, 429, 429], statuses)

    def test_interleaved_principals_cannot_reopen_an_older_rate_bucket(self):
        service, auth, _, _ = local_service(
            limits=Limits(calls_per_minute=1))
        principal = auth.principal
        auth.principal = replace(principal, subject="principal-a")
        timestamps = iter((59.98, 60.01, 59.99, 60.02))
        service.clock = lambda: next(timestamps)

        statuses = [service.handle(auth.authorization, payload())[0]]
        auth.principal = replace(principal, subject="principal-b")
        statuses.append(service.handle(auth.authorization, payload())[0])
        auth.principal = replace(principal, subject="principal-a")
        statuses.append(service.handle(auth.authorization, payload())[0])
        statuses.append(service.handle(auth.authorization, payload())[0])

        self.assertEqual([200, 200, 200, 429], statuses)

    def test_token_budget_reserves_full_input_and_output_before_dispatch(self):
        reservation = (len(payload()["prompt"].encode()) +
                       len(SYSTEM_PROMPT.encode()) + 64 + MAX_OUTPUT_TOKENS)
        service, auth, provider, _ = local_service(
            limits=Limits(app_daily_tokens=reservation))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        status, body = service.handle(auth.authorization, payload())
        self.assertEqual(429, status)
        self.assertEqual("BUDGET_EXHAUSTED", body["error"]["code"])
        self.assertEqual(1, len(provider.calls))

    def test_budget_too_small_never_dispatches(self):
        service, auth, provider, audit = local_service(limits=Limits(app_daily_tokens=1))
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        self.assertFalse(provider.calls)
        self.assertFalse(audit.events)

    def test_per_app_budgets_are_separate_but_global_cap_applies(self):
        service, auth, provider, _ = local_service(
            limits=Limits(app_daily_calls=1, global_daily_calls=2))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        auth.principal = replace(auth.principal, app="niknolig-defense")
        defense = payload(app="niknolig-defense")
        self.assertEqual(200, service.handle(auth.authorization, defense)[0])
        self.assertEqual(429, service.handle(auth.authorization, defense)[0])
        self.assertEqual(2, len(provider.calls))

    def test_daily_budget_recovers_next_day_not_on_clock_rollback(self):
        service, auth, _, _ = local_service(limits=Limits(app_daily_calls=1))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        service.clock = lambda: 900
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        auth.principal = replace(auth.principal, expires_at=200000)
        service.clock = lambda: 87400
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])

    def test_global_cap_blocks_other_app_even_with_its_unused_budget(self):
        service, auth, provider, _ = local_service(
            limits=Limits(global_daily_calls=1))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        auth.principal = replace(auth.principal, app="niknolig-defense")
        status, body = service.handle(
            auth.authorization, payload(app="niknolig-defense"))
        self.assertEqual(429, status)
        self.assertEqual("BUDGET_EXHAUSTED", body["error"]["code"])
        self.assertEqual(1, len(provider.calls))

    def test_tracked_principals_are_bounded_and_not_evicted_to_bypass_limits(self):
        service, auth, _, _ = local_service(limits=Limits(max_principals=1))
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        auth.principal = replace(auth.principal, subject=str(uuid4()))
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        self.assertEqual(1, len(service.quotas._rates))
        service.clock = lambda: 1060
        self.assertEqual(200, service.handle(auth.authorization, payload())[0])
        self.assertEqual(1, len(service.quotas._rates))

    def test_concurrent_reservations_cannot_overrun_daily_calls(self):
        service, auth, provider, _ = local_service(limits=Limits(app_daily_calls=1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(
                lambda _: service.handle(auth.authorization, payload())[0], range(20)))
        self.assertEqual(1, statuses.count(200))
        self.assertEqual(19, statuses.count(429))
        self.assertEqual(1, len(provider.calls))
        self.assertEqual(0, service.quotas._active)

    def test_inflight_cap_kill_and_offline_block_subsequent_requests(self):
        service, auth, provider, _ = local_service(limits=Limits(max_concurrent=1))
        provider.entered, provider.release = threading.Event(), threading.Event()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(service.handle, auth.authorization, payload())
            try:
                self.assertTrue(provider.entered.wait(1))
                self.assertEqual(429, service.handle(auth.authorization, payload())[0])
                service.controls.configure(enabled=True, provider_approved=True,
                                           cost_approved=True, killed=True)
                self.assertEqual(503, service.handle(auth.authorization, payload())[0])
                service.controls.configure(enabled=True, provider_approved=True,
                                           cost_approved=True, offline=True)
                self.assertEqual(503, service.handle(auth.authorization, payload())[0])
            finally:
                provider.release.set()
            status, body = pending.result()
            self.assertEqual(503, status)
            self.assertEqual("AI_DISABLED", body["error"]["code"])
            self.assertTrue(body["error"]["escalationRequired"])
        self.assertEqual(1, len(provider.calls))
        self.assertEqual(0, service.quotas._active)

    def test_audit_failure_does_not_offer_free_reservation_retries(self):
        service, auth, provider, audit = local_service(limits=Limits(app_daily_calls=1))
        audit.fail_at = 0
        self.assertEqual(503, service.handle(auth.authorization, payload())[0])
        audit.fail_at = None
        self.assertEqual(429, service.handle(auth.authorization, payload())[0])
        self.assertFalse(provider.calls)
        self.assertEqual(0, service.quotas._active)

    def test_limits_reject_unbounded_or_non_integer_values(self):
        for kwargs in ({"max_concurrent": 9}, {"max_principals": 999999},
                       {"calls_per_minute": True}, {"app_daily_tokens": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Limits(**kwargs)
        for field in Limits.__dataclass_fields__:
            for value in (-1, False, True, 1.5, "5", None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    Limits(**{field: value})
        for value in (False, 0, -1, {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SupportService(limits=value)

    def test_invalid_clock_fails_closed(self):
        for value in (float("nan"), float("inf"), -1, True, "1000"):
            with self.subTest(value=value):
                self.service.clock = lambda: value
                self.assertEqual(401, self.invoke()[0])
        self.assertFalse(self.provider.calls)

    def test_quota_store_is_injectable_and_release_uses_generated_request_id(self):
        class Store:
            def reserve(self, **kwargs):
                self.reservation = kwargs
                return None

            def finish(self, request_id):
                self.finished = request_id
        store = Store()
        service, auth, provider, _ = local_service(quotas=store)
        question = payload(prompt="Überprüfung 🔒")
        status, body = service.handle(auth.authorization, question)
        self.assertEqual(200, status)
        self.assertEqual(body["requestId"], store.reservation["request_id"])
        self.assertEqual(body["requestId"], store.finished)
        self.assertEqual(auth.principal, store.reservation["principal"])
        self.assertEqual(1000, store.reservation["now"])
        self.assertEqual(
            len(question["prompt"].encode("utf-8")) +
            len(SYSTEM_PROMPT.encode("utf-8")) + 64 + MAX_OUTPUT_TOKENS,
            store.reservation["tokens"],
        )
        self.assertEqual(1, len(provider.calls))
        with self.assertRaises(ValueError):
            SupportService(quotas=store, limits=Limits())

    def test_quota_store_failures_and_invalid_results_fail_closed(self):
        class Store:
            def __init__(self, result):
                self.result = result

            def reserve(self, **kwargs):
                if isinstance(self.result, Exception):
                    raise self.result
                return self.result

            def finish(self, request_id):
                raise AssertionError("No reservation was granted")
        for result in (RuntimeError("private"), False, True, 0, 1, "private", {}):
            with self.subTest(result=result):
                service, auth, provider, audit = local_service(quotas=Store(result))
                status, body = service.handle(auth.authorization, payload())
                self.assertEqual(503, status)
                self.assertEqual("QUOTA_UNAVAILABLE", body["error"]["code"])
                self.assertNotIn("private", json.dumps(body))
                self.assertFalse(provider.calls)
                self.assertFalse(audit.events)

    def test_quota_concurrency_release_failure_withholds_answer_without_refund(self):
        class Store:
            finish_calls = 0

            def reserve(self, **kwargs):
                self.reservation = kwargs
                return None

            def finish(self, request_id):
                self.finish_calls += 1
                raise RuntimeError("private")
        store = Store()
        service, auth, provider, _ = local_service(quotas=store)
        status, body = service.handle(auth.authorization, payload())
        self.assertEqual(503, status)
        self.assertEqual("QUOTA_UNAVAILABLE", body["error"]["code"])
        self.assertTrue(body["error"]["escalationRequired"])
        self.assertNotIn(provider.result.text, json.dumps(body))
        self.assertGreater(store.reservation["tokens"], MAX_OUTPUT_TOKENS)
        self.assertEqual(1, len(provider.calls))
        self.assertEqual(1, store.finish_calls)

    def test_quota_release_gate_closure_withholds_text(self):
        class Store:
            def __init__(self, closure):
                self.closure = closure
                self.finished = []

            def reserve(self, **kwargs):
                self.reservation = kwargs
                return None

            def finish(self, request_id):
                self.finished.append(request_id)
                self.controls.configure(**self.closure)

        closures = [
            {"enabled": True, "provider_approved": True, "cost_approved": True,
             "killed": True},
            {"enabled": True, "provider_approved": True, "cost_approved": True,
             "offline": True},
            {},
        ]
        for closure in closures:
            with self.subTest(closure=closure):
                store = Store(closure)
                service, auth, provider, audit = local_service(quotas=store)
                store.controls = service.controls
                status, body = service.handle(auth.authorization, payload())
                self.assertEqual(503, status)
                self.assertEqual("AI_DISABLED", body["error"]["code"])
                self.assertTrue(body["error"]["escalationRequired"])
                self.assertNotIn(provider.result.text, json.dumps(body))
                self.assertEqual([body["error"]["requestId"]], store.finished)
                self.assertEqual(1, len(provider.calls))
                self.assertEqual("ai_disabled", audit.events[-1]["outcome"])
                self.assertGreater(store.reservation["tokens"], MAX_OUTPUT_TOKENS)

    def test_local_concurrency_release_is_idempotent(self):
        status, body = self.invoke()
        self.assertEqual(200, status)
        reserved = self.service.quotas._apps["niknolig"]
        self.service.quotas.finish(body["requestId"])
        self.service.quotas.finish(body["requestId"])
        self.assertEqual(0, self.service.quotas._active)
        self.assertEqual(reserved, self.service.quotas._apps["niknolig"])


class CloudflareAdapterTests(unittest.TestCase):
    def test_transport_is_injected_and_model_and_generation_are_fixed(self):
        class Transport:
            def run(self, **kwargs):
                self.kwargs = kwargs
                return ProviderResult("Mock transport only.", 4, 4)
        transport = Transport()
        adapter = CloudflareWorkersAI(transport)
        self.assertEqual("Mock transport only.", adapter.generate("Local question").text)
        self.assertEqual(MODEL, transport.kwargs["model"])
        self.assertEqual(256, transport.kwargs["max_tokens"])
        self.assertEqual(5.0, transport.kwargs["timeout_seconds"])
        self.assertEqual(0.2, transport.kwargs["temperature"])
        self.assertEqual({"role": "system", "content": SYSTEM_PROMPT},
                         transport.kwargs["messages"][0])
        self.assertEqual({"role": "user", "content": "Local question"},
                         transport.kwargs["messages"][1])
        self.assertNotIn("url", transport.kwargs)
        self.assertNotIn("authorization", transport.kwargs)

    def test_no_default_transport_or_credential_path(self):
        with self.assertRaises(TypeError):
            CloudflareWorkersAI()

    def test_separate_contract_marks_preparation_and_preserves_health_only(self):
        backend = Path(__file__).resolve().parents[1]
        contract = (backend / "ai-support.openapi.yaml").read_text()
        self.assertIn("openapi: 3.1.0", contract)
        self.assertIn("/support:", contract)
        self.assertIn("/v1/ai/support:", contract)
        self.assertIn("message:", contract)
        self.assertIn("Not deployed, activated, or production-approved", contract)
        self.assertIn("durable distributed quotas", contract)
        self.assertNotIn("/v1/", (backend / "openapi.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
