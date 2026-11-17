"""Same frozen model, prompt and retrieval resources; no DAPOM scoring."""
import torch
from torch import nn
from DSAGM.dsl.engine import DSLEngine
from DSAGM.mapper import f_map
from DSAGM.assembler import f_assemble
from DAPOM.model import DAPOMAgent


class LLMAgent(nn.Module):
    def __init__(self, llm_client, runtime_config=None):
        super().__init__()
        self.llm_client = llm_client
        self.reference_examples = []
        # Reuse exactly the task declaration without creating a DAPOM instance.
        dsl = DAPOMAgent._default_dsl(self)
        _, ast = DSLEngine().parse(dsl)
        self.ir = f_map(ast)
        if runtime_config is None:
            from runtime_config import load_runtime_config
            runtime_config = load_runtime_config()
        self.runtime = f_assemble(self.ir, llm_core=llm_client.generate, **runtime_config)

    def forward(self, batch_facts, batch_articles=None, batch_accusations=None,
                batch_money=None, target_imprisonment=None):
        self.ir.Memory.short_term = list(self.reference_examples)
        predictions = []
        for fact in batch_facts:
            response = self.runtime.run(fact + '\n最终答案输出JSON对象，字段imprisonment为有期徒刑月数。')
            result = self.runtime.decode(response)
            if not isinstance(result, dict) or not isinstance(result.get('imprisonment'), (int, float)):
                raise ValueError('Expected a structured imprisonment prediction')
            predictions.append(float(result['imprisonment']))
        device = batch_money.device if batch_money is not None else 'cpu'
        return torch.tensor(predictions, device=device), torch.zeros(len(predictions), device=device)
