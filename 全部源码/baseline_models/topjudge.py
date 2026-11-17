import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder


class LawDatasetTopJudge(Dataset):
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


class TopJudgeTextDataset(Dataset):
    def __init__(self, texts, imprisonment_labels, accusation_labels, word2idx, max_length=512):
        self.texts = texts
        self.imprisonment_labels = imprisonment_labels
        self.accusation_labels = accusation_labels
        self.word2idx = word2idx
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def text_to_indices(self, text):
        words = text.split()
        indices = [self.word2idx.get(w, self.word2idx.get('<UNK>', 0)) for w in words]
        if len(indices) < self.max_length:
            indices += [self.word2idx.get('<PAD>', 1)] * (self.max_length - len(indices))
        return indices[:self.max_length]

    def __getitem__(self, idx):
        text = self.texts[idx]
        imprisonment_label = self.imprisonment_labels[idx]
        accusation_label = self.accusation_labels[idx]

        text_indices = self.text_to_indices(text)

        return {
            'text_indices': torch.tensor(text_indices, dtype=torch.long),
            'imprisonment_label': torch.tensor(imprisonment_label, dtype=torch.float),
            'accusation_label': torch.tensor(accusation_label, dtype=torch.long)
        }


class TextEncoderCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_filters, filter_sizes, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, num_filters, fs) for fs in filter_sizes
        ])
        self.fc = nn.Linear(len(filter_sizes) * num_filters, hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        embedded = self.embedding(x)
        embedded = embedded.permute(0, 2, 1)
        conv_outputs = [F.relu(conv(embedded)) for conv in self.convs]
        pooled = [F.max_pool1d(conv, conv.size(2)).squeeze(2) for conv in conv_outputs]
        concat = torch.cat(pooled, dim=1)
        output = self.fc(self.dropout(concat))
        return output


class TextEncoderLSTM(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_layers=2, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, num_layers=num_layers,
                           batch_first=True, dropout=dropout if num_layers > 1 else 0,
                           bidirectional=True)
        self.fc = nn.Linear(hidden_dim * 2, hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        embedded = self.embedding(x)
        lstm_out, (hidden, cell) = self.lstm(embedded)
        hidden_concat = torch.cat([hidden[-2], hidden[-1]], dim=1)
        output = self.fc(self.dropout(hidden_concat))
        return output


class TopJudgeMultiTask(nn.Module):
    def __init__(self, vocab_size, embed_dim=128, hidden_dim=256, num_filters=100,
                 filter_sizes=[2, 3, 4, 5], num_accusation_classes=None,
                 encoder_type='CNN', num_layers=2, dropout=0.3):
        super().__init__()

        if encoder_type == 'CNN':
            self.encoder = TextEncoderCNN(vocab_size, embed_dim, hidden_dim,
                                          num_filters, filter_sizes, dropout)
        elif encoder_type == 'LSTM':
            self.encoder = TextEncoderLSTM(vocab_size, embed_dim, hidden_dim,
                                           num_layers, dropout)
        else:
            raise ValueError(f"Unknown encoder type: {encoder_type}")

        self.dropout = nn.Dropout(dropout)

        self.imprisonment_fc1 = nn.Linear(hidden_dim, 128)
        self.imprisonment_fc2 = nn.Linear(128, 64)
        self.imprisonment_fc3 = nn.Linear(64, 1)

        self.accusation_fc1 = nn.Linear(hidden_dim, 128)
        self.accusation_fc2 = nn.Linear(128, 64)
        self.accusation_fc3 = nn.Linear(64, num_accusation_classes)

    def forward(self, text_indices):
        encoded = self.encoder(text_indices)
        x = self.dropout(encoded)

        imprisonment_out = F.relu(self.imprisonment_fc1(x))
        imprisonment_out = self.dropout(imprisonment_out)
        imprisonment_out = F.relu(self.imprisonment_fc2(imprisonment_out))
        imprisonment_out = self.dropout(imprisonment_out)
        imprisonment_out = self.imprisonment_fc3(imprisonment_out)

        accusation_out = F.relu(self.accusation_fc1(x))
        accusation_out = self.dropout(accusation_out)
        accusation_out = F.relu(self.accusation_fc2(accusation_out))
        accusation_out = self.dropout(accusation_out)
        accusation_out = self.accusation_fc3(accusation_out)

        return imprisonment_out.squeeze(), accusation_out


def build_vocabulary(texts, min_freq=2):
    word_counts = {}
    for text in texts:
        for word in text.split():
            word_counts[word] = word_counts.get(word, 0) + 1

    word2idx = {'<PAD>': 0, '<UNK>': 1}
    for word, count in word_counts.items():
        if count >= min_freq:
            word2idx[word] = len(word2idx)
    return word2idx


def calculate_metrics(true_values, pred_values, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_values, pred_values, terms=True)


def calculate_accusation_metrics(true_labels, pred_labels, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_labels, pred_labels, terms=False)


def train_topjudge_model(model, train_loader, epochs=10, lr=1e-3, device='cuda'):
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    imprisonment_criterion = nn.MSELoss()
    accusation_criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        total_loss = 0

        for batch in train_loader:
            text_indices = batch['text_indices'].to(device)
            imprisonment_labels = batch['imprisonment_label'].to(device)
            accusation_labels = batch['accusation_label'].to(device)

            optimizer.zero_grad()
            imprisonment_outputs, accusation_outputs = model(text_indices)

            loss1 = imprisonment_criterion(imprisonment_outputs, imprisonment_labels)
            loss2 = accusation_criterion(accusation_outputs, accusation_labels)
            loss = loss1 + loss2

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")


def evaluate_topjudge_model(model, data_loader, device='cuda'):
    model.eval()
    all_imprisonment_preds = []
    all_imprisonment_labels = []
    all_accusation_preds = []
    all_accusation_labels = []

    with torch.no_grad():
        for batch in data_loader:
            text_indices = batch['text_indices'].to(device)
            imprisonment_labels = batch['imprisonment_label']
            accusation_labels = batch['accusation_label']

            imprisonment_outputs, accusation_outputs = model(text_indices)

            all_imprisonment_preds.extend(imprisonment_outputs.cpu().numpy())
            all_imprisonment_labels.extend(imprisonment_labels.numpy())
            all_accusation_preds.extend(torch.argmax(accusation_outputs, dim=1).cpu().numpy())
            all_accusation_labels.extend(accusation_labels.numpy())

    imprisonment_metrics = calculate_metrics(all_imprisonment_labels, all_imprisonment_preds)
    accusation_metrics = calculate_accusation_metrics(all_accusation_labels, all_accusation_preds)

    return imprisonment_metrics, accusation_metrics


def run_topjudge_experiment(train_file, test_file, encoder_type='CNN', epochs=10):
    print(f"\n--- TopJudge ({encoder_type.upper()} Encoder) Experiment ---")

    train_dataset = LawDatasetTopJudge(train_file)
    test_dataset = LawDatasetTopJudge(test_file)

    train_texts = [item['fact'] for item in train_dataset.data]
    train_imprisonment = [item['imprisonment'] for item in train_dataset.data]
    train_accusation = [item['accusation'] for item in train_dataset.data]

    test_texts = [item['fact'] for item in test_dataset.data]
    test_imprisonment = [item['imprisonment'] for item in test_dataset.data]
    test_accusation = [item['accusation'] for item in test_dataset.data]

    print("\n--- Building Vocabulary ---")
    word2idx = build_vocabulary(train_texts + test_texts, min_freq=2)
    vocab_size = len(word2idx)
    print(f"Vocabulary size: {vocab_size}")

    print("\n--- Label Encoding for Accusation ---")
    label_encoder = LabelEncoder()
    y_train_accusation = label_encoder.fit_transform(train_accusation)
    y_test_accusation = label_encoder.transform(test_accusation)
    num_accusation_classes = len(label_encoder.classes_)
    print(f"Number of accusation classes: {num_accusation_classes}")

    print("\n--- Creating Datasets ---")
    train_dataset_topjudge = TopJudgeTextDataset(
        train_texts,
        train_imprisonment,
        y_train_accusation,
        word2idx,
        max_length=512
    )
    test_dataset_topjudge = TopJudgeTextDataset(
        test_texts,
        test_imprisonment,
        y_test_accusation,
        word2idx,
        max_length=512
    )

    train_loader = DataLoader(train_dataset_topjudge, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset_topjudge, batch_size=16, shuffle=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    print(f"\n--- Loading TopJudge-{encoder_type.upper()} Model ---")
    model = TopJudgeMultiTask(
        vocab_size=vocab_size,
        embed_dim=128,
        hidden_dim=256,
        num_filters=100,
        filter_sizes=[2, 3, 4, 5],
        num_accusation_classes=num_accusation_classes,
        encoder_type=encoder_type,
        dropout=0.3
    )

    print("\n--- Training ---")
    train_topjudge_model(model, train_loader, epochs=epochs, device=device)

    print("\n--- Evaluating ---")
    imprisonment_metrics, accusation_metrics = evaluate_topjudge_model(model, test_loader, device=device)

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

    print("=" * 60)
    print("Running TopJudge with CNN Encoder")
    print("=" * 60)
    run_topjudge_experiment(train_file, test_file, encoder_type='CNN', epochs=10)

    print("\n" + "=" * 60)
    print("Running TopJudge with LSTM Encoder")
    print("=" * 60)
    run_topjudge_experiment(train_file, test_file, encoder_type='LSTM', epochs=10)
