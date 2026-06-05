"""AlgorithmAgent writes the project algorithm design document."""

from __future__ import annotations

from pathlib import Path

from agent.base import BaseAgent


class AlgorithmAgent(BaseAgent):
    """Create the POMDP and self-evolution design document."""

    def run(self, output_path: str | Path = "docs/algorithm_design.md") -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ALGORITHM_DESIGN, encoding="utf-8")
        return path


ALGORITHM_DESIGN = """# Algorithm Design

## POMDP Formulation
- Observation: issue text, source snapshot, test files, last test output, current diff, tool history, and budget.
- Hidden state: true repository state, hidden tests, dependency health, and whether a patch generalizes.
- Actions: inspect_file, search_code, edit_file, run_tests, get_diff, revert_last_edit, final_answer.
- Transition: edits mutate the workspace; tests reveal partial feedback; memory updates across tasks.
- Termination: visible tests pass, max steps reached, timeout, or repeated invalid actions.

## Reward
R combines visible pass reward, improvement reward, patch-size penalty, tool-call penalty, unsafe-edit penalty,
timeout penalty, and no-progress penalty. Hidden/regression tests are represented by a proxy in the toy version.

## Self-Evolution
Successful trajectories become OPD teacher records. Successful/failing trajectory pairs become DPO preference
records. Memory stores action-pattern success rates and failure summaries for future policy updates.
"""

