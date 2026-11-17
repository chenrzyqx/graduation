"""Rule-computed violation slices, indexed as constraint x state x action."""
import math
import torch
from torch import nn


class ConstraintTensorSpace(nn.Module):
    def __init__(self, constraint_dim=128, state_dim=128, action_dim=1):
        super().__init__()
        self.k_dim, self.n_dim, self.m_dim = constraint_dim, state_dim, action_dim
        self.rule_names = []

    def feasible(self, constraints, state, action):
        if not isinstance(action, dict):
            return False
        caps = constraints.get('C_role', {}).get('capabilities', [])
        capability = action.get('capability')
        if caps and capability not in caps:
            return False
        if 'tool' in action:
            tools = {t['tool_id']: t for t in constraints.get('C_tool', [])}
            tool = tools.get(action['tool'])
            if tool is None:
                return False
            limit = tool.get('max_calls')
            if limit is not None and state['tool_calls'].get(action['tool'], 0) >= limit:
                return False
            return isinstance(action.get('arguments'), dict)
        if 'final' in action:
            final = action['final']
            return (isinstance(final, dict) and isinstance(final.get('imprisonment'), (int, float))
                    and not isinstance(final['imprisonment'], bool)
                    and math.isfinite(final['imprisonment']) and final['imprisonment'] >= 0)
        return False

    def current_slice(self, constraints, state, actions):
        rules = []
        required = constraints.get('C_output', {}).get('required_fields', [])
        if required:
            rules.append(('output.required_fields', lambda a: (
                sum(k not in a.get('final', {}) for k in required) / len(required)
                if 'final' in a else 0.0)))
        for resource, limit in constraints.get('C_budget', {}).items():
            if not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
                raise ValueError(f'Invalid explicitly configured budget: {resource}')
            if resource not in state:
                raise ValueError(f'No observed state for configured budget: {resource}')
            rules.append((f'budget.{resource}', lambda a, r=resource, l=limit:
                          max(0.0, (state[r] + (1 if r == 'steps' else 0) - l) / l)))
        if len(rules) > self.k_dim:
            raise ValueError('Configured constraints exceed constraint_dim')
        self.rule_names = [r[0] for r in rules]
        values = torch.zeros(self.k_dim, len(actions), dtype=torch.float32)
        for i, (_, check) in enumerate(rules):
            for j, action in enumerate(actions):
                values[i, j] = check(action)
        return values

    def forward(self, constraints, states, actions):
        return torch.stack([self.current_slice(constraints, state, actions) for state in states], dim=1)


def construct_tensor(constraints, states, actions, tensor_space):
    return tensor_space(constraints, states, actions)
