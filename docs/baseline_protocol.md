# V0 Baseline Protocol: mini-SWE-agent + Qwen3-Coder-30B-A3B on SWE-bench Lite

## Research Question

Without structured feedback, learned feedback selection, training, or fine-tuning, what SWE-bench Lite repair capability can local Qwen3-Coder-30B-A3B-Instruct reach when driven by vanilla mini-SWE-agent?

## Why This Is The Baseline

All later variants should be compared against this run. The goal is to avoid attributing the base model's existing coding and repair ability to later feedback strategies.

Fixed baseline settings:

- Agent: vanilla mini-SWE-agent
- Model: Qwen3-Coder-30B-A3B-Instruct
- Served model name: qwen3-coder-30b-a3b
- Inference: local vLLM OpenAI-compatible server, TP=4, bf16
- Port: 8001
- Initial max model length: 16384
- Temperature: 0
- SWE-bench subset: Lite
- Split: test
- Workers: 1
- Step limit: 80
- No structured feedback
- No selector
- No training
- No fine-tuning
- No paid API

## Later Versions

- V1: structured-feedback mini-SWE-agent
- V2: learned-selector mini-SWE-agent
- V3: optional self-evolution or preference data export

## Metrics

- Resolved rate
- Repair@k if later experiments generate multiple candidates
- Average step count
- Average wall time
- Failure type distribution
- Trajectory count
- Evaluation success and failure counts

## Ablation Slots

These are not implemented in V0, but the baseline keeps room for later comparison:

- Remove structured feedback
- Remove learned selector
- Remove execution verification
- Compare feedback formats
- Compare step limits
- Compare temperatures
