"""Per-constraint inference multipliers; no gradients or LLM parameter updates."""
import torch
from torch import nn


class LagrangianOptimizer(nn.Module):
    def __init__(self, lambda_init=1.0, alpha=5e-5, lambda_sem=0.5,
                 weight_decay=0.99, max_iter=100, lambda_min=0.0,
                 lambda_max=None, constraint_dim=128):
        super().__init__()
        self.lambda_init, self.alpha, self.lambda_sem = lambda_init, alpha, lambda_sem
        self.weight_decay, self.max_iter = weight_decay, max_iter
        self.lambda_min, self.lambda_max = lambda_min, lambda_max
        self.register_buffer('lambdas', torch.full((constraint_dim,), float(lambda_init)))

    def reset(self):
        self.lambdas.fill_(self.lambda_init)

    def compute_penalty(self, scores):
        # scores is [constraint, action]; retain a separate penalty for every candidate.
        weights = self.lambdas.to(scores.device)
        return (weights[:, None] * scores.square()).sum(dim=0)

    def compute_objective(self, utilities, penalties):
        return utilities - self.lambda_sem * penalties

    def score_actions(self, rewards, penalties, eta=None):
        return rewards - (self.lambda_sem if eta is None else eta) * penalties

    def select_best_action(self, scores):
        return torch.argmax(scores, dim=-1)

    def check_violation(self, action, scores, threshold=0.0):
        return (scores - threshold).clamp(min=0)

    def update_lambdas(self, violation):
        with torch.no_grad():
            violation = violation.to(self.lambdas.device)
            if violation.shape != self.lambdas.shape:
                raise ValueError('Expected one violation value per constraint')
            # Decay retained as the configured inference smoothing factor.
            updated = self.weight_decay * self.lambdas + self.alpha * violation
            self.lambdas.copy_(updated.clamp(min=self.lambda_min, max=self.lambda_max))
        return self.lambdas
