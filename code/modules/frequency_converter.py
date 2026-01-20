"""
频率转换模块
对应 interpolate_to_monthly.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import config
import utils


class FrequencyConverter:
    """频率转换器"""

    # 不变价GDP基准年
    BASE_YEAR = 2015

    def __init__(self):
        """初始化"""
        self.logger = utils.logger
        self.success_count = 0

    def convert_all_to_monthly(self, files: list = None) -> int:
        """
        将所有季度/年度数据转换为月度

        参数:
        - files: 要转换的文件列表，None表示默认列表

        返回:
        - 成功转换的文件数
        """
        utils.print_header("数据频率统一：季度/年度 → 月度")

        if files is None:
            files = [
                'GDP_标准日期.csv',
                '国债利差_标准日期.csv',
            ]

        self.success_count = 0

        for filename in files:
            if self.process_file(filename):
                self.success_count += 1

        # 总结
        utils.print_header("转换完成")
        utils.print_success(f"成功转换: {self.success_count}/{len(files)} 个文件")

        # 创建统一数据集
        if self.success_count > 0:
            self.create_unified_dataset()

        return self.success_count

    def process_file(self, filename: str, output_suffix: str = '_月度') -> bool:
        """
        处理单个文件

        参数:
        - filename: 输入文件名
        - output_suffix: 输出文件后缀

        返回:
        - 是否成功
        """
        filepath = os.path.join(config.DATA_DIR, filename)

        if not utils.file_exists(filepath):
            utils.print_warning(f"文件不存在: {filename}")
            return False

        try:
            # 读取数据
            df = utils.read_csv_safe(filepath)
            if df is None:
                return False

            utils.print_section(f"处理: {filename}")
            self.logger.info(f"原始数据: {len(df)}行")

            # 检测数据频率
            df['date'] = pd.to_datetime(df['date'])
            df_sorted = df.sort_values('date')
            date_diff = abs(df_sorted['date'].diff().dt.days.median())

            # 检测是否为GDP数据，需要先转换为不变价
            is_gdp_data = 'GDP' in filename and '国内生产总值-绝对值' in df.columns

            if is_gdp_data:
                utils.print_success("检测到GDP数据，将转换为不变价GDP（基准年=2015）")
                df = self._convert_gdp_to_real(
                    df,
                    value_col='国内生产总值-绝对值',
                    growth_col='国内生产总值-同比增长',
                    base_year=self.BASE_YEAR
                )
                # 同样处理三次产业的GDP
                for sector in ['第一产业', '第二产业', '第三产业']:
                    value_col = f'{sector}-绝对值'
                    growth_col = f'{sector}-同比增长'
                    if value_col in df.columns and growth_col in df.columns:
                        df = self._convert_gdp_to_real(
                            df,
                            value_col=value_col,
                            growth_col=growth_col,
                            base_year=self.BASE_YEAR
                        )

            if date_diff < 10:
                # 日度数据
                utils.print_success(f"检测到日度数据（平均间隔{date_diff:.0f}天）")
                result_df = self._aggregate_daily_to_monthly(df)
                method = "日度平均"

            elif date_diff > 50 and date_diff < 120:
                # 季度数据
                utils.print_success(f"检测到季度数据（平均间隔{date_diff:.0f}天）")
                result_df = self._interpolate_quarterly_to_monthly(df)
                method = "线性插值"

            elif date_diff > 300:
                # 年度数据
                utils.print_success(f"检测到年度数据（平均间隔{date_diff:.0f}天）")
                result_df = self._repeat_annual_to_monthly(df)
                method = "年度重复"

            else:
                # 已是月度或更高频
                utils.print_success(f"已是月度数据（平均间隔{date_diff:.0f}天），无需转换")
                return False

            # 保存结果
            output_filename = filename.replace('_标准日期.csv', f'{output_suffix}.csv')
            output_path = os.path.join(config.DATA_DIR, output_filename)

            if utils.save_csv_safe(result_df, output_path):
                start, end = utils.get_date_range(result_df)
                extra_info = "（不变价，基准年=2015）" if is_gdp_data else ""
                utils.print_success(
                    f"转换完成{extra_info}: {len(df)}行 → {len(result_df)}行 "
                    f"({start.date()} ~ {end.date()}) 方法: {method}"
                )
                return True

        except Exception as e:
            utils.print_error(f"处理失败: {e}")
            self.logger.exception(f"处理{filename}时出错")

        return False

    def _interpolate_quarterly_to_monthly(self, df: pd.DataFrame,
                                         date_col: str = 'date') -> pd.DataFrame:
        """
        季度数据插值为月度

        参数:
        - df: 输入DataFrame
        - date_col: 日期列名

        返回:
        - 月度DataFrame
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df_indexed = df.set_index(date_col).sort_index()

        # 只保留数值列
        numeric_cols = df_indexed.select_dtypes(include=[np.number]).columns
        df_numeric = df_indexed[numeric_cols]

        # 重采样为月度并插值
        df_monthly = df_numeric.resample('MS').mean()
        df_monthly = df_monthly.interpolate(
            method=config.INTERPOLATION_METHOD,
            limit_direction='both'
        )

        # 重置索引
        df_monthly = df_monthly.reset_index()
        df_monthly.rename(columns={'index': date_col}, inplace=True)

        return df_monthly

    def _repeat_annual_to_monthly(self, df: pd.DataFrame,
                                  date_col: str = 'date') -> pd.DataFrame:
        """
        年度数据重复为月度

        参数:
        - df: 输入DataFrame
        - date_col: 日期列名

        返回:
        - 月度DataFrame
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df['year'] = df[date_col].dt.year

        # 为每年生成12个月的数据
        all_monthly_data = []

        for idx, row in df.iterrows():
            year = row['year']
            for month in range(1, 13):
                monthly_row = row.copy()
                monthly_row[date_col] = pd.Timestamp(year=year, month=month, day=1)
                all_monthly_data.append(monthly_row)

        result_df = pd.DataFrame(all_monthly_data)
        result_df.drop('year', axis=1, inplace=True, errors='ignore')

        return result_df

    def _aggregate_daily_to_monthly(self, df: pd.DataFrame,
                                    date_col: str = 'date') -> pd.DataFrame:
        """
        日度数据聚合为月度（求均值）

        参数:
        - df: 输入DataFrame
        - date_col: 日期列名

        返回:
        - 月度DataFrame
        """
        df[date_col] = pd.to_datetime(df[date_col])
        df_indexed = df.set_index(date_col).sort_index()

        # 只保留数值列
        numeric_cols = df_indexed.select_dtypes(include=[np.number]).columns
        df_numeric = df_indexed[numeric_cols]

        # 重采样为月度并求均值
        df_monthly = df_numeric.resample('MS').mean()

        # 重置索引
        df_monthly = df_monthly.reset_index()

        return df_monthly

    def _convert_gdp_to_real(self, df: pd.DataFrame,
                              value_col: str = '国内生产总值-绝对值',
                              growth_col: str = '国内生产总值-同比增长',
                              base_year: int = None) -> pd.DataFrame:
        """
        将名义GDP转换为以基准年为基期的不变价GDP（实际GDP）

        计算方法:
        - 利用实际同比增长率，以基准年的名义GDP为基期
        - 使用链式法反推其他年份的实际GDP
        - Real_GDP[t] = Real_GDP[t-1年] × (1 + 同比增长率[t]/100)

        参数:
        - df: 输入DataFrame
        - value_col: 名义GDP列名
        - growth_col: 实际同比增长率列名
        - base_year: 基准年，默认为2015

        返回:
        - 包含不变价GDP的DataFrame
        """
        if base_year is None:
            base_year = self.BASE_YEAR

        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year

        # 创建不变价GDP列
        real_gdp_col = f'{value_col}_不变价'
        df[real_gdp_col] = np.nan

        # 按日期排序（从早到晚）
        df = df.sort_values('date').reset_index(drop=True)

        utils.print_section(f"计算不变价GDP（基准年={base_year}）")

        # 找到每年第1-4季度（全年）的数据行索引
        # 全年数据的特征：日期为12月31日
        annual_mask = df['date'].dt.month == 12
        annual_df = df[annual_mask].copy()

        if len(annual_df) == 0:
            utils.print_warning("未找到年度数据（12月31日），尝试使用现有数据")
            annual_df = df.copy()

        # 找到基准年的数据
        base_mask = annual_df['year'] == base_year
        if base_mask.sum() == 0:
            utils.print_warning(f"未找到{base_year}年数据，使用最近的年份作为基准")
            base_year = annual_df['year'].iloc[len(annual_df)//2]
            base_mask = annual_df['year'] == base_year
            utils.print_success(f"使用{base_year}年作为基准年")

        base_idx = annual_df[base_mask].index[0]
        base_nominal_gdp = annual_df.loc[base_idx, value_col]

        # 基准年的实际GDP = 名义GDP
        df.loc[base_idx, real_gdp_col] = base_nominal_gdp
        utils.print_success(f"{base_year}年基准名义GDP: {base_nominal_gdp:.2f}亿元")

        # 获取年度数据用于链式计算
        years = sorted(annual_df['year'].unique())
        base_year_idx = years.index(base_year)

        # 存储每年全年的实际GDP（用于链式计算）
        annual_real_gdp = {base_year: base_nominal_gdp}

        # 向后推算（基准年之后的年份）
        for i in range(base_year_idx + 1, len(years)):
            year = years[i]
            year_mask = annual_df['year'] == year
            if year_mask.sum() == 0:
                continue

            year_idx = annual_df[year_mask].index[0]
            growth_rate = annual_df.loc[year_idx, growth_col]

            # 使用前一年的实际GDP和当年增长率计算当年实际GDP
            prev_year = years[i-1]
            if prev_year in annual_real_gdp:
                real_gdp = annual_real_gdp[prev_year] * (1 + growth_rate / 100)
                annual_real_gdp[year] = real_gdp
                df.loc[year_idx, real_gdp_col] = real_gdp

        # 向前推算（基准年之前的年份）
        for i in range(base_year_idx - 1, -1, -1):
            year = years[i]
            next_year = years[i + 1]

            year_mask = annual_df['year'] == year
            next_year_mask = annual_df['year'] == next_year

            if year_mask.sum() == 0 or next_year_mask.sum() == 0:
                continue

            next_year_idx = annual_df[next_year_mask].index[0]
            growth_rate = annual_df.loc[next_year_idx, growth_col]

            # Real_GDP[t-1] = Real_GDP[t] / (1 + growth_rate[t] / 100)
            if next_year in annual_real_gdp:
                real_gdp = annual_real_gdp[next_year] / (1 + growth_rate / 100)
                annual_real_gdp[year] = real_gdp
                year_idx = annual_df[year_mask].index[0]
                df.loc[year_idx, real_gdp_col] = real_gdp

        # 现在处理季度累计数据（非12月31日的数据）
        # 对于每个季度累计值，使用相同的增长率逻辑
        for idx, row in df.iterrows():
            if pd.notna(df.loc[idx, real_gdp_col]):
                continue  # 已计算的跳过

            year = row['year']
            growth_rate = row[growth_col]
            prev_year = year - 1

            # 找到去年同期的数据
            prev_date = row['date'] - pd.DateOffset(years=1)
            prev_mask = (df['date'] == prev_date)

            if prev_mask.sum() > 0 and pd.notna(df.loc[prev_mask, real_gdp_col].values[0]):
                prev_real_gdp = df.loc[prev_mask, real_gdp_col].values[0]
                real_gdp = prev_real_gdp * (1 + growth_rate / 100)
                df.loc[idx, real_gdp_col] = real_gdp
            elif prev_year in annual_real_gdp:
                # 使用年度比例估算
                nominal_ratio = row[value_col] / annual_df[annual_df['year'] == year][value_col].values[0] \
                    if len(annual_df[annual_df['year'] == year]) > 0 else 1
                if year in annual_real_gdp:
                    real_gdp = annual_real_gdp[year] * nominal_ratio
                    df.loc[idx, real_gdp_col] = real_gdp

        # 再次尝试填充剩余的NaN（使用插值）
        if df[real_gdp_col].isna().sum() > 0:
            df[real_gdp_col] = df[real_gdp_col].interpolate(method='linear')

        # 打印转换结果统计
        filled_count = df[real_gdp_col].notna().sum()
        utils.print_success(f"不变价GDP计算完成: {filled_count}/{len(df)}行")

        # 将不变价GDP列替换原始GDP列
        df[value_col] = df[real_gdp_col]
        df.drop(columns=[real_gdp_col, 'year'], inplace=True, errors='ignore')

        return df

    def create_unified_dataset(self) -> Optional[pd.DataFrame]:
        """
        创建统一月度数据集

        返回:
        - 统一数据集DataFrame
        """
        utils.print_header("创建统一月度数据集")

        # 定义要合并的文件和变量
        files_to_merge = {
            'CPI_标准日期.csv': ['全国-当月', '全国-同比增长'],
            'PPI_标准日期.csv': ['当月', '当月同比增长'],
            'PMI_标准日期.csv': ['制造业-指数'],
            '新增贷款_标准日期.csv': ['当月', '当月-同比增长'],
            'GDP_月度.csv': ['国内生产总值-绝对值', '国内生产总值-同比增长'],
            '国债利差_月度.csv': ['spread'],
        }

        # 读取基础数据集（CPI）
        base_file = os.path.join(config.DATA_DIR, 'CPI_标准日期.csv')
        if not utils.file_exists(base_file):
            utils.print_error("基础文件不存在: CPI_标准日期.csv")
            return None

        merged_df = utils.read_csv_safe(base_file)
        if merged_df is None:
            return None

        merged_df['date'] = pd.to_datetime(merged_df['date'])
        merged_df = merged_df[['date', '全国-当月', '全国-同比增长']].copy()
        merged_df.rename(columns={'全国-当月': 'CPI', '全国-同比增长': 'CPI_yoy'}, inplace=True)

        utils.print_success(f"基础数据: CPI ({len(merged_df)}行)")

        # 逐个合并其他文件
        for filename, columns in list(files_to_merge.items())[1:]:
            filepath = os.path.join(config.DATA_DIR, filename)

            if not utils.file_exists(filepath):
                utils.print_warning(f"跳过: {filename}")
                continue

            df = utils.read_csv_safe(filepath)
            if df is None:
                continue

            df['date'] = pd.to_datetime(df['date'])

            # 选择需要的列
            available_cols = [col for col in columns if col in df.columns]
            if not available_cols:
                utils.print_warning(f"跳过 {filename}: 未找到指定列")
                continue

            df_subset = df[['date'] + available_cols].copy()

            # 重命名列
            prefix = filename.split('_')[0]
            rename_dict = {col: f'{prefix}_{i}' for i, col in enumerate(available_cols)}
            df_subset.rename(columns=rename_dict, inplace=True)

            # 合并
            merged_df = pd.merge(merged_df, df_subset, on='date', how='outer')
            utils.print_success(f"已合并: {filename} ({len(available_cols)}列)")

        # 排序
        merged_df = merged_df.sort_values('date').reset_index(drop=True)

        # 保存
        output_path = os.path.join(config.DATA_DIR, config.OUTPUT_FILES['unified_monthly'])
        if utils.save_csv_safe(merged_df, output_path):
            start, end = utils.get_date_range(merged_df)
            utils.print_success(
                f"统一数据集: {len(merged_df)}行 × {len(merged_df.columns)}列 "
                f"({start.date()} ~ {end.date()})"
            )

            # 缺失值统计
            missing = utils.check_missing_values(merged_df)
            if missing:
                utils.print_section("缺失值统计")
                for col, stats in missing.items():
                    print(f"  {col}: {stats['count']}个 ({stats['percentage']}%)")

            return merged_df

        return None


# 命令行入口
def main():
    """命令行主函数"""
    converter = FrequencyConverter()
    converter.convert_all_to_monthly()


if __name__ == "__main__":
    main()
