#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列数据处理主程序
统一入口，调用各个功能模块

使用方法:
    python main.py --help                   查看帮助
    python main.py --all                    执行所有步骤（包括Stata分析）
    python main.py --fetch                  爬取数据
    python main.py --unify-date             统一日期格式
    python main.py --interpolate            插值为月度
    python main.py --to-dta                 转换为DTA格式
    python main.py --run-stata              运行Stata SVAR分析
"""

import sys
import os
import argparse
import time
import subprocess
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import utils
from modules.data_fetcher import DataFetcher
from modules.date_processor import DateProcessor
from modules.frequency_converter import FrequencyConverter
from modules.format_converter import FormatConverter


class DataPipeline:
    """数据处理流水线"""

    def __init__(self, verbose: bool = True):
        """
        初始化

        参数:
        - verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.logger = utils.logger

        # 初始化各个模块
        self.data_fetcher = DataFetcher()
        self.date_processor = DateProcessor()
        self.frequency_converter = FrequencyConverter()
        self.format_converter = FormatConverter()

        # 统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'duration': 0,
            'steps_completed': 0,
            'steps_total': 0,
        }

    def run_all(self, run_stata: bool = True):
        """执行所有步骤

        参数:
        - run_stata: 是否运行Stata分析
        """
        utils.print_header("时间序列数据处理完整流程", width=100)

        self.stats['start_time'] = time.time()
        self.stats['steps_total'] = 6 if run_stata else 4

        steps = [
            ("爬取数据", self.step_fetch_data),
            ("统一日期格式", self.step_unify_dates),
            ("频率统一（插值）", self.step_interpolate),
            ("格式转换（DTA）", self.step_convert_to_dta),
        ]

        if run_stata:
            steps.append(("运行Stata分析", self.step_run_stata))
            steps.append(("运行extend_Stata分析", self.step_run_extend_stata))

        for i, (step_name, step_func) in enumerate(steps, 1):
            utils.print_header(f"步骤 {i}/{len(steps)}: {step_name}", width=100)

            try:
                success = step_func()
                if success:
                    self.stats['steps_completed'] += 1
                    utils.print_success(f"步骤 {i} 完成")
                else:
                    utils.print_warning(f"步骤 {i} 部分完成或跳过")

            except Exception as e:
                utils.print_error(f"步骤 {i} 失败: {e}")
                self.logger.exception(f"执行步骤{i}时出错")

            print()  # 空行分隔

        self.stats['end_time'] = time.time()
        self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']

        self._print_final_summary()

    def step_fetch_data(self) -> bool:
        """步骤1: 爬取数据"""
        try:
            data_dict = self.data_fetcher.fetch_all()
            return len(data_dict) > 0
        except Exception as e:
            self.logger.error(f"数据爬取失败: {e}")
            return False

    def step_unify_dates(self) -> bool:
        """步骤2: 统一日期格式"""
        try:
            success, fail = self.date_processor.process_all_files()
            return success > 0
        except Exception as e:
            self.logger.error(f"日期统一失败: {e}")
            return False

    def step_interpolate(self) -> bool:
        """步骤3: 频率统一"""
        try:
            count = self.frequency_converter.convert_all_to_monthly()
            return count > 0
        except Exception as e:
            self.logger.error(f"频率转换失败: {e}")
            return False

    def step_convert_to_dta(self) -> bool:
        """步骤4: 转换为DTA"""
        try:
            count = self.format_converter.convert_all_to_dta()
            return count > 0
        except Exception as e:
            self.logger.error(f"格式转换失败: {e}")
            return False

    def step_run_stata(self) -> bool:
        """步骤5: 运行Stata分析"""
        try:
            return run_stata_analysis("svar_analysis.do")
        except Exception as e:
            self.logger.error(f"Stata分析失败: {e}")
            return False

    def step_run_extend_stata(self) -> bool:
        """步骤6: 运行extend_Stata分析"""
        try:
            return run_stata_analysis("extend_svar_analysis.do")
        except Exception as e:
            self.logger.error(f"extend_Stata分析失败: {e}")
            return False

    def _print_final_summary(self):
        """打印最终总结"""
        utils.print_header("处理完成", width=100, char="=")

        summary_data = [
            ["开始时间", datetime.fromtimestamp(self.stats['start_time']).strftime("%Y-%m-%d %H:%M:%S")],
            ["结束时间", datetime.fromtimestamp(self.stats['end_time']).strftime("%Y-%m-%d %H:%M:%S")],
            ["总耗时", utils.format_duration(self.stats['duration'])],
            ["完成步骤", f"{self.stats['steps_completed']}/{self.stats['steps_total']}"],
        ]

        utils.print_table(summary_data, headers=["项目", "值"])

        # 检查生成的文件
        self._list_output_files()

        utils.print_section("下一步建议", width=100)
        print("  1. 查看生成的数据文件")
        print("  2. 使用统一月度数据集进行分析")
        print("  3. 在Stata中导入DTA文件")
        print("  4. 运行 SVAR 分析: python main.py --run-stata")
        print("  5. 进行数据质量检查和单位根检验")
        print()

    def _list_output_files(self):
        """列出输出文件"""
        utils.print_section("生成的文件", width=100)

        key_files = [
            '统一月度数据集.csv',
            'GDP_月度.csv',
        ]

        file_data = []
        for filename in key_files:
            filepath = os.path.join(config.DATA_DIR, filename)
            if os.path.exists(filepath):
                size = utils.get_file_size(filepath)
                file_data.append(["✓", filename, size])
            else:
                file_data.append(["✗", filename, "-"])

        utils.print_table(file_data, headers=["状态", "文件名", "大小"])


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="时间序列数据处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行完整流程
  python main.py --all

  # 仅爬取数据
  python main.py --fetch

  # 统一日期格式
  python main.py --unify-date

  # 插值为月度
  python main.py --interpolate

  # 转换为DTA格式
  python main.py --to-dta

  # 运行Stata SVAR分析
  python main.py --run-stata

  # 执行多个步骤
  python main.py --fetch --unify-date

  # 查看数据目录
  python main.py --list

  # 生成数据报告
  python main.py --report
        """
    )

    # 功能选项
    group = parser.add_argument_group('功能选项')
    group.add_argument('--all', action='store_true',
                      help='执行所有步骤（爬取、统一、插值、转换）')
    group.add_argument('--fetch', action='store_true',
                      help='爬取原始数据')
    group.add_argument('--unify-date', action='store_true',
                      help='统一日期格式为YYYY-MM-DD')
    group.add_argument('--interpolate', action='store_true',
                      help='将季度/年度数据插值为月度')
    group.add_argument('--to-dta', action='store_true',
                      help='将CSV转换为Stata DTA格式')
    group.add_argument('--run-stata', action='store_true',
                      help='运行Stata SVAR分析')
    group.add_argument('--run-stata-extend', action='store_true',
                       help='运行Stata extend_SVAR分析')
    group.add_argument('--list', action='store_true',
                      help='列出数据目录中的文件')
    group.add_argument('--report', action='store_true',
                      help='生成数据质量报告')

    # 高级选项
    adv_group = parser.add_argument_group('高级选项')
    adv_group.add_argument('--fetch-categories', nargs='+',
                          choices=['macro', 'expectation', 'bond'],
                          help='指定要爬取的数据类别')
    adv_group.add_argument('--files', nargs='+',
                          help='指定要处理的文件列表')

    # 通用选项
    gen_group = parser.add_argument_group('通用选项')
    gen_group.add_argument('-v', '--verbose', action='store_true',
                          help='显示详细信息')
    gen_group.add_argument('-q', '--quiet', action='store_true',
                          help='静默模式（最少输出）')
    gen_group.add_argument('--log-level',
                          choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                          default='INFO',
                          help='日志级别')

    return parser


def list_files():
    """列出数据目录中的文件"""
    utils.print_header("数据文件列表")

    categories = {
        '原始数据': '*_原始数据.csv',
        '标准日期': '*_标准日期.csv',
        '月度数据': '*_月度.csv',
        'DTA文件': '*.dta',
        '统一数据集': '统一*.csv',
    }

    for category, pattern in categories.items():
        utils.print_section(category)

        files = []
        for f in os.listdir(config.DATA_DIR):
            if pattern.startswith('*'):
                if f.endswith(pattern[1:]):
                    files.append(f)
            elif pattern.endswith('*'):
                if f.startswith(pattern[:-1]):
                    files.append(f)
            else:
                if pattern in f:
                    files.append(f)

        if files:
            for f in sorted(files):
                size = utils.get_file_size(os.path.join(config.DATA_DIR, f))
                print(f"  {f} ({size})")
        else:
            print("  (无文件)")
        print()


def run_stata_analysis(file_name) -> bool:
    """运行Stata分析脚本（使用pystata）"""
    utils.print_header("运行Stata SVAR分析")

    # 查找Stata do文件
    do_file = os.path.join(config.CODE_DIR, file_name)

    if not os.path.exists(do_file):
        utils.print_error(f"Stata脚本不存在: {do_file}")
        return False

    utils.print_success(f"找到Stata脚本: {os.path.basename(do_file)}")

    # 导入stata_setup
    try:
        import stata_setup
        utils.print_success("stata_setup模块加载成功")
    except ImportError:
        utils.print_error("未安装stata_setup模块")
        utils.print_warning("请运行: pip install stata-setup")
        utils.print_warning("然后运行: pip install pystata")
        utils.print_warning("或手动在Stata中运行: do svar_analysis.do")
        return False

    # 初始化Stata
    try:
        utils.print_section("初始化Stata")

        # 尝试常见的Stata安装路径
        stata_paths = [
            r"D:\stata19",
        ]

        # 检查环境变量中是否定义了STATA_DIR
        if 'STATA_DIR' in os.environ:
            stata_paths.insert(0, os.environ['STATA_DIR'])

        stata_dir = None
        for path in stata_paths:
            if os.path.exists(path):
                stata_dir = path
                break

        if stata_dir is None:
            utils.print_error("未找到Stata安装目录")
            utils.print_warning("请确保Stata已安装在以下路径之一：")
            utils.print_warning("  - D:\\stata19")
            utils.print_warning("或设置环境变量STATA_DIR指向Stata安装目录")
            return False

        utils.print_success(f"找到Stata目录: {stata_dir}")

        # 检测Stata版本类型
        stata_edition = 'mp'  # 默认使用MP

        # 检查目录中的可执行文件来确定版本
        try:
            files = os.listdir(stata_dir)
            if any('mp-64.dll' in f.lower() or 'statamp' in f.lower() for f in files):
                stata_edition = 'mp'
            elif any('se-64.dll' in f.lower() or 'statase' in f.lower() for f in files):
                stata_edition = 'se'
            elif any('be-64.dll' in f.lower() or 'statabe' in f.lower() for f in files):
                stata_edition = 'be'
        except:
            pass

        # 尝试初始化Stata（优先尝试检测到的版本）
        editions = [stata_edition] + [e for e in ['mp', 'se', 'be'] if e != stata_edition]
        stata_initialized = False

        for edition in editions:
            try:
                print(f"  尝试初始化Stata {edition.upper()}版本...")
                stata_setup.config(stata_dir, edition)
                utils.print_success(f"Stata已成功初始化 ({edition.upper()}版)")
                stata_initialized = True
                break
            except Exception as e:
                if 'shared library' in str(e):
                    print(f"  {edition.upper()}版未找到，尝试其他版本...")
                else:
                    utils.logger.debug(f"初始化Stata ({edition}) 失败: {e}")
                continue

        if not stata_initialized:
            raise Exception(f"无法初始化Stata。\n请检查：\n1. Stata是否正确安装在 {stata_dir}\n2. 是否有StataMP-64.exe或StataSE-64.exe等可执行文件")

    except Exception as e:
        utils.print_error(f"Stata初始化失败: {e}")
        utils.print_warning("请确保Stata已正确安装")
        utils.logger.exception("Stata初始化失败")
        return False

    # 运行Stata脚本
    try:
        utils.print_section("执行Stata脚本")
        print(f"  脚本: {os.path.basename(do_file)}")
        print(f"  工作目录: {config.CODE_DIR}")
        print()

        # 切换到代码目录
        original_dir = os.getcwd()
        os.chdir(config.CODE_DIR)

        # 导入pystata的stata模块
        from pystata import stata

        # 运行do文件
        stata.run(f'do "{do_file}"', echo=True)

        # 恢复原目录
        os.chdir(original_dir)

        # 检查日志文件
        log_file = do_file.replace('.do', '.log')
        if os.path.exists(log_file):
            utils.print_success(f"Stata日志已生成: {os.path.basename(log_file)}")

        # 检查输出目录
        output_dir = os.path.join(os.path.dirname(config.CODE_DIR), 'output')
        if os.path.exists(output_dir):
            files = os.listdir(output_dir)
            if files:
                utils.print_success(f"生成了 {len(files)} 个输出文件")

        utils.print_success("Stata分析完成")
        return True

    except Exception as e:
        utils.print_error(f"运行Stata时出错: {e}")
        utils.logger.exception("执行Stata时出错")
        # 恢复原目录
        try:
            os.chdir(original_dir)
        except:
            pass
        return False


def generate_report():
    """生成数据质量报告"""
    utils.print_header("数据质量报告")

    # 检查关键文件
    key_files = [
        '统一月度数据集.csv',
        'CPI_标准日期.csv',
        'PPI_标准日期.csv',
        'GDP_月度.csv',
    ]

    for filename in key_files:
        filepath = os.path.join(config.DATA_DIR, filename)

        if not os.path.exists(filepath):
            utils.print_warning(f"文件不存在: {filename}")
            continue

        df = utils.read_csv_safe(filepath)
        if df is None:
            continue

        utils.print_section(filename)

        report = utils.generate_data_quality_report(df, filename)

        print(f"  行数: {report['rows']}")
        print(f"  列数: {report['columns']}")
        print(f"  内存: {report['memory_usage']}")

        if report['date_range']:
            print(f"  日期范围: {report['date_range']}")

        if report['missing_values']:
            print(f"  缺失值:")
            for col, stats in report['missing_values'].items():
                print(f"    - {col}: {stats['count']} ({stats['percentage']}%)")
        else:
            print(f"  缺失值: 无")

        print()


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 没有任何参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # 设置日志级别
    if args.quiet:
        config.VERBOSE = False
        config.SHOW_PROGRESS = False
    elif args.verbose:
        config.VERBOSE = True

    # 创建流水线
    pipeline = DataPipeline(verbose=config.VERBOSE)

    # 执行相应功能
    if args.all:
        pipeline.run_all(run_stata=True)

    elif args.list:
        list_files()

    elif args.report:
        generate_report()

    else:
        # 执行选定的步骤
        executed = False

        if args.fetch:
            pipeline.step_fetch_data()
            executed = True

        if args.unify_date:
            pipeline.step_unify_dates()
            executed = True

        if args.interpolate:
            pipeline.step_interpolate()
            executed = True

        if args.to_dta:
            pipeline.step_convert_to_dta()
            executed = True

        if args.run_stata:
            run_stata_analysis("svar_analysis.do")
            executed = True

        if args.run_stata_extend:
            run_stata_analysis("extend_svar_analysis.do")
            executed = True

        if not executed:
            parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        utils.logger.exception("程序异常退出")
        print(f"\n错误: {e}")
        sys.exit(1)
