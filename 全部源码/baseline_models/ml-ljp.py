import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
import json
import numpy as np
from tqdm import tqdm

# ==================== 1. 配置参数 ====================
MODEL_NAME = "bert-base-chinese" # 替换成实际路径 "bert-base-chinese"
MAX_LEN = 512
BATCH_SIZE = 8
EPOCHS = 10
LEARNING_RATE = 2e-5
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ML-LJP 多目标损失函数权重
LAMBDA_A = 1.0  # 法条预测损失 (BCE)
LAMBDA_C = 1.0  # 罪名预测损失 (CE)
LAMBDA_P = 0.1  # 刑期回归损失 (MSE数值较大，调小权重进行平衡)
LAMBDA_CC = 0.5  # 监督对比学习损失
TEMPERATURE = 0.07


# ==================== 2. 数据与词表加载 ====================

def build_vocabularies(file_path):
    """遍历数据集，构建法条和罪名的词表映射"""
    articles_set = set()
    accusations_set = set()

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                item = json.loads(line)
                acc = item.get('meta', {}).get('accusation', ['未知'])[0]
                arts = item.get('meta', {}).get('relevant_articles', [])
                accusations_set.add(acc)
                for a in arts:
                    articles_set.add(str(a))
            except:
                continue

    article2id = {a: i for i, a in enumerate(sorted(list(articles_set)))}
    acc2id = {acc: i for i, acc in enumerate(sorted(list(accusations_set)))}
    return article2id, acc2id


class MLLJPLawDataset(Dataset):
    """适配 ML-LJP 的数据集，负责 Tokenize 和构建 Multi-hot 标签"""

    def __init__(self, file_path, tokenizer, article2id, acc2id, max_len=MAX_LEN):
        self.data = []
        self.tokenizer = tokenizer
        self.article2id = article2id
        self.acc2id = acc2id
        self.max_len = max_len

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    item = json.loads(line)
                    fact = item['fact']
                    imprisonment = item['meta'].get('term_of_imprisonment', {}).get('imprisonment', -1)
                    if imprisonment < 0: continue  # 忽略无期/死刑

                    arts = item['meta'].get('relevant_articles', [])
                    acc = item['meta'].get('accusation', ['未知'])[0]

                    self.data.append({
                        'fact': fact,
                        'articles': [str(a) for a in arts],
                        'accusation': acc,
                        'imprisonment': float(imprisonment)
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"ML-LJP Loaded {len(self.data)} valid samples from {file_path}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        # 1. 文本 Tokenize
        encoding = self.tokenizer(
            item['fact'],
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # 2. 构建多标签法条的 Multi-hot 向量
        article_multi_hot = torch.zeros(len(self.article2id))
        for a in item['articles']:
            if a in self.article2id:
                article_multi_hot[self.article2id[a]] = 1.0

        # 3. 罪名 ID
        acc_id = self.acc2id.get(item['accusation'], 0)

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels_article': article_multi_hot,
            'label_charge': torch.tensor(acc_id, dtype=torch.long),
            'imprisonment': torch.tensor(item['imprisonment'], dtype=torch.float)
        }


# ==================== 3. ML-LJP 核心网络组件 ====================

class LabelSpecificAttention(nn.Module):
    """标签感知注意力：利用标签查询向量，从案件事实中提取特定特征"""

    def __init__(self, hidden_dim):
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim=hidden_dim, num_heads=4, batch_first=True)

    def forward(self, query, key, value, key_padding_mask=None):
        attn_output, _ = self.attention(query, key, value, key_padding_mask=key_padding_mask)
        return attn_output


class GATLayer(nn.Module):
    """优化版图注意力网络层：时间与空间复杂度大幅降低"""

    def __init__(self, in_features, out_features, num_heads=4):
        super().__init__()
        self.num_heads = num_heads
        self.out_features = out_features
        self.W = nn.Linear(in_features, out_features * num_heads, bias=False)

        # 将原本的一个大权重 a 拆分为源(src)和目标(dst)，避免两两拼接
        self.a_src = nn.Parameter(torch.randn(num_heads, out_features, 1))
        self.a_dst = nn.Parameter(torch.randn(num_heads, out_features, 1))
        self.leakyrelu = nn.LeakyReLU(0.2)

    def forward(self, h, adj):
        B, N, _ = h.size()
        # Wh 维度: [B, N, Heads, Out]
        Wh = self.W(h).view(B, N, self.num_heads, self.out_features)

        # 巧妙利用 einsum 计算每个节点作为 src 和 dst 时的独立注意力得分
        # attn_src/dst 维度: [B, N, Heads]
        attn_src = torch.einsum('bnhf, hfc -> bnh', Wh, self.a_src)
        attn_dst = torch.einsum('bnhf, hfc -> bnh', Wh, self.a_dst)

        # 利用广播机制直接相加，完美等价于原先的拼接计算，但完全不额外占用显存！
        # [B, N, 1, Heads] + [B, 1, N, Heads] -> [B, N, N, Heads]
        e = self.leakyrelu(attn_src.unsqueeze(2) + attn_dst.unsqueeze(1))

        zero_vec = -9e15 * torch.ones_like(e)
        adj_expanded = adj.unsqueeze(-1).expand_as(e)
        attention = torch.where(adj_expanded > 0, e, zero_vec)
        attention = F.softmax(attention, dim=2)

        h_prime = torch.einsum('bnih, biho -> bnho', attention, Wh)
        return F.elu(h_prime.reshape(B, N, -1))
class LabelContrastiveLoss(nn.Module):
    """监督对比学习损失：拉近相同罪名的案件特征，推远不同罪名的特征"""

    def __init__(self, temperature=0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, feats, labels_multi_hot):
        B, L, H = feats.size()
        loss = 0.0
        valid = 0
        feats = F.normalize(feats, p=2, dim=-1)

        for i in range(B):
            actives = torch.where(labels_multi_hot[i] == 1)[0]
            if len(actives) < 2: continue

            for v in actives:
                anchor = feats[i, v].unsqueeze(0)

                # 正样本：同批次其他案件的相同法条
                pos_mask = labels_multi_hot[:, v] == 1
                pos_mask[i] = False
                pos_feats = feats[pos_mask, v, :]

                # 负样本：当前案件的其他法条
                neg_mask = actives != v
                neg_indices = actives[neg_mask]
                neg_feats = feats[i, neg_indices, :]

                if pos_feats.size(0) == 0 or neg_feats.size(0) == 0: continue

                pos_sim = torch.exp(torch.matmul(anchor, pos_feats.T) / self.temperature)
                neg_sim = torch.exp(torch.matmul(anchor, neg_feats.T) / self.temperature)

                denominator = pos_sim.sum() + neg_sim.sum()
                loss += -torch.log(pos_sim.sum() / (denominator + 1e-8))
                valid += 1

        return loss / (valid + 1e-8)


class MLLJPModel(nn.Module):
    """ML-LJP 完整模型架构"""

    def __init__(self, num_articles, num_charges, model_name=MODEL_NAME):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size

        self.article_embeds = nn.Parameter(torch.randn(num_articles, hidden_size))
        self.charge_embeds = nn.Parameter(torch.randn(num_charges, hidden_size))

        self.article_attn = LabelSpecificAttention(hidden_size)
        self.charge_attn = LabelSpecificAttention(hidden_size)

        # 角色嵌入 (定罪相关法条 vs 量刑相关法条)
        self.role_charge_related = nn.Parameter(torch.randn(hidden_size))
        self.role_term_related = nn.Parameter(torch.randn(hidden_size))

        self.gat = GATLayer(hidden_size, hidden_size // 4, num_heads=4)

        self.article_pred = nn.Linear(2 * hidden_size, num_articles)
        self.charge_pred = nn.Linear(2 * hidden_size, num_charges)

        # 刑期回归头
        self.prison_pred = nn.Sequential(
            nn.Linear(3 * hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1)
        )

    def forward(self, input_ids, attention_mask, adj_matrix):
        B = input_ids.size(0)
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        H_f = outputs.last_hidden_state
        key_padding_mask = (attention_mask == 0)

        # 1. 提取标签特异性事实特征
        H_a_query = self.article_embeds.unsqueeze(0).expand(B, -1, -1)
        H_c_query = self.charge_embeds.unsqueeze(0).expand(B, -1, -1)

        H_af = self.article_attn(H_a_query, H_f, H_f, key_padding_mask)
        H_cf = self.charge_attn(H_c_query, H_f, H_f, key_padding_mask)

        h_f = torch.max(H_f, dim=1)[0]
        h_af_pooled = torch.max(H_af, dim=1)[0]
        h_cf_pooled = torch.max(H_cf, dim=1)[0]

        # 2. 法条与罪名预测
        logits_article = self.article_pred(torch.cat([h_af_pooled, h_f], dim=-1))
        logits_charge = self.charge_pred(torch.cat([h_cf_pooled, h_f], dim=-1))

        # 3. 为法条注入角色信息 (一半是定罪法条，一半是量刑法条)
        num_articles = H_af.size(1)
        half_idx = num_articles // 2
        H_af_role = H_af.clone()
        H_af_role[:, :half_idx, :] += self.role_charge_related
        H_af_role[:, half_idx:, :] += self.role_term_related

        # 4. GAT 法条图交互
        gat_out = self.gat(H_af_role, adj_matrix)
        h_af_tilde = torch.max(gat_out, dim=1)[0]

        # 5. 刑期联合预测
        pred_prison = self.prison_pred(torch.cat([h_af_tilde, h_cf_pooled, h_f], dim=-1)).squeeze(-1)

        return logits_article, logits_charge, pred_prison, H_af


# ==================== 4. 双任务评测指标 ====================

def calculate_charge_metrics(y_true, y_pred, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(y_true, y_pred, terms=False)


def calculate_metrics_discrete(true_vals, pred_vals, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_vals, pred_vals, terms=True)


# ==================== 5. 训练与验证循环 ====================

def train_and_eval_mlljp(train_loader, test_loader, model, optimizer, device):
    criterion_bce = nn.BCEWithLogitsLoss()
    criterion_ce = nn.CrossEntropyLoss()
    criterion_mse = nn.MSELoss()
    criterion_con = LabelContrastiveLoss(TEMPERATURE)

    print("\n--- 启动 ML-LJP (多法条感知预测框架) 对比实验训练 ---")
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0
        pbar = tqdm(train_loader, desc=f"Epoch [{epoch + 1}/{EPOCHS}]")

        for batch in pbar:
            optimizer.zero_grad()

            input_ids = batch['input_ids'].to(device)
            attn_mask = batch['attention_mask'].to(device)
            labels_a = batch['labels_article'].to(device)
            labels_c = batch['label_charge'].to(device)
            labels_p = batch['imprisonment'].to(device)

            # 构建 GAT 邻接矩阵 (如果两个法条在同案中被引用，则连接边)
            adj_matrix = torch.bmm(labels_a.unsqueeze(2), labels_a.unsqueeze(1))

            logits_a, logits_c, pred_p, H_af = model(input_ids, attn_mask, adj_matrix)

            # 计算各项损失
            loss_a = criterion_bce(logits_a, labels_a)
            loss_c = criterion_ce(logits_c, labels_c)
            loss_p = criterion_mse(pred_p, labels_p)
            loss_cc = criterion_con(H_af, labels_a)

            loss = (LAMBDA_A * loss_a) + (LAMBDA_C * loss_c) + (LAMBDA_P * loss_p) + (LAMBDA_CC * loss_cc)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            pbar.set_postfix({'Loss': f"{loss.item():.4f}"})

        # ---------------- 验证评估阶段 ----------------
        model.eval()
        all_true_c, all_pred_c = [], []
        all_true_p, all_pred_p = [], []

        with torch.no_grad():
            for batch in test_loader:
                input_ids = batch['input_ids'].to(device)
                attn_mask = batch['attention_mask'].to(device)
                labels_a = batch['labels_article'].to(device)

                labels_c = batch['label_charge'].numpy()
                labels_p = batch['imprisonment'].numpy()

                adj_matrix = torch.bmm(labels_a.unsqueeze(2), labels_a.unsqueeze(1))
                _, logits_c, pred_p, _ = model(input_ids, attn_mask, adj_matrix)

                # 记录罪名
                pred_c = torch.argmax(logits_c, dim=1).cpu().numpy()
                all_true_c.extend(labels_c)
                all_pred_c.extend(pred_c)

                # 记录刑期 (ReLU防止预测负数)
                pred_p = F.relu(pred_p).cpu().numpy()
                all_true_p.extend(labels_p)
                all_pred_p.extend(pred_p)

        charge_metrics = calculate_charge_metrics(all_true_c, all_pred_c)
        prison_metrics = calculate_metrics_discrete(all_true_p, all_pred_p)

        print("\n" + "=" * 50)
        print(f"[Epoch {epoch + 1} 测试集评测结果]")
        print("【任务 1：罪名预测 (Charge Prediction)】")
        print(f"Accuracy (ACC):     {charge_metrics['ACC']:.4f}")
        print(f"Macro Precision(MP):{charge_metrics['MP']:.4f}")
        print(f"Macro Recall(MR):   {charge_metrics['MR']:.4f}")
        print(f"Macro F1:           {charge_metrics['F1']:.4f}")

        print("\n【任务 2：刑期预测 (Prison Term Prediction)】(离散化分桶)")
        print(f"Accuracy (ACC):     {prison_metrics['ACC']:.4f}")
        print(f"Macro Precision(MP):{prison_metrics['MP']:.4f}")
        print(f"Macro Recall(MR):   {prison_metrics['MR']:.4f}")
        print(f"Macro F1:           {prison_metrics['F1']:.4f}")
        print("=" * 50 + "\n")


# ==================== 6. 主程序入口 ====================

if __name__ == "__main__":
    TRAIN_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_train.jsonl")
    TEST_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_test.jsonl")

    print("正在构建词表映射...")
    article2id, acc2id = build_vocabularies(TRAIN_FILE)
    print(f"识别到 {len(article2id)} 种法条, {len(acc2id)} 种罪名。")

    print("正在加载预训练 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    print("正在构建 Dataset 和 DataLoader...")
    train_dataset = MLLJPLawDataset(TRAIN_FILE, tokenizer, article2id, acc2id)
    test_dataset = MLLJPLawDataset(TEST_FILE, tokenizer, article2id, acc2id)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    print(f"初始化 ML-LJP 模型 (基于 {MODEL_NAME})...")
    model = MLLJPModel(len(article2id), len(acc2id), MODEL_NAME).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    train_and_eval_mlljp(train_loader, test_loader, model, optimizer, DEVICE)