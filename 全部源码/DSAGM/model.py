"""DSAGM 主模型

包含:
- 冻结LLM，基于DSL、Agent-IR与真实资源进行推理期装配
- 形式化映射 f = f_assemble ∘ f_map ∘ f_parse
- 结构完整率 SIR
"""
import json
import os
import random
import re
import time
import requests
from tqdm import tqdm
from typing import List, Dict, Tuple, Optional, Any

from .dsl.engine import DSLEngine
from .agent_ir import AgentIR
from .mapper import f_map
from .assembler import f_assemble
from .prompt_generator import generate_prompt


API_KEY = os.environ.get("LLM_API_KEY", "")
URL = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1").rstrip('/') + '/chat/completions'
MODEL = os.environ.get("LLM_MODEL_NAME", "deepseek-reasoner")
TEMPERATURE = 0.1
MAX_TOKENS = 2048
TOP_P = 0.9
MAX_RETRIES = 3
RETORY_DELAY = 2

BATCH_SIZE = 32

LAMBDA_STRUCT_INIT = 1.0
LAMBDA_SEM_INIT = 0.8
LAMBDA_DECAY = 0.7


def load_data(file_path: str, sample_size: Optional[int] = None) -> Tuple[List[str], List[str]]:
    """从 JSONL 文件加载事实和罪名 (取第一个罪名), 跳过解析错误的行"""
    facts, accusations = [], []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            fact = item.get('fact', '')
            acc_list = item.get('meta', {}).get('accusation', [])
            if not acc_list:
                continue
            accusations.append(acc_list[0])
            facts.append(fact)

    if sample_size is not None and sample_size < len(facts):
        indices = random.sample(range(len(facts)), sample_size)
        facts = [facts[i] for i in indices]
        accusations = [accusations[i] for i in indices]
    return facts, accusations


def build_label_map_from_train(train_accusations: List[str]) -> Tuple[Dict[str, int], List[str]]:
    """基于训练集构建罪名到 ID 的映射"""
    unique_labels = sorted(set(train_accusations))
    label_to_id = {label: i for i, label in enumerate(unique_labels)}
    id_to_label = unique_labels
    return label_to_id, id_to_label


def call_llm(prompt: str) -> Optional[str]:
    if not API_KEY:
        raise ValueError("LLM_API_KEY is required; no fallback predictions are generated")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "top_p": TOP_P,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return content.strip()
        except Exception as e:
            print(f"API调用失败（尝试 {attempt + 1}/{MAX_RETRIES}）: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETORY_DELAY)
            else:
                return None


def clean_text(text: str) -> str:
    """清洗文本: 只保留中文字符 (Unicode 范围: 一-鿿)"""
    text = text.strip()
    return re.sub(r'[^一-鿿]', '', text)


def extract_accusation(response: str, label_list: List[str]) -> Optional[str]:
    """从模型输出中提取罪名, 先清洗 (只留中文), 再与清洗后的标签列表匹配"""
    if not response:
        return None
    response_clean = clean_text(response)
    if not response_clean:
        return None
    for label in label_list:
        if response_clean == clean_text(label):
            return label
    return None


def compute_metrics(y_true: List[int], y_pred: List[int], epsilon=1e-9, labels=None) -> Dict[str, float]:
    """Acc / Macro-P / Macro-R / Macro-F1"""
    from experiment_support import classification_metrics
    return classification_metrics(y_true, y_pred, labels=labels)


DEFAULT_DSL_TEMPLATE = """agent LegalAgent {{
  role legal_expert {{
    description "你是一名经验丰富的刑事法律专家，精通中国刑法，擅长根据案件事实准确判断罪名。"
    capabilities [case_analysis, law_retrieval, case_similarity, charge_prediction]
  }}
  goal predict_charge {{
    type classification
    priority 1.0
    content "根据提供的案件事实，预测被告人所犯的罪名。"
  }}
  tool law_retrieval {{
    name "law_retrieval"
    params query: string
    output string
  }}
  tool case_similarity {{
    name "case_similarity"
    params query: string
    output string
  }}
  memory {{
    type long
    storage "vector_db"
  }}
  planner {{
    strategy {strategy}
  }}
}}
"""


def build_default_dsl(strategy: str = "ReAct", memory_examples_num: int = 0) -> str:
    """生成默认 DSL 文本"""
    return DEFAULT_DSL_TEMPLATE.format(strategy=strategy)


class DSAGMGenerator:
    """f = f_assemble ∘ f_map ∘ f_parse

    - f_parse:   P_dsl -> AST  (DSL 解析引擎四阶段)
    - f_map:     AST -> Agent-IR
    - f_assemble: Agent-IR -> RuntimeAgent
    """

    def __init__(self):
        self.engine = DSLEngine()

    def generate(self, dsl_text: str, llm_core=None, **runtime_config) -> Tuple[AgentIR, Any]:
        """完整形式化映射: DSL -> AST -> Agent-IR -> RuntimeAgent"""
        _ir_dict, ast = self.engine.parse(dsl_text)
        ir = f_map(ast)
        runtime = f_assemble(ir, llm_core=llm_core, **runtime_config)
        return ir, runtime







def compute_sir(instances):
    instances = list(instances)
    if not instances:
        raise ValueError('No constructed instances available for SIR')
    return sum(instance.structure_integrity() for instance in instances) / len(instances) * 100.0
