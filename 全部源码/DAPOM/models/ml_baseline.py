"""ML 基线模型 (对比实验对照)

纯神经网络, 不接 LLM, 不接 DSL 约束.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.nn.functional as F


class MLBaselineAgent(nn.Module):
    """纯神经网络基线: 不接 LLM, 不接 DSL 约束"""

    def __init__(self, vocab_size: int = 500, embedding_dim: int = 64):
        super().__init__()
        self.accusation_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.article_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.money_projection = nn.Linear(1, embedding_dim)
        self.regressor = nn.Sequential(
            nn.Linear(embedding_dim * 3, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, batch_facts, batch_articles, batch_accusations,
                batch_money, target_imprisonment=None):
        device = batch_money.device
        acc_ids = [hash(a) % self.accusation_embedding.num_embeddings
                   for a in batch_accusations]
        acc_embs = self.accusation_embedding(
            torch.tensor(acc_ids, device=device)
        )
        art_ids = [hash(arts[0] if arts else '未知')
                   % self.article_embedding.num_embeddings
                   for arts in batch_articles]
        art_embs = self.article_embedding(
            torch.tensor(art_ids, device=device)
        )
        money_embs = self.money_projection(batch_money.unsqueeze(-1))
        x = torch.cat([acc_embs, art_embs, money_embs], dim=-1)
        pred = self.regressor(x).squeeze(-1)
        return pred, torch.tensor(0.0, device=device)
