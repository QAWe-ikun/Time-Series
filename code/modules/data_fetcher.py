"""
数据爬取模块
整合 fetch_svar_data.py 和 fetch_wage_and_expectation.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
from typing import Dict, Optional
import config
import utils


class DataFetcher:
    """数据爬取器"""

    def __init__(self):
        """初始化"""
        self.logger = utils.logger
        self.data_dict = {}

        try:
            import akshare as ak
            self.ak = ak
            self.logger.info("AKShare 库加载成功")
        except ImportError:
            self.logger.error("未安装 AKShare 库，请运行: pip install akshare")
            self.ak = None

    def fetch_all(self, categories: list = None) -> Dict[str, pd.DataFrame]:
        """
        爬取所有数据

        参数:
        - categories: 要爬取的数据类别列表
                     ['macro', 'wage', 'expectation'] 或 None（全部）

        返回:
        - 数据字典
        """
        if self.ak is None:
            self.logger.error("AKShare 未安装，无法爬取数据")
            return {}

        if categories is None:
            categories = ['macro', 'expectation', 'bond']

        utils.print_header("数据爬取开始")

        # 宏观数据
        if 'macro' in categories:
            self._fetch_macro_data()

        # 预期数据
        if 'expectation' in categories:
            self._fetch_expectation_data()

        # 国债数据
        if 'bond' in categories:
            self._fetch_bond_data()

        utils.print_header("数据爬取完成")
        self._print_summary()

        return self.data_dict

    def _fetch_macro_data(self):
        """爬取宏观经济数据"""
        utils.print_section("爬取宏观经济数据")

        macro_functions = {
            'PPI': ('macro_china_ppi', 'PPI_原始数据.csv'),
            'CPI': ('macro_china_cpi', 'CPI_原始数据.csv'),
            '新增贷款': ('macro_china_new_financial_credit', '新增贷款_原始数据.csv'),
            'GDP': ('macro_china_gdp', 'GDP_原始数据.csv'),
        }

        for name, (func, filename) in macro_functions.items():
            self._fetch_single_data(name, func, filename)
            time.sleep(config.FETCH_INTERVAL)

    def _fetch_expectation_data(self):
        """爬取预期数据"""
        utils.print_section("爬取预期数据")

        expectation_functions = {
            'PMI': ('macro_china_pmi', 'PMI_原始数据.csv'),
        }

        for name, (func, filename) in expectation_functions.items():
            self._fetch_single_data(name, func, filename)
            time.sleep(config.FETCH_INTERVAL)

    def _fetch_bond_data(self):
        """爬取国债利率数据并计算10年期-2年期利差"""
        utils.print_section("爬取国债利率数据")

        try:
            self.logger.info("正在获取国债收益率数据...")

            # 获取中国国债收益率数据
            df_bond = self.ak.bond_zh_us_rate()

            if df_bond is None or df_bond.empty:
                utils.print_error("国债收益率数据获取失败")
                return False

            utils.print_success(f"国债收益率数据: {len(df_bond)}行数据")
            self.logger.info(f"国债数据列名: {df_bond.columns.tolist()}")

            # 查找所需列
            date_col = None
            rate_2y_col = None
            rate_10y_col = None

            for col in df_bond.columns:
                if '日期' in col or 'date' in str(col).lower():
                    date_col = col
                elif '中国国债收益率2年' in col:
                    rate_2y_col = col
                elif '中国国债收益率10年' in col and '-' not in col:
                    rate_10y_col = col

            if date_col is None or rate_2y_col is None or rate_10y_col is None:
                utils.print_error(f"未找到所需列。可用列: {df_bond.columns.tolist()}")
                return False

            utils.print_success(f"识别列: 日期={date_col}, 2年期={rate_2y_col}, 10年期={rate_10y_col}")

            # 提取所需列
            df_result = df_bond[[date_col, rate_2y_col, rate_10y_col]].copy()
            df_result.columns = ['date', 'rate_2y', 'rate_10y']

            # 转换日期格式
            df_result['date'] = pd.to_datetime(df_result['date'])

            # 转换收益率为数值类型
            df_result['rate_2y'] = pd.to_numeric(df_result['rate_2y'], errors='coerce')
            df_result['rate_10y'] = pd.to_numeric(df_result['rate_10y'], errors='coerce')

            # 删除缺失值
            df_result = df_result.dropna()

            # 计算利差：10年期 - 2年期
            df_result['spread'] = df_result['rate_10y'] - df_result['rate_2y']

            utils.print_success(f"计算利差完成: {len(df_result)}行有效数据")

            # 保存原始数据
            filename = '国债利差_原始数据.csv'
            filepath = os.path.join(config.DATA_DIR, filename)
            if utils.save_csv_safe(df_result, filepath):
                self.data_dict['国债利差'] = df_result
                utils.print_success(f"国债利差: {len(df_result)}行数据 (10年期-2年期)")
                return True


        except Exception as e:
            utils.print_error(f"国债数据获取失败: {e}")
            self.logger.exception("获取国债数据时出错")

        return False

    def _fetch_single_data(self, name: str, func, filename: str) -> bool:
        """
        爬取单个数据

        参数:
        - name: 数据名称
        - func: AKShare函数名或函数对象
        - filename: 保存文件名

        返回:
        - 是否成功
        """
        try:
            self.logger.info(f"正在获取{name}数据...")

            # 调用函数
            if callable(func):
                df = func()
            else:
                df = getattr(self.ak, func)()

            if df is not None and not df.empty:
                # 保存到字典
                self.data_dict[name] = df

                # 保存到文件
                filepath = os.path.join(config.DATA_DIR, filename)
                if utils.save_csv_safe(df, filepath):
                    utils.print_success(f"{name}: {len(df)}行数据")
                    return True

        except Exception as e:
            utils.print_error(f"{name}获取失败: {e}")
            self.logger.exception(f"获取{name}数据时出错")

        return False

    def _print_summary(self):
        """打印爬取摘要"""
        utils.print_section("爬取摘要")

        if not self.data_dict:
            utils.print_warning("未爬取到任何数据")
            return

        data = []
        for name, df in self.data_dict.items():
            rows = len(df)
            cols = len(df.columns)
            data.append([name, f"{rows}行", f"{cols}列"])

        utils.print_table(data, headers=["数据名称", "行数", "列数"])

    def save_all(self):
        """保存所有数据"""
        if not self.data_dict:
            return

        utils.print_section("保存所有数据")

        for name, df in self.data_dict.items():
            filename = f"{name}_原始数据.csv"
            filepath = os.path.join(config.DATA_DIR, filename)
            utils.save_csv_safe(df, filepath)


# 命令行入口
def main():
    """命令行主函数"""
    fetcher = DataFetcher()
    fetcher.fetch_all()
    fetcher.save_all()


if __name__ == "__main__":
    main()
