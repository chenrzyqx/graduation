"""DSAGM 模块入口"""
from .model import (
    DSAGMGenerator,
    load_data, build_label_map_from_train, call_llm,
    clean_text, extract_accusation, compute_metrics, compute_sir,
    build_default_dsl,
)
from .agent_ir import AgentIR, Role, Goal, Memory, Tool, Planner
from .mapper import f_map
from .assembler import f_assemble, RuntimeAgent
from .prompt_generator import generate_prompt

__all__ = [
    "DSAGMGenerator",
    "load_data", "build_label_map_from_train", "call_llm",
    "clean_text", "extract_accusation", "compute_metrics", "compute_sir",
    "build_default_dsl",
    "AgentIR", "Role", "Goal", "Memory", "Tool", "Planner",
    "f_map", "f_assemble", "RuntimeAgent", "generate_prompt",
]
