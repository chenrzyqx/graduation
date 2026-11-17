"""Evaluate real configured baselines; never relabel a toy model as a published method."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from DAPOM.main import make_agent
from DAPOM.model import final_evaluation
from DAPOM.models.llm_only import LLMAgent

THESIS_BASELINES = ('TFIDF-SVM', 'LSTM', 'TOPJUDGE', 'BERT', 'NeurJudge', 'ML-LJP',
                   'CL4LJP', 'Qwen3', 'LexiLaw')


def run_comparison_experiment(llm_client, test_loader, device, *, baseline_runners=None,
                             runtime_config=None, runtime_constraints=None, record_dir=None):
    # External adapters must return per-sample predictions, not copied table scores.
    baseline_runners = baseline_runners or {}
    unknown = set(baseline_runners) - set(THESIS_BASELINES)
    if unknown:
        raise ValueError(f'Unknown baseline names: {unknown}')
    models = {'DAPOM': make_agent(llm_client, runtime_config=runtime_config,
                                 runtime_constraints=runtime_constraints),
              'DeepSeek-R1': LLMAgent(llm_client, runtime_config=runtime_config), **baseline_runners}
    results = {}
    for name, model in models.items():
        model.to(device)
        results[name] = final_evaluation(model, test_loader, device,
            record_path=Path(record_dir) / f'{name}_predictions.jsonl' if record_dir else None)
    return {'measured': results, 'not_configured': sorted(set(THESIS_BASELINES) - set(baseline_runners))}
