"""DAPOM evaluation entry point; never starts a model training loop."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
from datetime import datetime, timezone
from torch.utils.data import DataLoader
from DAPOM.model import (DAPOMAgent, OpenAICompatibleAPI, LawDataset, final_evaluation,
                         ConstraintExtractionEngine, ConstraintTensorSpace, LagrangianOptimizer)
from runtime_config import load_runtime_config


def make_agent(client=None, variant='full', runtime_config=None, runtime_constraints=None,
               fixed_constraints=None, trace_path=None):
    return DAPOMAgent(client or OpenAICompatibleAPI(), ConstraintExtractionEngine(),
                      ConstraintTensorSpace(), LagrangianOptimizer(),
                      runtime_config=runtime_config if runtime_config is not None else load_runtime_config(),
                      runtime_constraints=runtime_constraints, fixed_constraints=fixed_constraints,
                      variant=variant, trace_path=trace_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', choices=['small', 'big'], default='small')
    parser.add_argument('--constraints', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'results')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    test_path = root / ('cail_small/data_test.jsonl' if args.dataset == 'small' else 'cail_big/test.jsonl')
    constraints = json.loads(args.constraints.read_text(encoding='utf-8')) if args.constraints else {}
    run = args.output / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    agent = make_agent(runtime_constraints=constraints, trace_path=run / 'trajectory.jsonl')
    data = LawDataset(test_path)
    metrics = final_evaluation(agent, DataLoader(data, batch_size=1, collate_fn=list), 'cpu',
                               record_path=run / 'predictions.jsonl')
    (run / 'summary.json').write_text(json.dumps({'dataset': args.dataset, 'metrics': metrics,
        'sample_count': len(data), 'excluded_special_terms': data.excluded_special_terms,
        'term_bins_months': [6, 12, 36, 60, 120], 'special_term_policy': 'exclude_life_and_death',
        'model': agent.llm_client.model_name, 'generation': agent.llm_client.generation_kwargs,
        'constraints': constraints, 'completed_at': datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == '__main__':
    main()
