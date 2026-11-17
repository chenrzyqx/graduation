"""DAPOM: frozen LLM candidates, hard filtering, rule scores and inference feedback."""
import json
import os
from pathlib import Path
import requests
import torch
from torch import nn
from torch.utils.data import Dataset
from DSAGM.dsl.engine import DSLEngine
from DSAGM.mapper import f_map
from DSAGM.assembler import f_assemble
from DSAGM.model import build_default_dsl
from .cem import ConstraintExtractionEngine, ConstraintVector
from .constraint_tensor import ConstraintTensorSpace, construct_tensor
from .lagrangian import LagrangianOptimizer
from experiment_support import legacy_metrics, append_record

TEMPERATURE, MAX_TOKENS = 0.3, 4098
LAMBDA_INIT, ALPHA, LAMBDA_SEM = 1.0, 5e-5, 0.5
WEIGHT_DECAY, MAX_ITER, CONSTRAINT_DIM, STATE_DIM, ACTION_DIM = 0.99, 100, 128, 128, 1


class OpenAICompatibleAPI:
    def __init__(self, api_base=None, model_name=None, api_key=None, generation_kwargs=None):
        self.api_base = (api_base or os.environ.get('LLM_API_BASE', 'https://api.deepseek.com/v1')).rstrip('/')
        self.model_name = model_name or os.environ.get('LLM_MODEL_NAME', 'deepseek-reasoner')
        self.api_key = api_key or os.environ.get('LLM_API_KEY', '')
        if not self.api_key or any('YOUR_' in value for value in (self.api_base, self.model_name, self.api_key)):
            raise ValueError('Real model endpoint, model name and API key are required')
        self.generation_kwargs = {'temperature': TEMPERATURE, 'max_tokens': MAX_TOKENS,
                                  **(generation_kwargs or {})}

    def generate(self, prompt):
        response = requests.post(self.api_base + '/chat/completions',
            headers={'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'},
            json={'model': self.model_name, 'messages': [{'role': 'user', 'content': prompt}],
                  **self.generation_kwargs}, timeout=120)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()


class LawDataset(Dataset):
    def __init__(self, file_path):
        self.data, self.excluded_special_terms = [], 0
        with open(file_path, encoding='utf-8') as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                term = item['meta']['term_of_imprisonment']
                if term.get('death_penalty') or term.get('life_imprisonment') or term['imprisonment'] < 0:
                    self.excluded_special_terms += 1
                    continue
                self.data.append({'sample_id': f'{Path(file_path).name}:{line_number}',
                                  'fact': item['fact'], 'imprisonment': float(term['imprisonment'])})

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data[idx]
        # Targets are exposed for scoring only; oracle charges/articles/fines are never model inputs.
        return {**row, 'imprisonment': torch.tensor(row['imprisonment']),
                'articles': [], 'accusation': '', 'money': torch.tensor(0.0)}


class DAPOMAgent(nn.Module):
    def __init__(self, llm_client, cem, constraint_tensor_space, lagrangian_optimizer,
                 dsl_text=None, state_dim=STATE_DIM, *, runtime_config=None,
                 runtime_constraints=None, variant='full', fixed_constraints=None,
                 trace_path=None, reset_per_case=True):
        super().__init__()
        self.llm_client, self.cem = llm_client, cem
        self.constraint_tensor_space, self.lagrangian = constraint_tensor_space, lagrangian_optimizer
        self.variant, self.trace_path, self.reset_per_case = variant, trace_path, reset_per_case
        if variant not in {'full', 'wo_cem', 'wo_cts', 'wo_lmo', 'wo_awu'}:
            raise ValueError(f'Unknown DAPOM variant: {variant}')
        self.dsl_text = dsl_text or self._default_dsl()
        if variant == 'wo_cem':
            if fixed_constraints is None:
                raise ValueError('w/o CEM requires the explicitly configured fixed constraint set')
            self.constraints = fixed_constraints
            self.constraint_vec = None
        else:
            self.constraints, self.constraint_vec = cem.extract(self.dsl_text, runtime_constraints)
        _, ast = DSLEngine().parse(self.dsl_text)
        self.ir = f_map(ast)
        self.runtime = f_assemble(self.ir, llm_core=llm_client.generate, **(runtime_config or {}))
        self.reference_examples = []
        self.last_trace = []

    def _default_dsl(self):
        return (build_default_dsl().replace('charge_prediction]', 'charge_prediction, sentence_prediction]')
                .replace('type classification', 'type reasoning')
                .replace('根据提供的案件事实，预测被告人所犯的罪名。',
                         '根据案件事实、检索证据和情节预测有期徒刑月数。'))

    def predict(self, fact):
        if self.reset_per_case:
            self.lagrangian.reset()
        self.last_trace = []
        self.ir.Memory.short_term = list(self.reference_examples)
        base_prompt = self.runtime.build_prompt(fact)
        state = {'steps': 0, 'tool_calls': {}, 'completed_goals': [], 'observations': []}
        protocol = ('Return JSON {"candidates":[action,...]} with at most 8 alternatives. '
                    'Each action has capability, and either tool/arguments or final. '
                    'A final is {"imprisonment":nonnegative_number}. Use registered tool IDs. '
                    'Do not include private reasoning; provide only executable actions and final fields. ')
        for step in range(self.lagrangian.max_iter):
            response = self.llm_client.generate(base_prompt + '\n' + protocol + json.dumps(state, ensure_ascii=False))
            decoded = self.runtime.decode(response)
            if not isinstance(decoded, dict):
                raise ValueError('Expected a candidates object')
            candidates = decoded.get('candidates')
            if not isinstance(candidates, list) or not 1 <= len(candidates) <= 8:
                raise ValueError('Expected 1..8 candidate actions')
            feasible = [a for a in candidates if self.constraint_tensor_space.feasible(self.constraints, state, a)]
            if not feasible:
                raise ValueError('No feasible candidate action')
            violations = self.constraint_tensor_space.current_slice(self.constraints, state, feasible)
            if self.variant == 'wo_cts':
                # Retain a constraint vector, removing state/action-specific modulation.
                violations = violations.mean(dim=1, keepdim=True).expand_as(violations)
            utilities = torch.tensor([self.utility(state, a) for a in feasible])
            penalties = self.lagrangian.compute_penalty(violations)
            scores = utilities if self.variant == 'wo_lmo' else self.lagrangian.compute_objective(utilities, penalties)
            selected = int(self.lagrangian.select_best_action(scores))
            action = feasible[selected]
            before = self.lagrangian.lambdas.detach().cpu().tolist()
            if 'tool' in action:
                result = self.runtime.execute_tool(action, state['tool_calls'])
                state['observations'].append({'action': action, 'result': result})
            if self.variant != 'wo_awu':
                self.lagrangian.update_lambdas(violations[:, selected])
            event = {'step': step, 'state': {**state, 'tool_calls': dict(state['tool_calls']),
                      'observations': list(state['observations'])},
                     'candidates': feasible, 'violations': violations.tolist(),
                     'utilities': utilities.tolist(), 'scores': scores.tolist(), 'selected_action': action,
                     'multipliers_before': before, 'multipliers_after': self.lagrangian.lambdas.cpu().tolist(),
                     'tool_calls': dict(state['tool_calls']), 'raw_response': response}
            self.last_trace.append(event)
            if self.trace_path:
                append_record(self.trace_path, event)
            if 'final' in action:
                return float(action['final']['imprisonment'])
            state['steps'] += 1
        raise RuntimeError('Planning iteration limit reached')

    def utility(self, state, action):
        # Observable progress only; never consult a test target or reward larger sentences.
        goals = self.constraints.get('C_goal', [])
        goal_id = action.get('goal_id')
        if goal_id is None and len(goals) == 1:
            goal_id = goals[0]['goal_id']
        weight = sum(g['priority'] for g in goals
                     if g['goal_id'] == goal_id and g['goal_id'] not in state['completed_goals'])
        if 'tool' in action:
            return weight if not state['tool_calls'].get(action['tool'], 0) else 0.0
        return weight * (1.0 if state['observations'] else 0.5)

    def forward(self, batch_facts, batch_articles=None, batch_accusations=None,
                batch_money=None, target_imprisonment=None):
        device = batch_money.device if batch_money is not None else self.lagrangian.lambdas.device
        predictions = [self.predict(fact) for fact in batch_facts]
        return torch.tensor(predictions, device=device), torch.zeros(len(predictions), device=device)


def calculate_metrics(true_values, pred_values, epsilon=1e-8):
    return legacy_metrics(true_values, pred_values, terms=True)


def final_evaluation(agent, data_loader, device, record_path=None):
    agent.eval()
    all_true, all_pred = [], []
    for batch in data_loader:
        for item in batch:
            target = float(item['imprisonment'])
            try:
                with torch.no_grad():
                    prediction, _ = agent(batch_facts=[item['fact']], batch_articles=[[]],
                                          batch_accusations=[''], batch_money=torch.zeros(1, device=device))
                predicted = float(prediction[0])
                status, error = 'ok', None
            except Exception as exc:
                predicted, status, error = -1.0, 'failed', str(exc)
            all_true.append(target)
            all_pred.append(predicted)
            if record_path:
                append_record(record_path, {'sample_id': item.get('sample_id'), 'true_months': target,
                    'predicted_months': predicted, 'status': status, 'error': error,
                    'model': getattr(getattr(agent, 'llm_client', None), 'model_name', None)})
    return calculate_metrics(all_true, all_pred)


def save_experiment_results(results, experiment_type, filename):
    path = Path(__file__).resolve().parent / 'results' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite an existing result: {path}')
    with path.open('w', encoding='utf-8') as stream:
        json.dump({'experiment_type': experiment_type, 'results': results}, stream,
                  ensure_ascii=False, indent=2, allow_nan=False)
