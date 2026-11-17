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

# ==================== 配置参数 ====================
MODEL_NAME = "bert-base-chinese" # 替换成实际路径 "bert-base-chinese"
MAX_LEN = 512
BATCH_SIZE = 8
EPOCHS = 5
LEARNING_RATE = 2e-5
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 损失权重超参 (CL4LJP 的多粒度对比权重)
WEIGHT_CE = 1.0  # 罪名分类交叉熵权重
WEIGHT_MSE = 0.05  # 刑期回归 MSE 权重
LAMBDA_CASE = 0.4  # 案例级对比损失权重
LAMBDA_SENTENCE = 0.3  # 句子级对比损失权重
LAMBDA_WORD = 0.3  # 词级对比损失权重
TEMPERATURE = 0.1  # 对比学习温度系数


# ==================== 数据加载 ====================

def safe_load_jsonl_multitask(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                item = json.loads(line)
                fact = item.get('fact', '')
                acc_list = item.get('meta', {}).get('accusation', [])
                accusation = acc_list[0] if acc_list else None
                imprisonment = item.get('meta', {}).get('term_of_imprisonment', {}).get('imprisonment', -1)

                if fact and accusation and imprisonment >= 0:
                    data.append({
                        'fact': fact,
                        'accusation': accusation,
                        'imprisonment': float(imprisonment)
                    })
            except:
                continue
    return data


class CL4LJPDataset(Dataset):
    def __init__(self, data, label_to_id, tokenizer, max_len):
        self.data = data
        self.label_to_id = label_to_id
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        encoding = self.tokenizer(
            item['fact'],
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(self.label_to_id[item['accusation']], dtype=torch.long),
            'imprisonment': torch.tensor(item['imprisonment'], dtype=torch.float)
        }


# ==================== 监督对比损失 ====================

class SupConLoss(nn.Module):
    """
    监督对比损失：根据罪名标签，拉近同类样本的特征，推远不同类样本
    """

    def __init__(self, temperature=0.1):
        super(SupConLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features, labels):
        device = features.device
        batch_size = features.shape[0]

        # 特征 L2 归一化
        features = F.normalize(features, p=2, dim=1)

        # 计算余弦相似度矩阵 (缩放 temperature)
        similarity_matrix = torch.matmul(features, features.T) / self.temperature

        # 构建正样本 Mask
        labels = labels.contiguous().view(-1, 1)
        mask = torch.eq(labels, labels.T).float().to(device)

        # 消除对角线 (自己不与自己对比)
        logits_mask = torch.scatter(torch.ones_like(mask), 1, torch.arange(batch_size).view(-1, 1).to(device), 0)
        mask = mask * logits_mask

        # 数值稳定性
        sim_max, _ = torch.max(similarity_matrix, dim=1, keepdim=True)
        logits = similarity_matrix - sim_max.detach()

        # 计算对数概率
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True) + 1e-8)

        # 计算正样本平均似然
        mask_sum = mask.sum(1)
        mask_sum = torch.where(mask_sum == 0, torch.ones_like(mask_sum), mask_sum)
        mean_log_prob_pos = (mask * log_prob).sum(1) / mask_sum

        return -mean_log_prob_pos.mean()


# ==================== CL4LJP 核心模型 ====================

class CL4LJPModel(nn.Module):
    def __init__(self, num_classes, model_name=MODEL_NAME):
        super(CL4LJPModel, self).__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size

        # 1. 词粒度提取器 (使用 1D-CNN 提取局部 N-gram/短语特征)
        self.word_extractor = nn.Conv1d(in_channels=hidden_size, out_channels=hidden_size, kernel_size=3, padding=1)

        # 2. 多粒度特征投影头 (Projection Heads for Contrastive Learning)
        self.case_proj = nn.Sequential(nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 128))
        self.sentence_proj = nn.Sequential(nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 128))
        self.word_proj = nn.Sequential(nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 128))

        # 3. 联合预测头 (融合三种粒度的特征进行最终预测)
        fusion_size = hidden_size * 3

        self.classifier = nn.Sequential(
            nn.Linear(fusion_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, num_classes)
        )

        self.regressor = nn.Sequential(
            nn.Linear(fusion_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 1)
        )

    def forward(self, input_ids, attention_mask):
        # Base Encoder
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state  # [Batch, Seq_len, Hidden]

        # --- 粒度 1: 案例级特征 (Case Level) ---
        # 采用 [CLS] token 代表全局案件语义
        case_repr = sequence_output[:, 0, :]

        # --- 粒度 2: 句子/片段级特征 (Sentence Level) ---
        # 采用 Masked Mean Pooling 代表案件陈述的结构语义
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(sequence_output.size()).float()
        sentence_repr = torch.sum(sequence_output * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1),
                                                                                          min=1e-9)

        # --- 粒度 3: 词/短语级特征 (Word Level) ---
        # 采用 Conv1D 提取局部信息后做 Max Pooling
        seq_permuted = sequence_output.permute(0, 2, 1)  # [Batch, Hidden, Seq_len]
        word_conv = F.relu(self.word_extractor(seq_permuted))  # [Batch, Hidden, Seq_len]
        word_repr = F.max_pool1d(word_conv, kernel_size=word_conv.size(2)).squeeze(-1)  # [Batch, Hidden]

        # 计算投影特征用于对比学习损失
        case_feat = self.case_proj(case_repr)
        sentence_feat = self.sentence_proj(sentence_repr)
        word_feat = self.word_proj(word_repr)

        # 融合多粒度特征用于预测
        fused_repr = torch.cat([case_repr, sentence_repr, word_repr], dim=-1)

        logits = self.classifier(fused_repr)
        imprisonment_pred = self.regressor(fused_repr).squeeze(-1)

        return logits, imprisonment_pred, case_feat, sentence_feat, word_feat


# ==================== 评测指标 ====================

def calculate_accusation_metrics(y_true, y_pred, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(y_true, y_pred, terms=False)


def calculate_imprisonment_metrics(true_vals, pred_vals, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_vals, pred_vals, terms=True)


def evaluate_cl4ljp(model, data_loader, device):
    model.eval()
    acc_true, acc_pred = [], []
    imp_true, imp_pred = [], []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            imprisonments = batch['imprisonment'].to(device)

            logits, imp_preds, _, _, _ = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=1)

            acc_true.extend(labels.cpu().numpy())
            acc_pred.extend(preds.cpu().numpy())
            imp_true.extend(imprisonments.cpu().numpy())

            imp_preds = F.relu(imp_preds)
            imp_pred.extend(imp_preds.cpu().numpy())

    return (calculate_accusation_metrics(acc_true, acc_pred),
            calculate_imprisonment_metrics(imp_true, imp_pred))


# ==================== 主训练流程 ====================

def run_cl4ljp_experiment(train_path: str, test_path: str):
    print("--- 初始化 CL4LJP [多粒度对比学习框架] ---")
    train_data = safe_load_jsonl_multitask(train_path)
    test_data = safe_load_jsonl_multitask(test_path)

    unique_labels = sorted(list(set([d['accusation'] for d in train_data])))
    label_to_id = {l: i for i, l in enumerate(unique_labels)}
    num_classes = len(unique_labels)

    test_data = [d for d in test_data if d['accusation'] in label_to_id]

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    train_dataset = CL4LJPDataset(train_data, label_to_id, tokenizer, MAX_LEN)
    test_dataset = CL4LJPDataset(test_data, label_to_id, tokenizer, MAX_LEN)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = CL4LJPModel(num_classes=num_classes, model_name=MODEL_NAME).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    criterion_ce = nn.CrossEntropyLoss()
    criterion_mse = nn.MSELoss()
    criterion_supcon = SupConLoss(temperature=TEMPERATURE)

    print("\n--- 开始训练 CL4LJP ---")
    for epoch in range(EPOCHS):
        model.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{EPOCHS}")

        for batch in pbar:
            optimizer.zero_grad()

            input_ids = batch['input_ids'].to(DEVICE)
            attention_mask = batch['attention_mask'].to(DEVICE)
            labels = batch['label'].to(DEVICE)
            imprisonments = batch['imprisonment'].to(DEVICE)

            # 前向传播：返回预测值和三个维度的投影特征
            logits, imp_preds, case_feat, sentence_feat, word_feat = model(input_ids, attention_mask)

            # 1. 任务损失
            loss_ce = criterion_ce(logits, labels)
            loss_mse = criterion_mse(imp_preds, imprisonments)

            # 2. 多粒度监督对比损失
            loss_case_con = criterion_supcon(case_feat, labels)
            loss_sent_con = criterion_supcon(sentence_feat, labels)
            loss_word_con = criterion_supcon(word_feat, labels)

            # 3. 总损失计算
            loss = (WEIGHT_CE * loss_ce) + \
                   (WEIGHT_MSE * loss_mse) + \
                   (LAMBDA_CASE * loss_case_con) + \
                   (LAMBDA_SENTENCE * loss_sent_con) + \
                   (LAMBDA_WORD * loss_word_con)

            loss.backward()
            optimizer.step()

            pbar.set_postfix({
                'CE': f"{loss_ce.item():.2f}",
                'CL': f"{(loss_case_con + loss_sent_con + loss_word_con).item():.2f}"
            })

        acc_metrics, imp_metrics = evaluate_cl4ljp(model, test_loader, DEVICE)
        print(f"\n[Epoch {epoch + 1} 测试结果]")
        print(
            f"罪名 -> ACC: {acc_metrics['ACC']:.4f} | MP: {acc_metrics['MP']:.4f} | MR: {acc_metrics['MR']:.4f} | F1: {acc_metrics['F1']:.4f}")
        print(
            f"刑期 -> ACC: {imp_metrics['ACC']:.4f} | MP: {imp_metrics['MP']:.4f} | MR: {imp_metrics['MR']:.4f} | F1: {imp_metrics['F1']:.4f}\n")


if __name__ == "__main__":
    TRAIN_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_train.jsonl")
    TEST_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_test.jsonl")

    run_cl4ljp_experiment(TRAIN_FILE, TEST_FILE)