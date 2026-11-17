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

NUM_CIRCUMSTANCES = 4  # NeurJudge 核心超参：提取多少个"情节"
WEIGHT_CE = 1.0  # 罪名分类损失权重
WEIGHT_MSE = 0.05  # 刑期回归损失权重


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


class NeurJudgeDataset(Dataset):
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


# ==================== NeurJudge 核心：情节提取器 ====================

class CircumstanceAttention(nn.Module):
    """
    多通道注意力机制：将一段文本提取为 K 个不同的情节特征向量
    """

    def __init__(self, hidden_size, num_circumstances):
        super(CircumstanceAttention, self).__init__()
        self.num_circumstances = num_circumstances
        self.w1 = nn.Linear(hidden_size, hidden_size // 2)
        self.w2 = nn.Linear(hidden_size // 2, num_circumstances)

    def forward(self, hidden_states, attention_mask):
        # hidden_states: [Batch, Seq_len, Hidden_size]

        # 1. 计算注意力分数
        u = torch.tanh(self.w1(hidden_states))  # [B, L, H/2]
        attn_weights = self.w2(u)  # [B, L, K]
        attn_weights = attn_weights.transpose(1, 2)  # [B, K, L]

        # 2. 掩蔽 Padding 部分
        mask = attention_mask.unsqueeze(1)  # [B, 1, L]
        attn_weights = attn_weights.masked_fill(mask == 0, -1e9)

        # 3. 归一化注意力权重
        attn_weights = F.softmax(attn_weights, dim=-1)  # [B, K, L]

        # 4. 加权聚合得到 K 个情节特征
        # [B, K, L] x [B, L, H] -> [B, K, H]
        circumstance_repr = torch.bmm(attn_weights, hidden_states)
        return circumstance_repr


# ==================== NeurJudge 双任务模型 ====================

class NeurJudgeModel(nn.Module):
    def __init__(self, num_classes, model_name=MODEL_NAME, num_circumstances=NUM_CIRCUMSTANCES):
        super(NeurJudgeModel, self).__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size

        # 情节感知注意力层
        self.circumstance_extractor = CircumstanceAttention(hidden_size, num_circumstances)

        # 将 K 个情节特征展平后的维度
        flatten_size = hidden_size * num_circumstances

        # 任务 1：罪名分类器
        self.classifier = nn.Sequential(
            nn.Linear(flatten_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, num_classes)
        )

        # 任务 2：刑期回归器
        self.regressor = nn.Sequential(
            nn.Linear(flatten_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 1)
        )

    def forward(self, input_ids, attention_mask):
        # 1. 编码事实文本
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state  # [B, L, H]

        # 2. 提取多个情节特征
        # [B, K, H]
        circumstance_features = self.circumstance_extractor(sequence_output, attention_mask)

        # 3. 展平情节特征用于判决
        # [B, K * H]
        flatten_features = circumstance_features.view(circumstance_features.size(0), -1)

        # 4. 双任务预测
        logits = self.classifier(flatten_features)
        imprisonment_pred = self.regressor(flatten_features).squeeze(-1)

        return logits, imprisonment_pred


# ==================== 评测指标 ====================

def calculate_accusation_metrics(y_true, y_pred, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(y_true, y_pred, terms=False)


def calculate_imprisonment_metrics(true_vals, pred_vals, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_vals, pred_vals, terms=True)


def evaluate_neurjudge(model, data_loader, device):
    model.eval()
    acc_true, acc_pred = [], []
    imp_true, imp_pred = [], []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            imprisonments = batch['imprisonment'].to(device)

            logits, imp_preds = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=1)

            acc_true.extend(labels.cpu().numpy())
            acc_pred.extend(preds.cpu().numpy())
            imp_true.extend(imprisonments.cpu().numpy())

            # 使用 ReLU 防止预测出负数的刑期
            imp_preds = F.relu(imp_preds)
            imp_pred.extend(imp_preds.cpu().numpy())

    return (calculate_accusation_metrics(acc_true, acc_pred),
            calculate_imprisonment_metrics(imp_true, imp_pred))


# ==================== 主训练流程 ====================

def run_neurjudge_experiment(train_path: str, test_path: str):
    print("--- 初始化 NeurJudge [情节感知神经网络] (PyTorch) ---")

    train_data = safe_load_jsonl_multitask(train_path)
    test_data = safe_load_jsonl_multitask(test_path)

    unique_labels = sorted(list(set([d['accusation'] for d in train_data])))
    label_to_id = {l: i for i, l in enumerate(unique_labels)}
    num_classes = len(unique_labels)

    # 过滤测试集
    test_data = [d for d in test_data if d['accusation'] in label_to_id]

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    train_dataset = NeurJudgeDataset(train_data, label_to_id, tokenizer, MAX_LEN)
    test_dataset = NeurJudgeDataset(test_data, label_to_id, tokenizer, MAX_LEN)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = NeurJudgeModel(num_classes=num_classes, model_name=MODEL_NAME).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    criterion_ce = nn.CrossEntropyLoss()
    criterion_mse = nn.MSELoss()

    print("\n--- 开始训练 NeurJudge ---")
    for epoch in range(EPOCHS):
        model.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{EPOCHS}")

        for batch in pbar:
            optimizer.zero_grad()

            input_ids = batch['input_ids'].to(DEVICE)
            attention_mask = batch['attention_mask'].to(DEVICE)
            labels = batch['label'].to(DEVICE)
            imprisonments = batch['imprisonment'].to(DEVICE)

            logits, imp_preds = model(input_ids, attention_mask)

            # 1. 罪名预测损失
            loss_ce = criterion_ce(logits, labels)
            # 2. 刑期回归损失
            loss_mse = criterion_mse(imp_preds, imprisonments)

            # 联合损失
            loss = (WEIGHT_CE * loss_ce) + (WEIGHT_MSE * loss_mse)

            loss.backward()
            optimizer.step()

            pbar.set_postfix({'CE': f"{loss_ce.item():.2f}", 'MSE': f"{loss_mse.item():.2f}"})

        acc_metrics, imp_metrics = evaluate_neurjudge(model, test_loader, DEVICE)
        print(f"\n[Epoch {epoch + 1} 测试结果]")
        print(
            f"罪名 -> ACC: {acc_metrics['ACC']:.4f} | MP: {acc_metrics['MP']:.4f} | MR: {acc_metrics['MR']:.4f} | F1: {acc_metrics['F1']:.4f}")
        print(
            f"刑期 -> ACC: {imp_metrics['ACC']:.4f} | MP: {imp_metrics['MP']:.4f} | MR: {imp_metrics['MR']:.4f} | F1: {imp_metrics['F1']:.4f}\n")


if __name__ == "__main__":
    TRAIN_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_train.jsonl")
    TEST_FILE = str(_Path(__file__).resolve().parents[1] / "DSAGM" / "cail_small" / "data_test.jsonl")

    run_neurjudge_experiment(TRAIN_FILE, TEST_FILE)