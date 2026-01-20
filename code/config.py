"""
配置文件
所有路径、参数等配置集中管理
"""

import os

# ==================== 路径配置 ====================

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, "data")

# 代码目录
CODE_DIR = os.path.join(BASE_DIR, "code")

# 日志目录
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 确保必要目录存在
for directory in [DATA_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)


# ==================== 数据爬取配置 ====================

# 爬取间隔（秒）
FETCH_INTERVAL = 1

# HTTP请求配置
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

HTTP_TIMEOUT = 30

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2


# ==================== 数据处理配置 ====================

# 日期格式
DATE_FORMAT = "%Y-%m-%d"

# 插值方法
INTERPOLATION_METHOD = "linear"  # linear, cubic, quadratic

# 数据起始和结束年份
START_YEAR = 2008
END_YEAR = 2025

# 推荐分析时间范围
RECOMMENDED_START = "2008-01-01"
RECOMMENDED_END = "2025-12-31"


# ==================== Stata配置 ====================

# Stata版本
STATA_VERSION = 117  # Stata 14/15

# DTA文件编码
DTA_ENCODING = "utf-8"


# ==================== 列名映射配置 ====================

# 中文列名到英文的映射
COLUMN_MAPPING = {
    # 时间相关
    'date': 'date',
    '月份': 'month',
    '季度': 'quarter',
    '年份': 'year',

    # CPI相关
    '全国-当月': 'cpi_national',
    '全国-同比增长': 'cpi_national_yoy',
    '全国-环比增长': 'cpi_national_mom',
    '全国-累计': 'cpi_national_cum',
    '城市-当月': 'cpi_urban',
    '城市-同比增长': 'cpi_urban_yoy',
    '农村-当月': 'cpi_rural',
    '农村-同比增长': 'cpi_rural_yoy',

    # PPI相关
    '当月': 'ppi_current',
    '当月同比增长': 'ppi_yoy',
    '累计': 'ppi_cum',

    # GDP相关
    '国内生产总值-绝对值': 'gdp_value',
    '国内生产总值-同比增长': 'gdp_yoy',
    '第一产业-绝对值': 'gdp_primary_value',
    '第一产业-同比增长': 'gdp_primary_yoy',
    '第二产业-绝对值': 'gdp_secondary_value',
    '第二产业-同比增长': 'gdp_secondary_yoy',
    '第三产业-绝对值': 'gdp_tertiary_value',
    '第三产业-同比增长': 'gdp_tertiary_yoy',

    # PMI相关
    '制造业-指数': 'pmi_mfg',
    '制造业-同比增长': 'pmi_mfg_yoy',

    # 国债利差相关（10年期-2年期）
    'spread': 'inf_exp',
    'rate_10y': 'bond_10y',
    'rate_2y': 'bond_2y',
}


# ==================== 文件名配置 ====================

# 输出文件名
OUTPUT_FILES = {
    'unified_monthly': '统一月度数据集.csv',
    'gdp_monthly': 'GDP_月度.csv',
}

# 原始文件列表
ORIGIN_DATE_FILES = [
    'CPI_原始数据.csv',
    'PPI_原始数据.csv',
    'PMI_原始数据.csv',
    'GDP_原始数据.csv',
    '新增贷款_原始数据.csv',
    '国债利差_原始数据.csv',
]

# 标准日期文件列表
STANDARD_DATE_FILES = [
    'CPI_标准日期.csv',
    'PPI_标准日期.csv',
    'PMI_标准日期.csv',
    'GDP_标准日期.csv',
    '新增贷款_标准日期.csv',
    '国债利差_标准日期.csv',
]

# 日度数据文件列表（需要聚合到月度）
DAILY_FILES = [
    '国债利差_标准日期.csv',
]


# ==================== 日志配置 ====================

# 日志级别
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 日志文件
LOG_FILE = os.path.join(LOG_DIR, 'data_processing.log')


# ==================== 显示配置 ====================

# 是否显示详细信息
VERBOSE = True

# 是否显示进度条
SHOW_PROGRESS = True

# 表格显示宽度
TABLE_WIDTH = 80


# ==================== 数据源URL配置 ====================

# 国家统计局
STATS_GOV_URL = "https://data.stats.gov.cn/easyquery.htm"

# 央行
PBC_URL = "http://www.pbc.gov.cn/diaochatongjisi/116219/116227/index.html"

# AKShare文档
AKSHARE_DOC_URL = "https://akshare.akfamily.xyz/"


# ==================== 功能开关 ====================

# 是否启用缓存
ENABLE_CACHE = True

# 是否自动备份
AUTO_BACKUP = True

# 是否生成报告
GENERATE_REPORT = True

# 是否检查数据质量
CHECK_DATA_QUALITY = True
