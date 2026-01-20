/*==============================================================================
  时间序列分析：扩展SVAR模型 - 通缩传导机制验证
  数据：GDP、PPI、新增贷款、CPI月度数据

  模型设定（基于predict.md第二步）：
  变量排序（Cholesky分解）：
    GDP -> PPI → Credit → CPI

  经济学含义：
  - GDP（最接近外生的变量）
  - PPI可同期响应供给冲击
  - Credit银行系统根据经济热度调整信贷标准
  - CPI作为整体指标，最后综合反映所有冲击

  作者：时间序列分析项目
  日期：2026-01
==============================================================================*/

clear all
set more off
set type double

// 设置工作目录
cd "C:\Users\123\OneDrive\桌面\辅修选修\岭院\时间序列\data"

/*==============================================================================
  第一部分：数据导入与整合（使用月度数据）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第一部分：数据导入与整合"
display "================================================================================"
display _newline
display "正在导入月度数据..."
display _newline

* 1. 导入CPI月度数据（包含整体CPI和服务CPI）
use "CPI_标准日期.dta", clear
rename date month_date
save "temp_cpi.dta", replace

* 2. 导入PPI月度数据
use "PPI_标准日期.dta", clear
rename date month_date
save "temp_ppi.dta", replace

* 3. 导入新增贷款月度数据（信贷渠道）
use "新增贷款_标准日期.dta", clear
rename date month_date
save "temp_credit.dta", replace

* 4. 导入GDP月度数据（使用插值后的月度数据）
use "GDP_标准日期.dta", clear
rename date month_date
save "temp_gdp.dta", replace

* 5. 导入PMI月度数据
use "PMI_标准日期.dta", clear
rename date month_date
save "temp_pmi.dta", replace

* 5. 合并所有月度数据
use "temp_cpi.dta", clear
merge 1:1 month_date using "temp_ppi.dta", nogenerate
merge 1:1 month_date using "temp_credit.dta", nogenerate
merge 1:1 month_date using "temp_gdp.dta", nogenerate
merge 1:1 month_date using "temp_pmi.dta", nogenerate

* 清理临时文件
erase "temp_cpi.dta"
erase "temp_ppi.dta"
erase "temp_credit.dta"
erase "temp_gdp.dta"
erase "temp_pmi.dta"

* 按日期排序
sort month_date

* 设置时间序列（月度）
gen t = _n
tsset t

* 将毫秒时间戳转换为Stata日期格式（从1960-01-01开始）
gen date_stata = month_date / (1000 * 60 * 60 * 24)
format date_stata %tdCY-N-D

* 保存合并后的月度数据
save "merged_extend_data.dta", replace

display "数据导入完成：使用月度数据进行扩展SVAR分析"
display "观测数量: " _N
display "时间范围: " month_date[1] " 至 " month_date[_N]
display _newline

/*==============================================================================
  第二部分：变量定义与预处理
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第二部分：变量定义与预处理"
display "================================================================================"
display _newline

* 变量命名说明：
* - ppi_yoy: PPI同比增长率（通缩部门价格指数）
* - credit: 新增贷款（信贷渠道）
* - pmi_yoy: 工资同比
* - cpi_national_yoy: CPI整体同比（整体通胀）
* - gdp_yoy: 不变价GDP同比

* 检查变量是否存在，如不存在则创建
* 注意：根据实际数据文件中的变量名进行调整

* 数据标准化
gen credit = dangyue_tongbizengzhang / 100
egen mean_pmi = mean(pmi_mfg_yoy)
egen sd_pmi = sd(pmi_mfg_yoy)
gen pmi_yoy = (pmi_mfg_yoy - mean_pmi) / sd_pmi

* 查看数据描述
describe
summarize

* 显示当前可用变量
display "当前数据集中的变量："
describe, short

/*==============================================================================
  第三部分：描述性统计与可视化
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第三部分：描述性统计与可视化"
display "================================================================================"
display _newline

* 生成时间序列图 - 价格变量
twoway (line ppi_yoy date_stata, lcolor(blue)) ///
       (line cpi_national_yoy date_stata, lcolor(cranberry)), ///
    title("价格指数同比增长率") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "PPI") label(2 "CPI整体")) ///
    xlabel(, format(%tdCY-N)) ///
    name(tsline_price, replace)
graph export "../output/扩展SVAR_价格变量时间序列图.png", replace width(1200)

* 相关性分析
display _newline "变量相关性矩阵："
correlate gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy

/*==============================================================================
  第四部分：ADF检验（平稳性检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第四部分：单位根检验（ADF检验）- 检验序列是否平稳"
display "================================================================================"
display _newline

display "H0: 序列存在单位根（不平稳）"
display "H1: 序列平稳"
display _newline

* 对PPI同比增长率进行ADF检验
display _newline "1. PPI同比增长率 - ADF检验"
dfuller ppi_yoy, lags(4) regress
dfuller ppi_yoy, lags(4) trend regress

* 对新增贷款进行ADF检验
display _newline "2. 新增贷款 - ADF检验"
dfuller credit, lags(4) regress
dfuller credit, lags(4) trend regress

* 对工资进行ADF检验
display _newline "3. 工资 - ADF检验"
dfuller pmi_yoy, lags(4) regress
dfuller pmi_yoy, lags(4) trend regress

* 对CPI整体同比进行ADF检验
display _newline "4. CPI整体同比 - ADF检验"
dfuller cpi_national_yoy, lags(4) regress
dfuller cpi_national_yoy, lags(4) trend regress

* 对GDP整体同比进行ADF检验
display _newline "4. GDP整体同比 - ADF检验"
dfuller gdp_yoy, lags(4) regress
dfuller gdp_yoy, lags(4) trend regress

* PP检验（Phillips-Perron检验）作为补充
display _newline(2)
display "================================================================================"
display "PP检验（补充验证）"
display "================================================================================"
display _newline

pperron ppi_yoy, lags(4)
pperron credit, lags(4)
pperron pmi_yoy, lags(4)
pperron cpi_national_yoy, lags(4)
pperron gdp_yoy, lags(4)

/*==============================================================================
  第五部分：协整检验（Johansen协整检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第五部分：Johansen协整检验 - 检验变量间是否存在长期均衡关系"
display "================================================================================"
display _newline

display "协整检验用于检验多个非平稳序列之间是否存在长期稳定的均衡关系"
display "H0: 不存在协整关系"
display "H1: 存在至少一个协整关系"
display _newline

* 进行Johansen协整检验
* trace检验（迹检验）
display "迹检验（Trace Test）："
vecrank gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, lags(4) trend(constant)

* max检验（最大特征值检验）
display _newline "最大特征值检验（Max Eigenvalue Test）："
vecrank gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, lags(4) trend(constant) max

/*==============================================================================
  第六部分：VAR模型估计
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第六部分：VAR模型估计"
display "================================================================================"
display _newline

* 确定最优滞后阶数
display "确定最优滞后阶数："
varsoc gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, maxlag(8)

* 估计VAR模型
* 变量顺序按照Cholesky分解的递归假设排列
* GDP -> PPI → Wage → Credit → CPI
display _newline "估计VAR模型（滞后4期）："
var gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, lags(1/3)

* 保存VAR估计结果
estimates store var_extend_model

* VAR模型诊断检验
display _newline "VAR模型诊断检验："

* 残差自相关检验（LM检验）
display _newline "残差自相关检验（LM检验）："
varlmar, mlag(4)

* 残差正态性检验（Jarque-Bera检验）
display _newline "残差正态性检验（Jarque-Bera检验）："
varnorm

/*==============================================================================
  第七部分：格兰杰因果检验
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第七部分：格兰杰因果检验 - 检验变量间的因果关系"
display "================================================================================"
display _newline

display "格兰杰因果检验用于判断一个变量的滞后值是否对另一个变量有预测作用"
display "H0: X不是Y的格兰杰原因（X的滞后值对预测Y没有帮助）"
display "H1: X是Y的格兰杰原因（X的滞后值对预测Y有帮助）"
display _newline

display "重点关注以下因果链条："
display "  Credit → CPI（债务-信贷渠道）"
display _newline

* 所有变量的格兰杰因果检验
vargranger

/*==============================================================================
  第八部分：AR根表图（稳定性检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第八部分：AR根表图 - VAR模型稳定性检验"
display "================================================================================"
display _newline

display "AR根表图用于检验VAR模型的稳定性"
display "所有特征根的模必须小于1（在单位圆内），模型才是稳定的"
display _newline

* VAR稳定性检验并绘制AR根图
varstable, graph
graph export "../output/扩展SVAR_AR根表图.png", replace width(1200)

* 列出所有特征根
varstable

/*==============================================================================
  第九部分：SVAR模型设置与估计
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第九部分：SVAR模型估计"
display "================================================================================"
display _newline

display "识别策略：Cholesky分解（递归同期因果关系）"
display _newline
display "变量排序及其经济学含义："
display "  1. GDP：可同期响应GDP（最接近外生的变量）"
display "  2. PPI：可同期响应供给冲击"
display "  3. PMI：可同期响应工资冲击"
display "  4. Credit：银行系统根据经济热度调整信贷标准"
display "  5. CPI：作为整体指标，最后综合反映所有冲击"
display _newline

* 定义SVAR的短期约束矩阵（Cholesky分解）
* 6变量系统的下三角矩阵
* A矩阵：同期系数矩阵（下三角，对角线为1）
matrix A = (1, 0, 0, 0, 0 \ ///
            ., 1, 0, 0, 0 \ ///
            ., ., 1, 0, 0 \ ///
            ., ., ., 1, 0 \ ///
            ., ., ., ., 1)

* B矩阵：结构冲击的方差矩阵（对角矩阵）
matrix B = (., 0, 0, 0, 0 \ ///
            0, ., 0, 0, 0 \ ///
            0, 0, ., 0, 0 \ ///
            0, 0, 0, ., 0 \ ///
            0, 0, 0, 0, .)

* 估计SVAR模型
svar gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, ///
    lags(1/3) aeq(A) beq(B)

estimates store svar_extend_model

/*==============================================================================
  第十部分：脉冲响应函数分析 - 验证传导机制
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第十部分：脉冲响应函数分析 - 验证传导机制"
display "================================================================================"
display _newline

* 创建IRF结果
irf create svar_extend_irf, set(../output/svar_extend_irf) replace step(24)

/*--------------------------------------------------------------------------
  检验1：债务-通缩螺旋
  冲击：PPI负向冲击
  观察：信贷增速是否持续下降（6-12个月）
--------------------------------------------------------------------------*/

display _newline "检验1：债务-工资螺旋（PPI冲击→信贷）"

* PPI冲击对信贷的响应
irf graph oirf, impulse(ppi_yoy) response(credit) ///
    title("检验2：债务-工资螺旋") ///
    subtitle("PPI冲击对信贷的脉冲响应") ///
    note("若信贷收缩，印证'ppi下跌→资产负债表恶化→信贷收缩'的螺旋") ///
    name(irf_debt, replace)
graph export "../output/扩展SVAR_IRF_债务通缩螺旋.png", replace width(1200)

/*--------------------------------------------------------------------------
  检验2：工资-通缩螺旋
  冲击：PPI负向冲击
  观察：工资增速是否持续下降（6-12个月）
--------------------------------------------------------------------------*/

display _newline "检验2：工资-通缩螺旋（PPI冲击→工资）"

* PPI冲击对信贷的响应
irf graph oirf, impulse(ppi_yoy) response(pmi_yoy) ///
    title("检验2：工资-通缩螺旋") ///
    subtitle("PPI冲击对工资的脉冲响应") ///
    note("若工资收缩，印证'ppi下跌→工资减少'的螺旋") ///
    name(irf_wage, replace)
graph export "../output/扩展SVAR_IRF_工资通缩螺旋.png", replace width(1200)

/*--------------------------------------------------------------------------
  检验3：工资-信贷螺旋
  冲击：PMI负向冲击
  观察：信贷增速是否增加（6-12个月）
--------------------------------------------------------------------------*/

display _newline "检验3：工资-信贷螺旋（PMI冲击→信贷）"

* PPI冲击对信贷的响应
irf graph oirf, impulse(pmi_yoy) response(pmi_yoy) ///
    title("检验2：工资-信贷螺旋") ///
    subtitle("PMI冲击对信贷的脉冲响应") ///
    note("若工资收缩，印证'工资减少->信贷增加'的螺旋") ///
    name(irf_wage_debt, replace)
graph export "../output/扩展SVAR_IRF_工资信贷螺旋.png", replace width(1200)

/*--------------------------------------------------------------------------
  核心检验：结构性通缩到全面通缩的传导
  冲击：PPI负向冲击
  观察：CPI整体的响应路径
--------------------------------------------------------------------------*/

display _newline "核心检验：结构性通缩→全面通缩（PPI→CPI整体）"

* PPI冲击对CPI整体的响应
irf graph oirf, impulse(ppi_yoy) response(cpi_national_yoy) ///
    title("核心检验：结构性通缩→全面通缩") ///
    subtitle("PPI冲击对CPI整体的脉冲响应") ///
    note("观察PPI通缩冲击是否传导至整体CPI") ///
    name(irf_core, replace)
graph export "../output/扩展SVAR_IRF_核心传导机制.png", replace width(1200)

* 绘制完整的传导链条：GDP对所有变量的影响
irf graph oirf, impulse(gdp_yoy) ///
    response(gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy) ///
    title("GDP冲击对所有变量的脉冲响应") ///
    subtitle("结构性通缩的完整传导机制") ///
    name(irf_gdp_all, replace)
graph export "../output/扩展SVAR_IRF_GDP完整传导.png", replace width(1200)

* CPI整体对各变量冲击的响应（综合影响）
irf graph oirf, impulse(gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy) ///
    response(cpi_national_yoy) ///
    title("CPI整体对各变量冲击的响应") ///
    subtitle("识别通缩压力的主要来源") ///
    name(irf_cpi, replace)
graph export "../output/扩展SVAR_IRF_CPI响应.png", replace width(1200)

* 累积脉冲响应（长期效应）
irf graph coirf, impulse(ppi_yoy) response(cpi_national_yoy) ///
    title("CPI对PPI冲击的累积响应") ///
    subtitle("长期传导效应") ///
    name(cirf, replace)
graph export "../output/扩展SVAR_IRF_累积响应.png", replace width(1200)

/*==============================================================================
  第十一部分：方差分解 - 量化各渠道贡献度
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第十一部分：方差分解分析 - 量化各渠道贡献度"
display "================================================================================"
display _newline

display "在12-24个月预测期内，分解整体CPI波动的来源"
display "验证逻辑：若PPI冲击对CPI整体波动的贡献度随时间递增"
display "（尤其6个月后超过30%），说明结构性通缩是全面通缩的重要驱动因素"
display _newline

* CPI整体的方差分解
display "CPI整体的方差分解（显示24期）："
irf table fevd, impulse(cpi_national_yoy ppi_yoy pmi_yoy credit gdp_yoy ) ///
    response(cpi_national_yoy) step(24)

* 绘制CPI方差分解图
irf graph fevd, impulse(gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy) ///
    response(cpi_national_yoy) ///
    title("CPI整体的方差分解") ///
    subtitle("各冲击源对CPI波动的贡献度") ///
    name(fevd_cpi, replace)
graph export "../output/扩展SVAR_FEVD_CPI.png", replace width(1200)

* PPI的方差分解
irf graph fevd, impulse(gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy) ///
    response(ppi_yoy) ///
    title("PPI的方差分解") ///
    name(fevd_ppi, replace)
graph export "../output/扩展SVAR_FEVD_PPI.png", replace width(1200)

/*==============================================================================
  第十二部分：拟合与预测结果
==============================================================================*/

display _newline(2)
display "================================================================================"
display "第十二部分：拟合与预测分析"
display "================================================================================"
display _newline

* 保存当前VAR模型估计结果
estimates restore var_extend_model

* 1. 样本内拟合优度评估
display _newline "1. 样本内拟合优度："
display _newline

* 获取拟合值和残差
predict ppi_fitted if e(sample), equation(ppi_yoy) xb
predict credit_fitted if e(sample), equation(credit) xb
predict pmi_fitted if e(sample), equation(pmi_yoy) xb
predict cpi_fitted if e(sample), equation(cpi_national_yoy) xb
predict gdp_fitted if e(sample), equation(gdp_yoy) xb

predict ppi_resid if e(sample), equation(ppi_yoy) residuals
predict credit_resid if e(sample), equation(credit) residuals
predict pmi_resid if e(sample), equation(pmi_yoy) residuals
predict cpi_resid if e(sample), equation(cpi_national_yoy) residuals
predict gdp_resid if e(sample), equation(gdp_yoy) residuals

* 计算R方和RMSE
quietly {
    * PPI的拟合优度
    correlate ppi_yoy ppi_fitted if e(sample)
    local r2_ppi = r(rho)^2
    gen ppi_sqerr = ppi_resid^2 if e(sample)
    summarize ppi_sqerr
    local rmse_ppi = sqrt(r(mean))

    * PMI的拟合优度
    correlate pmi_yoy pmi_fitted if e(sample)
    local r2_pmi = r(rho)^2
    gen pmi_sqerr = pmi_resid^2 if e(sample)
    summarize pmi_sqerr
    local rmse_pmi = sqrt(r(mean))

    * 信贷的拟合优度
    correlate credit credit_fitted if e(sample)
    local r2_credit = r(rho)^2
    gen credit_sqerr = credit_resid^2 if e(sample)
    summarize credit_sqerr
    local rmse_credit = sqrt(r(mean))

    * CPI整体的拟合优度
    correlate cpi_national_yoy cpi_fitted if e(sample)
    local r2_cpi = r(rho)^2
    gen cpi_sqerr = cpi_resid^2 if e(sample)
    summarize cpi_sqerr
    local rmse_cpi = sqrt(r(mean))

    * CPI整体的拟合优度
    correlate gdp_yoy gdp_fitted if e(sample)
    local r2_gdp = r(rho)^2
    gen gdp_sqerr = gdp_resid^2 if e(sample)
    summarize gdp_sqerr
    local rmse_gdp = sqrt(r(mean))
}

display "PPI拟合优度 (R²): " %6.4f `r2_ppi' "  RMSE: " %6.4f `rmse_ppi'
display "信贷拟合优度 (R²): " %6.4f `r2_credit' "  RMSE: " %6.4f `rmse_credit'
display "PMI拟合优度 (R²): " %6.4f `r2_pmi' "  RMSE: " %6.4f `rmse_pmi'
display "CPI整体拟合优度 (R²): " %6.4f `r2_cpi' "  RMSE: " %6.4f `rmse_cpi'
display "GDP整体拟合优度 (R²): " %6.4f `r2_gdp' "  RMSE: " %6.4f `rmse_gdp'

* 2. 绘制拟合图
display _newline "2. 绘制拟合结果："

* CPI整体拟合图
twoway (line cpi_national_yoy date_stata, lcolor(blue) lwidth(medium)) ///
       (line cpi_fitted date_stata, lcolor(red) lpattern(dash) lwidth(medium)), ///
    title("CPI整体同比增长率：实际值 vs 拟合值") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "实际值") label(2 "拟合值")) ///
    xlabel(, format(%tdCY-N)) ///
    name(fit_cpi, replace)
graph export "../output/扩展SVAR_拟合图_CPI.png", replace width(1200)

* PPI拟合图
twoway (line ppi_yoy date_stata, lcolor(blue) lwidth(medium)) ///
       (line ppi_fitted date_stata, lcolor(red) lpattern(dash) lwidth(medium)), ///
    title("PPI同比增长率：实际值 vs 拟合值") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "实际值") label(2 "拟合值")) ///
    xlabel(, format(%tdCY-N)) ///
    name(fit_ppi, replace)
graph export "../output/扩展SVAR_拟合图_PPI.png", replace width(1200)

* 3. 样本外预测（预测未来6个月）
display _newline "3. 样本外预测（未来6个月）："
display _newline

matrix A_est = e(A)  // 保存结构参数

* 重新估计简约式VAR（用相同变量）
var gdp_yoy ppi_yoy pmi_yoy credit cpi_national_yoy, lags(1/3)

* 保存当前观测数
quietly count
local last_obs = r(N)

* 扩展数据集以容纳预测值
quietly set obs `=`last_obs' + 6'

* 为新观测生成时间索引
quietly replace t = _n if t == .

* 重新设置时间序列
tsset t

* 使用fcast进行动态预测
fcast compute f_, step(6)

* 绘制预测图 - CPI整体
tsline cpi_national_yoy f_cpi_national_yoy if t >= `last_obs' - 24, ///
    title("CPI整体同比增长率预测（未来6个月）") ///
    ytitle("同比增长率 (%)") xtitle("时间") ///
    legend(label(1 "实际值") label(2 "预测值")) ///
    tline(`last_obs') ///
    name(forecast_cpi, replace)
graph export "../output/扩展SVAR_预测图_CPI.png", replace width(1200)

* 绘制预测图 - PPI
tsline ppi_yoy f_ppi_yoy if t >= `last_obs' - 24, ///
    title("PPI同比增长率预测（未来6个月）") ///
    ytitle("同比增长率 (%)") xtitle("时间") ///
    legend(label(1 "实际值") label(2 "预测值")) ///
    tline(`last_obs') ///
    name(forecast_ppi, replace)
graph export "../output/扩展SVAR_预测图_PPI.png", replace width(1200)

* 恢复原始数据集大小
quietly drop if t > `last_obs'
tsset t

* 清理临时变量
drop ppi_fitted pmi_fitted credit_fitted cpi_fitted gdp_fitted
drop ppi_resid pmi_resid credit_resid cpi_resid gdp_resid
drop ppi_sqerr pmi_sqerr credit_sqerr cpi_sqerr gdp_sqerr

/*==============================================================================
  第十三部分：结果导出与分析结论
==============================================================================*/

* 导出所有结果到日志文件
log using "../output/extend_svar_results.log", text replace

display _newline(2)
display "================================================================================"
display "扩展SVAR模型分析结果汇总"
display "================================================================================"

* 显示VAR估计结果
estimates restore var_extend_model
estimates replay

* 显示SVAR估计结果
estimates restore svar_extend_model
estimates replay

* 显示格兰杰因果检验结果
estimates restore var_extend_model
vargranger

log close

/*==============================================================================
  第十四部分：分析结论 - 通缩传导机制验证
==============================================================================*/

display _newline(2)
display "================================================================================"
display "分析结论：通缩传导机制验证"
display "================================================================================"
display _newline

display "基于扩展SVAR模型分析，验证以下三大传导机制："
display _newline

display "【传导机制1：预期传染通道】"
display "  结构性通缩 → 通胀预期下降 → 消费延迟/投资观望 → CPI整体下降"
display "  判断标准：若响应在3-6个月内显著为负，说明预期传染存在"
display _newline

display "【传导机制2：债务-通缩螺旋】"
display "  PPI下降 → 资产价格下跌 → 抵押品价值缩水 → 信贷收缩 → 进一步通缩"
display "  检验指标：PPI冲击对信贷（credit）的脉冲响应"
display "  判断标准：若信贷在6-12个月内持续下降，印证螺旋效应"
display _newline

display "【核心结论指标】"
display "  方差分解中PPI对CPI整体波动的贡献度："
display "  - 若6个月后超过30%，说明结构性通缩是全面通缩的重要驱动因素"
display "  - 若贡献度随时间递增，说明传导效应在加强"
display _newline

display "【政策含义】"
display "  1. 干预窗口期：必须在预期形成但尚未固化时强力介入"
display "  2. 政策组合：需'货币+财政+收入政策+制度改革'组合拳"
display "  3. 预期管理：比实际政策更重要的是改变叙事"
display "  4. 结构性改革：需同步解决初始部门的产能过剩"
display _newline

display "================================================================================"
display "分析完成！"
display "================================================================================"
display _newline
display "结果已保存到 output 文件夹："
display "  - 价格变量时间序列图"
display "  - 传导渠道时间序列图"
display "  - AR根表图（VAR稳定性检验）"
display "  - IRF_预期传染效应（检验1）"
display "  - IRF_债务通缩螺旋（检验2）"
display "  - IRF_劳动力市场渗透（检验3）"
display "  - IRF_核心传导机制"
display "  - IRF_PPI完整传导"
display "  - IRF_CPI响应"
display "  - IRF_累积响应"
display "  - FEVD_CPI（方差分解）"
display "  - FEVD_PPI"
display "  - FEVD_通胀预期"
display "  - 拟合图（CPI、PPI）"
display "  - 预测图（CPI、PPI）"
display "  - extend_svar_results.log"
display "================================================================================"

/*==============================================================================
  结束
==============================================================================*/
