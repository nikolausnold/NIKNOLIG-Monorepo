"""Ephemeral learning experiments; proposals cannot alter active policy."""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_PROPOSALS = 32
MAX_PROPOSAL_CHARS = 1_000


@dataclass(frozen=True)
class RuleProposal:
    proposal_id: str
    candidate: str = field(repr=False)
    status: str = "unvalidated"


class LearningSandbox:
    """Collect bounded, in-memory proposals without evaluating or activating them."""

    def __init__(self) -> None:
        self._proposals: list[RuleProposal] = []

    def propose(self, proposal_id: str, candidate: str) -> RuleProposal:
        if not isinstance(proposal_id, str) or not proposal_id.strip() or len(proposal_id) > 64:
            raise ValueError("proposal_id is invalid")
        if not isinstance(candidate, str) or not candidate.strip() or len(candidate) > MAX_PROPOSAL_CHARS:
            raise ValueError("candidate is invalid")
        if len(self._proposals) >= MAX_PROPOSALS:
            raise ValueError("learning sandbox capacity reached")
        proposal = RuleProposal(proposal_id=proposal_id, candidate=candidate)
        self._proposals.append(proposal)
        return proposal

    def proposals(self) -> tuple[RuleProposal, ...]:
        return tuple(self._proposals)

    def clear(self) -> None:
        self._proposals.clear()
