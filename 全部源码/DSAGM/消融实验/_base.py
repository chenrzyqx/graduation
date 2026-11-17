"""Matched ablations: change only the selected component, preserving the task/resources."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import copy
import random
from types import SimpleNamespace
from DSAGM.dsl.engine import DSLEngine
from DSAGM.mapper import f_map
from DSAGM.assembler import f_assemble
from DSAGM.agent_ir import Role
from DSAGM.model import (load_data, build_label_map_from_train, call_llm, extract_accusation,
                         compute_metrics, build_default_dsl)
from experiment_support import append_record
from runtime_config import load_runtime_config


def dsl_wo_role():
    return build_default_dsl()


def dsl_wo_goal():
    return build_default_dsl()


def dsl_wo_tool():
    return build_default_dsl()


def dsl_wo_planning():
    return build_default_dsl()


def dsl_direct_mapping():
    return build_default_dsl()


def direct_view(ast):
    # Direct AST field access without AgentIR construction or semantic validation.
    return SimpleNamespace(
        Role=SimpleNamespace(role_id=ast.role.name, description=ast.role.description,
                             capabilities=ast.role.capabilities),
        Goals=[SimpleNamespace(priority=g.priority, content=g.content, goal_type=g.goal_type)
               for g in ast.goals],
        Tools=[SimpleNamespace(tool_id=t.name, name=t.tool_name,
               params=[{'name': p.name, 'type': p.type} for p in t.params],
               output_type=t.output_type, api=None) for t in ast.tools],
        Memory=SimpleNamespace(mem_type=ast.memory.mem_type, storage=ast.memory.storage, short_term=[]),
        Planner=SimpleNamespace(strategy=ast.planner.strategy))


def run_ablation(dsl_text, ablation_name, train_facts, train_accusations, test_facts,
                 test_accusations, label_to_id, id_to_label, num_examples=15, *,
                 runtime_config=None, seed=42, record_path=None):
    engine = DSLEngine()
    _, ast = engine.parse(dsl_text, validate='Direct' not in ablation_name)
    ir = direct_view(ast) if 'Direct' in ablation_name else f_map(ast)
    disabled = []
    if 'Role' in ablation_name:
        ir.Role = Role()
    if 'Goal' in ablation_name:
        ir.Goals = []
    if 'Tool' in ablation_name:
        ir.Tools = []
        disabled.append('Tool')
    if 'Planning' in ablation_name:
        ir.Planner.strategy = ''
        disabled.append('Planning')
    if 'Memory' in ablation_name:
        disabled.append('Memory')
    elif train_facts and num_examples:
        indices = random.Random(seed).sample(range(len(train_facts)), min(num_examples, len(train_facts)))
        ir.Memory.short_term = [(train_facts[i], train_accusations[i]) for i in indices]
    config = copy.copy(runtime_config if runtime_config is not None else load_runtime_config())
    runtime = f_assemble(ir, llm_core=call_llm, disabled_components=disabled, **config)
    truth, predictions = [], []
    for index, (fact, label) in enumerate(zip(test_facts, test_accusations)):
        if label not in label_to_id:
            continue
        try:
            response = runtime.run(fact, all_labels=id_to_label)
            prediction = label_to_id.get(extract_accusation(response, id_to_label), -1)
            status = 'ok' if prediction != -1 else 'invalid_output'
        except Exception as exc:
            response, prediction, status = str(exc), -1, 'failed'
        truth.append(label_to_id[label])
        predictions.append(prediction)
        if record_path:
            append_record(record_path, {'variant': ablation_name, 'sample_index': index,
                'true_label': label, 'predicted_id': prediction, 'raw_response': response, 'status': status})
    return compute_metrics(truth, predictions, labels=range(len(id_to_label)))


def main_ablation(dsl_builder, name, train_file=None, test_file=None, num_examples=15, **kwargs):
    root = Path(__file__).resolve().parents[1]
    train_facts, train_labels = load_data(train_file or root / 'cail_small/data_train.jsonl')
    facts, labels = load_data(test_file or root / 'cail_small/data_test.jsonl')
    mapping, classes = build_label_map_from_train(train_labels)
    return run_ablation(dsl_builder(), name, train_facts, train_labels, facts, labels,
                        mapping, classes, num_examples, **kwargs)
