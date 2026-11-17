<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div class="hLeft">
        <div class="title">
          <span class="tag">监控</span>
          智能体运行监控（实例/指标/轨迹/日志/约束闭环）
        </div>
        <div class="desc">
          纯前端模拟：多模型联动、记忆向量检索、规划策略(ReAct/CoT/ToT)、工具插件化调用、实时日志/异常、指标监控与DAPOM约束强度λ自适应更新闭环
        </div>
      </div>
      <div class="hRight">
        <el-button size="small" icon="el-icon-refresh" @click="resetAll"
          >重置演示</el-button
        >
      </div>
    </div>

    <!-- Flow steps -->
    <el-card class="card">
      <div slot="header" class="cardHeader">
        <div class="cardTitle">运行监控流程（按顺序展示）</div>
        <div class="miniTip">
          启动实例 → 运行管线 → 指标看板 → 约束调制 → 轨迹回放 → 日志/告警
        </div>
      </div>
      <el-steps :active="flowStep" finish-status="success" align-center>
        <el-step title="① 选择/启动实例" description="模型/版本/参数"></el-step>
        <el-step title="② 运行管线" description="记忆→策略→工具→输出"></el-step>
        <el-step title="③ 实时指标" description="QPS/成功率/延迟"></el-step>
        <el-step title="④ 约束调制(DAPOM)" description="λ自适应更新"></el-step>
        <el-step title="⑤ 轨迹回放" description="ReAct/ToT路径"></el-step>
        <el-step title="⑥ 日志与告警" description="筛选/导出"></el-step>
      </el-steps>
    </el-card>

    <!-- Top controls -->
    <el-card class="card">
      <div slot="header" class="cardHeader">
        <div class="cardTitle">① 选择智能体与启动运行实例</div>
        <div class="miniTip">
          模拟“多模型联动模块 +
          运行时执行层”：支持模型切换、温度/最大长度、实例启停
        </div>
      </div>

      <div class="controls">
        <el-select
          size="small"
          v-model="pick.agentId"
          placeholder="选择智能体"
          class="w220"
          @change="onPickAgent"
        >
          <el-option
            v-for="a in agents"
            :key="a.id"
            :label="a.name"
            :value="a.id"
          ></el-option>
        </el-select>

        <el-select
          size="small"
          v-model="pick.version"
          placeholder="版本"
          class="w120"
        >
          <el-option
            v-for="v in versionsOfPick"
            :key="v"
            :label="'v' + v"
            :value="v"
          ></el-option>
        </el-select>

        <el-select
          size="small"
          v-model="pick.model"
          placeholder="模型"
          class="w160"
        >
          <el-option label="GPT-4 (mock)" value="gpt4"></el-option>
          <el-option label="GPT-3.5 (mock)" value="gpt35"></el-option>
          <el-option label="文心一言4.0 (mock)" value="ernie4"></el-option>
          <el-option label="通义千问3.0 (mock)" value="qwen3"></el-option>
        </el-select>

        <div class="kv">
          <span>Temperature</span>
          <el-slider
            v-model="pick.temp"
            :min="0"
            :max="1"
            :step="0.05"
            show-input
          ></el-slider>
        </div>

        <div class="kv">
          <span>Max Tokens</span>
          <el-input-number
            size="small"
            v-model="pick.maxTokens"
            :min="256"
            :max="8192"
            :step="256"
          ></el-input-number>
        </div>

        <el-button
          size="small"
          type="primary"
          icon="el-icon-video-play"
          :disabled="!pick.agentId"
          :loading="loading.start"
          @click="startInstance"
          >启动实例</el-button
        >

        <el-button
          size="small"
          type="danger"
          icon="el-icon-switch-button"
          :disabled="!instance.running"
          @click="stopInstance"
          >停止</el-button
        >

        <el-tag
          v-if="instance.running"
          type="success"
          effect="dark"
          class="ml8"
        >
          RUNNING · {{ instance.id }}
        </el-tag>
        <el-tag v-else type="info" class="ml8">未运行</el-tag>
      </div>

      <el-alert
        class="mt12"
        show-icon
        :closable="false"
        type="info"
        title="说明：该监控页把“运行时装配后的智能体实例”视为可观测对象，展示：模块执行链路、性能指标、轨迹与日志，并提供语义约束λ的调制入口。"
      />
    </el-card>

    <div class="grid">
      <!-- Left: pipeline + constraint -->
      <div class="leftCol">
        <!-- Pipeline -->
        <el-card class="card">
          <div slot="header" class="cardHeader">
            <div class="cardTitle">② 运行管线（结构化执行链路）</div>
            <div class="miniTip">
              输入 → 记忆检索(top_k) → 策略选择 → 工具调用(受限) → 输出校验
            </div>
          </div>

          <div v-if="instance.running" class="pipe">
            <el-steps
              direction="vertical"
              :active="pipeActive"
              finish-status="success"
            >
              <el-step title="输入任务">
                <template slot="description">
                  <div class="pipeBox">
                    <el-input
                      type="textarea"
                      :rows="3"
                      v-model="taskInput"
                    ></el-input>
                    <div class="row mt8">
                      <span class="lbl">规划策略</span>
                      <el-radio-group v-model="pipe.strategy" size="small">
                        <el-radio-button label="ReAct"></el-radio-button>
                        <el-radio-button label="CoT"></el-radio-button>
                        <el-radio-button label="ToT"></el-radio-button>
                      </el-radio-group>
                      <span class="lbl ml12">记忆top_k</span>
                      <el-input-number
                        size="small"
                        v-model="pipe.topk"
                        :min="1"
                        :max="10"
                      ></el-input-number>
                    </div>
                    <div class="row mt8">
                      <el-button
                        size="small"
                        type="primary"
                        icon="el-icon-cpu"
                        :loading="loading.tick"
                        @click="singleTick"
                      >
                        执行一次Tick（模拟一步）
                      </el-button>
                      <el-button
                        size="small"
                        icon="el-icon-video-play"
                        :loading="loading.run"
                        @click="autoRun"
                      >
                        自动运行(5步)
                      </el-button>
                      <el-button
                        size="small"
                        icon="el-icon-delete"
                        @click="clearRunData"
                        >清空链路数据</el-button
                      >
                    </div>
                  </div>
                </template>
              </el-step>

              <el-step title="记忆检索（向量检索）">
                <template slot="description">
                  <div class="pipeBox">
                    <div class="miniTitle">命中结果（mock）</div>
                    <el-table :data="memHits" size="mini" border stripe>
                      <el-table-column
                        prop="text"
                        label="记忆片段"
                        min-width="240"
                      ></el-table-column>
                      <el-table-column
                        prop="score"
                        label="相似度"
                        width="90"
                        align="center"
                      ></el-table-column>
                    </el-table>
                    <el-tag class="mt8" type="info"
                      >命中率：{{
                        (metrics.memHitRate * 100).toFixed(0)
                      }}%</el-tag
                    >
                  </div>
                </template>
              </el-step>

              <el-step title="策略调度（ReAct/CoT/ToT）">
                <template slot="description">
                  <div class="pipeBox">
                    <div class="miniTitle">策略选择结果（mock）</div>
                    <el-tag type="warning" effect="plain" class="mr6"
                      >selected: {{ pipe.strategy }}</el-tag
                    >
                    <el-tag type="info" effect="plain"
                      >state_vector: s(t) · constraints_tensor · action</el-tag
                    >
                    <div class="mt8 tip">
                      DAPOM：规划目标 = 奖励最大化 +
                      语义惩罚项（λ控制强度），并可自适应更新。
                    </div>
                  </div>
                </template>
              </el-step>

              <el-step title="工具执行（插件化调用/限制）">
                <template slot="description">
                  <div class="pipeBox">
                    <div class="miniTitle">工具调用统计（mock）</div>
                    <el-table :data="toolStatsTable" size="mini" border stripe>
                      <el-table-column
                        prop="tool"
                        label="工具"
                        width="140"
                      ></el-table-column>
                      <el-table-column
                        prop="used"
                        label="已用/上限"
                        width="120"
                        align="center"
                      ></el-table-column>
                      <el-table-column
                        prop="last"
                        label="最近一次调用"
                        min-width="220"
                      ></el-table-column>
                    </el-table>
                    <div class="mt8 tip">
                      说明：工具调用受 DSL
                      语义约束（tool_call_limit）调制，超限触发告警。
                    </div>
                  </div>
                </template>
              </el-step>

              <el-step title="输出校验（语义约束/格式一致性）">
                <template slot="description">
                  <div class="pipeBox">
                    <div class="miniTitle">校验结果（mock）</div>
                    <el-tag
                      :type="outputCheck.ok ? 'success' : 'danger'"
                      effect="dark"
                    >
                      {{ outputCheck.ok ? "PASS" : "FAIL" }}
                    </el-tag>
                    <div class="mt8">
                      <el-progress
                        :percentage="Math.floor(outputCheck.score * 100)"
                        :status="outputCheck.ok ? 'success' : 'exception'"
                      ></el-progress>
                    </div>
                    <div class="mt8 tip">
                      λ={{
                        lambda.toFixed(2)
                      }}：λ越高，越严格遵循输出schema/角色边界/工具限制；违反会触发“自适应上调λ”。
                    </div>
                    <pre class="pre mt8">{{
                      pretty(outputCheck.sampleOutput)
                    }}</pre>
                  </div>
                </template>
              </el-step>
            </el-steps>
          </div>

          <empty-hint v-else text="未运行：请先在上方启动一个运行实例。" />
        </el-card>

        <!-- Constraint modulation -->
        <el-card class="card">
          <div slot="header" class="cardHeader">
            <div class="cardTitle">④ 语义约束调制（DAPOM 可视化）</div>
            <div class="miniTip">λ自适应更新：违反约束→λ↑；稳定执行→λ↓</div>
          </div>

          <div v-if="instance.running" class="dapom">
            <div class="row">
              <span class="lbl">语义惩罚系数 λ</span>
              <el-slider
                v-model="lambda"
                :min="0"
                :max="1"
                :step="0.05"
                show-input
              ></el-slider>
            </div>

            <div class="row mt10">
              <el-button
                size="small"
                type="primary"
                icon="el-icon-magic-stick"
                @click="autoTuneLambda"
                :disabled="loading.tune"
              >
                自动调节（模拟乘子更新）
              </el-button>
              <el-button
                size="small"
                icon="el-icon-refresh"
                @click="lambda = 0.5"
                >恢复默认</el-button
              >
              <el-tag class="ml8" type="info">学习率 η={{ eta }}</el-tag>
            </div>

            <el-divider></el-divider>

            <div class="miniTitle">约束张量切片（mock 可视化）</div>
            <div class="tensorGrid">
              <div v-for="(c, i) in constraints" :key="i" class="tensorCard">
                <div class="tHead">
                  <div class="tName">{{ c.name }}</div>
                  <el-tag
                    size="mini"
                    :type="c.level === 'hard' ? 'danger' : 'warning'"
                    effect="plain"
                    >{{ c.level }}</el-tag
                  >
                </div>
                <div class="tDesc">{{ c.desc }}</div>
                <el-progress
                  class="mt8"
                  :percentage="Math.floor(c.satisfaction * 100)"
                  :status="
                    c.satisfaction >= 0.7
                      ? 'success'
                      : c.satisfaction >= 0.45
                      ? 'warning'
                      : 'exception'
                  "
                ></el-progress>
                <div class="tFoot">
                  调制强度：{{ (lambda * c.weight).toFixed(2) }}
                </div>
              </div>
            </div>

            <el-alert
              class="mt12"
              show-icon
              :closable="false"
              type="info"
              title="说明：这里把 DSL 中抽取的目标优先级、角色能力边界、工具调用限制、记忆限制、输出规范等映射为约束集合，并用λ调节语义惩罚项强度。"
            />
          </div>

          <empty-hint
            v-else
            text="未运行：请先启动实例后查看 DAPOM 约束调制。"
          />
        </el-card>
      </div>

      <!-- Right: metrics + trace + logs -->
      <div class="rightCol">
        <!-- Metrics -->
        <el-card class="card">
          <div slot="header" class="cardHeader">
            <div class="cardTitle">③ 实时指标看板</div>
            <div class="btns">
              <el-button
                size="small"
                type="primary"
                icon="el-icon-video-play"
                :disabled="!instance.running || timer"
                @click="startRefresh"
              >
                开始刷新
              </el-button>
              <el-button
                size="small"
                icon="el-icon-video-pause"
                :disabled="!timer"
                @click="stopRefresh"
              >
                暂停
              </el-button>
            </div>
          </div>

          <div v-if="instance.running" class="kpiGrid">
            <div class="kpi">
              <div class="kTitle">QPS</div>
              <div class="kVal">{{ metrics.qps.toFixed(1) }}</div>
              <div class="kSub">请求/秒（mock）</div>
            </div>
            <div class="kpi">
              <div class="kTitle">成功率</div>
              <div class="kVal">
                {{ (metrics.successRate * 100).toFixed(0) }}%
              </div>
              <div class="kSub">PASS/总运行</div>
            </div>
            <div class="kpi">
              <div class="kTitle">平均延迟</div>
              <div class="kVal">{{ metrics.avgLatency.toFixed(0) }}ms</div>
              <div class="kSub">端到端（mock）</div>
            </div>
            <div class="kpi">
              <div class="kTitle">平均步数</div>
              <div class="kVal">{{ metrics.avgSteps.toFixed(1) }}</div>
              <div class="kSub">规划步数（mock）</div>
            </div>
            <div class="kpi">
              <div class="kTitle">记忆命中率</div>
              <div class="kVal">
                {{ (metrics.memHitRate * 100).toFixed(0) }}%
              </div>
              <div class="kSub">top_k={{ pipe.topk }}</div>
            </div>
            <div class="kpi">
              <div class="kTitle">约束遵循</div>
              <div class="kVal">
                {{ (metrics.constraintOK * 100).toFixed(0) }}%
              </div>
              <div class="kSub">与λ相关</div>
            </div>
          </div>

          <div v-if="instance.running" class="mt12">
            <div class="miniTitle">工具调用占比（mock）</div>
            <el-progress
              :percentage="toolShare.ToolSearch"
              text-inside
            ></el-progress>
            <el-progress
              :percentage="toolShare.ToolCalc"
              text-inside
              class="mt8"
            ></el-progress>
            <el-progress
              :percentage="toolShare.ToolWrite"
              text-inside
              class="mt8"
            ></el-progress>
            <div class="tip mt8">
              说明：插件化工具执行模块的可观测性：调用占比、超限告警、最近调用内容。
            </div>
          </div>

          <empty-hint v-else text="未运行：启动实例后可查看实时指标。" />
        </el-card>

        <!-- Trace replay -->
        <el-card class="card">
          <div slot="header" class="cardHeader">
            <div class="cardTitle">⑤ 轨迹回放（ReAct/ToT 可解释）</div>
            <div class="btns">
              <el-button
                size="small"
                icon="el-icon-delete"
                :disabled="trace.length === 0"
                @click="trace = []"
                >清空轨迹</el-button
              >
            </div>
          </div>

          <div v-if="instance.running">
            <el-timeline v-if="trace.length">
              <el-timeline-item
                v-for="(x, i) in trace"
                :key="i"
                :timestamp="x.time"
                :type="x.type"
              >
                <div class="tTitle">{{ x.step }}</div>
                <div class="tText">{{ x.content }}</div>
              </el-timeline-item>
            </el-timeline>
            <empty-hint
              v-else
              text="暂无轨迹：点击“执行一次Tick/自动运行”生成。"
            />
          </div>

          <empty-hint v-else text="未运行：启动实例后可回放轨迹。" />
        </el-card>

        <!-- Logs & Alerts -->
        <el-card class="card">
          <div slot="header" class="cardHeader">
            <div class="cardTitle">⑥ 日志与告警（实时记录/筛选/导出）</div>
            <div class="btns">
              <el-button
                size="small"
                icon="el-icon-download"
                :disabled="filteredLogs.length === 0"
                @click="exportLogs"
                >导出日志</el-button
              >
              <el-button
                size="small"
                icon="el-icon-delete"
                :disabled="logs.length === 0"
                @click="clearLogs"
                >清空</el-button
              >
            </div>
          </div>

          <div v-if="instance.running">
            <div class="logFilters">
              <el-select
                size="small"
                v-model="logFilter.level"
                placeholder="级别"
                class="w120"
              >
                <el-option label="全部" value=""></el-option>
                <el-option label="INFO" value="INFO"></el-option>
                <el-option label="WARN" value="WARN"></el-option>
                <el-option label="ERROR" value="ERROR"></el-option>
              </el-select>
              <el-input
                size="small"
                class="w240"
                v-model="logFilter.keyword"
                placeholder="关键词过滤"
                prefix-icon="el-icon-search"
              ></el-input>
              <el-button
                size="small"
                icon="el-icon-refresh"
                @click="logFilter = { level: '', keyword: '' }"
                >重置</el-button
              >
            </div>

            <el-table :data="filteredLogs" size="mini" stripe border>
              <el-table-column
                prop="time"
                label="时间"
                width="160"
              ></el-table-column>
              <el-table-column
                prop="level"
                label="级别"
                width="90"
                align="center"
              >
                <template slot-scope="s">
                  <el-tag size="mini" :type="levelType(s.row.level)">{{
                    s.row.level
                  }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="module"
                label="模块"
                width="130"
              ></el-table-column>
              <el-table-column
                prop="msg"
                label="内容"
                min-width="240"
              ></el-table-column>
              <el-table-column label="操作" width="100">
                <template slot-scope="s">
                  <el-button
                    type="text"
                    size="mini"
                    @click="openLogDetail(s.row)"
                    >详情</el-button
                  >
                </template>
              </el-table-column>
            </el-table>

            <el-alert
              class="mt12"
              show-icon
              :closable="false"
              type="warning"
              title="告警规则（mock）：工具超限、输出校验失败、约束遵循度<45% 时生成 ERROR，并触发λ自适应上调。"
            />
          </div>

          <empty-hint v-else text="未运行：启动实例后可查看日志与告警。" />
        </el-card>
      </div>
    </div>

    <!-- Dialogs -->
    <el-dialog title="日志详情" :visible.sync="dlg.logDetail" width="720px">
      <pre class="pre">{{ pretty(logDetail) }}</pre>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dlg.logDetail = false">关闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
export default {
  name: "AgentRuntimeMonitor",
  components: {
    EmptyHint: {
      props: { text: String },
      template: `
        <div class="empty">
          <i class="el-icon-info"></i>
          <div class="emptyText">{{text}}</div>
        </div>
      `,
    },
  },
  data() {
    return {
      flowStep: 0,

      agents: [],
      pick: {
        agentId: "",
        version: 1,
        model: "gpt4",
        temp: 0.3,
        maxTokens: 4096,
      },

      instance: { running: false, id: "" },

      taskInput:
        "根据案情预测罪名与刑期，并严格输出JSON：accusation,term_years,law_refs,factors（mock）。",
      pipe: { strategy: "ReAct", topk: 4 },
      pipeActive: 0,

      // memory hits
      memHits: [],

      // tools
      tools: [
        { tool: "ToolSearch", limit: 3, used: 0, last: "-" },
        { tool: "ToolCalc", limit: 2, used: 0, last: "-" },
        { tool: "ToolWrite", limit: 4, used: 0, last: "-" },
      ],

      // output check
      outputCheck: { ok: true, score: 0.85, sampleOutput: {} },

      // DAPOM
      lambda: 0.5,
      eta: "5e-5 (mock)",
      constraints: [],

      // metrics
      metrics: {
        qps: 0.0,
        successRate: 1.0,
        avgLatency: 680,
        avgSteps: 3.2,
        memHitRate: 0.5,
        constraintOK: 0.75,
      },
      toolShare: { ToolSearch: 40, ToolCalc: 25, ToolWrite: 35 },

      // trace
      trace: [],

      // logs
      logs: [],
      logFilter: { level: "", keyword: "" },
      dlg: { logDetail: false },
      logDetail: {},

      // timers/loading
      timer: null,
      loading: { start: false, tick: false, run: false, tune: false },
    };
  },
  computed: {
    versionsOfPick() {
      const a = this.agents.find((x) => x.id === this.pick.agentId);
      if (!a) return [1];
      // mock: versions 1..currentVersion
      const arr = [];
      for (let i = 1; i <= a.currentVersion; i++) arr.push(i);
      return arr;
    },
    toolStatsTable() {
      return this.tools.map((t) => ({
        tool: t.tool,
        used: `${t.used}/${t.limit}`,
        last: t.last,
      }));
    },
    filteredLogs() {
      const lv = this.logFilter.level;
      const kw = (this.logFilter.keyword || "").trim().toLowerCase();
      return this.logs.filter((x) => {
        const okLv = !lv || x.level === lv;
        const okKw = !kw || (x.msg || "").toLowerCase().includes(kw);
        return okLv && okKw;
      });
    },
  },
  created() {
    this.resetAll();
  },
  beforeDestroy() {
    this.stopRefresh();
  },
  methods: {
    // ----- utils -----
    pretty(o) {
      return JSON.stringify(o, null, 2);
    },
    nowISO() {
      const d = new Date();
      const pad = (n) => (n < 10 ? "0" + n : "" + n);
      return (
        d.getFullYear() +
        "-" +
        pad(d.getMonth() + 1) +
        "-" +
        pad(d.getDate()) +
        " " +
        pad(d.getHours()) +
        ":" +
        pad(d.getMinutes()) +
        ":" +
        pad(d.getSeconds())
      );
    },
    rand(min, max) {
      return min + Math.random() * (max - min);
    },
    sleep(ms) {
      return new Promise((r) => setTimeout(r, ms));
    },
    toast(type, msg) {
      this.$message({ type, message: msg, showClose: true });
    },
    levelType(lv) {
      if (lv === "INFO") return "info";
      if (lv === "WARN") return "warning";
      return "danger";
    },

    // ----- init -----
    resetAll() {
      this.stopRefresh();
      this.agents = [
        { id: "a_1001", name: "LegalAssistant", currentVersion: 3 },
        { id: "a_1002", name: "EduTutor", currentVersion: 2 },
        { id: "a_1003", name: "DocAnalyst", currentVersion: 1 },
      ];
      this.pick = {
        agentId: "",
        version: 1,
        model: "gpt4",
        temp: 0.3,
        maxTokens: 4096,
      };
      this.instance = { running: false, id: "" };
      this.flowStep = 0;

      this.pipe = { strategy: "ReAct", topk: 4 };
      this.pipeActive = 0;

      this.lambda = 0.5;
      this.constraints = this.seedConstraints();

      this.memHits = [];
      this.tools = [
        { tool: "ToolSearch", limit: 3, used: 0, last: "-" },
        { tool: "ToolCalc", limit: 2, used: 0, last: "-" },
        { tool: "ToolWrite", limit: 4, used: 0, last: "-" },
      ];

      this.outputCheck = { ok: true, score: 0.85, sampleOutput: {} };

      this.metrics = {
        qps: 0.0,
        successRate: 1.0,
        avgLatency: 680,
        avgSteps: 3.2,
        memHitRate: 0.5,
        constraintOK: 0.75,
      };
      this.toolShare = { ToolSearch: 40, ToolCalc: 25, ToolWrite: 35 };

      this.trace = [];
      this.logs = [];
      this.logFilter = { level: "", keyword: "" };

      this.toast("success", "已重置监控演示数据");
    },
    seedConstraints() {
      return [
        {
          name: "目标优先级",
          level: "soft",
          weight: 0.6,
          satisfaction: 0.78,
          desc: "多目标调度需遵循DSL设定的priority归一化权重",
        },
        {
          name: "角色能力边界",
          level: "hard",
          weight: 0.9,
          satisfaction: 0.72,
          desc: "角色越界行为抑制：输出风格/知识边界/安全约束",
        },
        {
          name: "工具调用限制",
          level: "hard",
          weight: 1.0,
          satisfaction: 0.66,
          desc: "tool_call_limit：防止工具滥用与资源超耗",
        },
        {
          name: "记忆使用限制",
          level: "soft",
          weight: 0.5,
          satisfaction: 0.7,
          desc: "top_k/过滤规则：避免无关记忆干扰决策",
        },
        {
          name: "输出规范约束",
          level: "hard",
          weight: 1.0,
          satisfaction: 0.62,
          desc: "output_schema=strict_json：结构化输出与可验证性",
        },
      ];
    },

    // ----- pick/start -----
    onPickAgent() {
      this.pick.version = 1;
      this.flowStep = Math.max(this.flowStep, 0);
    },
    async startInstance() {
      this.loading.start = true;
      try {
        await this.sleep(200);
        this.instance.running = true;
        this.instance.id =
          "inst_" + Math.floor(100000 + Math.random() * 900000);

        this.flowStep = 0;
        this.pipeActive = 0;

        this.pushLog("INFO", "Runtime", `启动实例：${this.instance.id}`);
        this.pushLog(
          "INFO",
          "LLM",
          `模型=${this.pick.model}, temp=${this.pick.temp.toFixed(
            2
          )}, maxTokens=${this.pick.maxTokens}`
        );
        this.toast("success", "实例已启动（mock）");
      } finally {
        this.loading.start = false;
      }
    },
    stopInstance() {
      this.stopRefresh();
      this.instance.running = false;
      this.pushLog("WARN", "Runtime", "实例停止（mock）");
      this.flowStep = 0;
      this.toast("warning", "已停止实例");
    },

    // ----- run pipeline ticks -----
    clearRunData() {
      this.pipeActive = 0;
      this.memHits = [];
      this.tools.forEach((t) => ((t.used = 0), (t.last = "-")));
      this.outputCheck = { ok: true, score: 0.85, sampleOutput: {} };
      this.trace = [];
      this.logs = [];
      this.toast("success", "已清空链路数据（mock）");
    },
    async singleTick() {
      if (!this.instance.running) return;
      this.loading.tick = true;
      try {
        // step 1 input
        this.flowStep = Math.max(this.flowStep, 1);
        this.pipeActive = 1;
        this.trace.push({
          type: "primary",
          time: this.nowISO(),
          step: "输入任务",
          content: this.taskInput,
        });

        // step 2 memory
        await this.sleep(140);
        this.memHits = this.mockMemoryHits(this.pipe.topk);
        this.metrics.memHitRate = this.rand(0.35, 0.85);
        this.pipeActive = 2;
        this.pushLog(
          "INFO",
          "Memory",
          `向量检索 top_k=${this.pipe.topk} 命中${this.memHits.length}条（mock）`
        );

        // step 3 strategy
        await this.sleep(140);
        this.pipeActive = 3;
        this.trace.push({
          type: "info",
          time: this.nowISO(),
          step: "策略调度",
          content: `选择策略=${this.pipe.strategy}（mock）`,
        });
        this.pushLog(
          "INFO",
          "Planner",
          `策略=${this.pipe.strategy}；引入语义惩罚项(λ=${this.lambda.toFixed(
            2
          )})（mock）`
        );

        // step 4 tool call
        await this.sleep(140);
        this.pipeActive = 4;
        this.mockToolCall();
        // step 5 output check
        await this.sleep(140);
        this.pipeActive = 5;
        this.mockOutputCheck();

        // update metrics + constraint satisfaction
        this.updateMetricsByLambda();

        // DAPOM auto adjust if fail
        if (!this.outputCheck.ok) {
          this.bumpLambdaUp();
        } else {
          this.relaxLambdaDown();
        }

        this.flowStep = Math.max(this.flowStep, 5);
      } finally {
        this.loading.tick = false;
      }
    },
    async autoRun() {
      if (!this.instance.running) return;
      this.loading.run = true;
      try {
        for (let i = 0; i < 5; i++) {
          await this.singleTick();
          await this.sleep(120);
        }
        this.toast("success", "自动运行完成（5步 mock）");
      } finally {
        this.loading.run = false;
      }
    },

    mockMemoryHits(k) {
      const pool = [
        "历史案例：类似情节中通常引用法条第X条",
        "反思记录：上次输出缺字段导致校验失败，需严格JSON",
        "工具结果：检索到相关司法解释要点",
        "长期记忆：用户偏好输出因子factors包含'自首/累犯'",
        "知识片段：量刑范围常见区间（示例）",
      ];
      const n = Math.min(k, 5);
      const arr = [];
      for (let i = 0; i < n; i++) {
        arr.push({ text: pool[i], score: this.rand(0.68, 0.96).toFixed(2) });
      }
      return arr;
    },
    mockToolCall() {
      // choose a tool by random, obey limit with warnings
      const t = this.tools[Math.floor(Math.random() * this.tools.length)];
      t.used += 1;
      t.last = `${this.nowISO()} · payload=...`;

      if (t.used > t.limit) {
        this.pushLog(
          "ERROR",
          "Tool",
          `工具超限：${t.tool} used=${t.used}/${t.limit}（mock）`
        );
        this.trace.push({
          type: "danger",
          time: this.nowISO(),
          step: "工具调用超限",
          content: `${t.tool} 超出上限，触发告警（mock）`,
        });
      } else if (t.used === t.limit) {
        this.pushLog(
          "WARN",
          "Tool",
          `工具接近上限：${t.tool} used=${t.used}/${t.limit}（mock）`
        );
      } else {
        this.pushLog(
          "INFO",
          "Tool",
          `调用工具：${t.tool} used=${t.used}/${t.limit}（mock）`
        );
      }

      // tool share
      const total = this.tools.reduce((s, x) => s + x.used, 0) || 1;
      const pct = (x) => Math.floor((x.used / total) * 100);
      this.toolShare = {
        ToolSearch: pct(this.tools[0]),
        ToolCalc: pct(this.tools[1]),
        ToolWrite: pct(this.tools[2]),
      };
    },
    mockOutputCheck() {
      // fail probability decreases as lambda increases
      const failProb = Math.max(0.05, 0.35 - this.lambda * 0.28);
      const ok = Math.random() > failProb;
      const score = ok ? this.rand(0.72, 0.98) : this.rand(0.2, 0.58);

      this.outputCheck.ok = ok;
      this.outputCheck.score = score;
      this.outputCheck.sampleOutput = ok
        ? {
            accusation: "盗窃罪(mock)",
            term_years: 3,
            law_refs: ["刑法264(mock)"],
            factors: ["自首(mock)", "退赃(mock)"],
          }
        : {
            accusation: "盗窃罪(mock)",
            term_years: "??",
            note: "字段缺失/类型不一致（mock）",
          };

      if (ok) {
        this.pushLog(
          "INFO",
          "Validator",
          "输出校验通过：strict_json OK（mock）"
        );
        this.trace.push({
          type: "success",
          time: this.nowISO(),
          step: "输出校验PASS",
          content: "结构化输出可验证（mock）",
        });
      } else {
        this.pushLog(
          "ERROR",
          "Validator",
          "输出校验失败：schema不一致/缺字段（mock）"
        );
        this.trace.push({
          type: "danger",
          time: this.nowISO(),
          step: "输出校验FAIL",
          content: "触发语义惩罚项与自适应上调λ（mock）",
        });
      }
    },

    // ----- DAPOM effects -----
    updateMetricsByLambda() {
      this.flowStep = Math.max(this.flowStep, 2);

      // basic metrics drift
      this.metrics.qps = this.rand(2.0, 8.0) * (1 - this.lambda * 0.25);
      this.metrics.avgLatency = this.rand(500, 1200) * (1 + this.lambda * 0.15);
      this.metrics.avgSteps = this.rand(2.5, 6.5);

      // successRate + constraintOK related to outputCheck and lambda
      const okBoost = this.outputCheck.ok ? 0.03 : -0.08;
      this.metrics.successRate = Math.min(
        1,
        Math.max(0, this.metrics.successRate + okBoost)
      );
      this.metrics.constraintOK = Math.min(
        1,
        Math.max(
          0.05,
          0.35 + this.lambda * 0.55 + (this.outputCheck.ok ? 0.06 : -0.1)
        )
      );

      // update per-constraint satisfaction
      this.constraints = this.constraints.map((c) => {
        const base = c.satisfaction;
        const move = this.outputCheck.ok
          ? this.rand(0.0, 0.06)
          : -this.rand(0.05, 0.12);
        const lam = (c.level === "hard" ? 0.08 : 0.04) * this.lambda;
        const next = Math.min(1, Math.max(0.05, base + move + lam - 0.02));
        return { ...c, satisfaction: next };
      });
    },
    bumpLambdaUp() {
      // mock "乘子更新：违反约束 -> λ上升"
      this.lambda = Math.min(1, this.lambda + 0.05);
      this.flowStep = Math.max(this.flowStep, 3);
      this.pushLog(
        "WARN",
        "DAPOM",
        `检测到约束违反：λ自适应上调至 ${this.lambda.toFixed(2)}（mock）`
      );
    },
    relaxLambdaDown() {
      // mock "稳定执行 -> λ下降"
      this.lambda = Math.max(0, this.lambda - 0.02);
      this.flowStep = Math.max(this.flowStep, 3);
    },
    async autoTuneLambda() {
      if (!this.instance.running) return;
      this.loading.tune = true;
      try {
        // simulate computing constraint deviation and updating multiplier
        await this.sleep(180);
        const avgSat =
          this.constraints.reduce((s, c) => s + c.satisfaction, 0) /
          this.constraints.length;
        if (avgSat < 0.55) {
          this.lambda = Math.min(1, this.lambda + 0.08);
          this.pushLog(
            "WARN",
            "DAPOM",
            `平均约束满足度=${avgSat.toFixed(2)}偏低：λ↑到${this.lambda.toFixed(
              2
            )}（mock）`
          );
        } else {
          this.lambda = Math.max(0, this.lambda - 0.05);
          this.pushLog(
            "INFO",
            "DAPOM",
            `平均约束满足度=${avgSat.toFixed(2)}良好：λ↓到${this.lambda.toFixed(
              2
            )}（mock）`
          );
        }
        this.flowStep = Math.max(this.flowStep, 3);
        this.toast("success", "已完成一次自动调节（mock）");
      } finally {
        this.loading.tune = false;
      }
    },

    // ----- refresh timer -----
    startRefresh() {
      if (this.timer) return;
      this.flowStep = Math.max(this.flowStep, 2);
      this.timer = setInterval(() => {
        if (!this.instance.running) return;
        // slight drift
        this.metrics.qps = Math.max(
          0.2,
          this.metrics.qps + this.rand(-0.4, 0.4)
        );
        this.metrics.avgLatency = Math.max(
          120,
          this.metrics.avgLatency + this.rand(-40, 60)
        );
        this.metrics.avgSteps = Math.max(
          1,
          this.metrics.avgSteps + this.rand(-0.2, 0.3)
        );
      }, 900);
      this.toast("success", "已开始刷新（mock）");
    },
    stopRefresh() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
        this.toast("info", "已暂停刷新");
      }
    },

    // ----- logs -----
    pushLog(level, module, msg) {
      this.logs.unshift({
        time: this.nowISO(),
        level,
        module,
        msg,
        detail: {
          time: this.nowISO(),
          level,
          module,
          msg,
          instanceId: this.instance.id,
          lambda: this.lambda,
        },
      });
    },
    openLogDetail(row) {
      this.logDetail = row.detail || row;
      this.dlg.logDetail = true;
    },
    clearLogs() {
      this.$confirm("确认清空日志？（mock）", "提示", { type: "warning" })
        .then(() => (this.logs = []))
        .catch(() => {});
    },
    exportLogs() {
      const blob = new Blob([JSON.stringify(this.filteredLogs, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `runtime_logs_${
        this.instance.id || "noinst"
      }_${this.nowISO().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      this.toast("success", "已导出日志（前端生成JSON）");
      this.flowStep = Math.max(this.flowStep, 5);
    },
  },
};
</script>

<style scoped>
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
      rgba(103, 194, 58, 0.14),
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
  font-weight: 900;
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
  font-weight: 900;
}
.desc {
  margin-top: 6px;
  color: #6b778c;
  font-size: 12px;
  max-width: 1000px;
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
  font-weight: 900;
}
.miniTip {
  color: #667085;
  font-size: 12px;
}
.btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.mt8 {
  margin-top: 8px;
}
.mt10 {
  margin-top: 10px;
}
.mt12 {
  margin-top: 12px;
}
.ml8 {
  margin-left: 8px;
}
.ml12 {
  margin-left: 12px;
}
.mr6 {
  margin-right: 6px;
}
.w220 {
  width: 220px;
}
.w160 {
  width: 160px;
}
.w120 {
  width: 120px;
}
.w240 {
  width: 240px;
}

.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.kv {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fbfcfe;
  border: 1px solid #eef2f7;
  padding: 6px 10px;
  border-radius: 12px;
}
.kv span {
  color: #667085;
  font-weight: 800;
  font-size: 12px;
  min-width: 86px;
}

.grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1.05fr 1.15fr;
  gap: 12px;
}
.leftCol,
.rightCol {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pipe .pipeBox {
  background: #fbfcfe;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 10px;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.lbl {
  font-weight: 800;
  color: #475467;
  min-width: 72px;
}
.miniTitle {
  font-weight: 900;
  color: #475467;
}
.tip {
  color: #667085;
  font-size: 12px;
  line-height: 1.6;
}

.pre {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px;
  max-height: 240px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  color: #344054;
}

.dapom .tensorGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.tensorCard {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 10px;
}
.tHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.tName {
  font-weight: 900;
  color: #344054;
}
.tDesc {
  margin-top: 6px;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}
.tFoot {
  margin-top: 8px;
  color: #475467;
  font-size: 12px;
  font-weight: 800;
}

.kpiGrid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.kpi {
  background: #fbfcfe;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 10px;
}
.kTitle {
  color: #667085;
  font-weight: 900;
  font-size: 12px;
}
.kVal {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 1000;
  color: #344054;
}
.kSub {
  margin-top: 4px;
  color: #98a2b3;
  font-size: 12px;
}

.tTitle {
  font-weight: 900;
  color: #344054;
}
.tText {
  color: #475467;
  margin-top: 4px;
  line-height: 1.6;
}

.logFilters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  height: 180px;
  border: 1px dashed #e7ebf3;
  border-radius: 14px;
  background: #fbfcfe;
}
.empty i {
  font-size: 24px;
  color: #98a2b3;
  margin-bottom: 8px;
}
.emptyText {
  color: #667085;
  font-size: 12px;
}
</style>
