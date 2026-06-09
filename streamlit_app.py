from __future__ import annotations

import html
import json
import time
import uuid
import zipfile
from datetime import date, datetime
from io import BytesIO
from typing import Any
from urllib import error, request
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from career_service import analyze_career, available_jobs, available_skills


BRAND_BLUE = "#17324d"
BRAND_ORANGE = "#f28c28"
INK = "#0f1f33"
MUTED = "#5f6d7c"

APPLICATION_STATUSES = ["已收藏", "准备中", "已投递", "笔试/面试", "已拿 Offer", "已拒绝/归档"]
STATUS_COLORS = {
    "已收藏": "#8294aa",
    "准备中": "#f5a623",
    "已投递": "#3d7be0",
    "笔试/面试": "#2cb36a",
    "已拿 Offer": "#6f58c9",
    "已拒绝/归档": "#e45656",
}
PRIORITIES = ["高", "中", "低"]
DEFAULT_API_CONFIG = {
    "provider": "OpenAI-compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4.1-mini",
    "temperature": 0.35,
    "timeout": 60,
}
DEFAULT_USER_CONTEXT = {
    "base_profile": "李华，普通本科应届生，正在寻找实习机会；有课程项目、校园实践和基础办公软件使用经验，方向仍在探索中。",
    "target_cities": ["北京市-北京市", "上海市-上海市", "广东省-深圳市", "浙江省-杭州市"],
    "availability": "立即到岗",
    "internship_duration": "3-6个月",
    "target_directions": ["互联网/AI-数据", "产品-产品经理", "市场/公关/广告-市场营销"],
    "skill_tags": ["英语四级", "Excel", "PPT", "数据分析", "沟通表达"],
    "resume_versions": [],
    "constraints": "优先考虑能积累项目经验、沟通协作和专业技能的实习岗位，简历表达需要真实、清晰、可追问。",
}
PROVINCE_CITY_OPTIONS = {
    "北京市": ["北京市"],
    "天津市": ["天津市"],
    "河北省": ["石家庄市", "唐山市", "秦皇岛市", "邯郸市", "邢台市", "保定市", "张家口市", "承德市", "沧州市", "廊坊市", "衡水市"],
    "山西省": ["太原市", "大同市", "阳泉市", "长治市", "晋城市", "朔州市", "晋中市", "运城市", "忻州市", "临汾市", "吕梁市"],
    "内蒙古自治区": ["呼和浩特市", "包头市", "乌海市", "赤峰市", "通辽市", "鄂尔多斯市", "呼伦贝尔市", "巴彦淖尔市", "乌兰察布市", "兴安盟", "锡林郭勒盟", "阿拉善盟"],
    "辽宁省": ["沈阳市", "大连市", "鞍山市", "抚顺市", "本溪市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市", "盘锦市", "铁岭市", "朝阳市", "葫芦岛市"],
    "吉林省": ["长春市", "吉林市", "四平市", "辽源市", "通化市", "白山市", "松原市", "白城市", "延边朝鲜族自治州"],
    "黑龙江省": ["哈尔滨市", "齐齐哈尔市", "鸡西市", "鹤岗市", "双鸭山市", "大庆市", "伊春市", "佳木斯市", "七台河市", "牡丹江市", "黑河市", "绥化市", "大兴安岭地区"],
    "上海市": ["上海市"],
    "江苏省": ["南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市", "连云港市", "淮安市", "盐城市", "扬州市", "镇江市", "泰州市", "宿迁市"],
    "浙江省": ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市", "衢州市", "舟山市", "台州市", "丽水市"],
    "安徽省": ["合肥市", "芜湖市", "蚌埠市", "淮南市", "马鞍山市", "淮北市", "铜陵市", "安庆市", "黄山市", "滁州市", "阜阳市", "宿州市", "六安市", "亳州市", "池州市", "宣城市"],
    "福建省": ["福州市", "厦门市", "莆田市", "三明市", "泉州市", "漳州市", "南平市", "龙岩市", "宁德市"],
    "江西省": ["南昌市", "景德镇市", "萍乡市", "九江市", "新余市", "鹰潭市", "赣州市", "吉安市", "宜春市", "抚州市", "上饶市"],
    "山东省": ["济南市", "青岛市", "淄博市", "枣庄市", "东营市", "烟台市", "潍坊市", "济宁市", "泰安市", "威海市", "日照市", "临沂市", "德州市", "聊城市", "滨州市", "菏泽市"],
    "河南省": ["郑州市", "开封市", "洛阳市", "平顶山市", "安阳市", "鹤壁市", "新乡市", "焦作市", "濮阳市", "许昌市", "漯河市", "三门峡市", "南阳市", "商丘市", "信阳市", "周口市", "驻马店市", "济源市"],
    "湖北省": ["武汉市", "黄石市", "十堰市", "宜昌市", "襄阳市", "鄂州市", "荆门市", "孝感市", "荆州市", "黄冈市", "咸宁市", "随州市", "恩施土家族苗族自治州", "仙桃市", "潜江市", "天门市", "神农架林区"],
    "湖南省": ["长沙市", "株洲市", "湘潭市", "衡阳市", "邵阳市", "岳阳市", "常德市", "张家界市", "益阳市", "郴州市", "永州市", "怀化市", "娄底市", "湘西土家族苗族自治州"],
    "广东省": ["广州市", "韶关市", "深圳市", "珠海市", "汕头市", "佛山市", "江门市", "湛江市", "茂名市", "肇庆市", "惠州市", "梅州市", "汕尾市", "河源市", "阳江市", "清远市", "东莞市", "中山市", "潮州市", "揭阳市", "云浮市"],
    "广西壮族自治区": ["南宁市", "柳州市", "桂林市", "梧州市", "北海市", "防城港市", "钦州市", "贵港市", "玉林市", "百色市", "贺州市", "河池市", "来宾市", "崇左市"],
    "海南省": ["海口市", "三亚市", "三沙市", "儋州市", "五指山市", "琼海市", "文昌市", "万宁市", "东方市", "定安县", "屯昌县", "澄迈县", "临高县", "白沙黎族自治县", "昌江黎族自治县", "乐东黎族自治县", "陵水黎族自治县", "保亭黎族苗族自治县", "琼中黎族苗族自治县"],
    "重庆市": ["重庆市"],
    "四川省": ["成都市", "自贡市", "攀枝花市", "泸州市", "德阳市", "绵阳市", "广元市", "遂宁市", "内江市", "乐山市", "南充市", "眉山市", "宜宾市", "广安市", "达州市", "雅安市", "巴中市", "资阳市", "阿坝藏族羌族自治州", "甘孜藏族自治州", "凉山彝族自治州"],
    "贵州省": ["贵阳市", "六盘水市", "遵义市", "安顺市", "毕节市", "铜仁市", "黔西南布依族苗族自治州", "黔东南苗族侗族自治州", "黔南布依族苗族自治州"],
    "云南省": ["昆明市", "曲靖市", "玉溪市", "保山市", "昭通市", "丽江市", "普洱市", "临沧市", "楚雄彝族自治州", "红河哈尼族彝族自治州", "文山壮族苗族自治州", "西双版纳傣族自治州", "大理白族自治州", "德宏傣族景颇族自治州", "怒江傈僳族自治州", "迪庆藏族自治州"],
    "西藏自治区": ["拉萨市", "日喀则市", "昌都市", "林芝市", "山南市", "那曲市", "阿里地区"],
    "陕西省": ["西安市", "铜川市", "宝鸡市", "咸阳市", "渭南市", "延安市", "汉中市", "榆林市", "安康市", "商洛市"],
    "甘肃省": ["兰州市", "嘉峪关市", "金昌市", "白银市", "天水市", "武威市", "张掖市", "平凉市", "酒泉市", "庆阳市", "定西市", "陇南市", "临夏回族自治州", "甘南藏族自治州"],
    "青海省": ["西宁市", "海东市", "海北藏族自治州", "黄南藏族自治州", "海南藏族自治州", "果洛藏族自治州", "玉树藏族自治州", "海西蒙古族藏族自治州"],
    "宁夏回族自治区": ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"],
    "新疆维吾尔自治区": ["乌鲁木齐市", "克拉玛依市", "吐鲁番市", "哈密市", "昌吉回族自治州", "博尔塔拉蒙古自治州", "巴音郭楞蒙古自治州", "阿克苏地区", "克孜勒苏柯尔克孜自治州", "喀什地区", "和田地区", "伊犁哈萨克自治州", "塔城地区", "阿勒泰地区", "石河子市", "阿拉尔市", "图木舒克市", "五家渠市", "北屯市", "铁门关市", "双河市", "可克达拉市", "昆玉市", "胡杨河市", "新星市", "白杨市"],
    "香港特别行政区": ["香港特别行政区"],
    "澳门特别行政区": ["澳门特别行政区"],
    "台湾省": ["台北市", "新北市", "桃园市", "台中市", "台南市", "高雄市", "基隆市", "新竹市", "嘉义市", "新竹县", "苗栗县", "彰化县", "南投县", "云林县", "嘉义县", "屏东县", "宜兰县", "花莲县", "台东县", "澎湖县", "金门县", "连江县"],
}
BOSS_DIRECTION_GROUPS = {
    "互联网/AI": ["后端开发", "前端/移动开发", "测试", "运维/技术支持", "人工智能", "销售技术支持", "数据", "技术项目管理", "高端技术职位", "其他技术职位"],
    "电子/电气/通信": ["电子/硬件开发", "半导体/芯片", "电气/自动化", "通信", "销售技术支持", "运维/技术支持"],
    "产品": ["产品经理", "AI产品经理", "数据产品经理", "电商产品经理", "移动产品经理", "金融产品经理", "用户研究", "游戏策划/制作"],
    "客服/运营": ["客服", "内容运营", "电商运营", "业务运营", "线下运营", "编辑", "高端运营职位", "其他运营职位"],
    "销售": ["销售", "销售管理", "销售行政/商务", "外贸销售", "教培销售", "汽车销售", "房地产销售/招商", "服务业销售", "医疗销售", "广告/会展销售", "金融销售"],
    "人力/行政/法务": ["人力资源", "行政", "法律服务", "其他职能职位"],
    "财务/审计/税务": ["会计", "审计/税务", "高级财务职位", "其他财务岗位"],
    "生产制造": ["普工", "机械加工", "技工", "运输设备操作", "质量管理", "机械设计/制造", "电气/自动化", "生产营运", "生产安全", "化工", "服装/纺织/皮革", "新能源汽车", "汽车研发/制造", "环保"],
    "零售/生活服务": ["零售", "美容美发", "理疗保健", "家政/保洁", "安保服务", "维修服务"],
    "旅游": ["旅游服务", "酒店服务", "餐饮服务"],
    "教育培训": ["教师", "培训", "教务管理", "教培销售", "其他教育培训职位"],
    "设计": ["视觉/交互设计", "环境设计", "工业/产品设计", "美术/3D/动画", "游戏设计", "设计管理"],
    "房地产/建筑": ["工程管理", "装饰装修", "物业管理", "建筑设计", "城市规划", "房地产开发"],
    "直播/影视/传媒": ["主播", "影视制作", "编导/导演", "摄影/摄像", "后期制作", "采编/写作/出版", "其他传媒职位"],
    "市场/公关/广告": ["市场营销", "推广/投放", "政府事务", "公关", "广告", "调研分析", "广告/会展销售", "其他市场职位"],
    "物流/仓储/司机": ["物流/运输", "配送理货", "驾驶员", "仓储", "供应链"],
    "采购/贸易": ["采购", "外贸销售", "进出口贸易"],
    "汽车": ["新能源汽车", "汽车研发/制造", "汽车销售", "汽车服务"],
    "医疗健康": ["医生/医技", "护士/护理", "医药研发", "医疗器械", "医务管理", "健康/康复"],
    "金融": ["银行", "证券/基金/期货", "中后台", "投融资", "保险", "金融销售", "其他金融职位"],
    "项目管理": ["项目管理", "软件项目经理", "硬件项目经理", "咨询项目管理", "物流/仓储项目经理", "汽车项目管理", "生产制造项目经理"],
    "咨询/翻译/法律": ["咨询/调研", "翻译", "法律服务"],
    "能源/环保/农业": ["能源/地质", "环保", "农/林/牧/渔"],
    "高级管理": ["高级管理职位"],
    "其他": ["其他职位类别"],
}
ABILITY_TAG_GROUPS = {
    "语言能力": ["英语四级", "英语六级", "雅思", "托福", "英语口语", "商务英语", "日语", "韩语", "法语", "德语", "西班牙语", "普通话", "粤语"],
    "计算机能力": ["Python", "Java", "C/C++", "JavaScript", "SQL", "Linux", "Git", "Excel", "PPT", "Word", "Power BI", "Tableau", "Photoshop", "CAD", "SPSS"],
    "数据/AI能力": ["数据分析", "数据可视化", "数据挖掘", "数据治理", "机器学习", "深度学习", "自然语言处理", "大模型", "推荐算法", "A/B测试", "指标体系", "Prompt"],
    "产品/运营能力": ["需求分析", "产品设计", "用户研究", "竞品分析", "原型设计", "项目管理", "内容运营", "电商运营", "用户运营", "社群运营", "数据/策略运营"],
    "设计/传媒能力": ["平面设计", "UI设计", "UX/交互设计", "视觉设计", "视频剪辑", "摄影摄像", "文案编辑", "新媒体运营", "直播运营"],
    "市场/销售能力": ["市场调研", "市场营销策划", "活动策划", "品牌公关", "SEO", "SEM", "信息流优化", "客户开发", "商务谈判", "客户成功"],
    "财务/职能能力": ["会计核算", "财务分析", "审计", "税务", "招聘", "HRBP", "行政支持", "法务", "合同管理"],
    "制造/工程能力": ["质量管理", "机械设计", "电气设计", "自动化", "生产计划", "供应链管理", "采购", "物流调度", "仓储管理"],
    "通用能力": ["沟通表达", "跨部门协作", "问题拆解", "文档写作", "复盘总结", "执行力", "抗压能力", "学习能力", "团队协作"],
}
NEXT_ACTION_OPTIONS = [
    "拆JD并生成岗位版简历",
    "完善用户求职上下文",
    "上传/更新简历PDF",
    "生成本地预览建议",
    "调用AI生成岗位版简历",
    "人工校对AI改写",
    "准备作品集/项目材料",
    "投递岗位",
    "等待简历筛选结果",
    "准备笔试/面试",
    "跟进HR反馈",
    "归档记录",
]
LEGACY_RESUME_VERSION_NAMES = {"基础通用版", "互联网产品版", "数据分析版", "AI产品版"}
KEYWORD_POOL = [
    "AI",
    "AIGC",
    "LLM",
    "产品设计",
    "需求分析",
    "用户研究",
    "竞品分析",
    "数据分析",
    "SQL",
    "Python",
    "Excel",
    "A/B测试",
    "指标体系",
    "知识图谱",
    "NLP",
    "Prompt",
    "项目管理",
    "沟通表达",
    "商业分析",
    "增长",
    "运营",
    "SaaS",
    "B端",
    "C端",
    "看板",
    "可视化",
    "风控",
    "策略",
] + [
    item
    for options in BOSS_DIRECTION_GROUPS.values()
    for item in options
] + [
    item
    for options in ABILITY_TAG_GROUPS.values()
    for item in options
]
KEYWORD_POOL = list(dict.fromkeys(KEYWORD_POOL))


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: #f7f9fb; }}
        .product-header {{
          background: {BRAND_BLUE};
          color: white;
          padding: 18px 20px;
          border-radius: 6px;
          margin-bottom: 18px;
        }}
        .product-header h1 {{
          margin: 0;
          font-size: 26px;
          letter-spacing: 0;
        }}
        .product-header p {{
          margin: 5px 0 0 0;
          color: #d7e1ec;
        }}
        .mode-badge {{
          display: inline-block;
          background: #fff3e0;
          color: #8a4d00;
          border: 1px solid #ffd49a;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 13px;
          margin-bottom: 12px;
        }}
        .info-card, .course-card, .job-card, .project-card, .question-card, .tracker-card, .context-card {{
          background: white;
          border: 1px solid #e3e8ef;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 10px;
          box-shadow: 0 2px 10px rgba(23, 50, 77, .05);
        }}
        .info-card strong, .course-card strong, .job-card strong, .project-card strong, .tracker-card strong, .context-card strong {{
          color: {BRAND_BLUE};
        }}
        .muted {{ color: {MUTED}; font-size: 13px; line-height: 1.5; }}
        .tag {{
          display: inline-block;
          background: #eef4fa;
          color: {INK};
          border-radius: 4px;
          padding: 3px 7px;
          margin: 2px 3px 2px 0;
          font-size: 12px;
        }}
        .tag-orange {{
          background: #fff3e0;
          color: #8a4d00;
        }}
        .tag-green {{
          background: #e7f7ef;
          color: #14784f;
        }}
        .tag-red {{
          background: #fff0f0;
          color: #a93434;
        }}
        .link-line a {{ color: {BRAND_ORANGE}; text-decoration: none; }}
        .tracker-card {{
          border-left: 4px solid {BRAND_ORANGE};
          min-height: 138px;
        }}
        .api-card {{
          background: #fff8ee;
          border: 1px solid #ffd49a;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 12px;
        }}
        .context-card {{
          border-left: 4px solid {BRAND_BLUE};
          background: #fbfdff;
        }}
        .score-box {{
          background: #eef4fa;
          border-radius: 6px;
          padding: 12px;
          text-align: center;
        }}
        .score-box strong {{
          color: {BRAND_BLUE};
          display: block;
          font-size: 24px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def read_neo4j_config() -> dict[str, str]:
    try:
        neo4j_cfg = st.secrets.get("neo4j", {})
        return {
            "uri": neo4j_cfg.get("uri", ""),
            "user": neo4j_cfg.get("user", ""),
            "password": neo4j_cfg.get("password", ""),
            "database": neo4j_cfg.get("database", "neo4j"),
        }
    except Exception:
        return {}


def ensure_result_schema(result: dict) -> dict:
    result.setdefault("target_job_profile", {"job_title": "", "industry": "", "path": "", "positioning": "", "outputs": []})
    result.setdefault("skill_gap", [])
    result.setdefault("salary_range", {"min": 0, "median": 0, "max": 0, "currency": "CNY", "period": "month"})
    result.setdefault("recommended_courses", [])
    result.setdefault("similar_jobs", [])
    result.setdefault("reference_projects", [])
    result.setdefault("interview_questions", [])
    result.setdefault("learning_plan", [])
    result.setdefault("mode", "demo")
    return result


def join_text(items: list[str], fallback: str = "") -> str:
    return "、".join([item for item in items if item]) or fallback


def default_applications() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-zhhipu",
            "company": "智谱华章",
            "role": "AI产品实习生",
            "direction": "AI产品",
            "status": "已收藏",
            "priority": "高",
            "apply_date": "2026-06-09",
            "deadline": "2026-06-16",
            "next_action": "拆JD并生成岗位版简历",
            "resume_version": "未关联PDF简历",
            "jd": "负责AI产品需求分析、竞品调研、用户反馈整理、数据指标跟踪；要求具备产品思维、数据分析和项目表达能力。",
            "notes": "重点突出职途智析、GrowthLens和AI产品理解。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
        {
            "id": "demo-tencent",
            "company": "腾讯云",
            "role": "数据产品经理实习",
            "direction": "数据产品",
            "status": "准备中",
            "priority": "高",
            "apply_date": "2026-06-08",
            "deadline": "2026-06-14",
            "next_action": "AI改写项目经历",
            "resume_version": "未关联PDF简历",
            "jd": "参与数据产品需求分析、指标体系建设、BI看板和客户需求沟通，要求理解数据分析、产品设计和B端业务。",
            "notes": "强调职途智析统一接口、GrowthLens字段映射和数据产品能力。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
        {
            "id": "demo-bytedance",
            "company": "字节跳动",
            "role": "增长产品实习",
            "direction": "增长",
            "status": "已投递",
            "priority": "高",
            "apply_date": "2026-06-06",
            "deadline": "2026-06-20",
            "next_action": "等待简历筛选结果",
            "resume_version": "未关联PDF简历",
            "jd": "负责增长场景需求分析、实验设计、转化漏斗监控和跨部门项目推进。",
            "notes": "可用GrowthLens讲A/B实验和漏斗分析。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
        {
            "id": "demo-baidu",
            "company": "百度",
            "role": "AI产品经理实习",
            "direction": "AI产品",
            "status": "笔试/面试",
            "priority": "高",
            "apply_date": "2026-06-05",
            "deadline": "2026-06-12",
            "next_action": "整理职途智析项目讲稿",
            "resume_version": "未关联PDF简历",
            "jd": "负责AI产品需求分析、用户反馈收集、Prompt方案设计、产品指标跟踪和项目推进。",
            "notes": "本周面试，优先准备产品作品集和AI简历版本。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
        {
            "id": "demo-offer",
            "company": "某AI工具公司",
            "role": "产品实习生",
            "direction": "AI产品",
            "status": "已拿 Offer",
            "priority": "中",
            "apply_date": "2026-05-28",
            "deadline": "2026-06-10",
            "next_action": "确认入职材料",
            "resume_version": "未关联PDF简历",
            "jd": "参与AI工具产品优化、用户反馈整理和功能迭代。",
            "notes": "已拿口头Offer。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
        {
            "id": "demo-archive",
            "company": "某教育科技",
            "role": "产品运营实习",
            "direction": "运营",
            "status": "已拒绝/归档",
            "priority": "低",
            "apply_date": "2026-05-25",
            "deadline": "2026-06-03",
            "next_action": "归档记录",
            "resume_version": "未关联PDF简历",
            "jd": "偏销售转化和社群维护。",
            "notes": "岗位偏销售，暂不优先。",
            "ai_resume_draft": "",
            "updated_at": "2026-06-09",
        },
    ]


def clone_default_user_context() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_USER_CONTEXT, ensure_ascii=False))


def normalize_lines(value: str) -> list[str]:
    normalized = value.replace("，", "\n").replace(",", "\n").replace("、", "\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return normalize_lines(value)
    return []


def merge_options(options: list[str], selected: list[str]) -> list[str]:
    return list(dict.fromkeys([*options, *selected]))


def job_direction_options() -> list[str]:
    return [f"{group}-{direction}" for group, directions in BOSS_DIRECTION_GROUPS.items() for direction in directions]


def city_label(province: str, city: str) -> str:
    return f"{province}-{city}"


def all_city_options() -> list[str]:
    return [city_label(province, city) for province, cities in PROVINCE_CITY_OPTIONS.items() for city in cities]


def normalize_city_labels(values: list[str]) -> list[str]:
    city_lookup: dict[str, str] = {}
    province_short_names = {
        "北京市": "北京",
        "天津市": "天津",
        "河北省": "河北",
        "山西省": "山西",
        "内蒙古自治区": "内蒙古",
        "辽宁省": "辽宁",
        "吉林省": "吉林",
        "黑龙江省": "黑龙江",
        "上海市": "上海",
        "江苏省": "江苏",
        "浙江省": "浙江",
        "安徽省": "安徽",
        "福建省": "福建",
        "江西省": "江西",
        "山东省": "山东",
        "河南省": "河南",
        "湖北省": "湖北",
        "湖南省": "湖南",
        "广东省": "广东",
        "广西壮族自治区": "广西",
        "海南省": "海南",
        "重庆市": "重庆",
        "四川省": "四川",
        "贵州省": "贵州",
        "云南省": "云南",
        "西藏自治区": "西藏",
        "陕西省": "陕西",
        "甘肃省": "甘肃",
        "青海省": "青海",
        "宁夏回族自治区": "宁夏",
        "新疆维吾尔自治区": "新疆",
        "香港特别行政区": "香港",
        "澳门特别行政区": "澳门",
        "台湾省": "台湾",
    }
    for province, cities in PROVINCE_CITY_OPTIONS.items():
        aliases = {province, province_short_names.get(province, province)}
        for city in cities:
            label = city_label(province, city)
            city_lookup[label] = label
            city_lookup[city] = label
            city_lookup[city.removesuffix("市")] = label
            for alias in aliases:
                city_lookup[f"{alias}-{city}"] = label
                city_lookup[f"{alias}-{city.removesuffix('市')}"] = label
        for alias in aliases:
            city_lookup[alias] = city_label(province, cities[0])

    normalized = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        if item in city_lookup:
            normalized.append(city_lookup[item])
        elif "-" in item:
            normalized.append(city_lookup.get(item.split("-", 1)[1], item))
        else:
            normalized.append(item)
    return list(dict.fromkeys(normalized))


def selected_provinces_for_cities(city_values: list[str]) -> list[str]:
    provinces = []
    for value in city_values:
        province = value.split("-", 1)[0]
        if province in PROVINCE_CITY_OPTIONS:
            provinces.append(province)
    return list(dict.fromkeys(provinces))


def city_options_for_provinces(provinces: list[str]) -> list[str]:
    return [
        city_label(province, city)
        for province in provinces
        for city in PROVINCE_CITY_OPTIONS.get(province, [])
    ]


def uploaded_pdf_names(uploaded_files: list[Any] | None) -> list[str]:
    if not uploaded_files:
        return []
    return list(dict.fromkeys(file.name for file in uploaded_files if str(file.name).lower().endswith(".pdf")))


def format_user_context_for_prompt(context: dict[str, Any]) -> str:
    target_cities = "、".join(as_text_list(context.get("target_cities"))) or "未填写"
    target_directions = "、".join(as_text_list(context.get("target_directions"))) or "未填写"
    skill_tags = "、".join(as_text_list(context.get("skill_tags"))) or "未填写"
    resume_versions = "、".join(as_text_list(context.get("resume_versions"))) or "未填写"
    return "\n".join(
        [
            f"- 基本画像：{context.get('base_profile', '') or '未填写'}",
            f"- 目标城市：{target_cities}",
            f"- 到岗时间：{context.get('availability', '') or '未填写'}",
            f"- 可实习周期：{context.get('internship_duration', '') or '未填写'}",
            f"- 目标方向：{target_directions}",
            f"- 能力标签：{skill_tags}",
            f"- 简历版本/素材：{resume_versions}",
            f"- 求职约束与偏好：{context.get('constraints', '') or '未填写'}",
        ]
    )


def render_user_context_panel(prefix: str) -> None:
    context = st.session_state.user_context
    current_cities = normalize_city_labels(as_text_list(context.get("target_cities")))
    current_directions = as_text_list(context.get("target_directions"))
    current_skills = as_text_list(context.get("skill_tags"))
    current_resumes = as_text_list(context.get("resume_versions"))
    current_availability = str(context.get("availability") or "立即到岗")
    current_duration = str(context.get("internship_duration") or "6个月以上")
    summary = format_user_context_for_prompt(context).replace("\n", "<br>")

    st.markdown(
        f"""
        <div class="context-card">
          <strong>用户求职上下文</strong>
          <div class="muted">这块是 AI 改简历、岗位筛选和求职记录的统一输入。后续调用 AI 时会一并带入，避免每个岗位重复解释自己的背景和偏好。</div>
          <div class="muted" style="margin-top:8px;">{html.escape(summary).replace('&lt;br&gt;', '<br>')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    availability_options = merge_options(["立即到岗", "一周内", "两周内", "一个月内", "待沟通"], [current_availability])
    duration_options = merge_options(["3个月", "3-6个月", "6个月以上", "长期实习", "待沟通"], [current_duration])
    direction_options = merge_options(job_direction_options(), current_directions)
    selected_provinces = selected_provinces_for_cities(current_cities)

    base_profile = st.text_area(
        "基本画像",
        value=str(context.get("base_profile", "")),
        height=82,
        key=f"{prefix}_base_profile",
    )
    location_cols = st.columns([1, 2])
    target_provinces = location_cols[0].multiselect(
        "目标省份/地区",
        list(PROVINCE_CITY_OPTIONS.keys()),
        default=selected_provinces,
        key=f"{prefix}_target_provinces",
    )
    city_options = city_options_for_provinces(target_provinces)
    city_defaults = [city for city in current_cities if city in city_options]
    target_cities = location_cols[1].multiselect(
        "目标城市",
        city_options,
        default=city_defaults,
        key=f"{prefix}_target_cities",
    )

    row1 = st.columns(2)
    availability = row1[0].selectbox(
        "到岗时间",
        availability_options,
        index=availability_options.index(current_availability),
        key=f"{prefix}_availability",
    )
    internship_duration = row1[1].selectbox(
        "可实习周期",
        duration_options,
        index=duration_options.index(current_duration),
        key=f"{prefix}_duration",
    )
    target_directions = st.multiselect("目标方向", direction_options, default=current_directions, key=f"{prefix}_target_directions")

    st.markdown("**能力标签**")
    selected_skills = []
    skill_columns = st.columns(2)
    for idx, (group, options) in enumerate(ABILITY_TAG_GROUPS.items()):
        defaults = [skill for skill in current_skills if skill in options]
        with skill_columns[idx % 2]:
            selected_skills.extend(
                st.multiselect(
                    group,
                    options,
                    default=defaults,
                    key=f"{prefix}_skill_{group}",
                )
            )
    uncategorized_skills = [
        skill
        for skill in current_skills
        if all(skill not in options for options in ABILITY_TAG_GROUPS.values())
    ]
    extra_skills = st.text_input(
        "补充能力标签",
        value="、".join(uncategorized_skills),
        placeholder="每项用逗号、顿号或换行分隔",
        key=f"{prefix}_extra_skills",
    )

    uploaded_resumes = st.file_uploader(
        "上传简历版本 PDF（1-10个，仅读取文件名）",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"{prefix}_resume_pdfs",
    )
    uploaded_resume_names = uploaded_pdf_names(uploaded_resumes)
    resume_names = uploaded_resume_names or current_resumes
    if uploaded_resumes and not 1 <= len(uploaded_resumes) <= 10:
        st.error("请上传 1-10 个 PDF 简历文件。")
    if resume_names:
        st.markdown("".join(f'<span class="tag tag-green">{html.escape(name)}</span>' for name in resume_names), unsafe_allow_html=True)
    else:
        st.warning("请上传 1-10 个 PDF 简历文件，文件名会作为简历版本供投递记录选择。")

    constraints = st.text_area(
        "求职约束与偏好",
        value=str(context.get("constraints", "")),
        height=78,
        key=f"{prefix}_constraints",
    )
    if st.button("保存用户求职上下文", type="primary", key=f"{prefix}_save_user_context"):
        if uploaded_resumes and not 1 <= len(uploaded_resumes) <= 10:
            st.error("保存失败：请上传 1-10 个 PDF 简历文件。")
            return
        if not resume_names:
            st.error("保存失败：请至少上传 1 个 PDF 简历文件。")
            return
        st.session_state.user_context = {
            "base_profile": base_profile.strip(),
            "target_cities": target_cities,
            "availability": availability,
            "internship_duration": internship_duration,
            "target_directions": target_directions,
            "skill_tags": list(dict.fromkeys([*selected_skills, *normalize_lines(extra_skills)])),
            "resume_versions": resume_names,
            "constraints": constraints.strip(),
        }
        st.success("用户求职上下文已更新。")


def init_session_state() -> None:
    if "applications" not in st.session_state:
        st.session_state.applications = default_applications()
    for application in st.session_state.applications:
        if application.get("resume_version") in LEGACY_RESUME_VERSION_NAMES:
            application["resume_version"] = "未关联PDF简历"
    if "api_config" not in st.session_state:
        st.session_state.api_config = DEFAULT_API_CONFIG.copy()
    if "user_context" not in st.session_state:
        st.session_state.user_context = clone_default_user_context()
    else:
        context = st.session_state.user_context
        if "中国石油大学" in str(context.get("base_profile", "")):
            context["base_profile"] = DEFAULT_USER_CONTEXT["base_profile"]
        for key, value in DEFAULT_USER_CONTEXT.items():
            context.setdefault(key, value)
        context["target_cities"] = normalize_city_labels(as_text_list(context.get("target_cities")))
        if set(as_text_list(context.get("resume_versions"))).issubset(LEGACY_RESUME_VERSION_NAMES):
            context["resume_versions"] = []
    if "selected_application_id" not in st.session_state and st.session_state.applications:
        st.session_state.selected_application_id = st.session_state.applications[0]["id"]
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""
    if "generated_resume" not in st.session_state:
        st.session_state.generated_resume = ""
    if "jd_precheck" not in st.session_state:
        st.session_state.jd_precheck = {}


def get_application(app_id: str | None) -> dict[str, Any] | None:
    if not app_id:
        return None
    for app in st.session_state.applications:
        if app["id"] == app_id:
            return app
    return None


def update_application(app_id: str, updates: dict[str, Any]) -> None:
    for app in st.session_state.applications:
        if app["id"] == app_id:
            app.update(updates)
            app["updated_at"] = date.today().isoformat()
            return


def delete_application(app_id: str) -> None:
    st.session_state.applications = [app for app in st.session_state.applications if app["id"] != app_id]
    if st.session_state.get("selected_application_id") == app_id:
        st.session_state.selected_application_id = st.session_state.applications[0]["id"] if st.session_state.applications else None


def add_application(record: dict[str, Any]) -> None:
    record = dict(record)
    record["id"] = uuid.uuid4().hex[:12]
    record["updated_at"] = date.today().isoformat()
    record.setdefault("ai_resume_draft", "")
    st.session_state.applications.append(record)
    st.session_state.selected_application_id = record["id"]


def safe_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def days_until(value: str | None) -> int | None:
    deadline = safe_date(value)
    if deadline is None:
        return None
    return (deadline - date.today()).days


def app_label(app: dict[str, Any]) -> str:
    return f"{app.get('company', '')}｜{app.get('role', '')}"


def extract_keywords(text: str) -> list[str]:
    normalized = text.lower()
    found = []
    for keyword in KEYWORD_POOL:
        if keyword.lower() in normalized:
            found.append(keyword)
    return found


def keyword_coverage(jd_text: str, resume_text: str) -> dict[str, Any]:
    jd_keywords = extract_keywords(jd_text)
    resume_normalized = resume_text.lower()
    covered = [keyword for keyword in jd_keywords if keyword.lower() in resume_normalized]
    missing = [keyword for keyword in jd_keywords if keyword not in covered]
    score = round((len(covered) / len(jd_keywords)) * 100) if jd_keywords else 0
    return {"score": score, "keywords": jd_keywords, "covered": covered, "missing": missing}


def extract_text_from_upload(uploaded_file: Any) -> str:
    if uploaded_file is None:
        return ""
    data = uploaded_file.getvalue()
    name = uploaded_file.name.lower()
    if name.endswith(".docx"):
        return extract_docx_text(data)
    if name.endswith((".txt", ".md")):
        for encoding in ("utf-8", "gbk", "utf-16"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")
    return ""


def extract_docx_text(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as docx:
        xml_bytes = docx.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        if parts:
            paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


def build_resume_prompt(
    application: dict[str, Any],
    jd_text: str,
    resume_text: str,
    focus: str,
    output_language: str,
    page_length: str,
    user_context: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你是一名严谨的求职简历优化顾问，擅长产品经理、数据产品、商业分析和AI产品岗位。"
        "必须基于用户提供的简历事实改写，不得编造学校、公司、奖项、实习或量化结果。"
        "如果缺少证据，请用“需要补充证据：...”标注。输出要适合直接复制到简历。"
    )
    context_text = format_user_context_for_prompt(user_context)
    user = f"""
请根据目标岗位JD和原始简历，生成岗位定制版简历改写建议。

【用户求职上下文】
{context_text}

【目标岗位记录】
公司：{application.get("company", "")}
岗位：{application.get("role", "")}
方向：{application.get("direction", "")}
优先级：{application.get("priority", "")}

【JD】
{jd_text}

【原始简历】
{resume_text}

【改写要求】
- 输出语言：{output_language}
- 目标篇幅：{page_length}
- 强调能力：{focus}
- 保留真实经历，不要编造事实。
- 优先强化：岗位关键词覆盖、项目结果、产品判断、数据指标、可面试追问的细节。

请按以下结构输出：
1. 岗位匹配诊断：给出0-100分和3条理由
2. JD关键词与简历缺口
3. 可直接替换的项目经历表述：至少3条STAR/项目型bullet
4. 简历摘要/个人优势：3-4行
5. 面试追问准备：5个可能问题
6. 需要用户补充的信息：如缺少量化结果、技术细节、业务结果等
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_chat_completion(config: dict[str, Any], messages: list[dict[str, str]]) -> str:
    api_key = str(config.get("api_key", "")).strip()
    base_url = str(config.get("base_url", "")).strip().rstrip("/")
    model = str(config.get("model", "")).strip()
    if not api_key:
        raise ValueError("请先在 API 配置中填写 API Key。")
    if not base_url:
        raise ValueError("请先填写 Base URL。")
    if not model:
        raise ValueError("请先填写模型名。")

    endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(config.get("temperature", 0.35)),
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=int(config.get("timeout", 60))) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API 请求失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"API 连接失败：{exc.reason}") from exc

    data = json.loads(raw)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"API 返回格式无法解析：{raw[:500]}") from exc


def local_resume_suggestion(
    application: dict[str, Any],
    jd_text: str,
    resume_text: str,
    focus: str,
    user_context: dict[str, Any],
) -> str:
    coverage = keyword_coverage(jd_text, resume_text)
    missing = "、".join(coverage["missing"]) or "暂无明显缺口"
    keywords = "、".join(coverage["keywords"]) or "未识别到关键词"
    company = application.get("company", "目标公司")
    role = application.get("role", "目标岗位")
    context_text = format_user_context_for_prompt(user_context)
    return f"""## 本地规则预览：{company}｜{role}

### 0. 用户求职上下文
{context_text}

### 1. 岗位匹配诊断
- JD关键词覆盖评分：{coverage["score"]}/100
- 已识别JD关键词：{keywords}
- 简历待补关键词：{missing}

### 2. 可优先强化的简历方向
- 把“做了一个系统/看板”改成“围绕{role}场景，定义用户问题、拆解需求、设计功能闭环并验证结果”。
- 如果强调能力是“{focus}”，建议把项目经历排序为：职途智析 → GrowthLens → 与JD最相关的数据/AI/产品项目。
- 每条项目经历尽量补齐：目标用户、问题、方案、关键功能、指标或结果、你的角色。

### 3. 可直接改写的项目表述草稿
- 基于岗位-技能-课程图谱设计「职途智析」职业路径推荐工具，支持目标岗位输入、技能缺口诊断、课程/项目推荐和面试问题生成，提升求职准备的可执行性。
- 将静态分析项目产品化为可在线体验的 Streamlit MVP，抽象统一分析接口并预留真实图谱、NER技能抽取和薪资预测模型接入，保证 demo 可演示且后端可扩展。
- 围绕电商增长复盘场景搭建 GrowthLens 分析工具，覆盖 KPI、RFM、cohort 留存、漏斗和 A/B 实验分析，输出可导出的运营策略建议。

### 4. 需要补充证据
- 是否有真实用户反馈、访谈、同学试用或老师建议。
- 是否有量化结果，例如覆盖岗位数、技能标签数、项目推荐数、分析耗时下降。
- 是否有上线链接、截图、GitHub、作品集PDF，建议在简历中保留。
"""


def radar_chart(target_job: str, user_skills: list[str], result: dict) -> go.Figure:
    missing = {item["skill"] for item in result["skill_gap"]}
    labels = [item["skill"] for item in result["skill_gap"][:8]]
    if not labels:
        labels = user_skills[:8] or ["SQL", "Python", "Excel", "业务理解"]
    target_values = [1.0 for _ in labels]
    user_values = [0.0 if skill in missing else 1.0 for skill in labels]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=target_values + [target_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="岗位要求",
            line_color=BRAND_BLUE,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=user_values + [user_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="当前技能",
            line_color=BRAND_ORANGE,
        )
    )
    fig.update_layout(
        title=f"{target_job} 技能匹配雷达图",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
        height=420,
    )
    return fig


def salary_chart(salary_range: dict) -> go.Figure:
    salary_df = pd.DataFrame(
        {
            "type": ["min", "median", "max"],
            "salary": [salary_range["min"], salary_range["median"], salary_range["max"]],
        }
    )
    fig = px.bar(
        salary_df,
        x="type",
        y="salary",
        color="type",
        title="薪资预期区间",
        color_discrete_sequence=[BRAND_BLUE, BRAND_ORANGE, "#5c7c99"],
    )
    fig.update_layout(showlegend=False, height=360, yaxis_title="CNY / month", xaxis_title="")
    return fig


def render_profile(profile: dict) -> None:
    outputs = join_text(profile.get("outputs", []), "岗位分析、项目复盘、业务汇报")
    st.markdown(
        f"""
        <div class="info-card">
          <strong>{html.escape(profile.get('job_title', '目标岗位'))}</strong>
          <div class="muted">{html.escape(profile.get('industry', ''))} · {html.escape(profile.get('path', ''))}</div>
          <p>{html.escape(profile.get('positioning', ''))}</p>
          <div class="muted">常见产出：{html.escape(outputs)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_github_projects(projects: list[dict]) -> None:
    if not projects:
        st.info("暂未匹配到 GitHub 参考项目。")
        return
    st.caption("以下均为公开 GitHub 项目，用于学习、对标、扩展项目思路和面试追问准备。")
    for project in projects:
        tags = "".join(f'<span class="tag">{html.escape(skill)}</span>' for skill in project.get("skills", [])[:10])
        link = ""
        if project.get("github_url"):
            link = f'<div class="link-line"><a href="{html.escape(project["github_url"])}" target="_blank">GitHub</a></div>'
        st.markdown(
            f"""
            <div class="project-card">
              <strong>{html.escape(project['title'])}</strong>
              <div class="muted">匹配度：{project['match_score']:.0%} · {html.escape(project.get('match_reason', ''))}</div>
              <p>{html.escape(project.get('summary', ''))}</p>
              <div>{tags}</div>
              <p><strong>参考价值：</strong>{html.escape(project.get('why_to_read', ''))}</p>
              {link}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_courses(courses: list[dict]) -> None:
    if not courses:
        st.info("当前技能差距较少，暂不需要课程推荐。")
        return
    for course in courses:
        skills = join_text(course.get("skill_covered", []), "相关技能")
        keywords = join_text(course.get("keywords", []), "按课程大纲补充")
        suitable_jobs = join_text(course.get("suitable_jobs", []), "相关岗位")
        st.markdown(
            f"""
            <div class="course-card">
              <strong>{html.escape(course.get('name', '课程'))}</strong><br>
              平台/资料：{html.escape(course.get('platform', ''))}<br>
              覆盖技能：{html.escape(skills)}<br>
              关键词：{html.escape(keywords)}<br>
              学习目标：{html.escape(course.get('goal', ''))}<br>
              可产出：{html.escape(course.get('deliverable', ''))}<br>
              适合岗位：{html.escape(suitable_jobs)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_similar_jobs(jobs: list[dict]) -> None:
    if not jobs:
        st.info("暂未找到相似岗位。")
        return
    cols = st.columns(min(4, len(jobs)))
    for idx, job in enumerate(jobs[:12]):
        with cols[idx % len(cols)]:
            st.markdown(
                f"""
                <div class="job-card">
                  <strong>{html.escape(job['job_title'])}</strong><br>
                  匹配度：{job['match_score']:.0%}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_text_cards(title: str, items: list[str]) -> None:
    st.subheader(title)
    if not items:
        st.info("暂无内容。")
        return
    for item in items:
        st.markdown(f'<div class="question-card">{html.escape(item)}</div>', unsafe_allow_html=True)


def render_catalog_preview() -> None:
    jobs = available_jobs()
    skills = available_skills()
    stat_cols = st.columns(2)
    stat_cols[0].metric("岗位样例", len(jobs))
    stat_cols[1].metric("技能标签", len(skills))

    st.markdown("可选岗位示例：")
    job_df = pd.DataFrame({"岗位": jobs})
    st.dataframe(job_df, use_container_width=True, height=380)


def render_career_analysis_workspace() -> None:
    left, right = st.columns([1, 2])
    with left:
        st.subheader("输入信息")
        job_options = available_jobs()
        target_job = st.selectbox("目标岗位", options=job_options, index=0)
        custom_job = st.text_input("自定义岗位", placeholder='如"战略分析实习"')
        if custom_job.strip():
            target_job = custom_job.strip()

        skill_pool = available_skills()
        default_skills = [skill for skill in ["Python", "Excel"] if skill in skill_pool]
        selected_skills = st.multiselect("当前技能", options=skill_pool, default=default_skills, placeholder="搜索并选择技能")
        extra_skills = st.text_input("补充技能（逗号分隔）", placeholder="如 Wind, PPT")
        if extra_skills:
            selected_skills = selected_skills + [skill.strip() for skill in extra_skills.replace("，", ",").split(",") if skill.strip()]
        st.caption("第一版默认使用扩展演示数据；配置 Neo4j secrets 后可切换真实后端。")
        submitted = st.button("开始分析", type="primary", use_container_width=True)

    with right:
        if not submitted:
            st.info("选择目标岗位和当前技能后，点击开始分析。")
            render_catalog_preview()
            return

        if not target_job.strip():
            st.warning("请输入目标岗位。")
            return

        with st.spinner("正在分析技能差距、薪资区间、课程、GitHub项目和面试问题..."):
            result = ensure_result_schema(analyze_career(target_job, selected_skills, read_neo4j_config()))

        mode_label = "真实后端模式" if result["mode"] == "neo4j" else "扩展演示数据模式"
        st.markdown(f'<div class="mode-badge">{mode_label}</div>', unsafe_allow_html=True)

        if result["salary_range"]["median"] == 0 and not result["skill_gap"]:
            st.warning("暂未找到该岗位，请尝试输入：数据分析师、商业分析师、产品经理、证券研究员、投行分析师、增长运营。")
            return

        render_profile(result["target_job_profile"])

        metric_cols = st.columns(4)
        metric_cols[0].metric("缺口技能", len(result["skill_gap"]))
        metric_cols[1].metric("薪资中位数", f"{result['salary_range']['median']:,} 元/月")
        metric_cols[2].metric("相似岗位", len(result["similar_jobs"]))
        metric_cols[3].metric("GitHub项目", len(result["reference_projects"]))

        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.plotly_chart(radar_chart(target_job, selected_skills, result), use_container_width=True)
        with chart_cols[1]:
            st.plotly_chart(salary_chart(result["salary_range"]), use_container_width=True)

        st.subheader("技能差距")
        gap_df = pd.DataFrame(result["skill_gap"])
        if gap_df.empty:
            st.success("当前技能已经覆盖该岗位的核心要求。")
        else:
            st.dataframe(gap_df, use_container_width=True)

        tab_github, tab_courses, tab_jobs, tab_interview = st.tabs(["GitHub项目", "推荐课程", "相似岗位", "面试准备"])
        with tab_github:
            render_github_projects(result["reference_projects"])
        with tab_courses:
            render_courses(result["recommended_courses"])
        with tab_jobs:
            render_similar_jobs(result["similar_jobs"])
        with tab_interview:
            render_text_cards("可能被追问的问题", result["interview_questions"])
            render_text_cards("学习与补强路径", result["learning_plan"])


def application_stats(applications: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(applications)
    interview_count = sum(1 for app in applications if app["status"] in {"笔试/面试", "已拿 Offer"})
    submitted_count = sum(1 for app in applications if app["status"] not in {"已收藏", "准备中"})
    offer_count = sum(1 for app in applications if app["status"] == "已拿 Offer")
    pending_count = sum(1 for app in applications if app["status"] not in {"已拿 Offer", "已拒绝/归档"})
    week_deadline = 0
    for app in applications:
        remaining = days_until(app.get("deadline"))
        if remaining is not None and 0 <= remaining <= 7:
            week_deadline += 1
    return {
        "total": total,
        "interview_rate": interview_count / max(submitted_count, 1),
        "offer_count": offer_count,
        "pending_count": pending_count,
        "week_deadline": week_deadline,
    }


def filtered_applications() -> list[dict[str, Any]]:
    applications = st.session_state.applications
    cols = st.columns([1.4, 1, 1, 1])
    search = cols[0].text_input("搜索", placeholder="公司、岗位、方向、备注...")
    direction_keyword = cols[1].text_input("方向关键词", placeholder="AI、产品、运营...")
    status = cols[2].selectbox("状态", ["全部进度"] + APPLICATION_STATUSES)
    priority = cols[3].selectbox("优先级", ["全部优先级"] + PRIORITIES)

    def matched(app: dict[str, Any]) -> bool:
        haystack = " ".join(
            str(app.get(key, ""))
            for key in ("company", "role", "direction", "status", "priority", "next_action", "notes", "jd")
        ).lower()
        direction_text = str(app.get("direction", "")).lower()
        return (
            (not search or search.lower() in haystack)
            and (not direction_keyword or direction_keyword.lower() in direction_text)
            and (status == "全部进度" or app.get("status") == status)
            and (priority == "全部优先级" or app.get("priority") == priority)
        )

    return [app for app in applications if matched(app)]


def render_application_summary(applications: list[dict[str, Any]]) -> None:
    stats = application_stats(st.session_state.applications)
    metric_cols = st.columns(5)
    metric_cols[0].metric("总投递", stats["total"])
    metric_cols[1].metric("面试转化率", f"{stats['interview_rate']:.0%}")
    metric_cols[2].metric("已拿 Offer", stats["offer_count"])
    metric_cols[3].metric("待跟进", stats["pending_count"])
    metric_cols[4].metric("本周截止", stats["week_deadline"])

    status_counts = pd.DataFrame(
        {"status": APPLICATION_STATUSES, "count": [sum(1 for app in st.session_state.applications if app["status"] == status) for status in APPLICATION_STATUSES]}
    )
    direction_counts = (
        pd.DataFrame(st.session_state.applications)
        .groupby("direction")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=True)
        if st.session_state.applications
        else pd.DataFrame({"direction": [], "count": []})
    )
    chart_cols = st.columns([1.2, 1])
    with chart_cols[0]:
        fig = px.bar(
            status_counts,
            x="count",
            y="status",
            orientation="h",
            color="status",
            color_discrete_map=STATUS_COLORS,
            title="进度分布",
        )
        fig.update_layout(showlegend=False, height=280, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with chart_cols[1]:
        fig = px.bar(direction_counts, x="count", y="direction", orientation="h", title="方向分布", color_discrete_sequence=[BRAND_BLUE])
        fig.update_layout(height=280, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    if applications and len(applications) != len(st.session_state.applications):
        st.caption(f"当前筛选结果：{len(applications)} 条。")


def render_add_application_form() -> None:
    resume_version_options = as_text_list(st.session_state.user_context.get("resume_versions"))
    direction_options = job_direction_options()
    with st.expander("新增投递记录", expanded=False):
        if not resume_version_options:
            st.warning("请先在上方用户求职上下文上传 1-10 个 PDF 简历文件，再选择关联简历版本。")
        with st.form("add_application_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            company = col1.text_input("公司名称 *")
            role = col2.text_input("岗位名称 *")
            direction = col3.selectbox("岗位方向", direction_options, index=direction_options.index("产品-AI产品经理") if "产品-AI产品经理" in direction_options else 0)
            col4, col5, col6 = st.columns(3)
            status = col4.selectbox("当前状态", APPLICATION_STATUSES, index=1)
            priority = col5.selectbox("优先级", PRIORITIES, index=1)
            resume_version = col6.selectbox(
                "关联简历版本",
                resume_version_options or ["请先上传PDF简历"],
                disabled=not bool(resume_version_options),
            )
            col7, col8 = st.columns(2)
            apply_date = col7.date_input("投递/创建日期", value=date.today())
            deadline = col8.date_input("截止/跟进日期", value=date.today())
            next_action = st.selectbox("下一步行动", NEXT_ACTION_OPTIONS)
            jd = st.text_area("岗位JD", height=110)
            notes = st.text_area("备注", height=80)
            submitted = st.form_submit_button("保存记录", type="primary")
            if submitted:
                if not company.strip() or not role.strip():
                    st.error("公司名称和岗位名称为必填。")
                elif not resume_version_options:
                    st.error("请先上传 1-10 个 PDF 简历文件，并保存用户求职上下文。")
                else:
                    add_application(
                        {
                            "company": company.strip(),
                            "role": role.strip(),
                            "direction": direction,
                            "status": status,
                            "priority": priority,
                            "apply_date": apply_date.isoformat(),
                            "deadline": deadline.isoformat(),
                            "next_action": next_action,
                            "resume_version": resume_version,
                            "jd": jd.strip(),
                            "notes": notes.strip(),
                        }
                    )
                    st.success("已新增投递记录。")
                    time.sleep(0.3)
                    rerun()


def render_import_export() -> None:
    with st.expander("导入 / 导出求职记录", expanded=False):
        export_json = json.dumps(st.session_state.applications, ensure_ascii=False, indent=2)
        st.download_button("下载求职记录 JSON", export_json, file_name="zhituzhixi_applications.json", mime="application/json")
        uploaded = st.file_uploader("导入 JSON", type=["json"], key="applications_import")
        if uploaded and st.button("确认导入并覆盖当前记录"):
            try:
                imported = json.loads(uploaded.getvalue().decode("utf-8"))
                if not isinstance(imported, list):
                    raise ValueError("JSON 顶层必须是列表。")
                for item in imported:
                    item.setdefault("id", uuid.uuid4().hex[:12])
                    item.setdefault("status", "准备中")
                    item.setdefault("priority", "中")
                    item.setdefault("ai_resume_draft", "")
                st.session_state.applications = imported
                st.session_state.selected_application_id = imported[0]["id"] if imported else None
                st.success("导入成功。")
                time.sleep(0.3)
                rerun()
            except Exception as exc:
                st.error(f"导入失败：{exc}")


def render_application_card(app: dict[str, Any]) -> None:
    remaining = days_until(app.get("deadline"))
    deadline_text = "未设置截止"
    if remaining is not None:
        deadline_text = f"{'逾期' if remaining < 0 else '还剩'} {abs(remaining)} 天"
    tags = "".join(
        [
            f'<span class="tag">{html.escape(app.get("direction", ""))}</span>',
            f'<span class="tag tag-orange">{html.escape(app.get("priority", ""))}</span>',
        ]
    )
    st.markdown(
        f"""
        <div class="tracker-card">
          <strong>{html.escape(app.get('company', ''))}</strong>
          <div class="muted">{html.escape(app.get('role', ''))}</div>
          <div>{tags}</div>
          <div class="muted">投递：{html.escape(str(app.get('apply_date', '')))} · {html.escape(deadline_text)}</div>
          <div class="muted"><strong>下一步：</strong>{html.escape(app.get('next_action', ''))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    button_cols = st.columns(3)
    if button_cols[0].button("用于AI", key=f"use_ai_{app['id']}", use_container_width=True):
        st.session_state.selected_application_id = app["id"]
        st.success("已加载到 AI 改简历工作台。")
    if button_cols[1].button("下一阶段", key=f"next_{app['id']}", use_container_width=True):
        current_idx = APPLICATION_STATUSES.index(app["status"])
        next_status = APPLICATION_STATUSES[min(current_idx + 1, len(APPLICATION_STATUSES) - 1)]
        update_application(app["id"], {"status": next_status})
        rerun()
    if button_cols[2].button("删除", key=f"delete_{app['id']}", use_container_width=True):
        delete_application(app["id"])
        rerun()


def render_kanban(applications: list[dict[str, Any]]) -> None:
    columns = st.columns(len(APPLICATION_STATUSES))
    for idx, status in enumerate(APPLICATION_STATUSES):
        apps = [app for app in applications if app["status"] == status]
        with columns[idx]:
            st.markdown(f"**{status}** `{len(apps)}`")
            for app in apps:
                render_application_card(app)
            if not apps:
                st.caption("暂无记录")


def render_applications_workspace() -> None:
    st.subheader("求职记录看板")
    st.caption("记录投递状态、下一步行动、关联简历版本，并可把岗位直接发送到 AI 改简历工作台。当前版本使用浏览器会话状态，支持 JSON 导入导出。")
    render_user_context_panel("tracker")
    render_add_application_form()
    render_import_export()
    applications = filtered_applications()
    render_application_summary(applications)
    render_kanban(applications)


def render_api_config_form(prefix: str = "main") -> None:
    config = st.session_state.api_config
    with st.form(f"{prefix}_api_config_form"):
        provider = st.text_input("Provider", value=config.get("provider", "OpenAI-compatible"))
        base_url = st.text_input("Base URL", value=config.get("base_url", "https://api.openai.com/v1"))
        api_key = st.text_input("API Key", value=config.get("api_key", ""), type="password")
        model = st.text_input("Model", value=config.get("model", "gpt-4.1-mini"))
        col1, col2 = st.columns(2)
        temperature = col1.slider("Temperature", min_value=0.0, max_value=1.0, value=float(config.get("temperature", 0.35)), step=0.05)
        timeout = col2.number_input("Timeout 秒", min_value=10, max_value=180, value=int(config.get("timeout", 60)), step=5)
        saved = st.form_submit_button("保存到当前会话", type="primary")
        if saved:
            st.session_state.api_config = {
                "provider": provider.strip() or "OpenAI-compatible",
                "base_url": base_url.strip(),
                "api_key": api_key.strip(),
                "model": model.strip(),
                "temperature": float(temperature),
                "timeout": int(timeout),
            }
            st.success("API 配置已保存到当前会话。")


def render_api_workspace() -> None:
    st.subheader("API配置")
    st.markdown(
        """
        <div class="api-card">
          <strong>安全边界</strong>
          <div class="muted">API Key 只保存在当前 Streamlit 会话状态里，不写入仓库文件。刷新或重启后可能需要重新填写。Base URL 支持 OpenAI-compatible 的 /chat/completions 接口。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_api_config_form("api_page")
    config = st.session_state.api_config
    is_ready = bool(config.get("api_key") and config.get("base_url") and config.get("model"))
    st.write("当前状态：", "已配置，可调用" if is_ready else "待配置")
    if st.button("测试连接", disabled=not is_ready):
        try:
            result = call_chat_completion(
                config,
                [
                    {"role": "system", "content": "你只需要回复 OK。"},
                    {"role": "user", "content": "请回复 OK，确认接口可用。"},
                ],
            )
            st.success(f"连接成功：{result[:200]}")
        except Exception as exc:
            st.error(str(exc))


def render_precheck(coverage: dict[str, Any]) -> None:
    cols = st.columns(3)
    cols[0].markdown(f'<div class="score-box"><strong>{coverage["score"]}</strong><span>JD匹配</span></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="score-box"><strong>{len(coverage["covered"])}</strong><span>已覆盖关键词</span></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="score-box"><strong>{len(coverage["missing"])}</strong><span>待补关键词</span></div>', unsafe_allow_html=True)
    st.markdown("**已识别JD关键词**")
    if coverage["keywords"]:
        st.markdown("".join(f'<span class="tag">{html.escape(item)}</span>' for item in coverage["keywords"]), unsafe_allow_html=True)
    else:
        st.caption("暂未识别到关键词。")
    st.markdown("**简历待补关键词**")
    if coverage["missing"]:
        st.markdown("".join(f'<span class="tag tag-orange">{html.escape(item)}</span>' for item in coverage["missing"]), unsafe_allow_html=True)
    else:
        st.success("当前简历覆盖了识别到的JD关键词。")


def render_ai_resume_workspace() -> None:
    st.subheader("AI改简历工作台")
    st.caption("从求职记录读取 JD，也可以手动粘贴。API Key 由用户自行填写；你可以先用本地规则预览，不调用外部接口。")
    if not st.session_state.applications:
        st.info("请先在求职记录里新增一个岗位。")
        return

    app_options = {app_label(app): app["id"] for app in st.session_state.applications}
    current_app = get_application(st.session_state.get("selected_application_id")) or st.session_state.applications[0]
    current_label = app_label(current_app)
    selected_label = st.selectbox("选择投递记录", list(app_options.keys()), index=list(app_options.keys()).index(current_label) if current_label in app_options else 0)
    st.session_state.selected_application_id = app_options[selected_label]
    application = get_application(st.session_state.selected_application_id) or current_app

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 步骤1：岗位JD")
        st.write(f"**{application.get('company')}｜{application.get('role')}**")
        jd_text = st.text_area("岗位JD", value=application.get("jd", ""), height=190, key=f"jd_{application['id']}")
        col1, col2 = st.columns(2)
        update_jd = col1.button("回写JD到记录", use_container_width=True)
        if update_jd:
            update_application(application["id"], {"jd": jd_text})
            st.success("已回写JD。")
        if col2.button("预检查JD关键词", use_container_width=True):
            st.session_state.jd_precheck = keyword_coverage(jd_text, st.session_state.resume_text)

        st.markdown("#### 步骤2：简历输入")
        uploaded_resume = st.file_uploader("上传简历（支持 docx/txt/md）", type=["docx", "txt", "md"])
        if uploaded_resume is not None:
            try:
                st.session_state.resume_text = extract_text_from_upload(uploaded_resume)
                st.success(f"已读取：{uploaded_resume.name}")
            except Exception as exc:
                st.error(f"读取失败：{exc}")
        resume_text = st.text_area("简历文本", value=st.session_state.resume_text, height=260, key="resume_text_area")
        st.session_state.resume_text = resume_text

    with right:
        st.markdown("#### 步骤3：改写配置")
        col1, col2 = st.columns(2)
        output_language = col1.selectbox("输出语言", ["中文", "英文", "中英双语"])
        page_length = col2.selectbox("目标篇幅", ["一页", "两页", "只输出项目段落"])
        focus = st.multiselect(
            "强调能力",
            ["产品/数据/AI", "商业分析", "策略运营", "用户研究", "增长实验", "项目管理", "金融科技"],
            default=["产品/数据/AI"],
        )
        focus_text = "、".join(focus)

        coverage = keyword_coverage(jd_text, resume_text)
        render_precheck(coverage)

        with st.expander("API配置（当前会话）", expanded=not bool(st.session_state.api_config.get("api_key"))):
            render_api_config_form("ai_inline")

        action_cols = st.columns(2)
        if action_cols[0].button("生成本地预览建议", use_container_width=True):
            st.session_state.generated_resume = local_resume_suggestion(application, jd_text, resume_text, focus_text, st.session_state.user_context)
        if action_cols[1].button("调用AI生成岗位版简历", type="primary", use_container_width=True):
            if not resume_text.strip():
                st.error("请先上传或粘贴简历文本。")
            elif not jd_text.strip():
                st.error("请先填写岗位JD。")
            else:
                try:
                    with st.spinner("正在调用 AI 生成改写建议..."):
                        messages = build_resume_prompt(
                            application,
                            jd_text,
                            resume_text,
                            focus_text,
                            output_language,
                            page_length,
                            st.session_state.user_context,
                        )
                        st.session_state.generated_resume = call_chat_completion(st.session_state.api_config, messages)
                    st.success("AI改写完成。")
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("#### 步骤4：AI输出与人工确认")
    generated = st.text_area("改写结果", value=st.session_state.generated_resume, height=360)
    st.session_state.generated_resume = generated
    col1, col2, col3 = st.columns(3)
    col1.download_button("下载 Markdown", generated, file_name=f"{application.get('company', 'company')}_{application.get('role', 'role')}_resume_draft.md", mime="text/markdown", use_container_width=True)
    if col2.button("保存到该岗位记录", use_container_width=True, disabled=not bool(generated.strip())):
        update_application(
            application["id"],
            {
                "ai_resume_draft": generated,
                "resume_version": f"{application.get('company', '')}-{application.get('role', '')}-岗位版",
                "next_action": "人工校对AI改写并投递",
            },
        )
        st.success("已保存到该岗位记录。")
    if col3.button("清空输出", use_container_width=True):
        st.session_state.generated_resume = ""
        rerun()


def main() -> None:
    st.set_page_config(page_title="职途智析", layout="wide")
    init_session_state()
    inject_css()
    st.markdown(
        """
        <div class="product-header">
          <h1>职途智析</h1>
          <p>职业定位、求职记录、AI简历改写和面试准备的一体化求职工作台</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_analysis, tab_tracker, tab_resume, tab_api = st.tabs(["岗位分析", "求职记录", "AI改简历", "API配置"])
    with tab_analysis:
        render_career_analysis_workspace()
    with tab_tracker:
        render_applications_workspace()
    with tab_resume:
        render_ai_resume_workspace()
    with tab_api:
        render_api_workspace()


if __name__ == "__main__":
    main()
