"""Independent inference-only variants using the same model and generation configuration."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from DAPOM.main import make_agent
from DAPOM.model import DAPOMAgent, final_evaluation


class AblationAgent(DAPOMAgent):
    def __init__(self, *args, ablation_type='full', **kwargs):
        super().__init__(*args, variant=ablation_type, **kwargs)


def run_ablation_study(llm_client, cem, constraint_tensor_space, lagrangian_optimizer,
                       test_loader, device, *, runtime_config=None, runtime_constraints=None,
                       fixed_constraints=None, record_dir=None):
    if fixed_constraints is None:
        raise ValueError('Provide the fixed constraint set for the w/o CEM control')
    results = {}
    for variant in ['full', 'wo_cem', 'wo_cts', 'wo_lmo', 'wo_awu']:
        # Fresh rule tensors and multipliers; no sharing of learned/adapted state across groups.
        agent = make_agent(llm_client, variant=variant, runtime_config=runtime_config,
                           runtime_constraints=runtime_constraints, fixed_constraints=fixed_constraints,
                           trace_path=Path(record_dir) / f'{variant}_trajectory.jsonl' if record_dir else None)
        results[variant] = final_evaluation(agent, test_loader, device,
            record_path=Path(record_dir) / f'{variant}_predictions.jsonl' if record_dir else None)
    return results
