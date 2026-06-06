# 求职市场智能分析与图谱推荐系统

这是一个面向数据分析、商业分析、数据产品、HR Tech、教育科技和职业发展平台的综合数据项目。项目基于大规模招聘岗位数据，构建技能抽取、薪资预测、技能缺口分析、课程推荐和知识图谱查询系统。

## 产品化入口：职途智析

`职途智析` 是本项目的公网可部署产品入口。用户输入目标岗位和当前技能后，系统输出技能差距、薪资预期、推荐课程和相似岗位。

在线访问链接：https://career-intel.streamlit.app/

作品集 PDF：[ZhiTuZhiXi_portfolio.pdf](portfolio/ZhiTuZhiXi_portfolio.pdf)

作品集 Markdown：[ZhiTuZhiXi_portfolio.md](portfolio/ZhiTuZhiXi_portfolio.md)

本地启动：

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

第一版默认使用扩展演示数据，确保可以直接部署到 Streamlit Community Cloud。若在 Streamlit Cloud 的 secrets 中配置 Neo4j 连接信息，后续可切换真实图谱后端。secrets 模板见 `secrets.example.toml`。

当前产品化入口已扩展为“岗位-技能-课程-个人项目-开源参考”推荐 demo，内置 38 个岗位样例、83 个技能标签、11 个个人项目素材和 23 个 GitHub 开源参考项目，可展示我的项目、开源参考、课程关键词、相似岗位和面试准备问题。

## 项目定位

本项目试图回答以下问题：

1. 不同行业、城市和薪资段分别需要哪些技能？
2. 求职者当前技能与目标岗位之间有什么差距？
3. 哪些技能对薪资预测影响更大？
4. 哪些课程可以补齐目标岗位所需技能？
5. 如何用知识图谱连接岗位、技能和课程？

## 系统架构

项目包含四层：

- 数据采集层：招聘平台岗位采集和课程数据采集。
- NLP 与特征工程层：岗位文本清洗、薪资解析、技能实体抽取。
- 分析建模层：岗位技能热力图、技能缺口分析、XGBoost 薪资预测和 SHAP 解释。
- 知识图谱层：使用 Neo4j 构建岗位-技能-课程图谱，并支持自然语言到 Cypher 查询。

## 核心功能

- 岗位市场分析：统计行业、城市、薪资段下的技能需求。
- 技能频率与 TF-IDF：识别不同岗位和薪资层级的代表性技能。
- 技能缺口诊断：输入个人技能或简历文本，计算目标岗位匹配度。
- 薪资预测：使用 XGBoost 预测岗位薪资，并用 SHAP 解释技能贡献。
- 课程推荐：基于岗位所需技能推荐可学习课程。
- 知识图谱查询：构建 Job-Skill-Course 关系网络，支持图谱可视化。
- LLM 辅助建议：生成个性化技能提升与职业发展建议。

## 项目结构

```text
.
|-- data_collection/                 # 岗位与课程采集模块
|   |-- job_scraping/
|   `-- course_scraping/
|-- analytics_dashboard/             # Streamlit 数据分析看板
|   |-- app/
|   |-- processing/
|   |-- scripts/
|   `-- models/
|-- knowledge_graph/                 # Neo4j 知识图谱推荐系统
|-- requirements.txt
`-- README.md
```

## 快速开始

```bash
git clone https://github.com/linjiayi497-max/Job-Market-Intelligence-Graph-Based-Career-Recommendation-Engine.git
cd Job-Market-Intelligence-Graph-Based-Career-Recommendation-Engine
pip install -r requirements.txt
```

如需运行完整图谱功能，需要提前安装 Neo4j 并配置环境变量：

```bash
export NEO4J_PASSWORD="your-neo4j-password"
```

如需使用 AI 技能报告，需要配置兼容的 LLM API Key：

```bash
export GROQ_API_KEY="your-groq-api-key"
```

启动分析看板：

```bash
cd analytics_dashboard
streamlit run app/main_page.py
```

启动知识图谱系统：

```bash
cd knowledge_graph
streamlit run app.py
```

## 数据与模型亮点

- 原始岗位规模：约 1.7M 条。
- 清洗后有效记录：约 1.4M+ 条。
- 覆盖行业：50+。
- 覆盖城市：300+。
- 技能实体：10,000+。
- 知识图谱节点：30M+。
- 知识图谱关系：110M+。
- 薪资预测模型：XGBoost + SHAP。
- 技能抽取模型：MacBERT-BiLSTM-CRF。

