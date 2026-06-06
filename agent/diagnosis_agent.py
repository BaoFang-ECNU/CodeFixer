"""DiagnosisAgent for explicit bug attribution."""

from __future__ import annotations

from agent.base import BaseAgent
from training.bug_taxonomy import BugTaxonomy


class DiagnosisAgent(BaseAgent):
    """Diagnose bug type from issue, source, and test feedback."""

    def __init__(self, taxonomy: BugTaxonomy | None = None):
        self.taxonomy = taxonomy or BugTaxonomy()

    def run(self, observation: dict) -> dict:
        return self.taxonomy.diagnose(observation).to_dict()

