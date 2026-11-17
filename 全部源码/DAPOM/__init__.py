"""DAPOM 模块入口"""
from .model import (
    DAPOMAgent, OpenAICompatibleAPI, LawDataset,
    calculate_metrics, final_evaluation, save_experiment_results,
    LAMBDA_INIT, ALPHA, LAMBDA_SEM, WEIGHT_DECAY, MAX_ITER,
    CONSTRAINT_DIM, STATE_DIM, ACTION_DIM,
    TEMPERATURE, MAX_TOKENS,
)
from .cem import ConstraintExtractionEngine, ConstraintVector
from .constraint_tensor import ConstraintTensorSpace, construct_tensor
from .lagrangian import LagrangianOptimizer
from .trainer import train_agent_with_dapom

__all__ = [
    "DAPOMAgent", "OpenAICompatibleAPI", "LawDataset",
    "calculate_metrics", "final_evaluation", "save_experiment_results",
    "ConstraintExtractionEngine", "ConstraintVector",
    "ConstraintTensorSpace", "construct_tensor",
    "LagrangianOptimizer", "train_agent_with_dapom",
    "LAMBDA_INIT", "ALPHA", "LAMBDA_SEM", "WEIGHT_DECAY", "MAX_ITER",
    "CONSTRAINT_DIM", "STATE_DIM", "ACTION_DIM",
    "TEMPERATURE", "MAX_TOKENS",
]
