import unittest

from elektro_engel import (
    ContextError,
    ContextStore,
    CoreEngine,
    InMemoryAuditLog,
    LearningSandbox,
    RequestError,
    TaskRequest,
    ToolApproval,
    ToolApprovalRequired,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistry,
)


class CoreTests(unittest.TestCase):
    def test_planning_is_bounded_and_does_not_execute_tools(self):
        calls = []
        tools = ToolRegistry()
        tools.register("send_message", lambda arguments: calls.append(arguments))
        audit = InMemoryAuditLog()
        engine = CoreEngine(tools=tools, audit_log=audit)
        request = TaskRequest("Review the draft")

        plan = engine.plan(request)

        self.assertEqual(request.request_id, plan.request_id)
        self.assertEqual(1, len(plan.steps))
        self.assertTrue(plan.steps[0].requires_human_review)
        self.assertFalse(calls)
        self.assertEqual("proposed", audit.events()[0].outcome)

    def test_request_rejects_empty_and_oversized_objectives(self):
        with self.assertRaises(RequestError):
            TaskRequest(" ")
        with self.assertRaises(RequestError):
            TaskRequest("x" * 2_001)
        with self.assertRaises(RequestError):
            TaskRequest("Review", request_id="token=private")

    def test_context_is_explicit_bounded_and_clearable(self):
        context = ContextStore(max_entries=1)
        context.put("locale", "de", category="non_sensitive")
        self.assertEqual({"locale": "de"}, context.snapshot())
        with self.assertRaises(ContextError):
            context.put("token", "not retained", category="sensitive")
        with self.assertRaises(ContextError):
            context.put("extra", "value", category="non_sensitive")
        context.clear()
        self.assertEqual({}, context.snapshot())

    def test_tool_requires_exact_explicit_request_and_tool_approval(self):
        calls = []
        tools = ToolRegistry()
        tools.register("calculate", lambda arguments: calls.append(dict(arguments)) or 4)
        engine = CoreEngine(tools=tools)
        request = TaskRequest("Calculate")

        with self.assertRaises(ToolApprovalRequired):
            engine.execute(
                request,
                "calculate",
                {"value": 2},
                ToolApproval(request.request_id, "calculate", False),
            )
        with self.assertRaises(ToolApprovalRequired):
            engine.execute(
                request,
                "calculate",
                {"value": 2},
                ToolApproval("another-request", "calculate", True),
            )
        self.assertFalse(calls)

        result = engine.execute(
            request,
            "calculate",
            {"value": 2},
            ToolApproval(request.request_id, "calculate", True),
        )
        self.assertEqual(4, result)
        self.assertEqual([{"value": 2}], calls)

    def test_unknown_tools_and_tool_errors_are_bounded(self):
        engine = CoreEngine()
        request = TaskRequest("Run a tool")
        approval = ToolApproval(request.request_id, "missing", True)
        with self.assertRaises(ToolNotFoundError):
            engine.execute(request, "token=private", {}, approval)
        self.assertIsNone(engine.audit_log.events()[0].tool_name)

        tools = ToolRegistry()
        tools.register("failure", lambda _: (_ for _ in ()).throw(ValueError("sensitive")))
        engine = CoreEngine(tools=tools)
        approval = ToolApproval(request.request_id, "failure", True)
        with self.assertRaisesRegex(ToolExecutionError, "^approved tool execution failed$"):
            engine.execute(request, "failure", {}, approval)
        self.assertEqual("denied_or_failed", engine.audit_log.events()[0].outcome)
        self.assertNotIn("sensitive", repr(engine.audit_log.events()))

    def test_learning_sandbox_only_retains_unvalidated_proposals(self):
        sandbox = LearningSandbox()
        proposal = sandbox.propose("proposal-1", "candidate policy")
        self.assertEqual("unvalidated", proposal.status)
        self.assertEqual((proposal,), sandbox.proposals())
        sandbox.clear()
        self.assertEqual((), sandbox.proposals())


if __name__ == "__main__":
    unittest.main()
