import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVR, SVC
from sklearn.preprocessing import StandardScaler
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


def calculate_metrics(true_values, pred_values, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_values, pred_values, terms=True)


def calculate_accusation_metrics(true_labels, pred_labels, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_labels, pred_labels, terms=False)


def run_tfidf_svm_experiment(train_file, test_file):
    print("--- TF-IDF + SVM Baseline Experiment ---")

    train_dataset = LawDatasetText(train_file)
    test_dataset = LawDatasetText(test_file)

    train_texts = [item['fact'] for item in train_dataset.data]
    train_imprisonment = [item['imprisonment'] for item in train_dataset.data]
    train_accusation = [item['accusation'] for item in train_dataset.data]

    test_texts = [item['fact'] for item in test_dataset.data]
    test_imprisonment = [item['imprisonment'] for item in test_dataset.data]
    test_accusation = [item['accusation'] for item in test_dataset.data]

    print("\n--- Building TF-IDF Features ---")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train = vectorizer.fit_transform(train_texts)
    X_test = vectorizer.transform(test_texts)

    y_train_imprisonment = np.array(train_imprisonment)
    y_test_imprisonment = np.array(test_imprisonment)

    print(f"Training samples: {X_train.shape[0]}, Features: {X_train.shape[1]}")
    print(f"Test samples: {X_test.shape[0]}")

    scaler = StandardScaler(with_mean=False)
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("\n--- Training SVM for Imprisonment Prediction ---")
    svm_model_imprisonment = SVR(kernel='rbf', C=1.0, gamma='scale')
    svm_model_imprisonment.fit(X_train_scaled, y_train_imprisonment)

    print("\n--- Evaluating Imprisonment Prediction ---")
    predictions_imprisonment = svm_model_imprisonment.predict(X_test_scaled)
    metrics_imprisonment = calculate_metrics(y_test_imprisonment, predictions_imprisonment)

    print(f"\nImprisonment Prediction Results:")
    print(f"Accuracy (ACC):     {metrics_imprisonment['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {metrics_imprisonment['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {metrics_imprisonment['MP']:.4f}")
    print(f"F1 Score (Macro):   {metrics_imprisonment['F1']:.4f}")

    print("\n--- Training SVM for Accusation Prediction ---")
    label_encoder = LabelEncoder()
    y_train_accusation = label_encoder.fit_transform(train_accusation)
    y_test_accusation = label_encoder.transform(test_accusation)

    svm_model_accusation = SVC(kernel='rbf', C=1.0, gamma='scale')
    svm_model_accusation.fit(X_train_scaled, y_train_accusation)

    print("\n--- Evaluating Accusation Prediction ---")
    predictions_accusation = svm_model_accusation.predict(X_test_scaled)
    metrics_accusation = calculate_accusation_metrics(y_test_accusation, predictions_accusation)

    print(f"\nAccusation Prediction Results:")
    print(f"Accuracy (ACC):     {metrics_accusation['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {metrics_accusation['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {metrics_accusation['MP']:.4f}")
    print(f"F1 Score (Macro):   {metrics_accusation['F1']:.4f}")

    return {'imprisonment': metrics_imprisonment, 'accusation': metrics_accusation}


if __name__ == "__main__":
    train_file = 'cail_small/data_train.jsonl'
    test_file = 'cail_small/data_test.jsonl'

    run_tfidf_svm_experiment(train_file, test_file)
