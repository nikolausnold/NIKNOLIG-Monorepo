import concurrent.futures
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
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

    def stage(self, entry):
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id,
                solution_entry_version=entry.version, positive=True,
            )
        return self.service.stage_learning(
            principal(), issue_code="installation",
            solution_entry_id=entry.entry_id, solution_entry_version=entry.version,
        )

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

    def test_registration_rejects_other_app_before_audit_or_storage(self):
        for app, other in (
            ("niknolig", "niknolig-defense"), ("niknolig-defense", "niknolig"),
        ):
            for trust in ("pending", "approved", "revoked"):
                with self.subTest(app=app, trust=trust):
                    foreign = source("foreign-source", scope=other, trust=trust)
                    before = list(self.audit.events)
                    with self.assertRaises(PermissionError):
                        self.service.register_source(principal(app), foreign)
                    self.assertEqual(before, self.audit.events)
                    self.assertIsNone(self.repository.get_source(foreign.source_id))
            own = source(app + "-source", scope=app)
            self.service.register_source(principal(app), own)
            self.assertEqual(own, self.repository.get_source(own.source_id))

    def test_versions_are_immutable_and_sequential(self):
        first = self.publish()
        second = self.publish(entry_id=first.entry_id, title="Install reliably")
        self.assertEqual(1, first.version)
        self.assertEqual(2, second.version)
        self.assertEqual(second, self.repository.current(first.entry_id))
        with self.assertRaises(ValueError):
            self.repository.publish(replace(second, version=4))
        self.assertEqual(first, self.repository.get_version(first.entry_id, 1))
        self.assertIsNone(self.repository.get_version(first.entry_id, 3))

    def test_feedback_and_candidates_stay_bound_to_entry_version(self):
        first = self.publish()
        candidate = self.stage(first)
        second = self.publish(entry_id=first.entry_id, content="Use different steps.")
        with self.assertRaises(ValueError):
            self.service.stage_learning(
                principal(), issue_code="installation",
                solution_entry_id=second.entry_id, solution_entry_version=second.version,
            )
        self.assertEqual((0, 0), self.repository.feedback_counts(
            "niknolig", "installation", second.entry_id, second.version,
        ))
        self.service.record_feedback(
            principal(), issue_code="installation", solution_entry_id=second.entry_id,
            solution_entry_version=second.version, positive=False,
        )
        self.assertEqual((3, 0), self.repository.feedback_counts(
            "niknolig", "installation", first.entry_id, first.version,
        ))
        self.assertEqual(first.version, candidate.solution_entry_version)
        self.assertEqual(first.entry_id, candidate.solution_entry_id)
        historical = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=first.entry_id,
            solution_entry_version=first.version,
        )
        self.assertEqual(3, historical.positive_count)
        self.assertEqual(first.version, historical.solution_entry_version)
        self.service.reject_learning(principal(), candidate.candidate_id)
        self.assertEqual(first.version, self.repository.get_candidate(
            candidate.candidate_id,
        ).solution_entry_version)
        newer = self.stage(second)
        self.assertEqual(second.version, newer.solution_entry_version)
        self.assertEqual((3, 1), (newer.positive_count, newer.negative_count))

    def test_feedback_versions_are_explicit_validated_and_app_scoped(self):
        entry = self.publish()
        for version in (0, -1, True, "1", 99):
            with self.subTest(version=version):
                before = list(self.audit.events)
                with self.assertRaises((ValueError, PermissionError)):
                    self.service.record_feedback(
                        principal(), issue_code="installation",
                        solution_entry_id=entry.entry_id,
                        solution_entry_version=version, positive=True,
                    )
                with self.assertRaises((ValueError, PermissionError)):
                    self.service.stage_learning(
                        principal(), issue_code="installation",
                        solution_entry_id=entry.entry_id, solution_entry_version=version,
                    )
                self.assertEqual(before, self.audit.events)
        with self.assertRaises(PermissionError):
            self.service.record_feedback(
                principal("niknolig-defense"), issue_code="installation",
                solution_entry_id=entry.entry_id, solution_entry_version=entry.version,
                positive=True,
            )
        self.assertEqual((0, 0), self.repository.feedback_counts(
            "niknolig", "installation", entry.entry_id, entry.version,
        ))

    def test_feedback_has_no_free_text_and_learning_requires_review(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
                solution_entry_version=entry.version,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id,
            solution_entry_version=entry.version,
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
        approved = self.repository.get_candidate(candidate.candidate_id)
        self.assertEqual("approved", approved.state)
        self.assertEqual(entry.version, approved.solution_entry_version)
        self.assertEqual("learning_candidate_approval_requested",
                         self.audit.events[-1]["event"])
        with self.assertRaises(PermissionError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Duplicate", content="Cannot approve twice.",
            )

    def test_learning_candidate_can_be_rejected_without_publishing(self):
        entry = self.publish()
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
                solution_entry_version=entry.version,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id,
            solution_entry_version=entry.version,
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
            solution_entry_version=entry.version,
        )
        with self.assertRaises(ValueError):
            self.service.stage_learning(
                principal(), issue_code="installation", solution_entry_id=entry.entry_id,
                solution_entry_version=entry.version,
            )

    def test_concurrent_approvals_publish_once(self):
        candidate = self.stage(self.publish())
        barrier = threading.Barrier(2)
        write = self.audit.write

        def audit(event):
            write(event)
            if event["event"] == "learning_candidate_approval_requested":
                barrier.wait(timeout=5)

        def approve():
            try:
                return self.service.approve_learning(
                    principal(), candidate.candidate_id, source_id="manual",
                    title="Reviewed solution", content="Use approved steps.",
                )
            except RuntimeError:
                return None

        before = len(self.repository.search(()))
        with patch.object(self.audit, "write", side_effect=audit):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(approve) for _ in range(2)]
                results = [future.result(timeout=10) for future in futures]
        self.assertEqual(1, sum(result is not None for result in results))
        self.assertEqual(before + 1, len(self.repository.search(())))
        self.assertEqual("approved", self.repository.get_candidate(candidate.candidate_id).state)

    def test_concurrent_approval_and_rejection_are_serialized(self):
        for winner in ("approve", "reject"):
            with self.subTest(winner=winner):
                candidate = self.stage(self.publish())
                barrier = threading.Barrier(2)
                committed = threading.Event()
                write = self.audit.write

                def audit(event):
                    write(event)
                    actions = {
                        "learning_candidate_approval_requested": "approve",
                        "learning_candidate_rejected": "reject",
                    }
                    if event["event"] in actions:
                        barrier.wait(timeout=5)
                        if actions[event["event"]] != winner:
                            self.assertTrue(committed.wait(timeout=5))

                def review(action):
                    try:
                        if action == "approve":
                            self.service.approve_learning(
                                principal(), candidate.candidate_id, source_id="manual",
                                title="Reviewed solution", content="Use approved steps.",
                            )
                        else:
                            self.service.reject_learning(principal(), candidate.candidate_id)
                        return True
                    except RuntimeError:
                        return False
                    finally:
                        if action == winner:
                            committed.set()

                before = len(self.repository.search(()))
                with patch.object(self.audit, "write", side_effect=audit):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                        futures = {action: pool.submit(review, action)
                                   for action in ("approve", "reject")}
                        results = {action: future.result(timeout=10)
                                   for action, future in futures.items()}
                self.assertTrue(results[winner])
                self.assertFalse(results["reject" if winner == "approve" else "approve"])
                self.assertEqual(before + int(winner == "approve"),
                                 len(self.repository.search(())))
                self.assertEqual("approved" if winner == "approve" else "rejected",
                                 self.repository.get_candidate(candidate.candidate_id).state)

    def test_failed_approval_commits_neither_publication_nor_state(self):
        entry = self.publish()
        candidate = self.stage(entry)
        before = self.repository.search(())
        with self.assertRaises(ValueError):
            self.repository.approve_candidate(candidate.candidate_id, entry)
        self.assertEqual("pending", self.repository.get_candidate(candidate.candidate_id).state)
        self.assertEqual(before, self.repository.search(()))
        self.audit.fail = True
        with self.assertRaises(RuntimeError):
            self.service.approve_learning(
                principal(), candidate.candidate_id, source_id="manual",
                title="Reviewed solution", content="Use approved steps.",
            )
        self.assertEqual("pending", self.repository.get_candidate(candidate.candidate_id).state)
        self.assertEqual(before, self.repository.search(()))
        self.assertIsNone(self.repository.approve_candidate(uuid4(), entry))

    def test_approval_cannot_cross_app_boundaries(self):
        entry = self.publish()
        candidate = None
        for _ in range(3):
            self.service.record_feedback(
                principal(), issue_code="installation",
                solution_entry_id=entry.entry_id, positive=True,
                solution_entry_version=entry.version,
            )
        candidate = self.service.stage_learning(
            principal(), issue_code="installation", solution_entry_id=entry.entry_id,
            solution_entry_version=entry.version,
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
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertIsNone(self.repository.current(uuid4()))

    def test_disabled_research_never_calls_external_service(self):
        with self.assertRaises(RuntimeError):
            self.service.research(principal(), "model_candidates")
        self.assertIsInstance(self.service.research_provider, DisabledResearchProvider)

    def test_empty_research_allowlist_prevents_provider_call(self):
        class Provider:
            provider_id = "approved-test"

            def search(self, query):
                raise AssertionError("Research must not be dispatched")

        service = KnowledgeService(
            self.repository, research_provider=Provider(), audit=self.audit,
            clock=lambda: NOW, research_approved=True, research_cost_approved=True,
        )
        with self.assertRaisesRegex(ValueError, "host allowlist"):
            service.research(principal(), "model_candidates")

    def test_retrieval_context_counts_all_newlines_at_exact_boundaries(self):
        for title in ("First setup", "Second setup", "Third setup"):
            self.publish(title=title)
        hits = self.service.search(principal(), "setup")
        full = self.service.retrieval_context(hits)
        parts = full.split("\n")
        self.assertEqual(4, len(parts))
        header = parts[0]
        self.assertEqual(header, self.service.retrieval_context((), max_chars=len(header)))
        for count in range(1, len(parts) + 1):
            expected = "\n".join(parts[:count])
            with self.subTest(count=count):
                self.assertEqual(expected, self.service.retrieval_context(
                    hits, max_chars=len(expected),
                ))
                if count > 1:
                    budget = len(expected) - 1
                    context = self.service.retrieval_context(hits, max_chars=budget)
                    self.assertEqual("\n".join(parts[:count - 1]), context)
                    self.assertLessEqual(len(context), budget)

    def test_retrieval_context_rejects_budgets_smaller_than_header(self):
        header = self.service.retrieval_context(())
        for budget in (0, 1, len(header) - 1, True, 6000.0, 12001):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.service.retrieval_context((), max_chars=budget)

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
