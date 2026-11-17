"""规则基线模型 (对比实验对照)

基于规则的刑期估算, 不接 LLM.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn


class RuleBasedAgent(nn.Module):
    """规则基线: 基于罚金 + 法条数的简单刑期估算"""

    def __init__(self):
        super().__init__()
        self.base_term = nn.Parameter(torch.tensor(12.0))

    def forward(self, batch_facts, batch_articles, batch_accusations,
                batch_money, target_imprisonment=None):
        device = batch_money.device
        money_effect = batch_money * 0.001
        article_effect = torch.tensor(
            [float(len(a)) for a in batch_articles],
            dtype=torch.float, device=device,
        ) * 3.0
        pred = self.base_term + money_effect + article_effect
        return pred, torch.tensor(0.0, device=device)
