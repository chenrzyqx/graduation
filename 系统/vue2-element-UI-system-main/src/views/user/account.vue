<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div class="hLeft">
        <div class="title">
          <span class="tag">5.3.1</span>
          智能体配置界面（纯前端演示：DSAGM + DAPOM 全流程）
        </div>
        <div class="desc">
          双模式构建：DSL 编辑 /
          拖拽配置；解析→AST→Agent-IR→装配→Prompt；约束抽取→张量→拉格朗日→自适应更新→试运行轨迹
        </div>
      </div>
      <div class="hRight">
        <el-radio-group v-model="mode" size="small">
          <el-radio-button label="dsl">DSL 代码编辑</el-radio-button>
          <el-radio-button label="drag">可视化拖拽</el-radio-button>
        </el-radio-group>
        <el-button
          size="small"
          @click="loadTemplate"
          icon="el-icon-document-add"
          >载入演示模板</el-button
        >
        <el-button size="small" @click="resetAll" icon="el-icon-refresh"
          >重置</el-button
        >
      </div>
    </div>

    <!-- Steps -->
    <el-card class="card">
      <div slot="header" class="cardHeader">
        <div class="cardTitle">流程步骤（按论文方法顺序）</div>
        <div class="btnRow">
          <el-button
            type="primary"
            size="small"
            :loading="loading.parse"
            @click="stepParse"
            icon="el-icon-cpu"
          >
            ① 解析 DSL（Token/AST）
          </el-button>
          <el-button
            type="primary"
            plain
            size="small"
            :loading="loading.ir"
            @click="stepIR"
            icon="el-icon-s-operation"
          >
            ② 生成 Agent-IR（五元组）
          </el-button>
          <el-button
            type="success"
            size="small"
            :loading="loading.assemble"
            @click="stepAssemble"
            icon="el-icon-connection"
          >
            ③ 装配 & Prompt 生成
          </el-button>
          <el-button
            type="warning"
            size="small"
            :loading="loading.dapom"
            @click="stepDAPOM"
            icon="el-icon-odometer"
          >
            ④ DAPOM 语义约束优化
          </el-button>
          <el-button
            type="info"
            size="small"
            :loading="loading.run"
            @click="stepRun"
            icon="el-icon-video-play"
          >
            ⑤ 试运行（轨迹）
          </el-button>
        </div>
      </div>

      <el-steps :active="activeStep" finish-status="success" align-center>
        <el-step title="DSL/拖拽输入" description="双模式构建"></el-step>
        <el-step title="ANTLR4解析" description="Token + AST"></el-step>
        <el-step title="语义映射" description="Agent-IR 五元组"></el-step>
        <el-step
          title="模块装配"
          description="LLM∘Memory∘Planner∘ToolExec"
        ></el-step>
        <el-step title="Prompt生成" description="结构化提示"></el-step>
        <el-step
          title="约束抽取"
          description="目标/边界/工具/输出/预算"
        ></el-step>
        <el-step title="张量构建" description="约束×状态×动作"></el-step>
        <el-step title="拉格朗日优化" description="多目标+惩罚项"></el-step>
        <el-step title="自适应更新" description="λ(t+1)"></el-step>
        <el-step title="运行轨迹" description="思考-行动-观察"></el-step>
      </el-steps>
    </el-card>

    <div class="grid">
      <!-- Left: Builder -->
      <el-card class="card left">
        <div slot="header" class="cardHeader">
          <div class="cardTitle">构建区（DSL 编辑 / 拖拽配置）</div>
          <el-tag type="info">纯前端数据模拟</el-tag>
        </div>

        <!-- DSL mode -->
        <div v-show="mode === 'dsl'">
          <div class="sectionTitle">
            DSL 编辑器（模拟 CodeMirror：高亮/补全/校验可扩展）
          </div>
          <el-input
            class="mono"
            type="textarea"
            :rows="16"
            v-model="dslText"
            placeholder="输入智能体 DSL..."
          />
          <div class="row mt8">
            <el-alert
              :title="
                lintErrors.length
                  ? '语法校验：发现问题（模拟 ANTLR4 报错）'
                  : '语法校验：通过（模拟）'
              "
              :type="lintErrors.length ? 'error' : 'success'"
              show-icon
              :closable="false"
            />
          </div>
          <ul v-if="lintErrors.length" class="errList">
            <li v-for="(e, i) in lintErrors" :key="i">{{ e }}</li>
          </ul>
        </div>

        <!-- Drag mode -->
        <div v-show="mode === 'drag'">
          <div class="sectionTitle">
            组件库（点击添加到画布，模拟 AntV X6 的节点/连线能力）
          </div>
          <div class="palette">
            <div class="pGroup">
              <div class="pTitle">基础组件</div>
              <div class="pItems">
                <div
                  class="chip base"
                  v-for="c in palette.base"
                  :key="c.type"
                  @click="addNode(c)"
                >
                  <i :class="c.icon"></i>{{ c.label }}
                </div>
              </div>
            </div>
            <div class="pGroup">
              <div class="pTitle">工具插件</div>
              <div class="pItems">
                <div
                  class="chip tool"
                  v-for="c in palette.tools"
                  :key="c.type"
                  @click="addNode(c)"
                >
                  <i :class="c.icon"></i>{{ c.label }}
                </div>
              </div>
            </div>
            <div class="pGroup">
              <div class="pTitle">规划策略</div>
              <div class="pItems">
                <div
                  class="chip strat"
                  v-for="c in palette.strategies"
                  :key="c.type"
                  @click="addNode(c)"
                >
                  <i :class="c.icon"></i>{{ c.label }}
                </div>
              </div>
            </div>
            <div class="pGroup">
              <div class="pTitle">语义约束（DAPOM）</div>
              <div class="pItems">
                <div
                  class="chip cons"
                  v-for="c in palette.constraints"
                  :key="c.type"
                  @click="addNode(c)"
                >
                  <i :class="c.icon"></i>{{ c.label }}
                </div>
              </div>
            </div>
          </div>

          <div class="sectionTitle mt12">
            配置画布（简化版）：节点配置 → 自动生成
            DSL（“拖拽即配置、配置即代码”）
            <el-button
              size="mini"
              class="fr"
              type="danger"
              plain
              @click="clearNodes"
              >清空</el-button
            >
          </div>

          <div class="canvas">
            <div v-for="n in nodes" :key="n.id" class="node" :class="n.kind">
              <div class="nodeTop">
                <i :class="n.icon"></i>
                <span class="nodeName">{{ n.label }}</span>
                <span class="sp"></span>
                <el-button
                  type="text"
                  icon="el-icon-close"
                  @click="removeNode(n.id)"
                ></el-button>
              </div>
              <el-input
                size="mini"
                v-model="n.value"
                placeholder="配置值（可选）"
                @input="syncDslFromNodes"
              ></el-input>
              <div class="nodeHint">{{ n.hint }}</div>
            </div>
          </div>

          <div class="sectionTitle mt12">同步生成的 DSL（可继续手工编辑）</div>
          <el-input
            class="mono"
            type="textarea"
            :rows="10"
            v-model="dslText"
          ></el-input>
        </div>
      </el-card>

      <!-- Right: Results -->
      <el-card class="card right">
        <div slot="header" class="cardHeader">
          <div class="cardTitle">流程结果展示（按步骤顺序展开）</div>
          <el-tag type="success" v-if="activeStep >= 4">已生成 Prompt</el-tag>
          <el-tag type="warning" v-if="activeStep >= 8" class="ml8"
            >已完成 DAPOM 优化</el-tag
          >
        </div>

        <el-collapse v-model="openPanels" accordion>
          <el-collapse-item name="p1">
            <template slot="title">① Token & AST（解析结果）</template>
            <div class="two">
              <div>
                <div class="miniTitle">Token 序列（模拟 ANTLR4 词法分析）</div>
                <div class="box">
                  <div v-for="(t, i) in tokens" :key="i" class="line">
                    {{ t }}
                  </div>
                </div>
              </div>
              <div>
                <div class="miniTitle">AST（模拟句法分析得到的树结构）</div>
                <pre class="pre">{{ pretty(ast) }}</pre>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item name="p2">
            <template slot="title"
              >② Agent-IR（五元组：Role/Goals/Memory/Tools/Strategy）</template
            >
            <div class="irGrid">
              <div class="irCard">
                <div class="miniTitle">
                  <i class="el-icon-user"></i> Role（身份/能力边界）
                </div>
                <pre class="pre">{{ pretty(agentIR.role) }}</pre>
              </div>
              <div class="irCard">
                <div class="miniTitle">
                  <i class="el-icon-aim"></i> Goals（含优先级归一化）
                </div>
                <pre class="pre">{{ pretty(agentIR.goals) }}</pre>
              </div>
              <div class="irCard">
                <div class="miniTitle">
                  <i class="el-icon-collection"></i> Memory（短期/长期向量检索）
                </div>
                <pre class="pre">{{ pretty(agentIR.memory) }}</pre>
              </div>
              <div class="irCard">
                <div class="miniTitle">
                  <i class="el-icon-s-tools"></i> Tools（插件化工具）
                </div>
                <pre class="pre">{{ pretty(agentIR.tools) }}</pre>
              </div>
              <div class="irCard">
                <div class="miniTitle">
                  <i class="el-icon-guide"></i> Strategy（候选策略+选择函数）
                </div>
                <pre class="pre">{{ pretty(agentIR.strategy) }}</pre>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item name="p3">
            <template slot="title"
              >③ 模块装配 & 结构化 Prompt（生成结果）</template
            >
            <div class="miniTitle">运行结构（模块函数组合表达）</div>
            <div class="assembly">
              <span class="pill">LLM</span><span class="op">∘</span>
              <span class="pill">Memory</span><span class="op">∘</span>
              <span class="pill">Planner</span><span class="op">∘</span>
              <span class="pill">ToolExecutor</span>
            </div>

            <div class="miniTitle mt12">
              结构化 Prompt（整合角色/目标/记忆/工具/策略约束）
            </div>
            <pre class="pre">{{ prompt }}</pre>
          </el-collapse-item>

          <el-collapse-item name="p4">
            <template slot="title"
              >④ DAPOM（约束抽取→张量→拉格朗日→自适应更新）</template
            >

            <div class="two">
              <div>
                <div class="miniTitle">语义约束集合 C（从 DSL 抽取）</div>
                <pre class="pre">{{ pretty(constraints) }}</pre>
              </div>
              <div>
                <div class="miniTitle">
                  语义控制向量 / 约束向量 v_c（向量化嵌入）
                </div>
                <pre class="pre">{{ pretty(constraintVector) }}</pre>
              </div>
            </div>

            <div class="miniTitle mt12">
              约束张量空间（状态×动作×约束）示意表
            </div>
            <el-table :data="tensorTable" size="mini" stripe border>
              <el-table-column prop="state" label="状态 s" min-width="120" />
              <el-table-column prop="action" label="动作 a" min-width="160" />
              <el-table-column prop="k" label="约束维 k" width="90" />
              <el-table-column prop="strength" label="调制强度" width="110" />
            </el-table>

            <div class="miniTitle mt12">
              拉格朗日松弛 + 自适应权重更新日志（λ(t+1)）
            </div>
            <el-table :data="lagrangeLog" size="mini" stripe border>
              <el-table-column prop="iter" label="迭代" width="70" />
              <el-table-column prop="reward" label="E[回报]" width="90" />
              <el-table-column prop="penalty" label="语义偏差" width="90" />
              <el-table-column prop="lambda" label="λ" width="90" />
              <el-table-column prop="note" label="说明" min-width="220" />
            </el-table>
          </el-collapse-item>

          <el-collapse-item name="p5">
            <template slot="title"
              >⑤ 试运行轨迹（ReAct：思考→行动→观察→约束校验）</template
            >
            <el-timeline>
              <el-timeline-item
                v-for="(x, i) in runTrace"
                :key="i"
                :timestamp="x.time"
                :type="x.type"
              >
                <div class="traceTitle">{{ x.step }}</div>
                <div class="traceContent">{{ x.content }}</div>
              </el-timeline-item>
            </el-timeline>
          </el-collapse-item>
        </el-collapse>

        <el-alert
          class="mt12"
          type="info"
          show-icon
          :closable="false"
          title="说明：本页面仅用于展示论文方法的前端交互流程与中间产物；Token/AST/IR/张量/优化日志/轨迹均为前端模拟数据。"
        />
      </el-card>
    </div>
  </div>
</template>

<script>
export default {
  name: "AgentConfig",
  data() {
    return {
      mode: "dsl",
      activeStep: 0,
      openPanels: "p1",

      dslText: "",
      lintErrors: [],

      loading: {
        parse: false,
        ir: false,
        assemble: false,
        dapom: false,
        run: false,
      },

      tokens: [],
      ast: null,

      agentIR: {
        role: null,
        goals: null,
        memory: null,
        tools: null,
        strategy: null,
      },

      prompt: "",

      constraints: null,
      constraintVector: null,
      tensorTable: [],
      lagrangeLog: [],

      runTrace: [],

      nodes: [],
      nextNodeId: 1,

      palette: {
        base: [
          {
            type: "role",
            label: "Role 角色",
            icon: "el-icon-user",
            hint: "身份/能力边界（capability_limit）",
          },
          {
            type: "goals",
            label: "Goals 目标",
            icon: "el-icon-aim",
            hint: "多目标+优先级权重（需归一化）",
          },
          {
            type: "memory",
            label: "Memory 记忆",
            icon: "el-icon-collection",
            hint: "短期/长期向量检索（top_k）",
          },
        ],
        tools: [
          {
            type: "tool_search",
            label: "Tool 检索",
            icon: "el-icon-search",
            hint: "插件化工具：检索接口",
          },
          {
            type: "tool_calc",
            label: "Tool 计算",
            icon: "el-icon-data-analysis",
            hint: "插件化工具：可计算能力",
          },
          {
            type: "tool_db",
            label: "Tool 数据库",
            icon: "el-icon-coin",
            hint: "插件化工具：结构化查询",
          },
        ],
        strategies: [
          {
            type: "strategy",
            label: "Strategy 策略",
            icon: "el-icon-guide",
            hint: "候选策略集合+选择函数",
          },
          {
            type: "react",
            label: "ReAct",
            icon: "el-icon-refresh",
            hint: "思考-行动-观察循环",
          },
          { type: "cot", label: "CoT", icon: "el-icon-more", hint: "链式推理" },
          {
            type: "tot",
            label: "ToT",
            icon: "el-icon-share",
            hint: "树状探索",
          },
        ],
        constraints: [
          {
            type: "c_goal",
            label: "目标优先级",
            icon: "el-icon-s-flag",
            hint: "sum(priority)=1",
          },
          {
            type: "c_role",
            label: "角色边界",
            icon: "el-icon-lock",
            hint: "strict/normal",
          },
          {
            type: "c_tool",
            label: "工具限制",
            icon: "el-icon-warning",
            hint: "调用次数/白名单",
          },
          {
            type: "c_output",
            label: "输出规范",
            icon: "el-icon-document-checked",
            hint: "strict_json/schema",
          },
          {
            type: "c_budget",
            label: "资源预算",
            icon: "el-icon-timer",
            hint: "max_steps/max_tokens",
          },
        ],
      },
    };
  },

  created() {
    this.loadTemplate();
    this.lintNow();
  },

  watch: {
    dslText() {
      this.lintNow();
    },
  },

  methods: {
    // ---------- UI helpers ----------
    pretty(obj) {
      return JSON.stringify(obj, null, 2);
    },
    nowTime() {
      return new Date().toLocaleTimeString();
    },
    sleep(ms) {
      return new Promise((r) => setTimeout(r, ms));
    },
    toast(type, msg) {
      this.$message({ type, message: msg, showClose: true });
    },

    // ---------- Template ----------
    loadTemplate() {
      this.dslText = `agent "LegalAssistant" {
  role {
    id: "r1"
    desc: "你是一名严谨的法律顾问，回答需引用法条依据，避免越界推断。"
    capability_limit: ["只基于给定案情与检索结果推理", "不输出个人隐私信息"]
  }

  goals [
    { type: "accusation_prediction", constraint: "输出JSON字段: accusation,evidence,law_refs", priority: 0.6 },
    { type: "term_prediction",       constraint: "输出JSON字段: term_years,factors",         priority: 0.4 }
  ]

  memory {
    short_term: "conversation_context"
    long_term: { store: "vector_db", embed_model: "embedding-mock", top_k: 4 }
  }

  tools [
    { name: "LawSearch", in: "query:string", out: "laws:list", api: "mock://law_search" },
    { name: "CaseCalc",  in: "facts:json",   out: "score:number", api: "mock://case_calc" }
  ]

  strategy {
    candidates: ["ReAct","CoT","ToT"]
    select_by: "utility(s, semantic_state)"
  }

  constraints {
    goal_priority_norm: true
    role_boundary: "strict"
    tool_call_limit: { LawSearch: 3, CaseCalc: 2 }
    output_schema: "strict_json"
    budget: { max_steps: 6, max_tokens: 1500 }
  }
}`;
      this.toast("success", "已载入演示模板（可按顺序点击 ①→⑤）");
    },

    resetAll() {
      this.activeStep = 0;
      this.openPanels = "p1";
      this.tokens = [];
      this.ast = null;
      this.agentIR = {
        role: null,
        goals: null,
        memory: null,
        tools: null,
        strategy: null,
      };
      this.prompt = "";
      this.constraints = null;
      this.constraintVector = null;
      this.tensorTable = [];
      this.lagrangeLog = [];
      this.runTrace = [];
      this.nodes = [];
      this.nextNodeId = 1;
      this.loadTemplate();
    },

    // ---------- Lint (mock ANTLR errors) ----------
    lintNow() {
      const t = this.dslText || "";
      const must = [
        "role",
        "goals",
        "memory",
        "tools",
        "strategy",
        "constraints",
      ];
      const errs = [];
      must.forEach((k) => {
        if (!t.includes(k)) errs.push(`缺少关键块：${k}`);
      });

      // 简单校验：priority 是否存在
      if (t.includes("goals") && !t.includes("priority"))
        errs.push("goals 中缺少 priority 权重（示例：priority:0.6）");

      this.lintErrors = errs;
    },

    // ---------- Drag builder ----------
    addNode(c) {
      const id = "n" + this.nextNodeId++;
      const defaults = {
        role: "你是一名领域专家…",
        goals: "taskA:0.6, taskB:0.4",
        memory: "short=ctx; long=vector(top_k=4)",
        strategy: "candidates=ReAct/CoT/ToT",
        react: "ReAct",
        cot: "CoT",
        tot: "ToT",
        tool_search: "LawSearch",
        tool_calc: "CaseCalc",
        tool_db: "DBQuery",
        c_goal: "sum(priority)=1",
        c_role: "strict",
        c_tool: "call_limit",
        c_output: "strict_json",
        c_budget: "max_steps=6",
      };

      this.nodes.push({
        id,
        type: c.type,
        label: c.label,
        icon: c.icon,
        hint: c.hint,
        kind: this.kindOf(c.type),
        value: defaults[c.type] || "",
      });
      this.syncDslFromNodes();
    },

    kindOf(type) {
      if (type.startsWith("tool")) return "kTool";
      if (type.startsWith("c_")) return "kCons";
      if (["strategy", "react", "cot", "tot"].includes(type)) return "kStrat";
      return "kBase";
    },

    removeNode(id) {
      this.nodes = this.nodes.filter((n) => n.id !== id);
      this.syncDslFromNodes();
    },

    clearNodes() {
      this.nodes = [];
      this.syncDslFromNodes();
    },

    syncDslFromNodes() {
      const base = this.nodes.filter((n) => n.kind === "kBase");
      const tools = this.nodes.filter((n) => n.kind === "kTool");
      const strat = this.nodes.filter((n) => n.kind === "kStrat");
      const cons = this.nodes.filter((n) => n.kind === "kCons");

      const role = base.find((x) => x.type === "role");
      const goals = base.find((x) => x.type === "goals");
      const memory = base.find((x) => x.type === "memory");

      const toolLines = tools.length
        ? tools
            .map(
              (t) =>
                `    { name: "${
                  t.value || t.label
                }", in:"mock", out:"mock", api:"mock://${t.type}" }`
            )
            .join(",\n")
        : `    { name: "MockTool", in:"mock", out:"mock", api:"mock://tool" }`;

      const cand = strat
        .filter((s) => ["react", "cot", "tot"].includes(s.type))
        .map((s) => s.value || s.label);
      const candArr = cand.length
        ? candArrToJson(cand)
        : `["ReAct","CoT","ToT"]`;

      const consLines = cons.length
        ? cons.map((c) => `    ${c.type}: "${c.value || "on"}"`).join("\n")
        : `    c_goal: "sum(priority)=1"\n    c_output: "strict_json"`;

      function candArrToJson(arr) {
        return JSON.stringify(
          arr.map((x) => x.replace("Strategy 策略", "Strategy"))
        );
      }

      this.dslText = `agent "DragBuiltAgent" {
  role {
    id: "r_drag"
    desc: "${(role && role.value) || "你是一名领域专家…"}"
    capability_limit: ["mock_limit_1","mock_limit_2"]
  }

  goals [
    { type: "${
      (goals && goals.value) || "taskA"
    }", constraint: "mock_schema", priority: 1.0 }
  ]

  memory {
    short_term: "${(memory && memory.value) || "conversation_context"}"
    long_term: { store:"vector_db", embed_model:"mock", top_k: 4 }
  }

  tools [
${toolLines}
  ]

  strategy {
    candidates: ${candArr}
    select_by: "utility(s, semantic_state)"
  }

  constraints {
${consLines}
  }
}`;
    },

    // ---------- Step ①: Parse ----------
    async stepParse() {
      if (this.lintErrors.length)
        return this.toast("error", "请先修复 DSL 校验错误或载入模板。");
      this.loading.parse = true;
      try {
        this.activeStep = 1;
        this.openPanels = "p1";
        await this.sleep(150);

        const lines = (this.dslText || "")
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean);
        this.tokens = this.mockTokenize(lines);
        this.ast = this.mockAST(lines);

        this.activeStep = 2;
        this.toast("success", "解析完成：Token & AST 已生成（前端模拟）");
      } finally {
        this.loading.parse = false;
      }
    },

    mockTokenize(lines) {
      const out = [];
      lines.forEach((l) => {
        l.split(/[\s{}[\],:]+/)
          .filter(Boolean)
          .forEach((p) => out.push(p));
      });
      return out.slice(0, 160);
    },

    mockAST(lines) {
      const text = lines.join("\n");
      const blocks = [
        "role",
        "goals",
        "memory",
        "tools",
        "strategy",
        "constraints",
      ];
      const ast = {
        type: "AgentProgram",
        name: this.pickAgentName(text),
        blocks: {},
      };
      blocks.forEach((b) => {
        ast.blocks[b] = {
          type: b.toUpperCase() + "_BLOCK",
          raw: this.extractBlock(text, b),
        };
      });
      return ast;
    },

    pickAgentName(text) {
      const m = text.match(/agent\s+"([^"]+)"/);
      return m ? m[1] : "UnnamedAgent";
    },

    extractBlock(text, name) {
      const keys = [
        "role",
        "goals",
        "memory",
        "tools",
        "strategy",
        "constraints",
      ];
      const start = text.indexOf(name);
      if (start < 0) return "";
      const after = text.slice(start);
      const next = keys
        .filter((k) => k !== name)
        .map((k) => {
          const idx = after.indexOf("\n  " + k);
          return idx < 0 ? Infinity : idx;
        });
      const endRel = Math.min(...next);
      return endRel === Infinity ? after : after.slice(0, endRel);
    },

    // ---------- Step ②: Agent-IR ----------
    async stepIR() {
      if (!this.ast) return this.toast("warning", "请先执行 ① 解析 DSL。");
      this.loading.ir = true;
      try {
        this.openPanels = "p2";
        await this.sleep(120);

        this.agentIR = this.mockIRFromAST(this.ast);
        this.activeStep = 3;
        this.toast("success", "Agent-IR 已生成（五元组展示）");
      } finally {
        this.loading.ir = false;
      }
    },

    mockIRFromAST(ast) {
      const b = ast.blocks || {};
      const roleRaw = (b.role && b.role.raw) || "";
      const goalsRaw = (b.goals && b.goals.raw) || "";
      const memoryRaw = (b.memory && b.memory.raw) || "";
      const toolsRaw = (b.tools && b.tools.raw) || "";
      const stratRaw = (b.strategy && b.strategy.raw) || "";

      // goals priority normalize
      const prios = (goalsRaw.match(/priority:\s*([0-9.]+)/g) || [])
        .map((x) => parseFloat(x.replace("priority:", "").trim()))
        .filter((n) => !isNaN(n));
      const sum = prios.reduce((a, c) => a + c, 0) || 1;
      const norm = prios.map((p) => +(p / sum).toFixed(3));

      const tools = (toolsRaw.match(/name:\s*"([^"]+)"/g) || []).map((m) =>
        m.replace(/name:\s*"/, "").replace(/"$/, "")
      );

      const candMatch = stratRaw.match(/candidates:\s*\[([^\]]+)\]/);
      const cand = candMatch
        ? candMatch[1]
            .replace(/"/g, "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : ["ReAct", "CoT", "ToT"];

      return {
        role: {
          id: this.pickKV(roleRaw, "id") || "r1",
          desc: this.pickKV(roleRaw, "desc") || "（未配置）",
          capability_limit: this.pickArray(roleRaw, "capability_limit") || [],
        },
        goals: {
          items: this.parseGoals(goalsRaw, norm),
          priority_normalized: true,
          normalized_weights: norm,
        },
        memory: {
          short_term:
            this.pickKV(memoryRaw, "short_term") || "conversation_context",
          long_term: {
            store: this.pickKV(memoryRaw, "store") || "vector_db",
            embed_model:
              this.pickKV(memoryRaw, "embed_model") || "embedding-mock",
            top_k: parseInt(this.pickKV(memoryRaw, "top_k") || "4", 10),
            // 前端伪造向量库预览
            vector_store_preview: [
              { text: "历史案例A：构成要件…", vec: [0.12, 0.33, 0.91] },
              { text: "历史案例B：量刑因素…", vec: [0.22, 0.71, 0.09] },
            ],
          },
        },
        tools: {
          items: (tools.length ? tools : ["MockTool"]).map((name) => ({
            name,
            in: "mock",
            out: "mock",
            api: "mock://" + name.toLowerCase(),
          })),
          select_fn: "t* = argmax U(t|s)",
        },
        strategy: {
          candidates: cand,
          select_fn: "π* = argmax U(π|semantic_state)",
          state_transition: "s(t+1)=T(s(t),a(t))",
        },
      };
    },

    pickKV(block, key) {
      const m = block.match(new RegExp(key + '\\s*:\\s*"?([^"\\n\\r}]+)"?'));
      return m ? m[1].trim() : "";
    },
    pickArray(block, key) {
      const m = block.match(new RegExp(key + "\\s*:\\s*\\[([^\\]]+)\\]"));
      if (!m) return null;
      return m[1]
        .split(",")
        .map((s) => s.replace(/"/g, "").trim())
        .filter(Boolean);
    },

    parseGoals(raw, normWeights) {
      const items = [];
      const parts = raw
        .split("{")
        .slice(1)
        .map((x) => "{" + x);
      parts.forEach((blk, idx) => {
        const type = this.pickKV(blk, "type") || "goal_" + (idx + 1);
        const constraint = this.pickKV(blk, "constraint") || "mock_constraint";
        items.push({
          type,
          constraint,
          priority:
            typeof normWeights[idx] === "number" ? normWeights[idx] : 0.5,
        });
      });
      return items.length
        ? items
        : [{ type: "mock_goal", constraint: "mock_constraint", priority: 1.0 }];
    },

    // ---------- Step ③: Assemble + Prompt ----------
    async stepAssemble() {
      if (!this.agentIR.role)
        return this.toast("warning", "请先执行 ② 生成 Agent-IR。");
      this.loading.assemble = true;
      try {
        this.openPanels = "p3";
        await this.sleep(120);

        this.prompt = this.makePrompt(this.agentIR);
        this.activeStep = 5;
        this.toast("success", "装配完成：运行结构与结构化 Prompt 已生成");
      } finally {
        this.loading.assemble = false;
      }
    },

    makePrompt(ir) {
      const goals = (ir.goals.items || [])
        .map((g) => `- ${g.type} (w=${g.priority}): ${g.constraint}`)
        .join("\n");
      const tools = (ir.tools.items || [])
        .map((t) => `- ${t.name}: api=${t.api}, in=${t.in}, out=${t.out}`)
        .join("\n");
      return [
        "【ROLE】",
        ir.role.desc,
        "",
        "【CAPABILITY_LIMIT】",
        JSON.stringify(ir.role.capability_limit || []),
        "",
        "【GOALS】",
        goals,
        "",
        "【MEMORY】",
        `short_term=${ir.memory.short_term}; long_term=${ir.memory.long_term.store}; top_k=${ir.memory.long_term.top_k}`,
        "",
        "【TOOLS】",
        tools,
        "",
        "【STRATEGY】",
        `candidates=${JSON.stringify(ir.strategy.candidates)}; select_fn=${
          ir.strategy.select_fn
        }`,
        "",
        "【OUTPUT_CONSTRAINT】",
        "严格输出 JSON；缺失证据/法条时需显式说明为空并给出原因。",
      ].join("\n");
    },

    // ---------- Step ④: DAPOM ----------
    async stepDAPOM() {
      if (!this.prompt)
        return this.toast("warning", "请先执行 ③ 生成 Prompt。");
      this.loading.dapom = true;
      try {
        this.openPanels = "p4";
        this.activeStep = 6;
        await this.sleep(150);

        this.constraints = this.extractConstraints(this.dslText);
        this.constraintVector = this.vectorizeConstraints(this.constraints);
        this.tensorTable = this.makeTensorTable(this.constraintVector);

        this.activeStep = 8;
        await this.sleep(150);

        this.lagrangeLog = this.makeLagrangeLog();
        this.activeStep = 9;

        this.toast("success", "DAPOM 完成：约束→张量→拉格朗日→自适应更新");
      } finally {
        this.loading.dapom = false;
      }
    },

    extractConstraints(text) {
      // 按论文：目标优先级、角色边界、工具限制、输出规范、预算
      const consBlock = this.extractBlock(text, "constraints");
      return {
        goal_priority: {
          normalized: text.includes("goal_priority_norm: true"),
        },
        role_boundary: {
          level: text.includes('role_boundary: "strict"') ? "strict" : "normal",
        },
        tool_limit: {
          raw:
            (text.match(/tool_call_limit:\s*\{[^}]+\}/) || [])[0] ||
            "tool_call_limit:{mock:1}",
        },
        output_spec: {
          schema: text.includes("strict_json") ? "strict_json" : "relaxed",
        },
        budget: {
          max_steps: parseInt(this.pickKV(consBlock, "max_steps") || "6", 10),
          max_tokens: parseInt(
            this.pickKV(consBlock, "max_tokens") || "1500",
            10
          ),
        },
      };
    },

    vectorizeConstraints(c) {
      // 伪造向量化：把约束映射到可计算维度
      const v = [
        c.goal_priority.normalized ? 1.0 : 0.4,
        c.role_boundary.level === "strict" ? 1.0 : 0.5,
        this.hash01(c.tool_limit.raw),
        c.output_spec.schema === "strict_json" ? 1.0 : 0.3,
        Math.min(1, c.budget.max_steps / 10),
      ].map((x) => +x.toFixed(3));

      return {
        dim_k: 5,
        v_c: v,
        explain: [
          "k1目标归一化",
          "k2角色边界",
          "k3工具限制",
          "k4输出规范",
          "k5预算强度",
        ],
      };
    },

    hash01(s) {
      let h = 0;
      for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
      return (h % 1000) / 1000;
    },

    makeTensorTable(v) {
      const states = ["s0初始", "s1检索后", "s2推理中"];
      const actions = ["a0调用检索", "a1调用计算", "a2直接生成"];
      const rows = [];
      for (let i = 0; i < 12; i++) {
        rows.push({
          state: states[i % 3],
          action: actions[(i * 2) % 3],
          k: "k" + ((i % v.dim_k) + 1),
          strength: +(0.2 + 0.75 * v.v_c[i % v.v_c.length]).toFixed(3),
        });
      }
      return rows;
    },

    makeLagrangeLog() {
      // 伪造 λ 更新
      const log = [];
      let lambda = 0.5;
      const lr = 0.18;
      for (let i = 1; i <= 8; i++) {
        const reward = +(0.65 + 0.04 * i + (1 - lambda) * 0.02).toFixed(3);
        const penalty = +(0.6 - 0.05 * i + lambda * 0.07).toFixed(3);
        const violation = Math.max(0, penalty - 0.25);
        lambda = Math.max(0, +(lambda + lr * violation).toFixed(3));
        log.push({
          iter: i,
          reward,
          penalty,
          lambda,
          note: violation > 0 ? "偏差较大→提升λ加强约束" : "偏差可控→λ稳定",
        });
      }
      return log;
    },

    // ---------- Step ⑤: Run ----------
    async stepRun() {
      if (!this.lagrangeLog.length)
        return this.toast("warning", "请先执行 ④ DAPOM 优化。");
      this.loading.run = true;
      try {
        this.openPanels = "p5";
        this.activeStep = 10;
        this.runTrace = [];

        const push = (type, step, content) => {
          this.runTrace.push({ type, step, content, time: this.nowTime() });
        };

        push(
          "primary",
          "输入任务",
          "用户输入：预测罪名与刑期，并给出法条依据（mock）。"
        );
        await this.sleep(120);

        push(
          "success",
          "检索长期记忆",
          "向量检索 top_k=4：命中历史案例A/B（mock）。"
        );
        await this.sleep(120);

        push(
          "warning",
          "策略选择",
          "根据语义状态+约束张量调制：选择 ReAct（稳定且可解释）。"
        );
        await this.sleep(120);

        push(
          "success",
          "行动(Action)",
          "调用工具 LawSearch(query=案情关键词)，受 tool_call_limit 约束。"
        );
        await this.sleep(120);

        push(
          "info",
          "观察(Observe)",
          "工具返回：相关法条列表 + 要件摘要（mock）。"
        );
        await this.sleep(120);

        push(
          "success",
          "行动(Action)",
          "调用工具 CaseCalc(facts=json) 计算量刑因素评分（mock）。"
        );
        await this.sleep(120);

        push(
          "info",
          "观察(Observe)",
          "返回 score=0.73（mock），提示从轻/从重因素（mock）。"
        );
        await this.sleep(120);

        push(
          "danger",
          "约束校验",
          "输出必须 strict_json，字段必须齐全：accusation/evidence/law_refs/term_years/factors。"
        );
        await this.sleep(120);

        push(
          "primary",
          "输出生成",
          "生成 JSON（mock）：accusation=盗窃罪；term_years=2.5；law_refs=[…]；factors=[自首,…]。"
        );

        this.toast("success", "试运行完成：已展示思考-行动-观察与约束校验闭环");
      } finally {
        this.loading.run = false;
      }
    },
  },
};
</script>

<style scoped>
/* --- Light theme --- */
.page {
  min-height: 100vh;
  padding: 16px 18px 24px;
  background: radial-gradient(
      900px 500px at 15% 10%,
      rgba(64, 158, 255, 0.14),
      transparent 60%
    ),
    radial-gradient(
      900px 500px at 85% 15%,
      rgba(230, 162, 60, 0.14),
      transparent 60%
    ),
    #f6f8fc;
  color: #1f2d3d;
  box-sizing: border-box;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e7ebf3;
  border-radius: 14px;
  box-shadow: 0 8px 22px rgba(16, 24, 40, 0.06);
}

.title {
  font-weight: 800;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 28px;
  border-radius: 10px;
  background: rgba(64, 158, 255, 0.12);
  color: #2b6fe8;
  font-weight: 800;
}
.desc {
  margin-top: 6px;
  color: #6b778c;
  font-size: 12px;
  max-width: 880px;
}

.hRight {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.card {
  margin-top: 12px;
  border-radius: 14px;
  border: 1px solid #e7ebf3;
  box-shadow: 0 8px 22px rgba(16, 24, 40, 0.06);
}
.cardHeader {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.cardTitle {
  font-weight: 800;
}

.btnRow {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1.05fr 1.35fr;
  gap: 12px;
}

.sectionTitle {
  font-weight: 800;
  margin-bottom: 8px;
  color: #344054;
}
.mt8 {
  margin-top: 8px;
}
.mt12 {
  margin-top: 12px;
}
.ml8 {
  margin-left: 8px;
}
.fr {
  float: right;
}

.mono ::v-deep textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", monospace;
  border-radius: 12px;
}
.errList {
  margin: 8px 0 0 16px;
  color: #d92d20;
}

.palette {
  display: grid;
  gap: 10px;
}
.pGroup {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px 12px;
}
.pTitle {
  font-weight: 800;
  margin-bottom: 8px;
  color: #475467;
}
.pItems {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  cursor: pointer;
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e7ebf3;
  background: #fff;
  font-weight: 700;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.12s ease;
}
.chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(16, 24, 40, 0.08);
}
.base {
  border-color: rgba(64, 158, 255, 0.35);
}
.tool {
  border-color: rgba(103, 194, 58, 0.35);
}
.strat {
  border-color: rgba(230, 162, 60, 0.35);
}
.cons {
  border-color: rgba(245, 108, 108, 0.35);
}

.canvas {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.node {
  background: #fff;
  border: 1px solid #e7ebf3;
  border-radius: 12px;
  padding: 10px 10px 12px;
}
.nodeTop {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.nodeName {
  font-weight: 800;
  color: #344054;
}
.nodeHint {
  margin-top: 6px;
  color: #667085;
  font-size: 12px;
}
.sp {
  flex: 1;
}
.kBase {
  border-left: 4px solid rgba(64, 158, 255, 0.55);
}
.kTool {
  border-left: 4px solid rgba(103, 194, 58, 0.55);
}
.kStrat {
  border-left: 4px solid rgba(230, 162, 60, 0.55);
}
.kCons {
  border-left: 4px solid rgba(245, 108, 108, 0.55);
}

.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.miniTitle {
  font-weight: 800;
  color: #475467;
  margin-bottom: 6px;
}
.box {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px;
  max-height: 240px;
  overflow: auto;
}
.line {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #344054;
}
.pre {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px;
  max-height: 320px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  color: #344054;
}

.irGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.irCard {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px;
}

.assembly {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 10px 0 6px;
}
.pill {
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e7ebf3;
  border-radius: 999px;
  font-weight: 800;
}
.op {
  font-weight: 900;
  color: #667085;
  font-size: 18px;
}

.traceTitle {
  font-weight: 800;
  color: #344054;
}
.traceContent {
  color: #475467;
  margin-top: 4px;
  line-height: 1.6;
}
</style>
