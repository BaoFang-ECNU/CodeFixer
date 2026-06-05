"""ResearchAgent writes a structured research report."""

from __future__ import annotations

from pathlib import Path

from agent.base import BaseAgent


class ResearchAgent(BaseAgent):
    """Create a concise survey of code repair agent directions."""

    def run(self, output_path: str | Path = "docs/research_report.md") -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RESEARCH_REPORT, encoding="utf-8")
        return path


RESEARCH_REPORT = """# Research Report

## Method Families
- SWE-bench style benchmarks frame repair as resolving real GitHub issues with test oracles.
- SWE-agent emphasizes a well-designed Agent-Computer Interface: inspect, search, edit, run tests, and submit.
- AutoCodeRover and related systems focus on structured repository search before patch generation.
- Agentless shows that localization, candidate patching, and validation/reranking form a strong simple baseline.
- RLVR, OPD, DPO, and self-evolution methods turn verifiable feedback into policy improvement data.

## Reproducibility and Engineering Cost
- Toy tasks and SWE-bench Lite are the most practical early targets.
- Full SWE-bench and Defects4J require stronger sandboxing, dependency management, and longer runtime budgets.
- LLM-backed policies are useful but should sit behind the same policy interface as rule-based agents.

## Recommended Route
1. Build a deterministic repair loop on toy tasks.
2. Save every observation, action, diff, test result, and reward.
3. Export DPO and OPD data from successful and failed trajectories.
4. Add richer localization and optional LLM policies.
5. Scale evaluation to SWE-bench Lite after the local loop is stable.
"""

