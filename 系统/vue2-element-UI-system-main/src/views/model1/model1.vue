<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <div class="hLeft">
        <div class="title">
          <span class="tag">5.3.2</span>
          智能体管理界面（全生命周期：版本/复用/运行/日志/导出）
        </div>
        <div class="desc">
          覆盖论文“智能体管理与运行模块”：保存、修改、删除、复用、版本控制；在线运行/调试；日志查询/筛选/导出；配置文件导出（纯前端模拟）
        </div>
      </div>
      <div class="hRight">
        <el-button
          size="small"
          icon="el-icon-document-add"
          type="primary"
          @click="openCreate"
          >新建智能体</el-button
        >
        <el-button size="small" icon="el-icon-refresh" @click="resetAll"
          >重置演示数据</el-button
        >
      </div>
    </div>

    <!-- Flow steps -->
    <el-card class="card">
      <div slot="header" class="cardHeader">
        <div class="cardTitle">管理闭环流程（按顺序展示）</div>
        <div class="miniTip">
          提示：先在列表选中智能体，再做版本/运行/日志/导出
        </div>
      </div>

      <el-steps :active="flowStep" finish-status="success" align-center>
        <el-step title="① 智能体列表" description="搜索/筛选/选择"></el-step>
        <el-step title="② 版本控制" description="保存/回滚/对比"></el-step>
        <el-step title="③ 在线运行/调试" description="测试指令交互"></el-step>
        <el-step title="④ 日志中心" description="记录/筛选/导出"></el-step>
        <el-step title="⑤ 配置导出" description="复用/部署"></el-step>
      </el-steps>
    </el-card>

    <div class="grid">
      <!-- Left: agent list -->
      <el-card class="card left">
        <div slot="header" class="cardHeader">
          <div class="cardTitle">智能体列表</div>
          <div class="rightOps">
            <el-input
              size="small"
              v-model="filters.keyword"
              placeholder="搜索名称/描述/标签"
              prefix-icon="el-icon-search"
              class="w240"
              @input="flowStep = Math.max(flowStep, 0)"
            />
            <el-select
              size="small"
              v-model="filters.status"
              placeholder="状态"
              class="w120"
            >
              <el-option label="全部" value=""></el-option>
              <el-option label="已启用" value="enabled"></el-option>
              <el-option label="已停用" value="disabled"></el-option>
              <el-option label="已归档" value="archived"></el-option>
            </el-select>
          </div>
        </div>

        <el-table
          :data="filteredAgents"
          size="mini"
          stripe
          border
          highlight-current-row
          @current-change="onPickAgent"
          :row-class-name="rowClass"
        >
          <el-table-column label="名称" min-width="160">
            <template slot-scope="s">
              <div class="nameCell">
                <div class="name">{{ s.row.name }}</div>
                <div class="sub">{{ s.row.desc }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center">
            <template slot-scope="s">
              <el-tag size="mini" :type="tagType(s.row.status)">{{
                statusText(s.row.status)
              }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="当前版本" width="100" align="center">
            <template slot-scope="s">
              <el-tag size="mini" type="info"
                >v{{ s.row.currentVersion }}</el-tag
              >
            </template>
          </el-table-column>

          <el-table-column label="标签" min-width="150">
            <template slot-scope="s">
              <el-tag
                v-for="t in s.row.tags"
                :key="t"
                size="mini"
                class="mr6"
                type="success"
                effect="plain"
                >{{ t }}</el-tag
              >
            </template>
          </el-table-column>

          <el-table-column label="操作" width="220" fixed="right">
            <template slot-scope="s">
              <el-button type="text" size="mini" @click.stop="pick(s.row)"
                >选择</el-button
              >
              <el-button type="text" size="mini" @click.stop="openEdit(s.row)"
                >编辑</el-button
              >
              <el-button type="text" size="mini" @click.stop="cloneAgent(s.row)"
                >复制</el-button
              >
              <el-button
                type="text"
                size="mini"
                @click.stop="toggleEnable(s.row)"
              >
                {{ s.row.status === "enabled" ? "停用" : "启用" }}
              </el-button>
              <el-button
                type="text"
                size="mini"
                style="color: #d92d20"
                @click.stop="removeAgent(s.row)"
                >删除</el-button
              >
            </template>
          </el-table-column>
        </el-table>

        <el-alert
          class="mt12"
          show-icon
          :closable="false"
          type="info"
          title="选择智能体后，可在右侧进行版本控制、在线运行调试、日志筛选导出、配置导出（均为前端模拟）。"
        />
      </el-card>

      <!-- Right: detail + tabs -->
      <el-card class="card right">
        <div slot="header" class="cardHeader">
          <div class="cardTitle">管理面板</div>
          <div class="picked" v-if="current">
            <el-tag type="primary" effect="dark">{{ current.name }}</el-tag>
            <el-tag class="ml8" type="info">ID: {{ current.id }}</el-tag>
            <el-tag class="ml8" :type="tagType(current.status)">{{
              statusText(current.status)
            }}</el-tag>
          </div>
          <div v-else class="picked">
            <el-tag type="info">请先从左侧选择一个智能体</el-tag>
          </div>
        </div>

        <el-tabs v-model="activeTab" @tab-click="onTab">
          <!-- Versions -->
          <el-tab-pane label="② 版本控制" name="versions">
            <div class="panelTop">
              <div class="hint">
                版本快照模拟包含：DSL/Agent-IR/约束摘要/策略模板（对应论文“保存、修改、复用与版本控制”）。
              </div>
              <div class="btns">
                <el-button
                  size="small"
                  type="primary"
                  icon="el-icon-circle-plus-outline"
                  :disabled="!current"
                  @click="openNewVersion"
                >
                  新建版本
                </el-button>
                <el-button
                  size="small"
                  icon="el-icon-sort"
                  :disabled="!current || selectedVersions.length !== 2"
                  @click="compareVersions"
                >
                  对比所选(2个)
                </el-button>
              </div>
            </div>

            <el-table
              v-if="current"
              :data="versionsOfCurrent"
              size="mini"
              stripe
              border
              @selection-change="onSelectVersions"
            >
              <el-table-column type="selection" width="45"></el-table-column>
              <el-table-column
                prop="ver"
                label="版本"
                width="70"
                align="center"
              >
                <template slot-scope="s">
                  <el-tag
                    size="mini"
                    :type="
                      s.row.ver === current.currentVersion ? 'success' : 'info'
                    "
                    >v{{ s.row.ver }}</el-tag
                  >
                </template>
              </el-table-column>
              <el-table-column
                prop="time"
                label="时间"
                width="120"
              ></el-table-column>
              <el-table-column
                prop="summary"
                label="摘要"
                min-width="220"
              ></el-table-column>
              <el-table-column label="策略模板" width="140">
                <template slot-scope="s">
                  <el-tag
                    v-for="x in s.row.strategies"
                    :key="x"
                    size="mini"
                    class="mr6"
                    type="warning"
                    effect="plain"
                    >{{ x }}</el-tag
                  >
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220">
                <template slot-scope="s">
                  <el-button
                    type="text"
                    size="mini"
                    @click="setCurrentVersion(s.row.ver)"
                    >设为当前</el-button
                  >
                  <el-button
                    type="text"
                    size="mini"
                    @click="openVersionDetail(s.row)"
                    >查看快照</el-button
                  >
                  <el-button
                    type="text"
                    size="mini"
                    style="color: #d92d20"
                    @click="deleteVersion(s.row)"
                    >删除</el-button
                  >
                </template>
              </el-table-column>
            </el-table>

            <empty-hint
              v-else
              text="未选择智能体：请先在左侧列表选择一个智能体。"
            />
          </el-tab-pane>

          <!-- Run / Debug -->
          <el-tab-pane label="③ 在线运行/调试" name="run">
            <div class="panelTop">
              <div class="hint">
                模拟“在线运行、调试与测试指令交互”：选择策略（ReAct/CoT/ToT）→输入指令→生成轨迹与约束遵循提示。
              </div>
              <div class="btns">
                <el-button
                  size="small"
                  type="primary"
                  icon="el-icon-video-play"
                  :disabled="!current"
                  :loading="loading.run"
                  @click="runTest"
                >
                  运行测试
                </el-button>
                <el-button
                  size="small"
                  icon="el-icon-delete"
                  :disabled="trace.length === 0"
                  @click="trace = []"
                  >清空轨迹</el-button
                >
              </div>
            </div>

            <div class="runGrid" v-if="current">
              <el-card class="subCard">
                <div class="subTitle">测试指令</div>
                <el-input
                  type="textarea"
                  :rows="5"
                  v-model="testInput"
                  placeholder="输入测试任务，例如：根据案情预测罪名并输出严格JSON..."
                ></el-input>
                <div class="row mt10">
                  <span class="lbl">策略选择</span>
                  <el-radio-group v-model="runStrategy" size="small">
                    <el-radio-button label="ReAct"></el-radio-button>
                    <el-radio-button label="CoT"></el-radio-button>
                    <el-radio-button label="ToT"></el-radio-button>
                  </el-radio-group>
                </div>
                <div class="row mt10">
                  <span class="lbl">语义约束强度 λ</span>
                  <el-slider
                    v-model="lambda"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                  ></el-slider>
                </div>
                <el-alert
                  class="mt10"
                  :closable="false"
                  type="warning"
                  show-icon
                  title="说明：这里用前端模拟 DAPOM 的约束调制效果：λ 越大，越强调输出格式/工具限制/角色边界。"
                />
              </el-card>

              <el-card class="subCard">
                <div class="subTitle">运行轨迹（模拟）</div>
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
                <empty-hint v-else text="暂无轨迹：点击“运行测试”生成。" />
              </el-card>
            </div>

            <empty-hint
              v-else
              text="未选择智能体：请先在左侧列表选择一个智能体。"
            />
          </el-tab-pane>

          <!-- Logs -->
          <el-tab-pane label="④ 日志中心" name="logs">
            <div class="panelTop">
              <div class="hint">
                模拟“实时记录运行日志与异常信息；日志查询、筛选与导出”。
              </div>
              <div class="btns">
                <el-button
                  size="small"
                  icon="el-icon-download"
                  :disabled="filteredLogs.length === 0"
                  @click="exportLogs"
                >
                  导出日志(JSON)
                </el-button>
                <el-button
                  size="small"
                  icon="el-icon-delete"
                  :disabled="logs.length === 0"
                  @click="clearLogs"
                >
                  清空日志
                </el-button>
              </div>
            </div>

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
                class="w260"
                v-model="logFilter.keyword"
                placeholder="关键词（工具/策略/异常/输出）"
                prefix-icon="el-icon-search"
              />
              <el-date-picker
                size="small"
                v-model="logFilter.range"
                type="daterange"
                unlink-panels
                range-separator="~"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="yyyy-MM-dd"
              />
              <el-button
                size="small"
                @click="logFilter = { level: '', keyword: '', range: [] }"
                icon="el-icon-refresh"
                >重置筛选</el-button
              >
            </div>

            <el-table :data="filteredLogs" size="mini" stripe border>
              <el-table-column prop="time" label="时间" width="160" />
              <el-table-column prop="agent" label="智能体" width="140" />
              <el-table-column
                prop="version"
                label="版本"
                width="80"
                align="center"
              >
                <template slot-scope="s">
                  <el-tag size="mini" type="info">v{{ s.row.version }}</el-tag>
                </template>
              </el-table-column>
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
              <el-table-column prop="msg" label="内容" min-width="260" />
              <el-table-column label="操作" width="120">
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
              type="info"
              title="提示：运行测试后会自动生成 INFO/WARN/ERROR 三类日志（工具调用限制、输出规范校验、异常模拟等）。"
            />
          </el-tab-pane>

          <!-- Export -->
          <el-tab-pane label="⑤ 配置导出" name="export">
            <div class="panelTop">
              <div class="hint">
                模拟“配置文件导出，适配多场景部署需求”：导出 DSL + Agent-IR 摘要
                + 约束摘要 + 版本信息。
              </div>
              <div class="btns">
                <el-button
                  size="small"
                  type="primary"
                  icon="el-icon-download"
                  :disabled="!current"
                  @click="exportAgentBundle"
                >
                  导出配置包(JSON)
                </el-button>
              </div>
            </div>

            <div v-if="current" class="exportBox">
              <div class="kv">
                <span>当前智能体</span><b>{{ current.name }}</b>
              </div>
              <div class="kv">
                <span>当前版本</span><b>v{{ current.currentVersion }}</b>
              </div>
              <div class="kv">
                <span>状态</span><b>{{ statusText(current.status) }}</b>
              </div>
              <div class="kv">
                <span>包含内容</span
                ><b
                  >meta / versions / dsl / agentIR / constraints / exportTime</b
                >
              </div>

              <el-divider></el-divider>

              <div class="miniTitle">导出预览（节选）</div>
              <pre class="pre">{{ pretty(makeBundlePreview()) }}</pre>
            </div>

            <empty-hint
              v-else
              text="未选择智能体：请先在左侧列表选择一个智能体。"
            />
          </el-tab-pane>

          <!-- Permission (mock) -->
          <el-tab-pane label="权限(模拟)" name="perm">
            <el-alert
              type="warning"
              show-icon
              :closable="false"
              title="论文提到“用户权限分级管理、敏感数据加密存储”。本页为纯前端展示，权限仅模拟：你可切换角色查看按钮是否禁用。"
            />
            <div class="permBox">
              <div class="row">
                <span class="lbl">当前角色</span>
                <el-radio-group v-model="mockRole" size="small">
                  <el-radio-button label="admin">管理员</el-radio-button>
                  <el-radio-button label="dev">开发者</el-radio-button>
                  <el-radio-button label="viewer">只读</el-radio-button>
                </el-radio-group>
              </div>
              <div class="row mt10">
                <el-tag type="info">admin：全权限</el-tag>
                <el-tag class="ml8" type="success"
                  >dev：可编辑/运行/导出</el-tag
                >
                <el-tag class="ml8" type="warning"
                  >viewer：仅查看/导出日志</el-tag
                >
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- dialogs -->
    <el-dialog
      :title="editForm.id ? '编辑智能体' : '新建智能体'"
      :visible.sync="dlg.edit"
      width="640px"
    >
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="名称">
          <el-input
            v-model="editForm.name"
            placeholder="例如：LegalAssistant"
          ></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.desc"
            placeholder="简要描述用途"
          ></el-input>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择标签"
          >
            <el-option
              v-for="t in allTags"
              :key="t"
              :label="t"
              :value="t"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status">
            <el-option label="已启用" value="enabled"></el-option>
            <el-option label="已停用" value="disabled"></el-option>
            <el-option label="已归档" value="archived"></el-option>
          </el-select>
        </el-form-item>

        <el-divider></el-divider>

        <el-form-item label="DSL(模拟)">
          <el-input
            type="textarea"
            :rows="6"
            v-model="editForm.dsl"
            placeholder="这里模拟保存 DSL 源码快照..."
          ></el-input>
        </el-form-item>
      </el-form>

      <span slot="footer" class="dialog-footer">
        <el-button @click="dlg.edit = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="mockRole === 'viewer'"
          @click="saveAgent"
          >保存</el-button
        >
      </span>
    </el-dialog>

    <el-dialog title="新建版本" :visible.sync="dlg.newVer" width="560px">
      <el-form :model="newVerForm" label-width="90px">
        <el-form-item label="摘要">
          <el-input
            v-model="newVerForm.summary"
            placeholder="例如：调整工具限制；强化输出JSON约束"
          ></el-input>
        </el-form-item>
        <el-form-item label="策略模板">
          <el-select
            v-model="newVerForm.strategies"
            multiple
            placeholder="选择策略"
          >
            <el-option label="ReAct" value="ReAct"></el-option>
            <el-option label="CoT" value="CoT"></el-option>
            <el-option label="ToT" value="ToT"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="约束摘要">
          <el-input
            type="textarea"
            :rows="4"
            v-model="newVerForm.constraints"
            placeholder="例如：output=strict_json; tool_call_limit=..."
          ></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dlg.newVer = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!current || mockRole === 'viewer'"
          @click="createVersion"
          >创建</el-button
        >
      </span>
    </el-dialog>

    <el-drawer
      title="版本快照详情（模拟）"
      :visible.sync="dlg.verDetail"
      size="52%"
    >
      <div class="drawerBody">
        <div class="kv">
          <span>版本</span><b>v{{ verDetail.ver }}</b>
        </div>
        <div class="kv">
          <span>时间</span><b>{{ verDetail.time }}</b>
        </div>
        <div class="kv">
          <span>摘要</span><b>{{ verDetail.summary }}</b>
        </div>
        <div class="miniTitle mt12">快照内容（节选）</div>
        <pre class="pre">{{ pretty(verDetail.snapshot || {}) }}</pre>
      </div>
    </el-drawer>

    <el-dialog
      title="版本对比（模拟）"
      :visible.sync="dlg.verCompare"
      width="860px"
    >
      <div class="compareGrid">
        <div class="cmp">
          <div class="cmpTitle">v{{ comparePair.a.ver }}</div>
          <pre class="pre">{{ pretty(comparePair.a.snapshot) }}</pre>
        </div>
        <div class="cmp">
          <div class="cmpTitle">v{{ comparePair.b.ver }}</div>
          <pre class="pre">{{ pretty(comparePair.b.snapshot) }}</pre>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dlg.verCompare = false">关闭</el-button>
      </span>
    </el-dialog>

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
  name: "AgentManagement",
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
      activeTab: "versions",

      mockRole: "admin", // admin / dev / viewer

      filters: { keyword: "", status: "" },
      agents: [],
      versions: {}, // {agentId: [{ver,time,summary,strategies,constraints,snapshot}]}

      current: null,
      selectedVersions: [],

      testInput:
        "根据案情预测罪名与刑期，并严格输出JSON字段：accusation,evidence,law_refs,term_years,factors（mock）。",
      runStrategy: "ReAct",
      lambda: 0.5,
      loading: { run: false },
      trace: [],

      logs: [],
      logFilter: { level: "", keyword: "", range: [] },
      logDetail: {},

      dlg: {
        edit: false,
        newVer: false,
        verDetail: false,
        verCompare: false,
        logDetail: false,
      },
      editForm: {
        id: "",
        name: "",
        desc: "",
        tags: [],
        status: "enabled",
        dsl: "",
      },

      newVerForm: {
        summary: "",
        strategies: ["ReAct"],
        constraints:
          "output_schema=strict_json; tool_call_limit={LawSearch:3,CaseCalc:2}",
      },
      verDetail: {},
      comparePair: { a: {}, b: {} },
    };
  },
  computed: {
    allTags() {
      const set = new Set();
      this.agents.forEach((a) => (a.tags || []).forEach((t) => set.add(t)));
      return Array.from(set).sort();
    },
    filteredAgents() {
      const kw = (this.filters.keyword || "").trim().toLowerCase();
      return this.agents.filter((a) => {
        const okStatus =
          !this.filters.status || a.status === this.filters.status;
        const blob = (
          a.name +
          " " +
          a.desc +
          " " +
          (a.tags || []).join(" ")
        ).toLowerCase();
        const okKw = !kw || blob.includes(kw);
        return okStatus && okKw;
      });
    },
    versionsOfCurrent() {
      if (!this.current) return [];
      return (this.versions[this.current.id] || [])
        .slice()
        .sort((x, y) => y.ver - x.ver);
    },
    filteredLogs() {
      const { level, keyword, range } = this.logFilter;
      const kw = (keyword || "").trim().toLowerCase();
      return this.logs.filter((x) => {
        const okLevel = !level || x.level === level;
        const okKw = !kw || (x.msg || "").toLowerCase().includes(kw);
        const okRange = this.inRange(x.date, range);
        const okAgent = !this.current ? true : x.agentId === this.current.id; // 若选中智能体，则默认聚焦该智能体日志
        return okLevel && okKw && okRange && okAgent;
      });
    },
  },
  created() {
    this.resetAll();
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
    today() {
      const d = new Date();
      const pad = (n) => (n < 10 ? "0" + n : "" + n);
      return (
        d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
      );
    },
    sleep(ms) {
      return new Promise((r) => setTimeout(r, ms));
    },
    toast(type, msg) {
      this.$message({ type, message: msg, showClose: true });
    },
    inRange(dateStr, range) {
      if (!range || !range.length) return true;
      const [s, e] = range;
      return (!s || dateStr >= s) && (!e || dateStr <= e);
    },

    statusText(s) {
      return s === "enabled"
        ? "已启用"
        : s === "disabled"
        ? "已停用"
        : "已归档";
    },
    tagType(s) {
      return s === "enabled"
        ? "success"
        : s === "disabled"
        ? "warning"
        : "info";
    },
    levelType(lv) {
      if (lv === "INFO") return "info";
      if (lv === "WARN") return "warning";
      return "danger";
    },
    rowClass({ row }) {
      return this.current && row.id === this.current.id ? "rowPicked" : "";
    },

    // ----- init/reset -----
    resetAll() {
      // mock agents
      this.agents = [
        {
          id: "a_1001",
          name: "LegalAssistant",
          desc: "法律领域：罪名/刑期预测（DSAGM结构+DAPOM约束）",
          status: "enabled",
          tags: ["法律", "ReAct", "strict_json"],
          currentVersion: 3,
        },
        {
          id: "a_1002",
          name: "EduTutor",
          desc: "教育领域：个性化辅导与作业讲解（记忆检索+策略自适应）",
          status: "disabled",
          tags: ["教育", "CoT", "memory"],
          currentVersion: 2,
        },
        {
          id: "a_1003",
          name: "DocAnalyst",
          desc: "文档分析：检索增强与结构化输出（工具插件化）",
          status: "archived",
          tags: ["检索", "工具", "ToT"],
          currentVersion: 1,
        },
      ];

      // mock versions
      this.versions = {
        a_1001: [
          this.makeVer(
            1,
            "初始版本：基础五元组/工具2个",
            ["CoT"],
            "output=relaxed; tool_limit=default"
          ),
          this.makeVer(
            2,
            "加入严格JSON输出与工具限制",
            ["ReAct"],
            "output=strict_json; tool_call_limit={LawSearch:3,CaseCalc:2}"
          ),
          this.makeVer(
            3,
            "DAPOM：提高λ稳定性，强化角色边界",
            ["ReAct", "CoT", "ToT"],
            "role_boundary=strict; lambda=0.5"
          ),
        ],
        a_1002: [
          this.makeVer(1, "初始：教学对话模板", ["CoT"], "output=markdown"),
          this.makeVer(
            2,
            "加入长期记忆top_k=4与反思记录",
            ["CoT", "ReAct"],
            "memory=vector(top_k=4)"
          ),
        ],
        a_1003: [
          this.makeVer(1, "归档：仅保留导出能力", ["ToT"], "status=archived"),
        ],
      };

      this.current = null;
      this.selectedVersions = [];
      this.trace = [];
      this.logs = this.seedLogs(); // 全局日志池（筛选时会按 current 聚焦）
      this.logFilter = { level: "", keyword: "", range: [] };
      this.flowStep = 0;
      this.activeTab = "versions";
      this.toast("success", "已重置演示数据");
    },
    makeVer(ver, summary, strategies, constraints) {
      return {
        ver,
        time: this.today(),
        summary,
        strategies,
        constraints,
        snapshot: {
          meta: { ver, summary, strategies, constraints },
          dsl: `agent "Mock" { ... version:${ver} }`,
          agentIR: {
            role: { id: "r1", desc: "mock", capability_limit: ["mock_limit"] },
            goals: [
              { type: "taskA", priority: 0.6 },
              { type: "taskB", priority: 0.4 },
            ],
            memory: { short: "ctx", long: { store: "vector_db", top_k: 4 } },
            tools: [{ name: "ToolA" }, { name: "ToolB" }],
            strategy: { candidates: strategies },
          },
          constraints: constraints,
        },
      };
    },
    seedLogs() {
      const base = [
        {
          agentId: "a_1001",
          agent: "LegalAssistant",
          version: 3,
          level: "INFO",
          msg: "启动运行：策略=ReAct, λ=0.50",
        },
        {
          agentId: "a_1001",
          agent: "LegalAssistant",
          version: 3,
          level: "WARN",
          msg: "工具调用接近上限：LawSearch (2/3)",
        },
        {
          agentId: "a_1001",
          agent: "LegalAssistant",
          version: 3,
          level: "INFO",
          msg: "输出校验通过：strict_json schema OK",
        },
        {
          agentId: "a_1002",
          agent: "EduTutor",
          version: 2,
          level: "INFO",
          msg: "记忆检索：top_k=4 命中2条历史对话",
        },
        {
          agentId: "a_1002",
          agent: "EduTutor",
          version: 2,
          level: "ERROR",
          msg: "异常：工具响应超时（mock）",
        },
      ];
      const date = this.today();
      return base.map((x) => ({
        ...x,
        date,
        time: this.nowISO(),
        detail: {
          ...x,
          date,
          time: this.nowISO(),
          stack: x.level === "ERROR" ? "MockStackTrace: ..." : "",
        },
      }));
    },

    // ----- pick agent -----
    onPickAgent(row) {
      if (!row) return;
      this.pick(row);
    },
    pick(row) {
      this.current = JSON.parse(JSON.stringify(row));
      this.flowStep = Math.max(this.flowStep, 0);
      this.toast("success", `已选择智能体：${row.name}`);
    },

    // ----- agent CRUD -----
    openCreate() {
      this.editForm = {
        id: "",
        name: "",
        desc: "",
        tags: [],
        status: "enabled",
        dsl: 'agent "NewAgent" { ... }',
      };
      this.dlg.edit = true;
    },
    openEdit(row) {
      this.editForm = JSON.parse(JSON.stringify(row));
      this.editForm.dsl = `agent "${row.name}" { ... }`;
      this.dlg.edit = true;
    },
    saveAgent() {
      if (!this.editForm.name.trim())
        return this.toast("error", "名称不能为空");
      if (this.editForm.id) {
        const idx = this.agents.findIndex((a) => a.id === this.editForm.id);
        if (idx >= 0)
          this.agents.splice(idx, 1, { ...this.agents[idx], ...this.editForm });
        if (this.current && this.current.id === this.editForm.id)
          this.current = JSON.parse(JSON.stringify(this.editForm));
        this.toast("success", "已保存修改（模拟）");
      } else {
        const id = "a_" + Math.floor(1000 + Math.random() * 9000);
        const agent = { ...this.editForm, id, currentVersion: 1 };
        this.agents.unshift(agent);
        this.versions[id] = [
          this.makeVer(
            1,
            "初始版本：新建智能体",
            ["ReAct"],
            "output=strict_json; budget=max_steps=6"
          ),
        ];
        this.toast("success", "已创建智能体（模拟）");
      }
      this.dlg.edit = false;
    },
    cloneAgent(row) {
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可复制");
      const id = "a_" + Math.floor(1000 + Math.random() * 9000);
      const copy = { ...row, id, name: row.name + "_Copy", status: "disabled" };
      this.agents.unshift(copy);
      this.versions[id] = (this.versions[row.id] || []).map((v) => ({ ...v }));
      this.toast("success", "已复制智能体（模拟复用）");
    },
    toggleEnable(row) {
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可变更状态");
      row.status = row.status === "enabled" ? "disabled" : "enabled";
      if (this.current && this.current.id === row.id)
        this.current.status = row.status;
      this.toast("success", `状态已更新：${this.statusText(row.status)}`);
    },
    removeAgent(row) {
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可删除");
      this.$confirm(`确认删除智能体「${row.name}」？（前端模拟）`, "提示", {
        type: "warning",
      })
        .then(() => {
          this.agents = this.agents.filter((a) => a.id !== row.id);
          delete this.versions[row.id];
          if (this.current && this.current.id === row.id) this.current = null;
          this.toast("success", "已删除（模拟）");
        })
        .catch(() => {});
    },

    // ----- versions -----
    openNewVersion() {
      if (!this.current) return this.toast("warning", "请先选择智能体");
      this.newVerForm = {
        summary: "",
        strategies: ["ReAct"],
        constraints:
          "output_schema=strict_json; tool_call_limit={MockTool:2}; role_boundary=strict",
      };
      this.dlg.newVer = true;
    },
    createVersion() {
      const list = this.versions[this.current.id] || [];
      const maxVer = list.reduce((m, x) => Math.max(m, x.ver), 0);
      const ver = maxVer + 1;
      const v = this.makeVer(
        ver,
        this.newVerForm.summary || `版本v${ver}`,
        this.newVerForm.strategies,
        this.newVerForm.constraints
      );
      list.push(v);
      this.$set(this.versions, this.current.id, list);

      // 可选：自动设为当前版本
      this.setCurrentVersion(ver, true);

      this.dlg.newVer = false;
      this.flowStep = Math.max(this.flowStep, 1);
      this.toast("success", `已创建版本 v${ver}（模拟快照保存）`);
    },
    setCurrentVersion(ver, silent) {
      if (!this.current) return;
      const idx = this.agents.findIndex((a) => a.id === this.current.id);
      if (idx >= 0) this.agents[idx].currentVersion = ver;
      this.current.currentVersion = ver;
      if (!silent) this.toast("success", `已切换当前版本为 v${ver}`);
    },
    deleteVersion(v) {
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可删除版本");
      this.$confirm(`确认删除版本 v${v.ver}？`, "提示", { type: "warning" })
        .then(() => {
          const list = (this.versions[this.current.id] || []).filter(
            (x) => x.ver !== v.ver
          );
          this.$set(this.versions, this.current.id, list);
          if (this.current.currentVersion === v.ver && list.length) {
            this.setCurrentVersion(list[list.length - 1].ver, true);
          }
          this.toast("success", "版本已删除（模拟）");
        })
        .catch(() => {});
    },
    openVersionDetail(v) {
      this.verDetail = {
        ...v,
        snapshot: {
          ...v.snapshot,
          note: "这里模拟“版本快照”：包含 DSL 源码、Agent-IR 五元组摘要、约束摘要、策略模板。",
        },
      };
      this.dlg.verDetail = true;
    },
    onSelectVersions(arr) {
      this.selectedVersions = arr || [];
    },
    compareVersions() {
      const [a, b] = this.selectedVersions;
      this.comparePair = { a, b };
      this.dlg.verCompare = true;
    },

    // ----- run/debug -----
    async runTest() {
      if (!this.current) return this.toast("warning", "请先选择智能体");
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可运行");
      this.loading.run = true;
      this.flowStep = Math.max(this.flowStep, 2);
      try {
        this.trace.push({
          type: "primary",
          time: this.nowISO(),
          step: "输入任务",
          content: this.testInput,
        });
        await this.sleep(150);

        this.trace.push({
          type: "success",
          time: this.nowISO(),
          step: "策略选择",
          content: `策略=${
            this.runStrategy
          }；语义约束强度λ=${this.lambda.toFixed(2)}（模拟DAPOM调制）`,
        });
        await this.sleep(150);

        this.trace.push({
          type: "info",
          time: this.nowISO(),
          step: "记忆检索",
          content: "向量检索 top_k=4：命中2条相关记忆（mock）",
        });
        await this.sleep(150);

        this.trace.push({
          type: "warning",
          time: this.nowISO(),
          step: "工具调用",
          content: "调用 MockTool / LawSearch（受 tool_call_limit 约束，模拟）",
        });
        await this.sleep(150);

        const strict = this.lambda >= 0.5;
        this.trace.push({
          type: strict ? "success" : "warning",
          time: this.nowISO(),
          step: "输出校验",
          content: strict
            ? "输出满足 strict_json schema（mock）"
            : "发现字段缺失风险：λ偏低导致格式松散（mock）",
        });
        await this.sleep(150);

        this.trace.push({
          type: "primary",
          time: this.nowISO(),
          step: "最终输出",
          content:
            "生成结果（mock）：{accusation:'...', term_years:..., law_refs:[...], factors:[...]} ",
        });

        // generate logs
        this.pushLog(
          "INFO",
          `启动运行：strategy=${this.runStrategy}, λ=${this.lambda.toFixed(2)}`
        );
        this.pushLog("WARN", "工具调用计数：MockTool (1/2)；接近上限（mock）");
        if (strict) {
          this.pushLog("INFO", "输出校验通过：strict_json OK（mock）");
        } else {
          this.pushLog("ERROR", "输出校验失败：字段缺失/格式不一致（mock）");
        }

        this.toast("success", "运行完成：已生成轨迹与日志（模拟）");
      } finally {
        this.loading.run = false;
      }
    },
    pushLog(level, msg) {
      const item = {
        agentId: this.current.id,
        agent: this.current.name,
        version: this.current.currentVersion,
        level,
        msg,
        date: this.today(),
        time: this.nowISO(),
      };
      item.detail = {
        ...item,
        stack: level === "ERROR" ? "MockStackTrace: ..." : "",
      };
      this.logs.unshift(item);
    },

    // ----- logs -----
    openLogDetail(row) {
      this.logDetail = row.detail || row;
      this.dlg.logDetail = true;
    },
    clearLogs() {
      if (this.mockRole === "viewer")
        return this.toast("warning", "只读角色不可清空日志");
      this.$confirm("确认清空所有日志？（前端模拟）", "提示", {
        type: "warning",
      })
        .then(() => {
          this.logs = [];
          this.toast("success", "日志已清空（模拟）");
        })
        .catch(() => {});
    },
    exportLogs() {
      // 前端导出 JSON 文件
      const blob = new Blob([JSON.stringify(this.filteredLogs, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agent_logs_${this.today()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      this.toast("success", "已导出日志（前端生成文件）");
      this.flowStep = Math.max(this.flowStep, 3);
    },

    // ----- export bundle -----
    makeBundlePreview() {
      if (!this.current) return {};
      const ver = this.current.currentVersion;
      const snap =
        (this.versions[this.current.id] || []).find((x) => x.ver === ver) || {};
      return {
        meta: {
          id: this.current.id,
          name: this.current.name,
          status: this.current.status,
          currentVersion: ver,
        },
        versionSnapshot: {
          ver: snap.ver,
          summary: snap.summary,
          strategies: snap.strategies,
          constraints: snap.constraints,
        },
        exportTime: this.nowISO(),
      };
    },
    exportAgentBundle() {
      if (!this.current) return this.toast("warning", "请先选择智能体");
      if (this.mockRole === "viewer") {
        // 只读也允许导出配置包（模拟）
      }
      const ver = this.current.currentVersion;
      const snap =
        (this.versions[this.current.id] || []).find((x) => x.ver === ver) || {};
      const bundle = {
        meta: { ...this.current },
        versions: (this.versions[this.current.id] || []).map((v) => ({
          ver: v.ver,
          time: v.time,
          summary: v.summary,
        })),
        dsl:
          (snap.snapshot && snap.snapshot.dsl) ||
          `agent "${this.current.name}" { ... }`,
        agentIR: (snap.snapshot && snap.snapshot.agentIR) || {},
        constraints: (snap.snapshot && snap.snapshot.constraints) || "",
        exportTime: this.nowISO(),
      };

      const blob = new Blob([JSON.stringify(bundle, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agent_bundle_${
        this.current.name
      }_v${ver}_${this.today()}.json`;
      a.click();
      URL.revokeObjectURL(url);

      this.flowStep = Math.max(this.flowStep, 4);
      this.toast("success", "已导出配置包（前端生成文件）");
    },

    // ----- tab flow -----
    onTab(t) {
      const name = t.name;
      if (name === "versions") this.flowStep = Math.max(this.flowStep, 1);
      if (name === "run") this.flowStep = Math.max(this.flowStep, 2);
      if (name === "logs") this.flowStep = Math.max(this.flowStep, 3);
      if (name === "export") this.flowStep = Math.max(this.flowStep, 4);
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
  max-width: 900px;
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

.grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1.05fr 1.35fr;
  gap: 12px;
}
.left {
  min-height: 620px;
}
.right {
  min-height: 620px;
}

.rightOps {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.w240 {
  width: 240px;
}
.w260 {
  width: 260px;
}
.w120 {
  width: 120px;
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
.mr6 {
  margin-right: 6px;
}

.nameCell .name {
  font-weight: 900;
  color: #344054;
}
.nameCell .sub {
  color: #667085;
  font-size: 12px;
  margin-top: 2px;
}

.panelTop {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.hint {
  color: #667085;
  font-size: 12px;
  line-height: 1.6;
  max-width: 640px;
}
.btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.runGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.subCard {
  border-radius: 14px;
  border: 1px solid #eef2f7;
  box-shadow: none;
}
.subTitle {
  font-weight: 900;
  margin-bottom: 8px;
  color: #344054;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.lbl {
  font-weight: 800;
  color: #475467;
  min-width: 92px;
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
  margin: 10px 0 8px;
}
.exportBox {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 12px;
}
.kv {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed #eef2f7;
}
.kv:last-child {
  border-bottom: none;
}
.kv span {
  color: #667085;
}
.kv b {
  color: #344054;
}
.miniTitle {
  font-weight: 900;
  color: #475467;
  margin-bottom: 6px;
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
.drawerBody {
  padding: 10px 14px;
}
.compareGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.cmpTitle {
  font-weight: 900;
  margin-bottom: 8px;
}

.permBox {
  margin-top: 12px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 12px;
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  height: 220px;
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

::v-deep .rowPicked td {
  background: rgba(64, 158, 255, 0.08) !important;
}
</style>
