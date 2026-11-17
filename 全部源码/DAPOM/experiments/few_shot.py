"""Frozen-model reference-pool experiment with three independent repetitions."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import random
from DAPOM.main import make_agent
from DAPOM.model import final_evaluation
from DAPOM.trainer import adapt_reference_pool
from DAPOM.models.llm_only import LLMAgent


def run_few_shot_experiment(llm_client, cem, constraint_tensor_space, lagrangian_optimizer,
                            train_dataset, test_loader, device,
                            shot_sizes=(100, 500, 1000, 3000, 5000, 10000, None), *,
                            resource_factory, repeats=3, seed=42, record_dir=None,
                            runtime_constraints=None):
    # The factory must build both methods' tools and memory from the same supplied pool.
    if repeats != 3:
        raise ValueError('The revised thesis protocol specifies exactly three repetitions')
    results = []
    for size in shot_sizes:
        if size is not None and size > len(train_dataset):
            raise ValueError(f'Requested {size} references, only {len(train_dataset)} available')
        for repeat in range(repeats):
            run_seed = seed + repeat
            rng = random.Random(run_seed)
            indices = (rng.sample(range(len(train_dataset)), size) if size is not None
                       else list(range(len(train_dataset))))
            pool = [train_dataset[i] for i in indices]
            # Recreate the same resource snapshot separately for each method.
            config = resource_factory(pool)
            agent = make_agent(llm_client, runtime_config=config, runtime_constraints=runtime_constraints)
            adapt_reference_pool(agent, pool)
            baseline = LLMAgent(llm_client, runtime_config=resource_factory(pool))
            baseline.reference_examples = list(agent.reference_examples)
            row = {'reference_pool_size': size if size is not None else 'full',
                   'repeat': repeat + 1, 'sampling_seed': run_seed, 'reference_indices': indices}
            for method, model in [('DAPOM', agent), ('prompt_retrieval_baseline', baseline)]:
                path = (Path(record_dir) / f'{size}_{repeat + 1}_{method}.jsonl') if record_dir else None
                row[method] = final_evaluation(model, test_loader, device, record_path=path)
            results.append(row)
    return results
