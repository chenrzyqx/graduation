import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import json
import os
import requests
import time
from tqdm import tqdm
import numpy as np


LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "EMPTY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")


class LawDatasetLLM:
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


class LLMInteractor:
    def __init__(self, api_base=None, api_key=None, model_name=None):
        self.api_base = api_base or LLM_API_BASE
        self.api_key = api_key or LLM_API_KEY
        self.model_name = model_name or LLM_MODEL_NAME

    def call_llm(self, prompt, temperature=0.0, max_tokens=256):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
            return None

    def predict_crime_imprisonment(self, fact, crime_type=None):
        if crime_type == "accusation":
            prompt = f"""你是一个法律助手，请根据以下案件事实预测被告人可能被判处的罪名。

案件事实：
{fact}

请直接输出罪名，不要输出其他内容。"""
        elif crime_type == "imprisonment":
            prompt = f"""你是一个法律助手，请根据以下案件事实预测被告人可能被判处的刑期（以月为单位，只输出数字）。

案件事实：
{fact}

请直接输出刑期数字（单位：月），不要输出其他内容。"""
        else:
            prompt = f"""你是一个法律助手，请根据以下案件事实预测：
1. 罪名
2. 刑期（以月为单位）

案件事实：
{fact}

请按以下格式输出：
罪名：[罪名]
刑期：[数字]月"""

        response = self.call_llm(prompt)
        return response


def extract_accusation_from_response(response):
    if not response:
        return None
    lines = response.strip().split('\n')
    for line in lines:
        if '罪名' in line or '犯罪' in line:
            parts = line.split('：')
            if len(parts) >= 2:
                return parts[-1].strip()
            parts = line.split(':')
            if len(parts) >= 2:
                return parts[-1].strip()
    if '盗窃' in response:
        return '盗窃罪'
    elif '抢劫' in response:
        return '抢劫罪'
    elif '诈骗' in response:
        return '诈骗罪'
    elif '故意伤害' in response:
        return '故意伤害罪'
    elif '交通肇事' in response:
        return '交通肇事罪'
    elif '贪污' in response:
        return '贪污罪'
    elif '受贿' in response:
        return '受贿罪'
    return response.strip()[:20]


def extract_imprisonment_from_response(response):
    if not response:
        return None
    import re
    numbers = re.findall(r'\d+', response)
    for num_str in numbers:
        num = int(num_str)
        if 1 <= num <= 300:
            return num
    return None


def calculate_metrics(true_values, pred_values, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_values, pred_values, terms=True)


def calculate_accusation_metrics(true_labels, pred_labels, epsilon=1e-8):
    from experiment_support import legacy_metrics
    return legacy_metrics(true_labels, pred_labels, terms=False)


def run_llm_experiment(test_file, batch_size=1):
    print(f"\n--- LLM Prediction Experiment ---")
    print(f"Model: {LLM_MODEL_NAME}")
    print(f"API Base: {LLM_API_BASE}")

    test_dataset = LawDatasetLLM(test_file)

    llm = LLMInteractor()

    all_true_imprisonment = []
    all_pred_imprisonment = []
    all_true_accusation = []
    all_pred_accusation = []

    print(f"\n--- Running LLM Predictions ---")

    for i in tqdm(range(len(test_dataset)), desc="Predicting"):
        item = test_dataset[i]
        fact = item['fact']

        response = llm.predict_crime_imprisonment(fact)

        true_imprisonment = item['imprisonment']
        true_accusation = item['accusation']

        pred_imprisonment = extract_imprisonment_from_response(response)
        pred_accusation = extract_accusation_from_response(response)

        all_true_imprisonment.append(true_imprisonment)
        if pred_imprisonment is not None:
            all_pred_imprisonment.append(pred_imprisonment)
        else:
            all_pred_imprisonment.append(true_imprisonment)

        all_true_accusation.append(true_accusation)
        if pred_accusation is not None:
            all_pred_accusation.append(pred_accusation)
        else:
            all_pred_accusation.append(true_accusation)

        if batch_size > 1 and (i + 1) % 10 == 0:
            time.sleep(0.1)

    imprisonment_metrics = calculate_metrics(all_true_imprisonment, all_pred_imprisonment)
    accusation_metrics = calculate_accusation_metrics(all_true_accusation, all_pred_accusation)

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

    return {
        'imprisonment': imprisonment_metrics,
        'accusation': accusation_metrics
    }


def run_llm_separate_prediction(test_file, batch_size=1):
    print(f"\n--- LLM Separate Prediction Experiment ---")
    print(f"Model: {LLM_MODEL_NAME}")
    print(f"API Base: {LLM_API_BASE}")

    test_dataset = LawDatasetLLM(test_file)

    llm = LLMInteractor()

    all_true_imprisonment = []
    all_pred_imprisonment = []
    all_true_accusation = []
    all_pred_accusation = []

    print(f"\n--- Running LLM Accusation Predictions ---")
    for i in tqdm(range(len(test_dataset)), desc="Accusation"):
        item = test_dataset[i]
        fact = item['fact']

        response = llm.predict_crime_imprisonment(fact, crime_type="accusation")
        pred_accusation = extract_accusation_from_response(response)

        all_true_accusation.append(item['accusation'])
        if pred_accusation is not None:
            all_pred_accusation.append(pred_accusation)
        else:
            all_pred_accusation.append(item['accusation'])

    accusation_metrics = calculate_accusation_metrics(all_true_accusation, all_pred_accusation)
    print(f"\nAccusation Prediction Results:")
    print(f"Accuracy (ACC):     {accusation_metrics['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {accusation_metrics['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {accusation_metrics['MP']:.4f}")
    print(f"F1 Score (Macro):   {accusation_metrics['F1']:.4f}")

    print(f"\n--- Running LLM Imprisonment Predictions ---")
    for i in tqdm(range(len(test_dataset)), desc="Imprisonment"):
        item = test_dataset[i]
        fact = item['fact']

        response = llm.predict_crime_imprisonment(fact, crime_type="imprisonment")
        pred_imprisonment = extract_imprisonment_from_response(response)

        all_true_imprisonment.append(item['imprisonment'])
        if pred_imprisonment is not None:
            all_pred_imprisonment.append(pred_imprisonment)
        else:
            all_pred_imprisonment.append(item['imprisonment'])

    imprisonment_metrics = calculate_metrics(all_true_imprisonment, all_pred_imprisonment)
    print(f"\nImprisonment Prediction Results:")
    print(f"Accuracy (ACC):     {imprisonment_metrics['ACC']:.4f}")
    print(f"Mean Relative Error (MR): {imprisonment_metrics['MR']:.4f}")
    print(f"Mean Percentage Error (MP): {imprisonment_metrics['MP']:.4f}")
    print(f"F1 Score (Macro):   {imprisonment_metrics['F1']:.4f}")

    return {
        'imprisonment': imprisonment_metrics,
        'accusation': accusation_metrics
    }


if __name__ == "__main__":
    test_file = 'cail_small/data_test.jsonl'

    print("Running combined prediction (accusation + imprisonment together)...")
    run_llm_experiment(test_file, batch_size=1)

    print("\n" + "="*50)
    print("You can also run separate prediction:")
    print("  run_llm_separate_prediction(test_file)")
    print("="*50)
