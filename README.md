# 求职市场智能分析与图谱推荐系统

这是一个面向数据分析、商业分析、数据产品、HR Tech、教育科技和职业发展平台的综合数据项目。项目基于大规模招聘岗位数据，构建技能抽取、薪资预测、技能缺口分析、课程推荐和知识图谱查询系统。

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

## 适配岗位

- 数据分析实习
- 商业分析实习
- 数据产品实习
- HR Tech / 人力资源数据分析实习
- 教育科技数据分析实习
- 互联网战略分析实习
- 职业发展平台运营 / 策略实习

## 简历表达方向

可强调：

- 构建基于 1.66M 招聘岗位的职业市场智能分析系统，完成岗位技能抽取、薪资预测、技能缺口诊断和课程推荐。
- 使用 MacBERT-BiLSTM-CRF 抽取岗位技能实体，并用 Neo4j 构建岗位-技能-课程知识图谱。
- 基于 XGBoost 和 SHAP 解释薪资影响因素，为求职者提供技能提升路径和职业匹配建议。

## 面试可讲点

- 如何定义岗位技能实体和技能抽取标签。
- 为什么需要知识图谱连接岗位、技能和课程。
- 薪资预测模型如何处理城市、经验、行业和技能变量。
- SHAP 如何解释技能对薪资的边际影响。
- 数据产品如何从分析看板扩展到职业推荐系统。

