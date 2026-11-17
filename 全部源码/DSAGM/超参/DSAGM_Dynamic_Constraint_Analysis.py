"""Inference/validation weight selection; no model training or test-vocabulary fitting."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiment_support import classification_metrics, append_record


def run_experiment(lambda_struct_strategy, lambda_sem_strategy, struct_fixed=0.5,
                   sem_fixed=0.5, *, cases, check_candidate, execute_candidate,
                   struct_init, sem_init, update_step, max_iterations=100,
                   record_path=None):
    """Each case supplies candidate configurations and a held-out expected label.

    check_candidate(candidate) returns normalized structure/semantic violations and a
    hard_valid flag. execute_candidate is called only after selection and receives no
    expected label. Original dynamic initial values and update step must be supplied.
    """
    if update_step < 0 or min(struct_init, sem_init, struct_fixed, sem_fixed) < 0:
        raise ValueError('Constraint weights and update step must be nonnegative')
    truth, predictions, valid_count = [], [], 0
    for case_id, case in enumerate(cases):
        weights = [struct_init if lambda_struct_strategy == '动态' else struct_fixed,
                   sem_init if lambda_sem_strategy == '动态' else sem_fixed]
        candidates = list(case['candidates'])
        chosen = None
        for iteration in range(max_iterations):
            evaluated = [(candidate, check_candidate(candidate)) for candidate in candidates]
            feasible = [(candidate, check) for candidate, check in evaluated if check['hard_valid']]
            if not feasible:
                break
            chosen, feedback = min(feasible, key=lambda item:
                weights[0] * item[1]['structure_violation'] + weights[1] * item[1]['semantic_violation'])
            for i, (strategy, key) in enumerate(((lambda_struct_strategy, 'structure_violation'),
                                                (lambda_sem_strategy, 'semantic_violation'))):
                if strategy == '动态':
                    weights[i] = max(0.0, weights[i] + update_step * feedback[key])
            if record_path:
                append_record(record_path, {'case_id': case_id, 'iteration': iteration,
                                           'weights': weights, 'checks': feedback})
            if feedback['structure_violation'] == 0 and feedback['semantic_violation'] == 0:
                break
        truth.append(case['expected_label'])
        if chosen is None:
            predictions.append('__INVALID__')
        else:
            valid_count += 1
            predictions.append(str(execute_candidate(chosen, case['input'])))
        truth[-1] = str(truth[-1])
    metrics = classification_metrics(truth, predictions, labels=sorted(set(truth)))
    return {'Micro-F1': metrics['accuracy'], 'Macro-F1': metrics['macro_f1'],
            'SIR': valid_count / len(truth) * 100.0, 'n_instances': len(truth)}
