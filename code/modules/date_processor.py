"""
日期格式处理模块
对应 unify_date_format.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import re
from typing import Optional, Tuple
import config
import utils


class DateProcessor:
    """日期格式处理器"""

    def __init__(self):
        """初始化"""
        self.logger = utils.logger
        self.success_count = 0
        self.fail_count = 0

    def process_all_files(self, input_files: list = None) -> Tuple[int, int]:
        """
        处理所有文件

        参数:
        - input_files: 输入文件列表，None表示处理所有CSV文件

        返回:
        - (成功数, 失败数)
        """
        utils.print_header("CSV文件日期格式统一")
        utils.print_section("目标格式: YYYY-MM-DD")

        if input_files is None:
            input_files = config.ORIGIN_DATE_FILES

        # 定义文件及其日期列
        file_date_columns = {
            'PPI_原始数据.csv': '月份',
            'CPI_原始数据.csv': '月份',
            'M2_原始数据.csv': '月份',
            '新增贷款_原始数据.csv': '月份',
            'PMI_原始数据.csv': '月份',
            'GDP_原始数据.csv': '季度',
            '企业景气指数_原始数据.csv': '季度',
            'SHIBOR_原始数据.csv': '报告日',
            '非制造业PMI_原始数据.csv': '日期',
            '工资数据_原始数据.csv': 'code',
            '国债利差_原始数据.csv': 'date',
        }

        self.success_count = 0
        self.fail_count = 0

        for filename in input_files:
            if filename not in file_date_columns:
                continue


            date_column = file_date_columns[filename]

            if self.convert_file_dates(filename, date_column):
                self.success_count += 1
            else:
                self.fail_count += 1

        # 打印总结
        utils.print_header("转换完成")
        utils.print_success(f"成功: {self.success_count}个文件")
        if self.fail_count > 0:
            utils.print_warning(f"失败: {self.fail_count}个文件")

        return self.success_count, self.fail_count

    def convert_file_dates(self, filename: str, date_column: str,
                          output_filename: Optional[str] = None) -> bool:
        """
        转换单个文件的日期格式

        参数:
        - filename: 输入文件名
        - date_column: 日期列名
        - output_filename: 输出文件名，None表示自动生成

        返回:
        - 是否成功
        """
        filepath = os.path.join(config.DATA_DIR, filename)

        if not utils.file_exists(filepath):
            utils.print_warning(f"文件不存在: {filename}")
            return False

        try:
            # 读取CSV
            df = utils.read_csv_safe(filepath)
            if df is None:
                return False

            if date_column not in df.columns:
                utils.print_warning(f"列 '{date_column}' 不存在于 {filename}")
                return False

            # 备份原始日期列
            df[f'{date_column}_原始'] = df[date_column]

            # 检测日期格式并转换
            sample = str(df[date_column].iloc[0])
            conversion_type = self._detect_date_format(sample)

            if not conversion_type:
                utils.print_warning(f"{filename}: 未识别的日期格式: {sample}")
                return False

            # 转换日期
            df['date'] = self._convert_dates(df[date_column], conversion_type)

            # 将date列移到第一列
            cols = ['date'] + [col for col in df.columns if col != 'date']
            df = df[cols]

            # 生成输出文件名
            if output_filename is None:
                output_filename = filename.replace('_原始数据', '_标准日期')
                if output_filename == filename:
                    output_filename = filename.replace('.csv', '_标准日期.csv')

            # 保存
            output_path = os.path.join(config.DATA_DIR, output_filename)
            if utils.save_csv_safe(df, output_path):
                start, end = utils.get_date_range(df)
                utils.print_success(
                    f"{filename} → {output_filename} "
                    f"({len(df)}行, {start.date()} ~ {end.date()})"
                )
                return True

        except Exception as e:
            utils.print_error(f"转换失败 {filename}: {e}")
            self.logger.exception(f"转换{filename}时出错")

        return False

    def _detect_date_format(self, sample: str) -> Optional[str]:
        """
        检测日期格式

        返回:
        - 'monthly': 月度格式
        - 'quarterly': 季度格式
        - 'annual': 年度格式
        - 'code': 代码格式
        - 'standard': 已是标准格式
        - None: 未识别
        """
        if '年' in sample and '月份' in sample:
            return 'monthly'
        elif '年' in sample and '季度' in sample:
            return 'quarterly'
        elif 'zb.A' in sample and '_sj.' in sample:
            return 'code'
        elif re.match(r'\d{4}-\d{2}-\d{2}', sample):
            return 'standard'
        else:
            return None

    def _convert_dates(self, series: pd.Series, conversion_type: str) -> pd.Series:
        """
        转换日期序列

        参数:
        - series: 日期序列
        - conversion_type: 转换类型

        返回:
        - 转换后的日期序列
        """
        if conversion_type == 'monthly':
            return series.apply(self._convert_chinese_month_to_date)
        elif conversion_type == 'quarterly':
            return series.apply(self._convert_chinese_quarter_to_date)
        elif conversion_type == 'code':
            return series.apply(self._extract_year_from_code)
        elif conversion_type == 'standard':
            return series
        else:
            return series

    @staticmethod
    def _convert_chinese_month_to_date(month_str: str) -> Optional[str]:
        """将中文月份转换为标准日期"""
        match = re.search(r'(\d{4})年(\d{1,2})月', str(month_str))
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)
            return f"{year}-{month}-01"
        return None

    @staticmethod
    def _convert_chinese_quarter_to_date(quarter_str: str) -> Optional[str]:
        """将中文季度转换为标准日期"""
        match = re.search(r'(\d{4})年第(\d)(?:-(\d))?季度', str(quarter_str))
        if match:
            year = match.group(1)
            start_q = int(match.group(2))
            end_q = int(match.group(3)) if match.group(3) else start_q

            quarter_end_dates = {
                1: f"{year}-03-31",
                2: f"{year}-06-30",
                3: f"{year}-09-30",
                4: f"{year}-12-31"
            }
            return quarter_end_dates[end_q]
        return None

    @staticmethod
    def _extract_year_from_code(code_str: str) -> Optional[str]:
        """从代码中提取年份"""
        match = re.search(r'_sj\.(\d{4})', str(code_str))
        if match:
            year = match.group(1)
            return f"{year}-12-31"
        return None


# 命令行入口
def main():
    """命令行主函数"""
    processor = DateProcessor()
    processor.process_all_files()


if __name__ == "__main__":
    main()
