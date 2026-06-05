"""Generate research and algorithm documents."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.algorithm_agent import AlgorithmAgent
from agent.research_agent import ResearchAgent


def main() -> None:
    print(f"Wrote {ResearchAgent().run()}")
    print(f"Wrote {AlgorithmAgent().run()}")


if __name__ == "__main__":
    main()
