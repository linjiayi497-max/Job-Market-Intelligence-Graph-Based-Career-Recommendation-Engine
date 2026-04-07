"""
教育-产业知识图谱推荐系统 (完整版)
Education-Industry Knowledge Graph Recommendation System

包含三大功能模块：
1. 岗位导向的课程推荐 (Job-to-Course)
2. 课程导向的岗位匹配 (Course-to-Job)
3. 知识图谱可视化探索 (Graph Visualization)
"""

import streamlit as st
import pandas as pd
from neo4j import GraphDatabase
from typing import List, Dict, Tuple
import warnings
import re
import json
import os
warnings.filterwarnings('ignore')

# 尝试导入可视化库
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

# 尝试导入 LLM 客户端（支持 OpenAI 兼容接口，如 DeepSeek）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ==================== Neo4j 连接器 ====================
class Neo4jConnector:
    """Neo4j 数据库连接器 - 支持三大推荐功能"""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """初始化数据库连接"""
        self.database = database
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # 测试连接
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            self.connected = True
        except Exception as e:
            st.error(f"❌ Neo4j 连接失败: {str(e)}")
            self.driver = None
            self.connected = False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
    
    # ========== 模块1: 岗位 -> 课程推荐 ==========
    def get_job_to_course_recommendations(
        self, 
        job_name: str, 
        top_k_skills: int = 20,
        min_coverage: float = 0.0
    ) -> pd.DataFrame:
        """
        岗位导向的课程推荐
        
        参数:
            job_name: 目标职位名称
            top_k_skills: 核心技能数量
            min_coverage: 最低覆盖率阈值
        
        返回:
            推荐课程列表 DataFrame
        """
        query = """
        MATCH (j:Job {name: $job_name})-[r:REQUIRES]->(s:Skill)
        WITH j, s, r
        ORDER BY r.weight DESC
        LIMIT $top_k
        WITH collect(s) AS top_skills, size(collect(s)) AS total_skills
        
        UNWIND top_skills AS skill
        MATCH (c:Course)-[:PROVIDES]->(skill)
        
        WITH c, 
             collect(DISTINCT skill.name) AS covered_skills,
             total_skills
        WITH c.name AS course_name,
             size(covered_skills) AS skill_count,
             covered_skills,
             toFloat(size(covered_skills)) / total_skills AS coverage_rate
        WHERE coverage_rate >= $min_coverage
        
        RETURN course_name,
               skill_count,
               covered_skills,
               coverage_rate
        ORDER BY coverage_rate DESC, skill_count DESC
        LIMIT 100
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    job_name=job_name,
                    top_k=top_k_skills,
                    min_coverage=min_coverage
                )
                
                recommendations = []
                for record in result:
                    recommendations.append({
                        '课程名称': record['course_name'],
                        '覆盖率': f"{record['coverage_rate'] * 100:.1f}%",
                        '覆盖技能数': record['skill_count'],
                        '具体技能列表': ', '.join(record['covered_skills'])
                    })
                
                return pd.DataFrame(recommendations) if recommendations else pd.DataFrame()
        except Exception as e:
            st.error(f"❌ 查询错误: {str(e)}")
            return pd.DataFrame()
    
    # ========== 模块2: 课程 -> 岗位推荐 ==========
    def get_course_to_job_recommendations(
        self, 
        course_names: List[str],
        min_match_rate: float = 0.1
    ) -> pd.DataFrame:
        """
        课程导向的岗位匹配（基于技能画像）
        
        算法逻辑:
        1. 提取用户选择的课程提供的所有技能（用户技能画像）
        2. 遍历所有职位，计算用户技能与职位需求的匹配度
        3. 使用 Jaccard 系数：匹配度 = |交集| / |并集|
        
        参数:
            course_names: 用户已修课程列表
            min_match_rate: 最低匹配率阈值
        
        返回:
            推荐职位列表 DataFrame
        """
        query = """
        // 🔥 修复版查询 - 先找相关职位
        
        // 第一步：提取用户技能（限制到50个）
        MATCH (c:Course)-[:PROVIDES]->(s:Skill)
        WHERE c.name IN $course_names
        WITH c.name AS course_name, collect(DISTINCT s)[0..20] AS course_skills
        
        WITH collect(course_skills) AS all_course_skills
        UNWIND all_course_skills AS skills_list
        UNWIND skills_list AS skill
        
        WITH collect(DISTINCT skill) AS user_skills_all
        WITH user_skills_all[0..50] AS user_skills,
             size(user_skills_all) AS user_skill_count
        
        // 第二步：找需要这些技能的职位（关键修复！）
        UNWIND user_skills AS user_skill
        MATCH (j:Job)-[:REQUIRES]->(user_skill)
        
        // 去重职位并限制数量
        WITH DISTINCT j, user_skills, user_skill_count
        LIMIT 100
        
        // 第三步：获取每个职位的所有技能（限制50个）
        MATCH (j)-[:REQUIRES]->(s_job:Skill)
        WITH j.name AS job_name,
             collect(DISTINCT s_job)[0..50] AS job_skills_limited,
             user_skills,
             user_skill_count
        
        // 第四步：计算匹配度
        WITH job_name,
             [s IN user_skills WHERE s IN job_skills_limited] AS matched_skills,
             [s IN job_skills_limited WHERE NOT s IN user_skills] AS missing_skills,
             user_skills,
             job_skills_limited,
             user_skill_count
        
        WHERE size(matched_skills) > 0
        
        WITH job_name,
             size(matched_skills) AS matched_count,
             size(job_skills_limited) AS job_skill_count,
             [s IN matched_skills | s.name] AS matched_skill_names,
             [s IN missing_skills | s.name] AS missing_skill_names,
             toFloat(size(matched_skills)) / (user_skill_count + size(job_skills_limited) - size(matched_skills)) AS match_rate
        
        WHERE match_rate >= $min_match_rate
        
        RETURN job_name,
               match_rate,
               matched_count,
               job_skill_count,
               matched_skill_names,
               missing_skill_names
        ORDER BY match_rate DESC, matched_count DESC
        LIMIT 100
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    course_names=course_names,
                    min_match_rate=min_match_rate
                )
                
                recommendations = []
                for record in result:
                    missing_skills = record['missing_skill_names'][:5]  # 只显示前5个缺失技能
                    recommendations.append({
                        '职位名称': record['job_name'],
                        '匹配度': f"{record['match_rate'] * 100:.1f}%",
                        '已掌握技能数': record['matched_count'],
                        '职位需求技能数': record['job_skill_count'],
                        '匹配技能': ', '.join(record['matched_skill_names'][:5]),  # 前5个
                        '缺失技能提示': ', '.join(missing_skills) if missing_skills else '无'
                    })
                
                return pd.DataFrame(recommendations) if recommendations else pd.DataFrame()
        except Exception as e:
            st.error(f"❌ 查询错误: {str(e)}")
            return pd.DataFrame()
    
    def get_popular_courses(self, limit: int = 50) -> List[str]:
        """
        获取热门课程列表（用于多选框预加载）
        
        逻辑：按课程提供的技能数量降序排序（覆盖度高的课程）
        """
        query = """
        MATCH (c:Course)-[:PROVIDES]->(s:Skill)
        WITH c.name AS course_name, count(s) AS skill_count
        ORDER BY skill_count DESC
        LIMIT $limit
        RETURN course_name
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, limit=limit)
                return [record['course_name'] for record in result]
        except Exception as e:
            st.error(f"❌ 获取课程列表失败: {str(e)}")
            return []
    
    # ========== 模块3: 图谱可视化 ==========
    def get_subgraph(self, center_keyword: str, max_hops: int = 2) -> Tuple[List[Node], List[Edge]]:
        """
        获取以关键词为中心的子图（2跳内的节点和关系）
        
        参数:
            center_keyword: 中心节点关键词
            max_hops: 最大跳数
        
        返回:
            (nodes, edges) 元组
        """
        query = """
        // 🔥 优化版查询 - 限制节点数量
        
        // 查找中心节点（精确匹配优先）
        MATCH (center)
        WHERE toLower(center.name) CONTAINS toLower($keyword)
        WITH center
        LIMIT 1
        
        // 获取1跳邻居（限制20个）
        OPTIONAL MATCH (center)-[r1]-(neighbor1)
        WITH center, 
             collect(DISTINCT neighbor1)[0..20] AS neighbors1, 
             collect(DISTINCT r1)[0..20] AS rels1
        
        // 如果max_hops=2，再获取2跳邻居（限制10个）
        OPTIONAL MATCH (n1)-[r2]-(neighbor2)
        WHERE n1 IN neighbors1
        WITH center, 
             neighbors1, 
             rels1,
             collect(DISTINCT neighbor2)[0..10] AS neighbors2,
             collect(DISTINCT r2)[0..15] AS rels2
        
        // 合并邻居和关系
        WITH center,
             CASE $max_hops 
                 WHEN 1 THEN neighbors1
                 ELSE neighbors1 + neighbors2
             END AS all_neighbors,
             CASE $max_hops
                 WHEN 1 THEN rels1
                 ELSE rels1 + rels2
             END AS all_rels
        
        RETURN center,
               all_neighbors AS neighbors,
               all_rels AS rels
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query, 
                    keyword=center_keyword,
                    max_hops=max_hops
                )
                record = result.single()
                
                if not record:
                    return [], []
                
                nodes = []
                edges = []
                node_ids = set()
                
                # 添加中心节点
                center = record['center']
                center_id = center.element_id
                center_label = list(center.labels)[0] if center.labels else 'Node'
                
                nodes.append(Node(
                    id=center_id,
                    label=center.get('name', 'Unknown')[:12],  # 缩短标签
                    size=60,  # 再次缩小
                    color=self._get_node_color(center_label),
                    title=f"{center_label}: {center.get('name', 'Unknown')}"
                ))
                node_ids.add(center_id)
                
                # 添加邻居节点
                for neighbor in record['neighbors']:
                    if neighbor:
                        neighbor_id = neighbor.element_id
                        if neighbor_id not in node_ids:
                            neighbor_label = list(neighbor.labels)[0] if neighbor.labels else 'Node'
                            nodes.append(Node(
                                id=neighbor_id,
                                label=neighbor.get('name', 'Unknown')[:10],  # 缩短标签
                                size=30,  # 再次缩小
                                color=self._get_node_color(neighbor_label),
                                title=f"{neighbor_label}: {neighbor.get('name', 'Unknown')}"
                            ))
                            node_ids.add(neighbor_id)
                
                # 添加关系
                for rel in record['rels']:
                    if rel:
                        edges.append(Edge(
                            source=rel.start_node.element_id,
                            target=rel.end_node.element_id,
                            label=rel.type,
                            color='#888888'
                        ))
                
                return nodes, edges
        
        except Exception as e:
            st.error(f"❌ 图谱查询错误: {str(e)}")
            return [], []
    
    @staticmethod
    def _get_node_color(label: str) -> str:
        """根据节点类型返回颜色"""
        color_map = {
            'Job': '#3498db',      # 蓝色
            'Skill': '#e74c3c',    # 红色
            'Course': '#2ecc71'    # 绿色
        }
        return color_map.get(label, '#95a5a6')  # 默认灰色
    
    # ========== 辅助方法 ==========
    def search_jobs(self, keyword: str, limit: int = 20) -> List[str]:
        """搜索职位（模糊匹配）"""
        query = """
        MATCH (j:Job)
        WHERE toLower(j.name) CONTAINS toLower($keyword)
        RETURN DISTINCT j.name AS job_name
        ORDER BY job_name
        LIMIT $limit
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, keyword=keyword, limit=limit)
                return [record['job_name'] for record in result]
        except Exception as e:
            return []


# ==================== NL2Cypher 引擎 ====================
class NL2CypherEngine:
    """
    自然语言 → Cypher → 执行 → 推荐结果
    
    流程：用户自然语言输入 → LLM 生成 Cypher → 安全校验 → Neo4j 执行 → 结果展示
    对标参考仓库 app.py 中 LLM 调用 + service 层图谱查询的组合模式。
    """

    # 图谱 Schema 说明，注入到 System Prompt，告知 LLM 可用的节点/关系/属性
    GRAPH_SCHEMA = """
你是一个 Neo4j Cypher 查询专家，负责将用户的自然语言问题转换为 Cypher 查询。

【知识图谱 Schema】
节点类型：
  - Job(name)                          岗位节点，name 为职位名称
  - Skill(name)                        技能节点，name 为技能名称
  - Course(name)                       课程节点，name 为课程名称

关系类型：
  - (Job)-[:REQUIRES {weight: float}]->(Skill)   岗位需要某技能，weight 为重要性权重
  - (Course)-[:PROVIDES]->(Skill)                课程提供某技能

【低碳技能权重规则（用于 ORDER BY 排序）】
  碳/双碳/低碳/脱碳/碳交易 → 权重 5.0
  新能源/储能/光伏/风电/氢能/锂电 → 权重 4.0
  环保/节能/减排/污染治理 → 权重 4.0
  能源/电力/配电 → 权重 3.0
  其他技能 → 权重 1.0

【生成规则】
1. 只生成 MATCH...RETURN 查询，严禁 CREATE / DELETE / MERGE / SET / DROP
2. 字符串匹配统一用 CONTAINS（不要用 = 精确匹配）
3. 结果必须有 LIMIT，最多 20 条
4. 如需统计数量用 count()，如需排序用 ORDER BY
5. 只输出纯 Cypher 代码，不要任何解释，不要 markdown 代码块（```）
"""

    # 安全校验：禁止写操作的正则
    FORBIDDEN_PATTERN = re.compile(
        r'\b(CREATE|DELETE|MERGE|REMOVE|SET|DROP|CALL\s+apoc\.periodic)\b',
        re.IGNORECASE
    )

    def __init__(self, api_key: str, base_url: str, model: str, neo4j_connector):
        self.connector = neo4j_connector
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @staticmethod
    def _fix_cypher(cypher: str) -> str:
        """
        修复 LLM 常见的 Cypher 语法错误：
        1. CONTAINS(x, y)    -> x CONTAINS y
        2. STARTS_WITH(x, y) -> x STARTS WITH y
        3. ENDS_WITH(x, y)   -> x ENDS WITH y
        4. 末尾多余的分号
        """
        cypher = re.sub(
            r'CONTAINS\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)',
            lambda m: f"{m.group(1).strip()} CONTAINS {m.group(2).strip()}",
            cypher
        )
        cypher = re.sub(
            r'STARTS_WITH\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)',
            lambda m: f"{m.group(1).strip()} STARTS WITH {m.group(2).strip()}",
            cypher
        )
        cypher = re.sub(
            r'ENDS_WITH\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)',
            lambda m: f"{m.group(1).strip()} ENDS WITH {m.group(2).strip()}",
            cypher
        )
        cypher = cypher.rstrip(';').strip()
        return cypher

    def generate_cypher(self, nl_query: str) -> str:
        """调用 LLM 将自然语言转换为 Cypher"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": self.GRAPH_SCHEMA},
                {"role": "user",   "content": f"将以下问题转换为 Cypher 查询：\n{nl_query}"}
            ]
        )
        raw = response.choices[0].message.content.strip()
        # 清理 LLM 可能包裹的 markdown 代码块
        cypher = re.sub(r"```(?:cypher)?\s*|\s*```", "", raw).strip()
        # 自动修复常见语法错误
        cypher = self._fix_cypher(cypher)
        return cypher

    def execute_cypher(self, cypher: str) -> list:
        """在 Neo4j 上执行 Cypher，返回 list[dict]"""
        with self.connector.driver.session(database=self.connector.database) as session:
            result = session.run(cypher)
            return [dict(record) for record in result]

    def summarize_with_llm(self, nl_query: str, results: list) -> str:
        """可选：让 LLM 把原始图谱结果转成自然语言推荐摘要"""
        results_str = json.dumps(results[:10], ensure_ascii=False, indent=2)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是一个招聘与课程推荐专家，请根据图谱查询结果给出简洁的中文推荐说明。"},
                {"role": "user",   "content": f"用户问题：{nl_query}\n\n图谱返回数据：\n{results_str}\n\n请用3-5句话给出推荐说明。"}
            ]
        )
        return response.choices[0].message.content.strip()

    def query(self, nl_query: str) -> dict:
        """
        完整流水线：自然语言 → Cypher → 安全校验 → 执行 → 结构化结果
        返回：{cypher, results, error}
        """
        try:
            cypher = self.generate_cypher(nl_query)
        except Exception as e:
            return {"cypher": "", "results": [], "error": f"LLM 调用失败：{str(e)}"}

        # 安全校验：阻断写操作
        if self.FORBIDDEN_PATTERN.search(cypher):
            return {
                "cypher": cypher,
                "results": [],
                "error": "⚠️ 生成的 Cypher 包含写操作（CREATE/DELETE 等），已拒绝执行。请重新描述查询意图。"
            }

        try:
            results = self.execute_cypher(cypher)
            return {"cypher": cypher, "results": results, "error": None}
        except Exception as e:
            return {"cypher": cypher, "results": [], "error": f"Cypher 执行失败：{str(e)}"}


# ==================== Streamlit 主应用 ====================
def main():
    """主应用程序"""
    
    # 页面配置
    st.set_page_config(
        page_title="教育-产业知识图谱推荐系统",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if not AGRAPH_AVAILABLE:
        st.sidebar.warning("⚠️ streamlit-agraph 未安装，图谱可视化功能不可用。请运行: pip install streamlit-agraph")
    if not OPENAI_AVAILABLE:
        st.sidebar.warning("⚠️ openai 未安装，自然语言查询功能不可用。请运行: pip install openai")
    
    # ==================== 侧边栏：系统信息 ====================
    with st.sidebar:
        st.title("🎓 教育-产业知识图谱")
        st.subheader("推荐系统")
        
        st.divider()
        
        st.markdown("### ⚙️ 数据库配置")
        
        # 数据库连接配置
        uri = st.text_input(
            "Neo4j 地址",
            value="bolt://127.0.0.1:7687",
            help="Neo4j 数据库连接地址"
        )
        
        user = st.text_input(
            "用户名",
            value="neo4j"
        )
        
        password = st.text_input(
            "密码",
            value=os.environ.get("NEO4J_PASSWORD", ""),
            type="password"
        )
        
        database = st.text_input(
            "数据库名称",
            value="job-skill-graph",
            help="指定数据库名称"
        )
        
        st.divider()
        
        # ── LLM 配置（Tab4 自然语言查询用）──────────────────────────
        st.markdown("### 🤖 LLM 配置（自然语言查询）")
        
        llm_api_key = st.text_input(
            "API Key",
            value="",
            type="password",
            help="支持 DeepSeek / OpenAI / 其他兼容接口"
        )
        llm_base_url = st.text_input(
            "API Base URL",
            value="https://api.groq.com/openai/v1",
            help="https://api.groq.com/openai/v1"
        )
        llm_model = st.text_input(
            "模型名称",
            value="llama-3.3-70b-versatile",
            help="DeepSeek: deepseek-chat  |  OpenAI: gpt-4o"
        )
        
        # 保存 LLM 配置到 session_state
        st.session_state['llm_config'] = {
            'api_key': llm_api_key,
            'base_url': llm_base_url,
            'model': llm_model
        }
        
        st.divider()
        
        # 连接按钮
        if 'connector' not in st.session_state:
            if st.button("🔌 连接数据库", type="primary", use_container_width=True):
                connector = Neo4jConnector(uri, user, password, database)
                if connector.connected:
                    st.session_state.connector = connector
                    st.success("✅ 已连接")
                    st.rerun()
        else:
            # 显示连接状态
            st.success("✅ 数据库已连接")
            st.info(f"📊 数据库: {database}")
            
            if st.button("🔄 重新连接", use_container_width=True):
                st.session_state.connector.close()
                del st.session_state.connector
                st.rerun()
        
        st.divider()
        
        st.caption("💡 提示：连接数据库后即可使用")
    
    # ==================== 主界面 ====================
    st.title("🎓 教育-产业知识图谱推荐系统")
    st.markdown("### 基于大规模异构知识图谱的智能推荐平台")
    
    # ==================== 系统介绍（详细版）====================
    st.divider()
    
    # 创建三列展示数据规模
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="📊 图谱节点总数",
            value="3000万+",
            help="包含Job（职位）、Skill（技能）、Course（课程）三类节点"
        )
    with col2:
        st.metric(
            label="🔗 关系总数",
            value="1.1亿条",
            help="包含REQUIRES和PROVIDES两种核心关系"
        )
    with col3:
        st.metric(
            label="⚡ 查询响应时间",
            value="< 60秒",
            help="采用内存优化算法，支持大规模图谱查询"
        )
    
    st.divider()
    
    # 系统功能介绍
    st.markdown("## 💡 系统功能与亮点")
    
    # 创建可展开的功能介绍
    with st.expander("**数据来源与规模**", expanded=False):
        st.markdown("""
        **数据构成**：
        - **职位节点（Job）**：来自真实招聘市场的岗位信息
        - **技能节点（Skill）**：覆盖各行业领域的专业技能标签
        - **课程节点（Course）**：来自高校和在线教育平台的课程资源
        
        **关系类型**：
        - **REQUIRES（职位→技能）**：表示职位对技能的需求关系
        - **PROVIDES（课程→技能）**：表示课程能够培养的技能
        
        **数据规模**：
        - 节点总数：超过3000万个实体节点
        - 关系总数：超过1.1亿条关联关系
        - 图谱密度：平均每个节点连接7-8个关系
        """)
    
    with st.expander("**核心功能模块**", expanded=False):
        st.markdown("""
        **模块一：岗位导向的课程推荐（Job-to-Course）**
        - **输入**：用户选择或输入目标职位名称
        - **算法**：基于技能覆盖度的课程推荐算法（GMSCR）
        - **输出**：推荐覆盖该职位核心技能的课程列表
        - **特点**：智能识别职位核心技能，优先推荐高覆盖率课程
        
        **模块二：课程导向的岗位匹配（Course-to-Job）**
        - **输入**：用户选择已修读的课程清单（1-3门）
        - **算法**：基于技能画像的职位匹配算法（SPJM）
        - **输出**：推荐匹配用户技能画像的职位，并显示缺失技能
        - **特点**：采用Jaccard相似度计算，提供可解释的推荐结果
        
        **模块三：知识图谱可视化探索（Graph Visualization）**
        - **输入**：输入关键词（职位/技能/课程）
        - **功能**：交互式展示关键词周围的图谱结构
        - **输出**：可视化网络图，支持拖拽、缩放、点击查看
        - **特点**：直观展示教育-产业连接路径
        """)
    
    with st.expander("**系统技术亮点**", expanded=False):
        st.markdown("""
        **1. 大规模图谱处理**
        - 成功处理1.1亿级别的关系数据
        - 采用分批查询和内存优化策略
        - 查询响应时间控制在60秒以内
        
        **2. 智能推荐算法**
        - **GMSCR算法**：基于图谱多跳路径的技能覆盖推荐
        - **SPJM算法**：基于用户技能画像的Jaccard相似度匹配
        - 两种算法相互补充，满足不同应用场景
        
        **3. 可解释性设计**
        - 明确显示推荐依据（匹配技能、缺失技能）
        - 提供量化的匹配度指标（覆盖率、相似度）
        - 支持用户理解推荐逻辑，增强信任度
        
        **4. 交互式探索**
        - 图谱可视化模块支持自由探索
        - 多参数调节（跳数、阈值）
        - 结果可导出为CSV文件
        
        **5. 实时连接能力**
        - 直连Neo4j图数据库
        - 支持动态查询和实时推荐
        - 可扩展至更大规模数据集
        """)
    
    st.divider()
    
    # 检查数据库连接
    if 'connector' not in st.session_state:
        st.info("👈 请在左侧配置并连接 Neo4j 数据库")
        st.stop()
    
    connector = st.session_state.connector
    
    # ==================== 三个标签页 ====================
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 岗位 → 课程推荐",
        "💼 课程 → 岗位匹配",
        "🌐 图谱可视化探索",
        "💬 自然语言查询（新）"
    ])
    
    # ==================== Tab 1: 岗位 -> 课程推荐 ====================
    with tab1:
        st.header("🎯 岗位导向的课程推荐")
        st.markdown("输入目标职位，系统推荐最适合的课程学习路径")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🔍 选择目标岗位")
            
            # 搜索职位
            search_keyword = st.text_input(
                "搜索职位关键词",
                placeholder="例如: 算法、工程师、数据分析...",
                key="tab1_search"
            )
            
            # 获取职位列表
            if search_keyword:
                job_options = connector.search_jobs(search_keyword, limit=50)
            else:
                job_options = []
            
            # 选择职位
            selected_job = None
            if job_options:
                selected_job = st.selectbox(
                    "从搜索结果中选择",
                    options=job_options,
                    key="tab1_job_select"
                )
            
            # 手动输入
            st.markdown("---")
            st.markdown("**💡 直接输入职位名称**")
            manual_input = st.text_input(
                "输入职位",
                placeholder="例如: 算法工程师、数据分析师...",
                key="tab1_manual"
            )
            
            # 确定最终职位
            final_job = manual_input.strip() if manual_input.strip() else selected_job
            
            if final_job:
                st.success(f"✅ 目标职位: **{final_job}**")
        
        with col2:
            st.subheader("⚙️ 推荐参数")
            
            top_k = st.slider(
                "核心技能数量",
                min_value=5,
                max_value=50,
                value=20,
                step=5,
                key="tab1_topk"
            )
            
            min_cov = st.slider(
                "最低覆盖率",
                min_value=0,
                max_value=100,
                value=10,
                step=5,
                format="%d%%",
                key="tab1_cov"
            )
        
        st.divider()
        
        # 推荐按钮
        if st.button("🚀 开始推荐", type="primary", use_container_width=True, key="tab1_btn"):
            if final_job:
                with st.spinner(f"正在为 **{final_job}** 生成推荐..."):
                    results = connector.get_job_to_course_recommendations(
                        job_name=final_job,
                        top_k_skills=top_k,
                        min_coverage=min_cov / 100.0
                    )
                    
                    if not results.empty:
                        st.success(f"✅ 找到 **{len(results)}** 门推荐课程")
                        
                        # 统计信息
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("推荐课程数", len(results))
                        with col_stat2:
                            st.metric("最高覆盖率", results['覆盖率'].iloc[0])
                        with col_stat3:
                            avg_skills = results['覆盖技能数'].mean()
                            st.metric("平均覆盖技能数", f"{avg_skills:.1f}")
                        
                        st.divider()
                        
                        # 结果表格
                        st.dataframe(results, use_container_width=True, height=400)
                        
                        # 下载按钮
                        csv = results.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            "📥 下载结果 (CSV)",
                            data=csv,
                            file_name=f"{final_job}_课程推荐.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning(f"⚠️ 未找到职位 **{final_job}** 的推荐课程")
            else:
                st.error("❌ 请先输入或选择职位")
    
    # ==================== Tab 2: 课程 -> 岗位匹配 ====================
    with tab2:
        st.header("💼 课程导向的岗位匹配")
        st.markdown("选择已修课程，系统推荐最匹配的职位")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📚 选择已修课程")
            
            # 预加载热门课程
            if 'popular_courses' not in st.session_state:
                with st.spinner("正在加载课程列表..."):
                    st.session_state.popular_courses = connector.get_popular_courses(limit=100)
            
            # 多选框
            selected_courses = st.multiselect(
                "选择您已修读的课程（建议1-2门）",
                options=st.session_state.popular_courses,
                help="⚠️ 建议只选1-2门课程，选太多可能导致查询缓慢",
                key="tab2_courses"
            )
            
            if selected_courses:
                if len(selected_courses) > 3:
                    st.warning("⚠️ 已选择 {} 门课程（较多），推荐查询可能需要较长时间".format(len(selected_courses)))
                else:
                    st.success(f"✅ 已选择 **{len(selected_courses)}** 门课程")
                with st.expander("查看已选课程列表"):
                    for i, course in enumerate(selected_courses, 1):
                        st.write(f"{i}. {course}")
        
        with col2:
            st.subheader("⚙️ 推荐参数")
            
            min_match = st.slider(
                "最低匹配度",
                min_value=0,
                max_value=100,
                value=5,
                step=5,
                format="%d%%",
                key="tab2_match",
                help="建议从5%开始，逐步提高以获得更精准推荐"
            )
        
        st.divider()
        
        # 推荐按钮
        if st.button("🚀 开始匹配", type="primary", use_container_width=True, key="tab2_btn"):
            if selected_courses:
                with st.spinner("正在分析您的技能画像并匹配职位..."):
                    results = connector.get_course_to_job_recommendations(
                        course_names=selected_courses,
                        min_match_rate=min_match / 100.0
                    )
                    
                    if not results.empty:
                        st.success(f"✅ 找到 **{len(results)}** 个匹配职位")
                        
                        # 统计信息
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("匹配职位数", len(results))
                        with col_stat2:
                            st.metric("最高匹配度", results['匹配度'].iloc[0])
                        with col_stat3:
                            avg_match = results['已掌握技能数'].mean()
                            st.metric("平均掌握技能数", f"{avg_match:.1f}")
                        
                        st.divider()
                        
                        # 结果表格
                        st.dataframe(results, use_container_width=True, height=400)
                        
                        # 下载按钮
                        csv = results.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            "📥 下载结果 (CSV)",
                            data=csv,
                            file_name="岗位匹配结果.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ 未找到匹配的职位")
                        st.info("""
**建议尝试：**
1. **降低匹配度到 0-5%**（当前: {}%）
2. **选择技术类课程**（如：Python、数据结构、算法等）
3. **选择更多课程**（当前: {}门）

💡 提示：思政类、体育类课程与技术岗位相关性较低
                        """.format(min_match, len(selected_courses)))
            else:
                st.error("❌ 请先选择至少一门课程")
    
    # ==================== Tab 3: 图谱可视化 ====================
    with tab3:
        st.header("🌐 知识图谱可视化探索")
        st.markdown("输入关键词，探索知识图谱中的关系网络")
        
        if not AGRAPH_AVAILABLE:
            st.error("❌ 图谱可视化功能不可用")
            st.info("请安装依赖: `pip install streamlit-agraph`")
            st.stop()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("🔍 搜索中心节点")
            
            center_keyword = st.text_input(
                "输入关键词",
                placeholder="例如: 机器学习、Python、数据分析...",
                key="tab3_keyword"
            )
            
            if center_keyword:
                st.info(f"🎯 中心关键词: **{center_keyword}**")
        
        with col2:
            st.subheader("⚙️ 可视化参数")
            
            max_hops = st.select_slider(
                "路径跳数",
                options=[1, 2],
                value=2,
                key="tab3_hops"
            )
        
        st.divider()
        
        # 可视化按钮
        if st.button("🌐 生成图谱", type="primary", use_container_width=True, key="tab3_btn"):
            if center_keyword:
                with st.spinner(f"正在构建以 **{center_keyword}** 为中心的子图..."):
                    nodes, edges = connector.get_subgraph(center_keyword, max_hops)
                    
                    if nodes and edges:
                        st.success(f"✅ 找到 **{len(nodes)}** 个节点，**{len(edges)}** 条关系")
                        
                        # 统计信息
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("节点数", len(nodes))
                        with col_stat2:
                            st.metric("关系数", len(edges))
                        with col_stat3:
                            st.metric("路径跳数", max_hops)
                        
                        st.divider()
                        
                        # 图例
                        st.markdown("### 🎨 节点图例")
                        col_legend1, col_legend2, col_legend3 = st.columns(3)
                        with col_legend1:
                            st.markdown("🔵 **蓝色**: 职位 (Job)")
                        with col_legend2:
                            st.markdown("🔴 **红色**: 技能 (Skill)")
                        with col_legend3:
                            st.markdown("🟢 **绿色**: 课程 (Course)")
                        
                        st.divider()
                        
                        # 可视化配置
                        config = Config(
                            width=1000,
                            height=700,
                            directed=True,
                            physics=True,
                            hierarchical=False,
                            nodeHighlightBehavior=True,
                            highlightColor="#F7A7A6",
                            collapsible=True,
                            node={
                                'labelProperty': 'label',
                                'renderLabel': False,
                                'fontSize': 18,  # 增大字体
                                'fontColor': '#000000',
                                'fontWeight': 'bold'
                            },
                            link={
                                'labelProperty': 'label', 
                                'renderLabel': False,  # 不显示关系标签（删除REQUIRES）
                                'fontSize': 12,
                                'fontColor': '#666666'
                            }
                        )
                        
                        # 渲染图谱
                        st.markdown("### 📊 交互式图谱")
                        return_value = agraph(nodes=nodes, edges=edges, config=config)
                        
                        # 显示提示
                        st.info("💡 提示: 拖动节点可移动，滚轮可缩放，点击节点查看详情")
                    
                    elif nodes and not edges:
                        st.warning(f"⚠️ 找到中心节点，但周围没有关系")
                        st.info("请尝试其他关键词或增加跳数")
                    else:
                        st.warning(f"⚠️ 未找到包含 '{center_keyword}' 的节点")
                        st.info("""
**建议尝试以下关键词：**

**技能类**（最常见）：
• Python、Java、数据分析、机器学习、算法

**课程类**：
• 数据结构、操作系统、计算机网络、数据库

**职位类**：
• 工程师、分析师、开发

💡 提示：避免使用完整职位名称，尝试关键词的一部分
                        """)
            else:
                st.error("❌ 请先输入关键词")


    # ==================== Tab 4: 自然语言图谱查询（新增）====================
    with tab4:
        st.header("💬 自然语言图谱查询")
        st.markdown(
            "用自然语言描述你的问题，系统自动生成 Cypher 查询并在图谱上执行，返回推荐结果。"
        )

        # ── 依赖检查 ──────────────────────────────────────────────────────
        if not OPENAI_AVAILABLE:
            st.error("❌ 自然语言查询功能需要安装 openai 库")
            st.code("pip install openai", language="bash")
            st.stop()

        llm_cfg = st.session_state.get('llm_config', {})
        if not llm_cfg.get('api_key'):
            st.warning("👈 请在左侧侧边栏填写 LLM API Key 后使用本功能")
            st.stop()

        # ── 初始化 NL2Cypher 引擎（按需创建，避免重复实例化）──────────────
        engine_key = f"nl2cypher_{llm_cfg['api_key'][:8]}_{llm_cfg['model']}"
        if engine_key not in st.session_state:
            st.session_state[engine_key] = NL2CypherEngine(
                api_key=llm_cfg['api_key'],
                base_url=llm_cfg['base_url'],
                model=llm_cfg['model'],
                neo4j_connector=connector
            )
        engine = st.session_state[engine_key]

        # ── 使用说明 ──────────────────────────────────────────────────────
        with st.expander("💡 使用说明与示例问题", expanded=True):
            st.markdown("""
**系统工作流程**：
`自然语言输入` → `LLM 生成 Cypher` → `安全校验` → `Neo4j 执行` → `结果展示`

**示例问题（点击下方快速体验）**：
- 「哪些课程能同时覆盖碳排放核算和储能两个技能？」
- 「新能源行业岗位最常要求哪些技能？按需求频次列出前10」
- 「有哪些课程能帮助我胜任碳资产管理师岗位？」
- 「光伏发电工程师和储能系统工程师有哪些共同技能需求？」
- 「哪些岗位对低碳相关技能的要求权重最高？」
            """)

        # ── 输入区 ────────────────────────────────────────────────────────
        nl_query = st.text_input(
            "输入你的问题",
            placeholder="例如：有哪些课程能帮我找到碳管理相关工作？",
            key="tab4_nl_input"
        )

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            show_cypher = st.checkbox("显示生成的 Cypher（调试）", value=True)
        with col_opt2:
            use_summary = st.checkbox("启用 LLM 自然语言摘要", value=False,
                                      help="会额外消耗一次 LLM 调用")

        query_btn = st.button("🔍 查询", type="primary", key="tab4_query_btn")

        # ── 快速示例按钮 ──────────────────────────────────────────────────
        st.markdown("**🚀 快速示例**")
        examples = [
            "哪些课程能同时覆盖碳排放核算和储能两个技能？",
            "新能源行业岗位最常要求哪些技能，按频次列前10",
            "有哪些课程能帮我胜任碳资产管理师岗位？",
            "光伏工程师和储能工程师有哪些共同技能需求？",
        ]
        ex_cols = st.columns(2)
        triggered_example = None
        for i, ex in enumerate(examples):
            with ex_cols[i % 2]:
                if st.button(f"📌 {ex[:22]}…", key=f"tab4_ex_{i}"):
                    triggered_example = ex

        # ── 执行查询（主动提交 或 示例按钮触发）─────────────────────────
        active_query = triggered_example or (nl_query if query_btn and nl_query else None)

        if active_query:
            st.divider()
            st.markdown(f"**查询问题**：{active_query}")

            with st.spinner("LLM 生成 Cypher 中…"):
                result = engine.query(active_query)

            # 展示生成的 Cypher
            if show_cypher:
                with st.expander("📝 生成的 Cypher 查询", expanded=True):
                    st.code(result["cypher"], language="cypher")
                    st.caption("你可以复制上方 Cypher 到 Neo4j Browser 中进一步验证或修改")

            # 错误处理
            if result["error"]:
                st.error(result["error"])
                st.info("💡 建议：换一种描述方式，或检查侧边栏 LLM 配置是否正确")

            # 成功展示结果
            elif result["results"]:
                st.success(f"✅ 查询成功，返回 **{len(result['results'])}** 条结果")

                # LLM 摘要（可选）
                if use_summary:
                    with st.spinner("LLM 生成推荐摘要中…"):
                        summary = engine.summarize_with_llm(active_query, result["results"])
                    st.info(f"📋 **推荐摘要**：{summary}")

                # 结果表格
                df = pd.DataFrame(result["results"])
                st.dataframe(df, use_container_width=True, height=400)

                # 下载
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "📥 下载结果 (CSV)",
                    data=csv,
                    file_name="自然语言查询结果.csv",
                    mime="text/csv",
                    key="tab4_download"
                )

            else:
                st.warning("图谱中未找到匹配结果，请尝试换个描述方式或降低条件限制。")

        elif query_btn and not nl_query:
            st.error("❌ 请先在输入框中输入问题")


if __name__ == "__main__":
    main()