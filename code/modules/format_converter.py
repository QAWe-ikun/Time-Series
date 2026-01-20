"""
格式转换模块
对应 csv_to_dta_fixed.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
import re
from typing import Dict, Tuple
import config
import utils


class FormatConverter:
    """格式转换器"""

    def __init__(self):
        """初始化"""
        self.logger = utils.logger
        self.success_count = 0

    def convert_all_to_dta(self, files: list = None) -> int:
        """
        将所有CSV转换为Stata DTA格式

        参数:
        - files: 要转换的文件列表，None表示所有标准日期文件

        返回:
        - 成功转换的文件数
        """
        utils.print_header("CSV转Stata DTA格式")

        if files is None:
            files = config.STANDARD_DATE_FILES.copy()
            # GDP和国债利差使用月度文件而不是标准日期文件
            if 'GDP_标准日期.csv' in files:
                files = [f if f != 'GDP_标准日期.csv' else 'GDP_月度.csv' for f in files]
            if '国债利差_标准日期.csv' in files:
                files = [f if f != '国债利差_标准日期.csv' else '国债利差_月度.csv' for f in files]

        self.success_count = 0
        results = []

        for filename in files:
            # 确定输出DTA文件名（月度文件输出为标准日期.dta）
            if filename == 'GDP_月度.csv':
                dta_filename = 'GDP_标准日期.dta'
            elif filename == '国债利差_月度.csv':
                dta_filename = '国债利差_标准日期.dta'
            else:
                dta_filename = filename.replace('.csv', '.dta')

            success, shape = self.convert_single_file(filename, dta_filename=dta_filename)
            if success:
                self.success_count += 1
                results.append((filename, dta_filename, shape))

        # 打印总结
        utils.print_header("转换完成")
        utils.print_success(f"成功: {self.success_count}/{len(files)} 个文件")

        if results:
            utils.print_section("生成的DTA文件")
            data = [[i+1, dta, f"{shape[0]}行", f"{shape[1]}列"]
                    for i, (_, dta, shape) in enumerate(results)]
            utils.print_table(data, headers=["#", "文件名", "行数", "列数"])

        return self.success_count

    def convert_single_file(self, filename: str, dta_filename: str = None, verbose: bool = True) -> Tuple[bool, tuple]:
        """
        转换单个CSV文件为DTA格式

        参数:
        - filename: 输入文件名
        - dta_filename: 输出DTA文件名，None表示自动生成
        - verbose: 是否显示详细信息

        返回:
        - (是否成功, (行数, 列数))
        """
        csv_path = os.path.join(config.DATA_DIR, filename)

        if not utils.file_exists(csv_path):
            if verbose:
                utils.print_warning(f"文件不存在: {filename}")
            return False, None

        try:
            # 读取CSV
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # 处理重复列名
            cols = df.columns.tolist()
            seen = {}
            new_cols = []
            for col in cols:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols

            if verbose:
                self.logger.info(f"正在转换: {filename}")

            # 保存原始列名
            original_columns = df.columns.tolist()

            # 创建列名映射，确保没有重复
            column_mapping = {}
            used_names = set()
            for col in original_columns:
                new_col = self._sanitize_column_name(col)
                # 如果新列名已经被使用，添加后缀
                if new_col in used_names:
                    counter = 1
                    while f"{new_col}_{counter}" in used_names:
                        counter += 1
                    new_col = f"{new_col}_{counter}"
                used_names.add(new_col)
                column_mapping[col] = new_col

            # 应用列名映射
            df.rename(columns=column_mapping, inplace=True)

            # 再次检查是否有重复列名（双重保险）
            if len(df.columns) != len(set(df.columns)):
                cols = df.columns.tolist()
                seen = {}
                new_cols = []
                for col in cols:
                    if col in seen:
                        seen[col] += 1
                        new_cols.append(f"{col}_{seen[col]}")
                    else:
                        seen[col] = 0
                        new_cols.append(col)
                df.columns = new_cols

            # 删除包含中文的列（Stata不支持）
            columns_to_drop = []

            # 检查列名中包含特定关键词的
            for col in df.columns:
                if 'orig' in col or col in ['month', 'quarter', 'report_date', 'commodity', 'date_cn']:
                    columns_to_drop.append(col)
                    continue

                # 检查列内容是否包含中文字符
                if df[col].dtype == 'object':
                    try:
                        # 检查前几行是否有中文
                        sample = df[col].dropna().astype(str).head(10)
                        has_chinese = any(any('\u4e00' <= char <= '\u9fff' for char in str(val))
                                        for val in sample)
                        if has_chinese:
                            columns_to_drop.append(col)
                    except:
                        pass

            if columns_to_drop and verbose:
                self.logger.info(f"删除中文列: {', '.join(columns_to_drop)}")

            df.drop(columns=columns_to_drop, inplace=True, errors='ignore')

            # 确保date列是datetime格式
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')

            df = df[df['date'] >= datetime.strptime(config.RECOMMENDED_START, "%Y-%m-%d")]

            # 保存为DTA格式
            if dta_filename is None:
                dta_path = csv_path.replace('.csv', '.dta')
            else:
                dta_path = os.path.join(config.DATA_DIR, dta_filename)

            df.to_stata(dta_path, write_index=False, version=config.STATA_VERSION)

            if verbose:
                utils.print_success(
                    f"{filename} → {os.path.basename(dta_path)} "
                    f"({df.shape[0]}行 × {df.shape[1]}列)"
                )

            return True, df.shape

        except Exception as e:
            if verbose:
                utils.print_error(f"转换失败 {filename}: {e}")
            self.logger.exception(f"转换{filename}时出错")

        return False, None

    def _sanitize_column_name(self, col_name: str) -> str:
        """
        将列名转换为Stata兼容格式

        参数:
        - col_name: 原始列名

        返回:
        - Stata兼容的列名
        """
        # 先查找预定义映射
        if col_name in config.COLUMN_MAPPING:
            return config.COLUMN_MAPPING[col_name]

        # 自动生成
        sanitized = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', col_name)

        # 简单的中文到拼音转换
        chinese_map = {
            '货币': 'huobi', '准货币': 'zhunhuobi', '数量': 'shuliang',
            '同比': 'tongbi', '环比': 'huanbi', '增长': 'zengzhang',
            '累计': 'leiji', '当月': 'dangyue', '绝对值': 'juedui',
            '产业': 'chanye', '指数': 'zhishu', '企业': 'qiye',
            '景气': 'jingqi', '信心': 'xinxin', '制造业': 'zhizaoye',
            '非制造业': 'feizhizaoye', '报告': 'baogao', '日': 'ri',
        }

        for cn, pinyin in chinese_map.items():
            sanitized = sanitized.replace(cn, pinyin)

        # 移除剩余中文
        sanitized = re.sub(r'[\u4e00-\u9fff]', '', sanitized)

        # 清理
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')

        if not sanitized:
            sanitized = 'var'

        if sanitized[0].isdigit():
            sanitized = 'v' + sanitized

        # 限制长度
        if len(sanitized) > 32:
            sanitized = sanitized[:32]

        return sanitized.lower()


# 命令行入口
def main():
    """命令行主函数"""
    converter = FormatConverter()
    converter.convert_all_to_dta()


if __name__ == "__main__":
    main()
