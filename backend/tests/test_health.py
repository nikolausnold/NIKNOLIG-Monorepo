import asyncio
import logging
import time
import tomllib
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import yaml
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from jsonschema import Draft202012Validator

from backend.app.health import Readiness
from backend.app.main import CONTRACT_PATH, create_app


class HealthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.application = create_app()
        self.client = self.client_for(self.application)
        self.addAsyncCleanup(self.client.aclose)
        self.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    def client_for(self, application):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        )

    def assert_contract_response(self, response, schema_name):
        schema = {
            "$ref": f"#/components/schemas/{schema_name}",
            "components": self.contract["components"],
        }
        Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        ).validate(response.json())
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual("application/json", response.headers["content-type"])

    def assert_safe_error(self, response, status, code, message):
        self.assertEqual(status, response.status_code)
        self.assert_contract_response(response, "ApiError")
        error = response.json()["error"]
        self.assertEqual(code, error["code"])
        self.assertEqual(message, error["message"])
        self.assertEqual(4, UUID(error["requestId"]).version)
        self.assertEqual({"error"}, set(response.json()))
        self.assertEqual({"code", "message", "requestId"}, set(error))

    async def test_liveness_only_reports_process_availability(self):
        probe = AsyncMock(side_effect=RuntimeError("private-diagnostic-sentinel"))
        async with self.client_for(create_app(readiness_checks=[probe])) as client:
            response = await client.get("/health/live")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "live"}, response.json())
        self.assert_contract_response(response, "HealthStatus")
        probe.assert_not_awaited()

    async def test_default_readiness_has_no_database_or_product_dependency(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            response = await self.client.get("/health/ready")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ready"}, response.json())
        self.assert_contract_response(response, "HealthStatus")

    async def test_readiness_checks_all_registered_dependencies(self):
        first = AsyncMock(return_value=True)
        second = AsyncMock(return_value=True)
        async with self.client_for(
            create_app(readiness_checks=[first, second])
        ) as client:
            response = await client.get("/health/ready")
        self.assertEqual(200, response.status_code)
        first.assert_awaited_once_with()
        second.assert_awaited_once_with()

    async def test_dependency_failure_is_minimized_and_not_logged(self):
        probe = AsyncMock(side_effect=RuntimeError("private-diagnostic-sentinel"))
        async with self.client_for(create_app(readiness_checks=[probe])) as client:
            with self.assertNoLogs("backend.app", level=logging.DEBUG):
                response = await client.get("/health/ready")
        self.assert_safe_error(
            response, 503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable."
        )
        self.assertNotIn("private-diagnostic-sentinel", response.text)

    async def test_false_or_non_boolean_probe_results_fail_closed(self):
        for result in (False, None, 1, "ready", {}):
            with self.subTest(result=result):
                probe = AsyncMock(return_value=result)
                async with self.client_for(
                    create_app(readiness_checks=[probe])
                ) as client:
                    response = await client.get("/health/ready")
                self.assertEqual(503, response.status_code)

    async def test_failed_readiness_does_not_change_liveness(self):
        probe = AsyncMock(return_value=False)
        async with self.client_for(create_app(readiness_checks=[probe])) as client:
            self.assertEqual(503, (await client.get("/health/ready")).status_code)
            self.assertEqual({"status": "live"}, (await client.get("/health/live")).json())
        probe.assert_awaited_once_with()

    async def test_readiness_recovers_without_caching_dependency_state(self):
        probe = AsyncMock(side_effect=[False, True])
        async with self.client_for(create_app(readiness_checks=[probe])) as client:
            self.assertEqual(503, (await client.get("/health/ready")).status_code)
            response = await client.get("/health/ready")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ready"}, response.json())
        self.assertEqual(2, probe.await_count)

    async def test_readiness_timeout_cancels_probe_and_returns_safe_503(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def stalled():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with self.client_for(
            create_app(readiness_checks=[stalled], readiness_timeout_seconds=0.02)
        ) as client:
            start = time.monotonic()
            response = await asyncio.wait_for(client.get("/health/ready"), timeout=1)
            self.assertLess(time.monotonic() - start, 1)
        self.assertTrue(started.is_set())
        self.assertTrue(cancelled.is_set())
        self.assert_safe_error(
            response, 503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable."
        )

    async def test_unknown_routes_and_product_operations_are_absent(self):
        for path in (
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/v1/devices",
            "/v1/profiles",
            "/v1/pairing",
            "/v1/sensors",
            "/v1/finance",
            "/health/live/",
            "/health/ready/",
        ):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assert_safe_error(
                    response, 404, "NOT_FOUND", "Resource not found."
                )
                self.assertNotIn("location", response.headers)
        self.assertFalse(self.application.debug)

    async def test_non_get_health_methods_are_rejected(self):
        for path in ("/health/live", "/health/ready"):
            for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
                with self.subTest(path=path, method=method):
                    response = await self.client.request(method, path)
                    self.assert_safe_error(
                        response, 405, "METHOD_NOT_ALLOWED", "Method not allowed."
                    )
                    self.assertEqual("GET", response.headers["allow"])
            self.assertEqual(405, (await self.client.head(path)).status_code)

    async def test_internal_errors_do_not_escape_or_expose_diagnostics(self):
        with patch.object(
            Readiness, "is_ready",
            new=AsyncMock(side_effect=RuntimeError("private-diagnostic-sentinel")),
        ):
            with self.assertNoLogs("uvicorn.error", level=logging.DEBUG):
                response = await self.client.get("/health/ready")
        self.assert_safe_error(
            response, 500, "INTERNAL_ERROR", "An internal error occurred."
        )
        self.assertNotIn("private-diagnostic-sentinel", response.text)

    async def test_validation_errors_never_echo_input_or_exception_details(self):
        exception = RequestValidationError(
            [{"type": "value_error", "msg": "private-diagnostic-sentinel"}],
            body={"untrusted": "private-diagnostic-sentinel"},
        )
        with patch.object(
            Readiness, "is_ready", new=AsyncMock(side_effect=exception)
        ):
            response = await self.client.get("/health/ready")
        self.assert_safe_error(
            response, 400, "VALIDATION_FAILED", "Request validation failed."
        )
        self.assertNotIn("private-diagnostic-sentinel", response.text)

    async def test_errors_use_fresh_server_generated_correlation_ids(self):
        responses = [
            await self.client.get("/missing", headers={"X-Request-ID": "untrusted"})
            for _ in range(2)
        ]
        ids = [response.json()["error"]["requestId"] for response in responses]
        self.assertNotEqual(*ids)
        for request_id in ids:
            self.assertEqual(4, UUID(request_id).version)

    async def test_openapi_source_and_route_matrix_match_exactly(self):
        self.assertEqual(self.contract, self.application.openapi())
        self.assertEqual("0.1.0", self.application.version)
        project = tomllib.loads(
            (CONTRACT_PATH.parent / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(project["project"]["version"], self.application.version)
        routes = self.application.routes
        self.assertTrue(all(isinstance(route, APIRoute) for route in routes))
        self.assertEqual(set(self.contract["paths"]), {route.path for route in routes})
        for route in routes:
            self.assertEqual({"GET"}, route.methods)
            operation = self.contract["paths"][route.path]["get"]
            self.assertEqual(operation["operationId"], route.operation_id)
            self.assertEqual([], operation["security"])
            self.assertEqual(["Health"], route.tags)
            self.assertEqual({"200", "default"} | (
                {"503"} if route.path == "/health/ready" else set()
            ), set(operation["responses"]))
        modified = self.application.openapi()
        modified["paths"].clear()
        self.assertEqual(self.contract, self.application.openapi())

    async def test_contract_schemas_and_all_response_examples_are_valid(self):
        for schema in self.contract["components"]["schemas"].values():
            Draft202012Validator.check_schema(schema)
        for path in self.contract["paths"].values():
            for response in path["get"]["responses"].values():
                if "$ref" in response:
                    response = self.contract["components"]["responses"]["SafeError"]
                content = response["content"]["application/json"]
                schema = deepcopy(content["schema"])
                schema["components"] = self.contract["components"]
                if "example" in content:
                    Draft202012Validator(
                        schema, format_checker=Draft202012Validator.FORMAT_CHECKER
                    ).validate(content["example"])


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_configuration_is_bounded(self):
        for timeout in (0, -1, 5.01, float("inf"), float("-inf"), float("nan"), True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    Readiness(timeout_seconds=timeout)

    async def test_probe_list_is_snapshotted_at_app_creation(self):
        checks = []
        readiness = Readiness(checks)
        checks.append(AsyncMock(return_value=False))
        self.assertTrue(await readiness.is_ready())

    async def test_timeout_is_an_overall_budget_not_reset_per_probe(self):
        first = AsyncMock(return_value=True)
        cancelled = asyncio.Event()

        async def second():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch(
            "backend.app.health.asyncio.timeout", wraps=asyncio.timeout
        ) as timeout:
            self.assertFalse(
                await Readiness([first, second], timeout_seconds=0.02).is_ready()
            )
        timeout.assert_called_once_with(0.02)
        first.assert_awaited_once_with()
        self.assertTrue(cancelled.is_set())

    async def test_request_cancellation_is_not_converted_to_readiness_failure(self):
        entered = asyncio.Event()
        finished = asyncio.Event()

        async def probe():
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        task = asyncio.create_task(Readiness([probe]).is_ready())
        await asyncio.wait_for(entered.wait(), timeout=1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(finished.is_set())


if __name__ == "__main__":
    unittest.main()
