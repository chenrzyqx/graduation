import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder


class LawDatasetText:
    def __init__(self, file_path):
        self.data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    item = json.loads(line)
                    fact = item['fact']
                    imprisonment = item['meta']['term_of_imprisonment']['imprisonment']
                    if imprisonment < 0:
                        continue
                    self.data.append({
                        'fact': fact,
                        'imprisonment': imprisonment,
                        'relevant_articles': item['meta'].get('relevant_articles', []),
                        'accusation': item['meta'].get('accusation', ['未知'])[0],
                        'punish_of_money': item['meta'].get('punish_of_money', 0)
                    })
        print(f"Loaded {len(self.data)} valid samples from {file_path}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        return {
            'fact': item['fact'],
            'imprisonment': item['imprisonment'],
            'articles': item['relevant_articles'],
            'accusation': item['accusation'],
            'money': item['punish_of_money']
        }


class LawformerTextDataset(Dataset):
    def __init__(self, texts, imprisonment_labels, accusation_labels, tokenizer, max_length=512):
        self.texts = texts
        self.imprisonment_labels = imprisonment_labels
        self.accusation_labels = accusation_labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        imprisonment_label = self.imprisonment_labels[idx]
        accusation_label = self.accusation_labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'imprisonment_label': torch.tensor(imprisonment_label, dtype=torch.float),
            'accusation_label': torch.tensor(accusation_label, dtype=torch.long)
        }


class LawformerMultiTask(nn.Module):
    def __init__(self, model_name='thu-coai/roberta-legal-large-chinese', dropout=0.3, num_accusation_classes=None):
        super().__init__()
        try:
            from transformers import AutoModel, AutoTokenizer
            self.lawformer = AutoModel.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            hidden_size = self.lawformer.config.hidden_size
        except Exception as e:
            raise ImportError(f"Please install transformers and download model: {e}")

        self.dropout = nn.Dropout(dropout)

        self.imprisonment_fc1 = nn.Linear(hidden_size, 256)
        self.imprisonment_fc2 = nn.Linear(256, 128)
        self.imprisonment_fc3 = nn.Linear(128, 1)

        self.accusation_fc1 = nn.Linear(hidden_size, 256)
        self.accusation_fc2 = nn.Linear(256, 128)
        self.accusation_fc3 = nn.Linear(128, num_accusation_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.lawformer(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0, :]
        x = self.dropout(pooled_output)

        imprisonment_out = torch.relu(self.imprisonment_fc1(x))
        imprisonment_out = self.dropout(imprisonment_out)
        imprisonment_out = torch.relu(self.imprisonment_fc2(imprisonment_out))
        imprisonment_out = self.dropout(imprisonment_out)
        imprisonment_out = self.imprisonment_fc3(imprisonment_out)

        accusation_out = torch.relu(self.accusation_fc1(x))
        accusation_out = self.dropout(accusation_out)
        accusation_out = torch.relu(self.accusation_fc2(accusation_out))
        accusation_out = self.dropout(accusation_out)
        accusation_out = self.accusation_fc3(accusation_out)

        return imprisonment_out.squeeze(), accusation_out


def calculate_metrics(true_values, pred_values, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_values, pred_values, terms=True)


def calculate_accusation_metrics(true_labels, pred_labels, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_labels, pred_labels, terms=False)


def train_lawformer_model(model, train_loader, epochs=3, lr=2e-5, device='cuda'):
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    imprisonment_criterion = nn.MSELoss()
    accusation_criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        total_loss = 0

        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            imprisonment_labels = batch['imprisonment_label'].to(device)
            accusation_labels = batch['accusation_label'].to(device)

            optimizer.zero_grad()
            imprisonment_outputs, accusation_outputs = model(input_ids, attention_mask)
            loss1 = imprisonment_criterion(imprisonment_outputs, imprisonment_labels)
            loss2 = accusation_criterion(accusation_outputs, accusation_labels)
            loss = loss1 + loss2
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")


def evaluate_lawformer_model(model, data_loader, device='cuda'):
    model.eval()
    all_imprisonment_preds = []
    all_imprisonment_labels = []
    all_accusation_preds = []
    all_accusation_labels = []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            imprisonment_labels = batch['imprisonment_label']
            accusation_labels = batch['accusation_label']

            imprisonment_outputs, accusation_outputs = model(input_ids, attention_mask)
            all_imprisonment_preds.extend(imprisonment_outputs.cpu().numpy())
            all_imprisonment_labels.extend(imprisonment_labels.numpy())
            all_accusation_preds.extend(torch.argmax(accusation_outputs, dim=1).cpu().numpy())
            all_accusation_labels.extend(accusation_labels.numpy())

    imprisonment_metrics = calculate_metrics(all_imprisonment_labels, all_imprisonment_preds)
    accusation_metrics = calculate_accusation_metrics(all_accusation_labels, all_accusation_preds)

    return imprisonment_metrics, accusation_metrics


def run_lawformer_experiment(train_file, test_file, model_name='thu-coai/roberta-legal-large-chinese', epochs=3):
    print(f"\n--- Lawformer ({model_name}) Experiment ---")

    train_dataset = LawDatasetText(train_file)
    test_dataset = LawDatasetText(test_file)

    train_texts = [item['fact'] for item in train_dataset.data]
    train_imprisonment = [item['imprisonment'] for item in train_dataset.data]
    train_accusation = [item['accusation'] for item in train_dataset.data]

    test_texts = [item['fact'] for item in test_dataset.data]
    test_imprisonment = [item['imprisonment'] for item in test_dataset.data]
    test_accusation = [item['accusation'] for item in test_dataset.data]

    print("\n--- Label Encoding for Accusation ---")
    label_encoder = LabelEncoder()
    y_train_accusation = label_encoder.fit_transform(train_accusation)
    y_test_accusation = label_encoder.transform(test_accusation)
    num_accusation_classes = len(label_encoder.classes_)
    print(f"Number of accusation classes: {num_accusation_classes}")

    print("\n--- Loading Lawformer Model ---")
    model = LawformerMultiTask(model_name=model_name, num_accusation_classes=num_accusation_classes)
    tokenizer = model.tokenizer

    train_dataset_lf = LawformerTextDataset(
        train_texts, 
        train_imprisonment, 
        y_train_accusation, 
        tokenizer
    )
    test_dataset_lf = LawformerTextDataset(
        test_texts, 
        test_imprisonment, 
        y_test_accusation, 
        tokenizer
    )

    train_loader = DataLoader(train_dataset_lf, batch_size=4, shuffle=True)
    test_loader = DataLoader(test_dataset_lf, batch_size=4, shuffle=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    print("\n--- Training ---")
    train_lawformer_model(model, train_loader, epochs=epochs, device=device)

    print("\n--- Evaluating ---")
    imprisonment_metrics, accusation_metrics = evaluate_lawformer_model(model, test_loader, device=device)

    print(f"\nImprisonment Prediction Results:")
    print(f"Accuracy (ACC):     {imprisonment_metrics['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {imprisonment_metrics['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {imprisonment_metrics['MP']:.4f}")
    print(f"F1 Score (Macro):   {imprisonment_metrics['F1']:.4f}")

    print(f"\nAccusation Prediction Results:")
    print(f"Accuracy (ACC):     {accusation_metrics['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {accusation_metrics['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {accusation_metrics['MP']:.4f}")
    print(f"F1 Score (Macro):   {accusation_metrics['F1']:.4f}")

    return {'imprisonment': imprisonment_metrics, 'accusation': accusation_metrics}


if __name__ == "__main__":
    train_file = 'cail_small/data_train.jsonl'
    test_file = 'cail_small/data_test.jsonl'

    run_lawformer_experiment(train_file, test_file, model_name='thu-coai/roberta-legal-large-chinese', epochs=3)
