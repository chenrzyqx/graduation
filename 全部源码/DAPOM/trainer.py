"""Inference-time reference adaptation; no optimizer, loss or backpropagation."""
from warnings import warn


def adapt_reference_pool(agent, samples, max_examples=5):
    if max_examples < 0:
        raise ValueError('max_examples must be nonnegative')
    reference = list(samples)
    # Retain bounded prompt examples. A retrieval factory may index the entire reference pool.
    agent.reference_examples = [
        {'fact': item['fact'], 'label': str(float(item['imprisonment'])) + '个月'}
        for item in reference[:max_examples]]
    return agent


def train_agent_with_dapom(agent, train_loader, val_loader=None, epochs=100, lr=5e-5, device='cpu'):
    warn('train_agent_with_dapom is a compatibility alias for reference adaptation; no training occurs',
         DeprecationWarning, stacklevel=2)
    return adapt_reference_pool(agent, [row for batch in train_loader for row in batch])
