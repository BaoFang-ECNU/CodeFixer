# Experiment Log Template

## Run Metadata

- Date:
- Operator:
- Git commit:
- Run name:
- Slice:
- Model path:
- Served model name: qwen3-coder-30b-a3b
- API base: http://127.0.0.1:8001/v1
- mini-SWE-agent version:
- SWE-bench version:

## Fixed Settings

- Agent: vanilla mini-SWE-agent
- Temperature: 0
- Step limit: 80
- Workers: 1
- Max model length: 16384
- Tensor parallel size: 4
- No structured feedback
- No selector
- No training or fine-tuning

## Commands

```bash
source /inspire/ssd/project/machine-behavior/czxs25150055/vllm-cu128-fast/bin/activate
bash scripts/check_vllm_server.sh
bash scripts/run_slice.sh 0 5
bash scripts/run_eval.sh outputs/runs/qwen3_lite_test_0_5/preds.json qwen3_lite_0_5
python scripts/collect_summary.py
```

## Results

- Number of instances:
- Number resolved:
- Resolved rate:
- Average steps:
- Average wall time:
- Runtime failures:
- Evaluation failures:

## Notes

- CLI adjustments:
- Environment issues:
- Failure patterns:
- Follow-up action:
