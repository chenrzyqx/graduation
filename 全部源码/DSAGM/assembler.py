"""Bind declared resources and execute bounded, observable action loops."""
import json
from .agent_ir import AgentIR
from .prompt_generator import generate_prompt


class RuntimeAgent:
    def __init__(self, ir, llm_core=None, *, tool_registry=None, memory_backends=None,
                 max_steps=100, max_calls=None, trace_path=None, disabled_components=()):
        if not callable(llm_core):
            raise ValueError('A configured LLM callable is required')
        self.ir, self.llm_core = ir, llm_core
        self.max_steps, self.trace_path = max_steps, trace_path
        self.disabled = set(disabled_components)
        self.tools = {}
        registry = tool_registry or {}
        if 'Tool' not in self.disabled:
            for tool in ir.Tools:
                binding = registry.get(tool.tool_id) or registry.get(tool.name)
                if not callable(binding):
                    raise ValueError(f'Unregistered tool: {tool.tool_id}/{tool.name}')
                tool.api = binding
                self.tools[tool.tool_id] = tool
        self.memory_backend = None
        if 'Memory' not in self.disabled and ir.Memory.mem_type == 'long':
            self.memory_backend = (memory_backends or {}).get(ir.Memory.storage)
            if not callable(self.memory_backend):
                raise ValueError(f'Unconfigured memory backend: {ir.Memory.storage}')
        self.max_calls = dict(max_calls or {})
        if max_steps < 1 or any(v < 0 for v in self.max_calls.values()):
            raise ValueError('Invalid execution limit')
        self.last_trace = []

    def build_prompt(self, user_input, all_labels=None):
        examples = []
        if 'Memory' not in self.disabled:
            examples = list(self.ir.Memory.short_term)
            if self.memory_backend:
                examples.extend(self.memory_backend(user_input))
        return generate_prompt(self.ir, user_input=user_input,
                               memory_examples=examples, all_labels=all_labels)

    @staticmethod
    def decode(response):
        text = response.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {'final': response.strip()}

    def execute_tool(self, action, counts):
        tool_id = action['tool']
        if tool_id not in self.tools:
            raise ValueError(f'Action references an unavailable tool: {tool_id}')
        count = counts.get(tool_id, 0)
        if tool_id in self.max_calls and count >= self.max_calls[tool_id]:
            raise ValueError(f'Tool call limit exceeded: {tool_id}')
        tool, arguments = self.tools[tool_id], action.get('arguments', {})
        expected = {p['name']: p['type'] for p in tool.params}
        if set(arguments) != set(expected):
            raise ValueError(f'Incorrect argument names for {tool_id}')
        types = {'string': str, 'int': int, 'float': (int, float), 'bool': bool}
        for name, kind in expected.items():
            value = arguments[name]
            if kind not in types or not isinstance(value, types[kind]) or (
                    kind in ('int', 'float') and isinstance(value, bool)):
                raise ValueError(f'Incorrect argument type: {tool_id}.{name}')
        counts[tool_id] = count + 1
        result = tool.api(**arguments)
        if tool.output_type not in types or not isinstance(result, types[tool.output_type]):
            raise ValueError(f'Incorrect return type: {tool_id}')
        return result

    def run(self, user_input, all_labels=None, **kwargs):
        from experiment_support import append_record
        prompt = self.build_prompt(user_input, all_labels)
        if 'Planning' in self.disabled:
            return self.llm_core(prompt)
        protocol = ('\nReturn JSON only: {"tool":"registered_id","arguments":{...}} '
                    'to request a tool, or {"final":"answer"} when complete.\n')
        observations, counts = [], {}
        self.last_trace = []
        for step in range(self.max_steps):
            response = self.llm_core(prompt + protocol + json.dumps(observations, ensure_ascii=False))
            action = self.decode(response)
            if not isinstance(action, dict):
                raise ValueError('Expected an action object')
            event = {'step': step, 'action': action, 'raw_response': response}
            if 'final' in action:
                answer = (json.dumps(action['final'], ensure_ascii=False)
                          if isinstance(action['final'], (dict, list)) else str(action['final']))
                event['status'] = 'completed'
            elif 'tool' in action:
                event['observation'] = self.execute_tool(action, counts)
                observations.append({'action': action, 'result': event['observation']})
            else:
                raise ValueError('Action must provide tool or final')
            self.last_trace.append(event)
            if self.trace_path:
                append_record(self.trace_path, event)
            if 'final' in action:
                return answer
        raise RuntimeError('Maximum planning iterations reached before completion')


def InitModel(role_id, description, llm_core=None):
    if not callable(llm_core):
        raise ValueError('Missing LLM configuration')
    return llm_core


def Bind(llm_core, prompt_template, tools, memory, **config):
    ir = AgentIR()
    ir.Role.description = prompt_template
    ir.Tools = tools or []
    ir.Memory = memory if isinstance(memory, type(ir.Memory)) else ir.Memory
    return RuntimeAgent(ir, llm_core, **config)


def f_assemble(ir, llm_core=None, **config):
    return RuntimeAgent(ir, llm_core, **config)
