"""Structured-agent charge evaluation. Importing this module runs no experiment."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import random
from DSAGM.model import (DSAGMGenerator, load_data, build_label_map_from_train,
                         call_llm, extract_accusation, compute_metrics, build_default_dsl)
from experiment_support import append_record
from runtime_config import load_runtime_config


def create_agent_from_dsl(num_examples=0, train_facts=None, train_accusations=None,
                          strategy='ReAct', runtime_config=None, seed=42):
    config = runtime_config if runtime_config is not None else load_runtime_config()
    ir, runtime = DSAGMGenerator().generate(build_default_dsl(strategy), llm_core=call_llm, **config)
    if num_examples and train_facts:
        indices = random.Random(seed).sample(range(len(train_facts)), min(num_examples, len(train_facts)))
        ir.Memory.short_term = [(train_facts[i], train_accusations[i]) for i in indices]
    return ir, runtime


def main(train_path, test_path, train_shot_size=15, test_sample_size=None, *,
         runtime_config=None, seed=42, record_path=None):
    train_facts, train_labels = load_data(train_path)
    facts, labels = load_data(test_path)
    mapping, classes = build_label_map_from_train(train_labels)
    selected = list(range(len(facts)))
    if test_sample_size is not None and test_sample_size < len(facts):
        selected = random.Random(seed).sample(selected, test_sample_size)
    _, runtime = create_agent_from_dsl(train_shot_size, train_facts, train_labels,
                                      runtime_config=runtime_config, seed=seed)
    truth, predictions = [], []
    excluded = 0
    for index in selected:
        if labels[index] not in mapping:
            excluded += 1
            if record_path:
                append_record(record_path, {'sample_index': index, 'status': 'excluded_unseen_label'})
            continue
        try:
            response = runtime.run(facts[index], all_labels=classes)
            label = extract_accusation(response, classes)
            pred, status, error = mapping.get(label, -1), 'ok' if label else 'invalid_output', None
        except Exception as exc:
            response, pred, status, error = None, -1, 'failed', str(exc)
        truth.append(mapping[labels[index]])
        predictions.append(pred)
        if record_path:
            append_record(record_path, {'sample_index': index, 'true_label': labels[index],
                'predicted_id': pred, 'raw_response': response, 'status': status, 'error': error})
    metrics = compute_metrics(truth, predictions, labels=range(len(classes)))
    return {'metrics': metrics, 'evaluated_samples': len(truth), 'excluded_unseen_labels': excluded,
            'sampling_seed': seed}


if __name__ == '__main__':
    from datetime import datetime, timezone
    root = Path(__file__).resolve().parent
    run_dir = root / 'results' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir.mkdir(parents=True, exist_ok=False)
    result = main(root / 'cail_small/data_train.jsonl', root / 'cail_small/data_test.jsonl',
                  record_path=run_dir / 'predictions.jsonl')
    import json
    (run_dir / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
