"""
通用工具函数
提供各模块共用的辅助功能
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
import config


# ==================== 日志配置 ====================

def setup_logging(log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    配置日志系统

    参数:
    - log_file: 日志文件路径
    - level: 日志级别

    返回:
    - logger: 配置好的logger对象
    """
    logger = logging.getLogger('data_processing')
    logger.setLevel(getattr(logging, level))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(config.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# 全局logger
logger = setup_logging(config.LOG_FILE, config.LOG_LEVEL)


# ==================== 文件操作 ====================

def ensure_dir(directory: str) -> None:
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)


def file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(filepath) and os.path.isfile(filepath)


def get_file_size(filepath: str) -> str:
    """获取文件大小（人类可读格式）"""
    if not file_exists(filepath):
        return "0B"

    size_bytes = os.path.getsize(filepath)

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f}TB"


def list_files(directory: str, extension: str = None) -> List[str]:
    """
    列出目录下的文件

    参数:
    - directory: 目录路径
    - extension: 文件扩展名（如'.csv'）

    返回:
    - 文件列表
    """
    if not os.path.exists(directory):
        return []

    files = os.listdir(directory)

    if extension:
        files = [f for f in files if f.endswith(extension)]

    return sorted(files)


# ==================== 数据处理 ====================

def read_csv_safe(filepath: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    安全读取CSV文件

    参数:
    - filepath: 文件路径
    - **kwargs: pandas.read_csv的其他参数

    返回:
    - DataFrame或None
    """
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', **kwargs)
        logger.info(f"成功读取: {os.path.basename(filepath)} ({len(df)}行)")
        return df
    except Exception as e:
        logger.error(f"读取失败 {os.path.basename(filepath)}: {e}")
        return None


def save_csv_safe(df: pd.DataFrame, filepath: str, **kwargs) -> bool:
    """
    安全保存CSV文件

    参数:
    - df: DataFrame
    - filepath: 保存路径
    - **kwargs: pandas.to_csv的其他参数

    返回:
    - 是否成功
    """
    try:
        df.to_csv(filepath, index=False, encoding='utf-8-sig', **kwargs)
        logger.info(f"已保存: {os.path.basename(filepath)} ({len(df)}行 × {len(df.columns)}列)")
        return True
    except Exception as e:
        logger.error(f"保存失败 {os.path.basename(filepath)}: {e}")
        return False


def get_date_range(df: pd.DataFrame, date_col: str = 'date') -> tuple:
    """
    获取数据的日期范围

    返回:
    - (start_date, end_date)
    """
    if date_col not in df.columns:
        return None, None

    df[date_col] = pd.to_datetime(df[date_col])
    return df[date_col].min(), df[date_col].max()


def check_missing_values(df: pd.DataFrame) -> Dict[str, Any]:
    """
    检查缺失值

    返回:
    - 缺失值统计字典
    """
    missing = df.isnull().sum()
    missing = missing[missing > 0]

    result = {}
    for col, count in missing.items():
        pct = count / len(df) * 100
        result[col] = {'count': int(count), 'percentage': round(pct, 2)}

    return result


# ==================== 显示和格式化 ====================

def print_header(text: str, width: int = 80, char: str = "=") -> None:
    """打印标题"""
    print(char * width)
    print(text.center(width))
    print(char * width)


def print_section(text: str, width: int = 80, char: str = "-") -> None:
    """打印章节"""
    print("\n" + text)
    print(char * width)


def print_success(text: str) -> None:
    """打印成功信息"""
    print(f"✓ {text}")
    logger.info(text)


def print_warning(text: str) -> None:
    """打印警告信息"""
    print(f"⚠️ {text}")
    logger.warning(text)


def print_error(text: str) -> None:
    """打印错误信息"""
    print(f"❌ {text}")
    logger.error(text)


def print_table(data: List[List[str]], headers: List[str] = None) -> None:
    """
    打印表格

    参数:
    - data: 数据列表
    - headers: 表头列表
    """
    if not data:
        return

    # 计算每列最大宽度
    if headers:
        data_with_headers = [headers] + data
    else:
        data_with_headers = data

    col_widths = []
    for i in range(len(data_with_headers[0])):
        max_width = max(len(str(row[i])) for row in data_with_headers)
        col_widths.append(min(max_width + 2, 40))  # 最大40字符

    # 打印分隔线
    separator = "+" + "+".join(["-" * w for w in col_widths]) + "+"

    # 打印表头
    if headers:
        print(separator)
        header_row = "|" + "|".join([str(h).center(w) for h, w in zip(headers, col_widths)]) + "|"
        print(header_row)
        print(separator)

    # 打印数据行
    for row in data:
        data_row = "|" + "|".join([str(cell).ljust(w) for cell, w in zip(row, col_widths)]) + "|"
        print(data_row)

    print(separator)


# ==================== 进度显示 ====================

class ProgressBar:
    """简单的进度条"""

    def __init__(self, total: int, desc: str = "处理中", width: int = 50):
        self.total = total
        self.current = 0
        self.desc = desc
        self.width = width

    def update(self, n: int = 1) -> None:
        """更新进度"""
        self.current += n
        self._display()

    def _display(self) -> None:
        """显示进度条"""
        if not config.SHOW_PROGRESS:
            return

        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)

        print(f"\r{self.desc}: [{bar}] {pct*100:.1f}% ({self.current}/{self.total})", end="")

        if self.current >= self.total:
            print()  # 换行


# ==================== 数据验证 ====================

def validate_date_column(df: pd.DataFrame, date_col: str = 'date') -> bool:
    """验证日期列是否有效"""
    if date_col not in df.columns:
        logger.error(f"缺少日期列: {date_col}")
        return False

    try:
        pd.to_datetime(df[date_col])
        return True
    except Exception as e:
        logger.error(f"日期格式无效: {e}")
        return False


def validate_numeric_columns(df: pd.DataFrame, columns: List[str]) -> bool:
    """验证数值列是否有效"""
    for col in columns:
        if col not in df.columns:
            logger.error(f"缺少列: {col}")
            return False

        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.error(f"列 {col} 不是数值类型")
            return False

    return True


# ==================== 时间处理 ====================

def get_current_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f}分钟"
    else:
        return f"{seconds/3600:.1f}小时"


# ==================== 备份功能 ====================

def backup_file(filepath: str) -> Optional[str]:
    """
    备份文件

    返回:
    - 备份文件路径
    """
    if not file_exists(filepath):
        return None

    backup_dir = os.path.join(config.DATA_DIR, "backups")
    ensure_dir(backup_dir)

    filename = os.path.basename(filepath)
    timestamp = get_current_timestamp()
    backup_name = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        import shutil
        shutil.copy2(filepath, backup_path)
        logger.info(f"已备份: {backup_name}")
        return backup_path
    except Exception as e:
        logger.error(f"备份失败: {e}")
        return None


# ==================== 数据质量报告 ====================

def generate_data_quality_report(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
    """
    生成数据质量报告

    返回:
    - 报告字典
    """
    report = {
        'filename': filename,
        'rows': len(df),
        'columns': len(df.columns),
        'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB",
        'date_range': None,
        'missing_values': {},
        'numeric_columns': [],
        'object_columns': [],
    }

    # 日期范围
    if 'date' in df.columns:
        start, end = get_date_range(df)
        if start and end:
            report['date_range'] = f"{start.date()} ~ {end.date()}"

    # 缺失值
    report['missing_values'] = check_missing_values(df)

    # 列类型
    report['numeric_columns'] = df.select_dtypes(include=['number']).columns.tolist()
    report['object_columns'] = df.select_dtypes(include=['object']).columns.tolist()

    return report


if __name__ == "__main__":
    # 测试
    print_header("工具函数测试")
    print_success("成功消息")
    print_warning("警告消息")
    print_error("错误消息")

    # 测试进度条
    import time
    progress = ProgressBar(100, "测试进度")
    for i in range(100):
        time.sleep(0.01)
        progress.update(1)
