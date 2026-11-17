"""DSAGM 结构化提示生成函数

GeneratePrompt(Agent-IR):
    通过整合角色语义/目标信息/记忆内容/工具说明/策略约束,
    构建结构化提示, 保证输出行为具备一致性与可控性.
"""
from typing import Optional, List
from .agent_ir import AgentIR


def generate_prompt(ir: AgentIR,
                    user_input: str = "",
                    memory_examples: Optional[List] = None,
                    all_labels: Optional[List[str]] = None) -> str:
    """结构化提示构造函数

    通过整合 Role/Goal/Memory/Tool/Planner 五元组语义信息构建结构化提示.
    """
    prompt = ""

    if ir.Role.role_id or ir.Role.description:
        prompt += "# 角色\n"
        if ir.Role.description:
            prompt += f"{ir.Role.description}\n"
        if ir.Role.capabilities:
            prompt += f"能力: {', '.join(ir.Role.capabilities)}\n"
        prompt += "\n"

    if ir.Goals:
        prompt += "# 目标\n"
        for i, g in enumerate(ir.Goals, 1):
            prompt += f"目标{i} (priority={g.priority:.2f}): {g.content or g.goal_type}\n"
        prompt += "\n"

    if memory_examples:
        prompt += "# 参考示例\n"
        for i, example in enumerate(memory_examples, 1):
            if isinstance(example, dict):
                ex_fact = example.get('fact', '')
                ex_acc = example.get('accusation', example.get('label', ''))
            else:
                ex_fact, ex_acc = example
            prompt += f"示例{i}:\n事实：{ex_fact}\n输出：{ex_acc}\n\n"
    elif ir.Memory.short_term:
        prompt += "# 参考示例\n"
        for i, ex in enumerate(ir.Memory.short_term, 1):
            prompt += f"示例{i}: {ex}\n"
        prompt += "\n"

    if ir.Tools:
        prompt += "# 可用工具\n"
        for t in ir.Tools:
            params_str = ", ".join(f"{p['name']}:{p['type']}" for p in t.params)
            prompt += f"- {t.name}({params_str}) -> {t.output_type}\n"
        prompt += "\n"

    if ir.Planner.strategy:
        prompt += f"# 推理策略\n{ir.Planner.strategy}\n\n"

    if user_input:
        prompt += f"# 当前案件事实\n{user_input}\n\n"

    if all_labels:
        import re
        def _clean(t):
            return re.sub(r'[^一-鿿]', '', t.strip())
        label_list = "、".join(_clean(l) for l in all_labels)
        prompt += ("请从以下罪名中选择一个最合适的输出，**只输出一个罪名**，不要输出其他任何内容。\n"
                   f"输出格式：直接输出罪名名称，例如\"盗窃\"，**不要带\"罪\"字**。\n"
                   f"严格从以下可选罪名中选择并输出：{label_list}\n")

    return prompt
