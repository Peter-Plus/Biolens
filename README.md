# BioLens

面向生物信息学科研人员的本地分析与可视化 Agent。Windows 客户端与网页版，项目与聊天组织，用户控制文件读取、外部检索与报告交付。

## 使用

网页版：[biolens.worldlinesite.com](https://biolens.worldlinesite.com)。与桌面共用账号和聊天；网页版通过“项目文件”上传资料，在服务器分析并生成报告。桌面版继续读取本地目录。

本机已构建后，双击 `启动BioLens.cmd`。独立分发版本运行 `release/0.3.0/win-unpacked/BioLens.exe`，注册或登录 BioLens 账号即可使用云端模型，无需填写 API Key。整个 `win-unpacked` 目录必须一起保留，不能只复制 exe。

1. 创建项目并选择研究目录。选择目录不会自动读取文件。
2. 正常聊天，按需开启“阅读本地项目”和“外部检索”。外部检索开启后，仍只有明确要求检索的消息才会调用 PubMed。
3. 需要报告时选择“可视化报告”，选择 HTML、PDF 或两者。描述想分析/展示什么；不明确时 Agent 会追问。
4. 在“成果”中预览、保存报告、SVG/PNG图及CSV表。旧轮次成果保留，新轮次输出新版本。

模型在聊天输入区的下拉菜单选择；正式客户端的模型目录与服务配置由云端管理。六个模型选项由后端 `backend/biolens/models.py` 统一提供和校验，客户端不能自行添加。默认使用 Qwen3.7 Flash，最高档为 Qwen3.8 Max。档位代表产品定位，不保证所有任务上的严格能力排名。选择会在本机记住，打开旧聊天会恢复仍在开放名单中的上一轮模型；运行期间不能切换，历史任务记录保留实际使用的模型。

本地读取仅限选定路径，密钥/环境配置等不提供给模型。开启读取后，被实际读取的资料片段可能作为上下文经 BioLens 云端发送到千问模型服务；并非完全离线软件。原始数据在本地计算。

云端账号与运维说明见 [部署文档](docs/deployment.md)。原有本地聊天保留，不会自动导入新账号。

## 首版范围

- 资料：文本 PDF、Markdown、TXT；扫描件尚不支持OCR。
- 数据：CSV/TSV表达矩阵（首列基因ID，行基因、列样本）与样本表（`sample_id`和用户指定分组列）。单文件最多100 MB、500个样本、100000个基因。
- 分析：严格样本对应检查、PCA（可按指定技术因素标记点形状）、主成分解释率、样本表达分布、Pearson相关性、高变异基因热图、指定基因分组表达。明确指定两组参考方向后还可生成组均值差概览及候选排序；不含p值/FDR。不会自动删除样本、归一化或做正式差异表达检验。
- 检索：本地关键词查询；PubMed查询与摘要获取，不是全文系统综述。
- 模型：兼容Chat Completions和工具调用的服务。千问关闭深度思考；默认温度0.2。
- 输出：交互HTML、打印PDF、SVG/PNG、CSV、报告结构JSON和数据SHA256。

`examples/expression-demo` 为明确标注的合成数据，仅验证软件，不支持真实疾病结论。

## 开发

需要 Node.js 22+、Python 3.11+（推荐3.12）。

```powershell
./scripts/setup.ps1 -Python python
npm run desktop
```

已有本地运行环境时：

```powershell
npm run build
npm start
npm test
node scripts/python.mjs scripts/report_smoke.py
```

`.local/dev.json` 指定开发Python及数据目录。本机启动入口使用 `.local/app-data/settings.json` 保存模型配置，不进入版本库或分发包；早期测试数据位于 `.local/data`。开发模式可在客户端设置填写配置；正式客户端使用云端账号，不要发送自己的 `.local` 目录。

依赖锁：`package-lock.json`；实际验证的Python版本见 `requirements-lock.txt`。`requirements.txt`是兼容范围。

## 打包

本次工作环境可运行 `node scripts/python.mjs scripts/prepare_runtime.py` 准备独立运行时，再执行 `npm run package:win`。此脚本从项目的 `.local/pylibs` 复制依赖；常规venv环境需先运行 `python -m pip install --target .local/pylibs -r requirements-lock.txt`。

`npm run package:installer` 可额外生成安装器。首版优先交付可直接运行的Windows目录版。运行时含Python及Chromium，体积较大；尚未做代码签名和自动更新。

## 课程材料

`course/BioLens-course-report.ipynb` 是课程Notebook，导出HTML同目录。`course/evaluation` 保存真实模型测试问题、回答和工具证据。复跑真实测试会调用模型并产生费用。GPT/Codex跨产品对照应按 `course/comparison-protocol.md` 记录真实结果，不使用模拟结果替代。

## 架构

```text
electron/            Windows窗口、目录对话框、本地后端生命周期
src/                 React聊天界面、权限开关、成果预览
backend/biolens/      API、LangGraph Agent、工具、报告与持久化
backend/tests/        权限、工具计算、状态与引用验证
assets/              无底框SVG标志与Windows图标
examples/            合成示例与失败案例
scripts/             环境准备、构建、集成测试和课程材料生成
course/              Notebook、实际测试证据与汇报说明
```

Agent只调用明确注册的工具，不执行任意生成代码。UI权限由后端再次检查；模型不能通过提示词绕过目录范围。报告来自同一份结果结构，HTML和PDF不分别重新计算。

真实数据示例见 `examples/pasilla/README.md`（14,599基因、7样本）。`scripts/prepare_pasilla.py` 记录显式log2(CPM+1)预处理；`scripts/visual_iteration.py` 可复现完整报告与逐页检查。最新版示例位于 `artifacts/visual-iterations/final`。

可视化模块：`expression_data.py` 校验输入，`expression_stats.py` 计算，`expression_charts.py` 构图，`chart_theme.py` 统一样式，`report_document.py` 与 `report.css` 排版，`report_export.py` 导出。PDF使用同源矢量SVG，HTML保留Plotly交互。


## Git 仓库内容

仓库保留源码、依赖锁、部署脚本、课程 Notebook、验收记录及可复现实验的示例数据。依赖与运行时（`node_modules`、`runtime`）、构建目录（`dist`、`release`）、生成成果（`artifacts`、课程导出 HTML）、本机配置与账号数据（`.local`、SQLite）、凭据和缓存均由 `.gitignore` 排除，不会随源码上传。

首次克隆后按“开发”和“打包”步骤安装依赖、准备运行时。部署需要自行准备服务器凭据与模型配置；这些私人文件不包含在仓库中。分发客户端应使用构建产物，不能把 `.local` 一起打包。
