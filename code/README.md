# 时间序列数据处理工具

统一的Python数据处理工具，用于SVAR模型数据准备。

## 📁 项目结构

```
code/
├── main.py                 # 主程序入口 ⭐
├── config.py              # 配置文件
├── utils.py               # 工具函数
├── modules/               # 功能模块
│   ├── __init__.py
│   ├── data_fetcher.py         # 数据爬取
│   ├── date_processor.py       # 日期格式处理
│   ├── frequency_converter.py  # 频率转换
│   └── format_converter.py     # 格式转换
└── README.md              # 本文件
```

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy akshare openpyxl
```

### 基本使用

```bash
# 1. 查看帮助
python main.py --help

# 2. 执行完整流程（推荐）
python main.py --all

# 3. 查看生成的文件
python main.py --list

# 4. 生成数据质量报告
python main.py --report
```

## 📖 详细说明

### 命令行选项

#### 功能选项

| 选项              | 说明       | 示例                             |
| --------------- | -------- | ------------------------------ |
| `--all`         | 执行所有步骤   | `python main.py --all`         |
| `--fetch`       | 爬取原始数据   | `python main.py --fetch`       |
| `--unify-date`  | 统一日期格式   | `python main.py --unify-date`  |
| `--interpolate` | 插值为月度    | `python main.py --interpolate` |
| `--to-dta`      | 转换为DTA格式 | `python main.py --to-dta`      |
| `--list`        | 列出数据文件   | `python main.py --list`        |
| `--report`      | 生成质量报告   | `python main.py --report`      |

#### 高级选项

| 选项                   | 说明     | 示例                                                            |
| -------------------- | ------ | ------------------------------------------------------------- |
| `--fetch-categories` | 指定爬取类别 | `python main.py --fetch --fetch-categories macro expectation` |
| `--files`            | 指定处理文件 | `python main.py --unify-date --files CPI.csv PPI.csv`         |

#### 通用选项

| 选项              | 说明   | 示例                                       |
| --------------- | ---- | ---------------------------------------- |
| `-v, --verbose` | 详细输出 | `python main.py --all -v`                |
| `-q, --quiet`   | 静默模式 | `python main.py --all -q`                |
| `--log-level`   | 日志级别 | `python main.py --all --log-level DEBUG` |

### 使用场景

#### 场景1：首次使用（完整流程）

```bash
# 执行所有步骤：爬取 → 日期统一 → 插值 → 转换
python main.py --all
```

**处理流程**:

1. 爬取原始数据（CPI、PPI、GDP等）
2. 将所有日期统一为YYYY-MM-DD格式
3. 将季度/年度数据插值为月度
4. 转换为Stata DTA格式

**生成文件**:

- `*_原始数据.csv` - 爬取的原始数据
- `*_标准日期.csv` - 日期统一后的数据
- `*_月度.csv` - 插值后的月度数据
- `统一月度数据集.csv` - 合并的月度数据集 ⭐
- `*.dta` - Stata格式文件

#### 场景2：仅爬取新数据

```bash
# 爬取所有类别
python main.py --fetch

# 仅爬取宏观数据
python main.py --fetch --fetch-categories macro

# 仅爬取工资和预期数据
python main.py --fetch --fetch-categories wage expectation
```

#### 场景3：重新处理现有数据

```bash
# 仅统一日期格式
python main.py --unify-date

# 仅插值为月度
python main.py --interpolate

# 仅转换为DTA
python main.py --to-dta
```

#### 场景4：组合多个步骤

```bash
# 爬取后立即统一日期
python main.py --fetch --unify-date

# 统一日期后插值
python main.py --unify-date --interpolate

# 插值后转换为DTA
python main.py --interpolate --to-dta
```

#### 场景5：查看和检查

```bash
# 列出所有生成的文件
python main.py --list

# 生成数据质量报告
python main.py --report

# 详细模式查看处理过程
python main.py --all -v
```

## 🔧 配置说明

所有配置参数在 `config.py` 中定义：

### 路径配置

```python
DATA_DIR = "../data"        # 数据目录
LOG_DIR = "../logs"          # 日志目录
```

### 数据处理配置

```python
DATE_FORMAT = "%Y-%m-%d"               # 日期格式
INTERPOLATION_METHOD = "linear"        # 插值方法
START_YEAR = 2008                      # 起始年份
END_YEAR = 2025                        # 结束年份
RECOMMENDED_START = "2008-01-01"       # 推荐开始日期
RECOMMENDED_END = "2024-12-31"         # 推荐结束日期
```

### 爬取配置

```python
FETCH_INTERVAL = 1          # 爬取间隔（秒）
HTTP_TIMEOUT = 30           # 请求超时（秒）
MAX_RETRIES = 3             # 最大重试次数
```

### 显示配置

```python
VERBOSE = True              # 详细输出
SHOW_PROGRESS = True        # 显示进度条
TABLE_WIDTH = 80            # 表格宽度
```

## 📊 模块说明

### 1. DataFetcher（数据爬取）

从AKShare和国家统计局获取数据。

```python
from modules.data_fetcher import DataFetcher

fetcher = DataFetcher()
data_dict = fetcher.fetch_all()  # 爬取所有数据
fetcher.save_all()               # 保存所有数据
```

**支持的数据**:

- 宏观数据：CPI、PPI、GDP、M2、PMI、SHIBOR
- 工资数据：城镇就业人员平均工资
- 预期数据：企业景气指数、PMI

### 2. DateProcessor（日期处理）

统一各种日期格式。

```python
from modules.date_processor import DateProcessor

processor = DateProcessor()
success, fail = processor.process_all_files()
```

**支持的格式**:

- 月度：`2025年12月份` → `2025-12-01`
- 季度：`2025年第3季度` → `2025-09-30`
- 年度：`zb.A090201_sj.2024` → `2024-12-31`
- 标准：`2025-01-01` → 不变

### 3. FrequencyConverter（频率转换）

将季度/年度数据插值为月度。

```python
from modules.frequency_converter import FrequencyConverter

converter = FrequencyConverter()
count = converter.convert_all_to_monthly()
unified_df = converter.create_unified_dataset()
```

**转换方法**:

- 季度 → 月度：线性插值
- 年度 → 月度：重复12次

### 4. FormatConverter（格式转换）

将CSV转换为Stata DTA格式。

```python
from modules.format_converter import FormatConverter

converter = FormatConverter()
count = converter.convert_all_to_dta()
```

**特点**:

- 自动处理中文列名
- 删除Stata不支持的列
- 支持Stata 14/15格式

## 📝 日志系统

日志文件位置：`logs/data_processing.log`

日志级别：

- `DEBUG`: 调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

查看日志：

```bash
# 查看最新日志
tail -f logs/data_processing.log

# 查看错误日志
grep ERROR logs/data_processing.log
```

## 🐛 常见问题

### Q1: AKShare导入失败

**错误**: `ModuleNotFoundError: No module named 'akshare'`

**解决**:

```bash
pip install akshare
```

### Q2: 爬取失败或超时

**错误**: 网络超时或请求失败

**解决**:

1. 检查网络连接
2. 增加 `config.py` 中的 `HTTP_TIMEOUT` 值
3. 减少 `FETCH_INTERVAL` 间隔

### Q3: 日期格式未识别

**错误**: `未识别的日期格式`

**解决**:
检查CSV文件的日期列格式，确保符合支持的格式之一。

### Q4: Stata导入失败

**错误**: `Not a valid Stata file`

**解决**:

1. 确保使用Stata 14或更高版本
2. 检查DTA文件是否完整
3. 重新生成DTA文件：`python main.py --to-dta`

### Q5: 内存不足

**错误**: `MemoryError`

**解决**:

1. 分批处理文件
2. 减少同时处理的数据量
3. 使用更小的时间范围

## 🔄 与旧脚本对应关系

| 旧脚本                             | 新模块                              | 说明      |
| ------------------------------- | -------------------------------- | ------- |
| `fetch_svar_data.py`            | `modules/data_fetcher.py`        | 整合到统一模块 |
| `fetch_wage_and_expectation.py` | `modules/data_fetcher.py`        | 整合到统一模块 |
| `unify_date_format.py`          | `modules/date_processor.py`      | 保持功能一致  |
| `interpolate_to_monthly.py`     | `modules/frequency_converter.py` | 保持功能一致  |
| `csv_to_dta_fixed.py`           | `modules/format_converter.py`    | 保持功能一致  |

**迁移指南**:

- 旧脚本仍然可用，但推荐使用新的 `main.py`
- 所有功能都可以通过 `main.py` 调用
- 配置统一在 `config.py` 中管理

## 💡 最佳实践

### 1. 首次使用

```bash
# 完整流程
python main.py --all

# 检查结果
python main.py --list
python main.py --report
```

### 2. 定期更新数据

```bash
# 仅爬取最新数据
python main.py --fetch

# 处理新数据
python main.py --unify-date --interpolate --to-dta
```

### 3. 数据验证

```bash
# 生成质量报告
python main.py --report

# 检查缺失值、日期范围等
```

### 4. 调试模式

```bash
# 详细输出模式
python main.py --all -v --log-level DEBUG

# 查看日志
tail -f logs/data_processing.log
```

## 📚 进阶使用

### 作为Python模块导入

```python
# 示例：自定义处理流程
from main import DataPipeline
import config

# 自定义配置
config.INTERPOLATION_METHOD = 'cubic'  # 使用三次样条插值
config.START_YEAR = 2010               # 只处理2010年后的数据

# 创建流水线
pipeline = DataPipeline(verbose=True)

# 执行特定步骤
pipeline.step_fetch_data()
pipeline.step_unify_dates()

# 或执行完整流程
pipeline.run_all()
```

### 批处理脚本

创建 `batch_process.sh`:

```bash
#!/bin/bash

# 设置环境
export PYTHONPATH=$PYTHONPATH:./code

# 执行处理
python code/main.py --all

# 备份结果
cp data/统一月度数据集.csv backups/unified_$(date +%Y%m%d).csv

echo "批处理完成"
```

### 定时任务

使用cron定时爬取数据：

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每周一早上8点）
0 8 * * 1 cd /path/to/project && python code/main.py --fetch
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题，请通过Issue反馈。
