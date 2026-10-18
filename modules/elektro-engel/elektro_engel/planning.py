"""Deterministic, bounded planning without model or network access."""

from .models import PlanStep, TaskPlan, TaskRequest

MAX_PLAN_STEPS = 1


class BoundedPlanner:
    """Turn an objective into a review-only plan; never executes the plan."""

    def plan(self, request: TaskRequest) -> TaskPlan:
        return TaskPlan(
            request_id=request.request_id,
            steps=(
                PlanStep(
                    sequence=1,
                    description=f"Review the requested objective: {request.objective.strip()}",
                ),
            ),
        )
