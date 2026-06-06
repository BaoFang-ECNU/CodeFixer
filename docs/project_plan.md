# Project Plan

## Problem Definition

CodeFixer studies self-evolving post-training for code repair agents. A task
contains an issue, code files, tests, and a command. The agent must inspect the
environment, edit source code, run tests, and output a patch.

## POMDP and Tools

The repair process is a POMDP with partial observations from files and tests,
hidden state from unrevealed tests, and actions implemented as tools:
`inspect_file`, `search_code`, `edit_file`, `run_tests`, `get_diff`,
`revert_last_edit`, and `final_answer`.

## Environment State

`CodeRepairEnv` creates an isolated workspace for each task, copies the issue,
source, and tests, tracks original files, counts tool calls, records unsafe
edits, executes pytest with timeout, and computes unified diffs.

## Reward

The reward model includes visible test pass, test improvement, patch-size
penalty, tool-call penalty, unsafe-edit penalty, timeout penalty, and
no-progress penalty. Hidden tests are approximated by a regression/safety proxy
in the toy version.

## Self-Evolution Loop

The project stores trajectories in JSONL, adds them to a replay buffer, then
summarizes success patterns and failure causes. It exports evolved policy
metadata plus DPO and OPD distillation data for later training.

## Multi-Agent Collaboration

`ResearchAgent` writes survey notes, `AlgorithmAgent` writes the algorithm
design, `CodingAgent` performs repairs, and `EvaluationAgent` runs experiments.
The current orchestrator keeps these responsibilities modular.

## Evaluation and Ablation

Metrics include pass@1, pass@k, visible test pass rate, reward, steps, tool
calls, runtime, patch size, unsafe edit rate, timeout rate, and cost estimate.
Ablations include no memory, no test feedback, no self-evolution, no patch
penalty, and different max-step budgets.

## Current Version

The current version repairs eight toy Python tasks with a rule-based policy and
pytest feedback. It includes optional LLMPolicy scaffolding, GitHub Actions,
SWE-bench Lite metadata loading, repository workspace utilities, richer
evaluation diagnostics, and self-evolution data export. It does not train model
weights yet.

## Roadmap

1. Connect the SWE-bench Lite adapter to real cloned workspaces.
2. Add OpenAI/local LLM integration tests with mocked tool-action responses.
3. Implement full best-of-N patch generation and candidate reranking.
4. Add hidden/regression test suites.
5. Train with DPO, OPD, or RLVR on exported trajectories.

## Third-Stage Implementation

The project now includes a lightweight benchmark builder that generates Python
and JavaScript repair tasks with visible and hidden/regression tests. Evaluation
can compare three system versions: baseline, feedback, and learning/evolution.
The multi-agent path adds DiagnosisAgent, RepairAgent, CriticAgent, and
EvolutionAgent. Metrics now include hidden/regression pass rate, average test
runs, patch file count, API cost estimate, runtime cost, and grouped results by
system version, bug type, language, and project source.

## Risks and Limits

Rule-based repair only handles simple patterns. Toy tests do not prove
generalization. Real repositories need stronger dependency isolation, larger
timeouts, and stricter security controls.
