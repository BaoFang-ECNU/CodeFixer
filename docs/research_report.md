# Research Report

## Existing Directions

Code repair agents usually combine repository understanding, tool use, patch
generation, and test feedback. SWE-bench defines realistic issue-resolution
tasks; SWE-agent shows the value of a controlled Agent-Computer Interface;
AutoCodeRover emphasizes structured localization; Agentless demonstrates a
strong localization-patch-validation pipeline; RLVR/OPD/DPO/self-evolution
methods convert verifiable outcomes into training or distillation data.

## Reproducibility

Toy tasks are the safest first step because they make the whole loop observable
and cheap. SWE-bench Lite is the natural next benchmark once sandboxing,
dependency setup, and timeout handling become more mature. Defects4J is useful
for Java repair but requires a separate environment manager.

## Recommended Route

1. Build a deterministic tool loop and trajectory logger.
2. Use test output as visible reward.
3. Store successful and failed rollouts.
4. Export DPO and OPD data without requiring model training.
5. Replace the rule policy with optional LLM or trainable policies later.

## Minimum and Advanced Versions

- Minimum: eight toy tasks, rule policy, pytest feedback, JSONL trajectory,
  reward, evaluation, ablations, and CI.
- Advanced: SWE-bench Lite adapter connected to real repositories, repository
  graph search, hidden tests, LLM policy, best-of-N patch search, real
  DPO/OPD/RLVR training.
