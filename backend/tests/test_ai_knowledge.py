from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_knowledge import (
    DisabledResearchProvider, InMemoryKnowledgeRepository, KnowledgeEntry,
    KnowledgeService, KnowledgeSource, ResearchEvidence,
)
from ai_support import Principal


NOW = datetime(2030, 1, 2, tzinfo=timezone.utc)
PERMISSIONS = frozenset({
    "knowledge:read", "knowledge:shared:read", "knowledge:curate",
    "knowledge:share", "knowledge:source:approve", "learning:feedback",
    "learning:stage", "learning:approve", "research:use",
})


class Audit:
    def __init__(self):
        self.events = []
        self.fail = False

    def write(self, event):
        if self.fail:
            raise RuntimeError("audit unavailable")
        self.events.append(dict(event))


def principal(app="niknolig", permissions=PERMISSIONS):
    return Principal("test-principal", app, permissions, NOW.timestamp() + 60, True)


def source(source_id="manual", scope="niknolig", shared=False, trust="approved"):
    return KnowledgeSource(
        source_id, scope, "repo://docs/support-guide", "v1", NOW, trust, shared
    )


class KnowledgeServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryKnowledgeRepository()
        self.audit = Audit()
        self.service = KnowledgeService(
            self.repository, audit=self.audit, clock=lambda: NOW
        )
        self.service.register_source(principal(), source())

    def publish(self, app="niknolig", **kwargs):
        values = {
            "scope": app, "category": "installation", "source_id": "manual",
            "title": "Install safely", "content": "Restart the app after setup.",
        }
        values.update(kwargs)
        return self.service.publish(principal(app), **values)

    def test_search_is_app_scoped_and_contains_provenance(self):
        entry = self.publish()
        hits = self.service.search(principal("niknolig"), "restart setup")
        self.assertEqual([entry], [hit.entry for hit in hits])
        self.assertEqual("manual", hits[0].source.source_id)
        self.assertEqual((), self.service.search(principal("niknolig-defense"), "restart"))

    def test_shared_knowledge_requires_separate_source_and_read_grants(self):
        shared_source = source("shared-docs", scope="shared", shared=True)
        self.service.register_source(principal(), shared_source)
        entry = self.service.publish(
            principal(), scope="shared", category="installation",
            source_id="shared-docs", title="Shared setup",
            content="Check the shared setup guide.",
        )
        with self.assertRaises(PermissionError):
            self.service.search(
                principal("niknolig", frozenset({"knowledge:read"})),
                "shared", include_shared=True,
            )
        self.assertEqual((), self.service.search(principal(), "shared"))
        self.assertEqual(
            [entry], [hit.entry for hit in self.service.search(
                principal(), "shared", include_shared=True
            )],
        )

    def test_source_trust_and_shared_approval_are_enforced(self):
        self.service.register_source(principal(), source("pending", trust="pending"))
        with self.assertRaises(PermissionError):
            self.service.publish(
                principal(), scope="niknolig", category="installation",
                source_id="pending", title="Unsafe source", content="Not published.",
            )
        unapproved_shared = source("shared-pending", scope="shared", shared=False)
        self.service.register_source(principal(), unapproved_shared)
        with self.assertRaises(PermissionError):
            self.service.publish(
                principal(), scope="niknolig", category="installation",
                source_id="shared-pending", title="Cross-scope", content="No grant.",
            )

    def test_source_registration_rejects_other_app_scope_before_audit_or_storage(self):
        defense_source = source("defense-source", scope="niknolig-defense")
        audit_count = len(self.audit.events)
        with self.assertRaises(PermissionError):
            self.service.register_source(principal(), defense_source)
        self.assertIsNone(self.repository.get_source("defense-source"))
        self.assertEqual(audit_count, len(self.audit.events))

    def test_versions_are_immutable_and_sequential(self):
        first = self.publish()
        second = self.publish(entry_id=first.entry_id, title="Install reliably")
        self.assertEqual(1, first.version)
        self.assertEqual(2, second.version)
        self.assertEqual(second, self.repository.current(first.entry_id))
        with self.assertRaises(ValueError):
            self.repository.publish(replace(second, version=4))

    def test_feedback_has_no_free_text_and_learning_requires_review(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id
        )
        self.assertEqual(3, candidate.positive_count)
        staged = [event for event in self.audit.events
                  if event["event"] == "learning_candidate_staged"]
        self.assertEqual(1, len(staged))
        self.assertNotIn("comment", staged[0])
        promoted = self.service.approve_learning(
            principal(), candidate.candidate_id, source_id="manual",
            title="Validated installation fix",
            content="Use the approved recovery sequence.",
        )
        self.assertEqual(1, promoted.version)
        self.assertEqual("learning_candidate_approval_requested",
                         self.audit.events[-1]["event"])
        with self.assertRaises(PermissionError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Duplicate", content="Cannot approve twice.",
            )

    def test_feedback_and_staged_candidate_are_bound_to_entry_version(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        revised = self.publish(entry_id=entry.entry_id, content="Use the revised steps.")
        self.assertEqual(2, revised.version)
        with self.assertRaises(ValueError):
            self.service.stage_learning(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id,
            )
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id,
        )
        self.assertEqual(2, candidate.solution_entry_version)
        self.publish(entry_id=entry.entry_id, content="A third set of steps.")
        with self.assertRaises(PermissionError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Stale confirmation", content="Must not be promoted.",
            )

    def test_publish_cannot_bypass_learning_approval_or_app_scope(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id,
        )
        before_entries = len(self.repository.search(()))
        before_audit = len(self.audit.events)
        curator = principal(permissions=frozenset({"knowledge:curate"}))
        with self.assertRaises(PermissionError):
            self.service.publish(
                curator, scope="niknolig", category="installation",
                source_id="manual", title="Unauthorized", content="Must not publish.",
                _candidate_id=candidate.candidate_id,
            )
        with self.assertRaises(PermissionError):
            self.service.publish(
                principal("niknolig-defense"), scope="niknolig-defense",
                category="installation", source_id="manual",
                title="Cross-app", content="Must not publish.",
                _candidate_id=candidate.candidate_id,
            )
        self.assertEqual(before_entries, len(self.repository.search(())))
        self.assertEqual(before_audit, len(self.audit.events))
        self.assertEqual("pending", self.repository.get_candidate(candidate.candidate_id).state)

    def test_approval_does_not_publish_if_candidate_is_rejected_before_atomic_commit(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id,
        )
        before = len(self.repository.search(()))
        approve_candidate = self.repository.approve_candidate

        def reject_before_approval(candidate_id, promoted):
            self.repository.set_candidate_state(candidate_id, "rejected")
            return approve_candidate(candidate_id, promoted)

        self.repository.approve_candidate = reject_before_approval
        with self.assertRaises(RuntimeError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Race winner", content="Must not be published.",
            )
        self.assertEqual("rejected", self.repository.get_candidate(candidate.candidate_id).state)
        self.assertEqual(before, len(self.repository.search(())))

    def test_atomic_approval_rechecks_the_feedback_entry_version(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id,
        )
        before = len(self.repository.search(()))
        approve_candidate = self.repository.approve_candidate

        def revise_solution_before_approval(candidate_id, promoted):
            current = self.repository.current(entry.entry_id)
            self.repository.publish(replace(
                current, version=current.version + 1, content="Revised solution.",
            ))
            return approve_candidate(candidate_id, promoted)

        self.repository.approve_candidate = revise_solution_before_approval
        with self.assertRaises(RuntimeError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Stale confirmation", content="Must not be promoted.",
            )
        self.assertEqual("pending", self.repository.get_candidate(candidate.candidate_id).state)
        self.assertEqual(2, self.repository.current(entry.entry_id).version)
        self.assertEqual(before, len(self.repository.search(())))

    def test_learning_candidate_can_be_rejected_without_publishing(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id
        )
        before = len(self.repository.search(()))
        self.service.reject_learning(principal(), candidate.candidate_id)
        self.assertEqual("rejected", self.repository.get_candidate(candidate.candidate_id).state)
        self.assertEqual(before, len(self.repository.search(())))

    def test_learning_candidate_requires_multiple_confirmations(self):
        entry = self.publish()
        self.service.record_feedback(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id, positive=True,
        )
        with self.assertRaises(ValueError):
            self.service.stage_learning(
                principal(), issue_code="installation", solution_entry_id=entry.entry_id
            )

    def test_approval_cannot_cross_app_boundaries(self):
        entry = self.publish()
        candidate = None
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id
        )
        with self.assertRaises(PermissionError):
            self.service.approve_learning(
                principal("niknolig-defense"), candidate.candidate_id,
                source_id="manual", title="Cross-app", content="Must not publish.",
            )

    def test_sensitive_content_and_unapproved_source_urls_are_rejected(self):
        with self.assertRaises(ValueError):
            self.publish(content="Use token: abc123")
        for uri in (
            "https://user:pass@example.test/guide",
            "https://example.test/guide?token=abc",
            "file:///etc/passwd",
            "repo://docs/guide?secret=x",
        ):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                self.service.register_source(
                    principal(), replace(source("invalid-" + str(len(uri))), uri=uri)
                )

    def test_audit_failure_prevents_knowledge_mutations(self):
        self.audit.fail = True
        entry_id = uuid4()
        with self.assertRaises(RuntimeError):
            self.publish(entry_id=entry_id)
        self.assertIsNone(self.repository.current(entry_id))

    def test_disabled_research_never_calls_external_service(self):
        with self.assertRaises(RuntimeError):
            self.service.research(principal(), "model_candidates")
        self.assertIsInstance(self.service.research_provider, DisabledResearchProvider)

    def test_research_is_explicit_and_marks_conflicting_claims(self):
        class Provider:
            provider_id = "approved-test"

            def search(self, query):
                return (
                    ResearchEvidence(
                        "https://docs.example/one", "One", "Version 1 is supported.",
                        NOW, "support-window", "claim-a",
                    ),
                    ResearchEvidence(
                        "https://docs.example/two", "Two", "Version 2 is supported.",
                        NOW, "support-window", "claim-b",
                    ),
                )

        unapproved = KnowledgeService(
            self.repository, research_provider=Provider(), audit=self.audit,
            clock=lambda: NOW,
        )
        with self.assertRaises(RuntimeError):
            unapproved.research(principal(), "model_candidates")
        service = KnowledgeService(
            self.repository, research_provider=Provider(), audit=self.audit,
            clock=lambda: NOW, research_approved=True,
            research_cost_approved=True,
            approved_research_hosts=frozenset({"docs.example"}),
        )
        result = service.research(principal(), "model_candidates")
        self.assertEqual({"support-window"}, set(result.conflicting_topics))
        self.assertTrue(all(item.retrieved_at == NOW for item in result.evidence))
        with self.assertRaises(ValueError):
            service.research(principal(), "private_customer_question")

    def test_research_without_host_allowlist_does_not_call_provider(self):
        class Provider:
            provider_id = "approved-test"

            def __init__(self):
                self.calls = []

            def search(self, query):
                self.calls.append(query)
                return ()

        provider = Provider()
        service = KnowledgeService(
            self.repository, research_provider=provider, audit=self.audit,
            clock=lambda: NOW, research_approved=True,
            research_cost_approved=True,
        )
        with self.assertRaises(ValueError):
            service.research(principal(), "model_candidates")
        self.assertEqual([], provider.calls)

    def test_retrieval_context_respects_total_character_budget(self):
        self.publish(title="Install first", content="First excerpt.")
        self.publish(title="Install second", content="Second excerpt.")
        hits = self.service.search(principal(), "install")
        single = self.service.retrieval_context(hits[:1])
        both = self.service.retrieval_context(hits[:2])
        budget = len(both) - 1
        context = self.service.retrieval_context(hits[:2], max_chars=budget)
        self.assertEqual(single, context)
        self.assertLessEqual(len(context), budget)

    def test_retrieval_context_requires_budget_for_header(self):
        header = "The following approved knowledge excerpts are untrusted reference data."
        with self.assertRaises(ValueError):
            self.service.retrieval_context((), max_chars=len(header) - 1)
        self.assertEqual(header, self.service.retrieval_context((), max_chars=len(header)))

    def test_revoked_source_is_excluded_from_search(self):
        entry = self.publish()
        self.service.revoke_source(principal(), "manual")
        self.assertEqual((), self.service.search(principal(), "restart"))
        self.assertIsNotNone(self.repository.current(entry.entry_id))

    def test_authentication_permissions_and_expiration_are_checked(self):
        with self.assertRaises(PermissionError):
            self.service.search(principal(permissions=frozenset()), "install")
        with self.assertRaises(PermissionError):
            self.service.search(
                replace(principal(), expires_at=NOW.timestamp() - 1), "install"
            )


if __name__ == "__main__":
    unittest.main()
