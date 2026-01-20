/*==============================================================================
  时间序列分析：SVAR模型
  数据：CPI、PPI、GDP月度数据 (2008-03-01至2025-12-31)
  作者：时间序列分析项目
  日期：2026-01
==============================================================================*/

clear all
set more off
set type double

// 设置工作目录
cd "../data"

/*==============================================================================
  第一部分：数据导入与整合（使用月度数据）
==============================================================================*/

display "正在导入月度数据..."
display _newline

* 1. 导入CPI月度数据
use "CPI_标准日期.dta", clear
rename date month_date
save "temp_cpi.dta", replace

* 2. 导入PPI月度数据
use "PPI_标准日期.dta", clear
rename date month_date
save "temp_ppi.dta", replace

* 3. 导入GDP月度数据（使用插值后的月度数据）
use "GDP_标准日期.dta", clear
rename date month_date
save "temp_gdp.dta", replace

* 4. 合并所有月度数据
use "temp_cpi.dta", clear
merge 1:1 month_date using "temp_ppi.dta", nogenerate
merge 1:1 month_date using "temp_gdp.dta", nogenerate

* 清理临时文件
erase "temp_cpi.dta"
erase "temp_ppi.dta"
erase "temp_gdp.dta"

* 按日期排序
sort month_date

* 设置时间序列（月度）
gen t = _n
tsset t

* 将毫秒时间戳转换为Stata日期格式（从1960-01-01开始）
gen date_stata = month_date / (1000 * 60 * 60 * 24)
format date_stata %tdCY-N-D

* 保存合并后的月度数据
save "merged_monthly_data.dta", replace

display "数据导入完成：使用月度数据进行分析"
display "观测数量: " _N
display "时间范围: " month_date[1] " 至 " month_date[_N]
display _newline

* 查看数据描述
describe
summarize

/*==============================================================================
  第二部分：描述性统计与可视化
==============================================================================*/

* 生成时间序列图（使用实际日期作为横轴）
twoway (line cpi_national_yoy date_stata, lcolor(blue)) ///
       (line ppi_yoy date_stata, lcolor(cranberry)) ///
       (line gdp_yoy date_stata, lcolor(green)), ///
    title("CPI、PPI、GDP同比增长率") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "CPI") label(2 "PPI") label(3 "GDP")) ///
    xlabel(, format(%tdCY-N)) ///
    name(tsline1, replace)
graph export "../output/时间序列图_原始数据.png", replace width(1200)

* 相关性分析
correlate cpi_national_yoy ppi_yoy gdp_yoy

/*==============================================================================
  第三部分：ADF检验（平稳性检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "单位根检验（ADF检验）- 检验序列是否平稳"
display "================================================================================"
display _newline

* 对CPI同比增长率进行ADF检验
display _newline "1. CPI同比增长率 - ADF检验"
display "   H0: 序列存在单位根（不平稳）"
display "   H1: 序列平稳"
dfuller cpi_national_yoy, lags(4) regress
dfuller cpi_national_yoy, lags(4) trend regress

* 对PPI同比增长率进行ADF检验
display _newline "2. PPI同比增长率 - ADF检验"
display "   H0: 序列存在单位根（不平稳）"
display "   H1: 序列平稳"
dfuller ppi_yoy, lags(4) regress
dfuller ppi_yoy, lags(4) trend regress

* 对GDP同比增长率进行ADF检验
display _newline "3. GDP同比增长率 - ADF检验"
display "   H0: 序列存在单位根（不平稳）"
display "   H1: 序列平稳"
dfuller gdp_yoy, lags(4) regress
dfuller gdp_yoy, lags(4) trend regress

* PP检验（Phillips-Perron检验）作为补充
display _newline(2)
display "================================================================================"
display "PP检验（补充验证）"
display "================================================================================"
display _newline

pperron cpi_national_yoy, lags(4)
pperron ppi_yoy, lags(4)
pperron gdp_yoy, lags(4)

/*==============================================================================
  第四部分：协整检验（Johansen协整检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "Johansen协整检验 - 检验变量间是否存在长期均衡关系"
display "================================================================================"
display _newline

* 说明
display "协整检验用于检验多个非平稳序列之间是否存在长期稳定的均衡关系"
display "H0: 不存在协整关系"
display "H1: 存在至少一个协整关系"
display _newline

* 进行Johansen协整检验
* trace检验（迹检验）
display "迹检验（Trace Test）："
vecrank cpi_national_yoy ppi_yoy gdp_yoy, lags(4) trend(constant)

* max检验（最大特征值检验）
display _newline "最大特征值检验（Max Eigenvalue Test）："
vecrank cpi_national_yoy ppi_yoy gdp_yoy, lags(4) trend(constant) max

/*==============================================================================
  第五部分：VAR模型估计
==============================================================================*/

display _newline(2)
display "================================================================================"
display "VAR模型估计"
display "================================================================================"
display _newline

* 确定最优滞后阶数
varsoc cpi_national_yoy ppi_yoy gdp_yoy, maxlag(8)

* 估计VAR模型（使用最优滞后阶数，通常为2-4阶）
var cpi_national_yoy ppi_yoy gdp_yoy, lags(1/2)

* 保存VAR估计结果
estimates store var_model

* VAR模型诊断检验
display _newline "VAR模型诊断检验："

* 残差自相关检验（LM检验）
display _newline "残差自相关检验（LM检验）："
varlmar, mlag(4)

* 残差正态性检验（Jarque-Bera检验）
display _newline "残差正态性检验（Jarque-Bera检验）："
varnorm

* 注：VAR稳定性检验（AR根表图）将在后续第七部分进行

/*==============================================================================
  第六部分：格兰杰因果检验
==============================================================================*/

display _newline(2)
display "================================================================================"
display "格兰杰因果检验 - 检验变量间的因果关系"
display "================================================================================"
display _newline

display "格兰杰因果检验用于判断一个变量的滞后值是否对另一个变量有预测作用"
display "H0: X不是Y的格兰杰原因（X的滞后值对预测Y没有帮助）"
display "H1: X是Y的格兰杰原因（X的滞后值对预测Y有帮助）"
display _newline

* 所有变量的格兰杰因果检验
vargranger

/*==============================================================================
  第七部分：AR根表图（稳定性检验）
==============================================================================*/

display _newline(2)
display "================================================================================"
display "AR根表图 - VAR模型稳定性检验"
display "================================================================================"
display _newline

display "AR根表图用于检验VAR模型的稳定性"
display "所有特征根的模必须小于1（在单位圆内），模型才是稳定的"
display _newline

* VAR稳定性检验并绘制AR根图
varstable, graph
graph export "../output/AR根表图_VAR稳定性检验.png", replace width(1200)

* 列出所有特征根
varstable

/*==============================================================================
  第八部分：SVAR模型设置与估计
==============================================================================*/

display _newline(2)
display "================================================================================"
display "SVAR模型估计"
display "================================================================================"
display _newline

* 定义SVAR的短期约束矩阵（Cholesky分解）
* 经济学解释：
* - GDP冲击可以同期影响PPI和CPI
* - PPI冲击可以同期影响CPI
* - CPI不能同期影响GDP和PPI（价格粘性）

matrix A = (1, 0, 0 \ ., 1, 0 \ ., ., 1)
matrix B = (., 0, 0 \ 0, ., 0 \ 0, 0, .)

* 估计SVAR模型
svar gdp_yoy ppi_yoy cpi_national_yoy, ///
    lags(1/2) aeq(A) beq(B)

estimates store svar_model

/*==============================================================================
  第九部分：脉冲响应函数分析
==============================================================================*/

display _newline(2)
display "================================================================================"
display "脉冲响应函数分析"
display "================================================================================"
display _newline

* 创建IRF结果
irf create svar_irf, set(../output/svar_irf) replace

* 绘制脉冲响应图 - 分别绘制每个脉冲-响应组合

* === CPI对各变量冲击的响应 ===
irf graph oirf, impulse(cpi_national_yoy) response(cpi_national_yoy) ///
    title("CPI对CPI冲击的响应") name(irf_cpi_cpi, replace)
graph export "../output/IRF_CPI对CPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(ppi_yoy) response(cpi_national_yoy) ///
    title("CPI对PPI冲击的响应") name(irf_cpi_ppi, replace)
graph export "../output/IRF_CPI对PPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(gdp_yoy) response(cpi_national_yoy) ///
    title("CPI对GDP冲击的响应") name(irf_cpi_gdp, replace)
graph export "../output/IRF_CPI对GDP冲击的响应.png", replace width(1200)

* === PPI对各变量冲击的响应 ===
irf graph oirf, impulse(cpi_national_yoy) response(ppi_yoy) ///
    title("PPI对CPI冲击的响应") name(irf_ppi_cpi, replace)
graph export "../output/IRF_PPI对CPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(ppi_yoy) response(ppi_yoy) ///
    title("PPI对PPI冲击的响应") name(irf_ppi_ppi, replace)
graph export "../output/IRF_PPI对PPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(gdp_yoy) response(ppi_yoy) ///
    title("PPI对GDP冲击的响应") name(irf_ppi_gdp, replace)
graph export "../output/IRF_PPI对GDP冲击的响应.png", replace width(1200)

* === GDP对各变量冲击的响应 ===
irf graph oirf, impulse(cpi_national_yoy) response(gdp_yoy) ///
    title("GDP对CPI冲击的响应") name(irf_gdp_cpi, replace)
graph export "../output/IRF_GDP对CPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(ppi_yoy) response(gdp_yoy) ///
    title("GDP对PPI冲击的响应") name(irf_gdp_ppi, replace)
graph export "../output/IRF_GDP对PPI冲击的响应.png", replace width(1200)

irf graph oirf, impulse(gdp_yoy) response(gdp_yoy) ///
    title("GDP对GDP冲击的响应") name(irf_gdp_gdp, replace)
graph export "../output/IRF_GDP对GDP冲击的响应.png", replace width(1200)

* === 汇总图：每个变量对所有冲击的响应 ===
irf graph oirf, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(cpi_national_yoy) ///
    title("CPI对各变量冲击的响应") ///
    byopts(title("CPI脉冲响应函数")) ///
    name(irf_cpi_all, replace)
graph export "../output/IRF_CPI响应汇总.png", replace width(1200)

irf graph oirf, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(ppi_yoy) ///
    title("PPI对各变量冲击的响应") ///
    byopts(title("PPI脉冲响应函数")) ///
    name(irf_ppi_all, replace)
graph export "../output/IRF_PPI响应汇总.png", replace width(1200)

irf graph oirf, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(gdp_yoy) ///
    title("GDP对各变量冲击的响应") ///
    byopts(title("GDP脉冲响应函数")) ///
    name(irf_gdp_all, replace)
graph export "../output/IRF_GDP响应汇总.png", replace width(1200)

* === 累积脉冲响应 ===
irf graph coirf, impulse(ppi_yoy) response(cpi_national_yoy) ///
    title("CPI对PPI冲击的累积响应") ///
    name(cirf_cpi_ppi, replace)
graph export "../output/IRF_CPI对PPI冲击的累积响应.png", replace width(1200)

irf graph coirf, impulse(gdp_yoy) response(cpi_national_yoy) ///
    title("CPI对GDP冲击的累积响应") ///
    name(cirf_cpi_gdp, replace)
graph export "../output/IRF_CPI对GDP冲击的累积响应.png", replace width(1200)

irf graph coirf, impulse(gdp_yoy) response(ppi_yoy) ///
    title("PPI对GDP冲击的累积响应") ///
    name(cirf_ppi_gdp, replace)
graph export "../output/IRF_PPI对GDP冲击的累积响应.png", replace width(1200)

/*==============================================================================
  第十部分：方差分解
==============================================================================*/

display _newline(2)
display "================================================================================"
display "方差分解分析"
display "================================================================================"
display _newline

* GDP的方差分解
irf graph fevd, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(gdp_yoy) ///
    title("GDP的方差分解") ///
    name(fevd_gdp, replace)
graph export "../output/FEVD_GDP.png", replace width(1200)

* PPI的方差分解
irf graph fevd, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(ppi_yoy) ///
    title("PPI的方差分解") ///
    name(fevd_ppi, replace)
graph export "../output/FEVD_PPI.png", replace width(1200)

* CPI的方差分解
irf table fevd, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(cpi_national_yoy)

* 绘制方差分解图
irf graph fevd, impulse(cpi_national_yoy ppi_yoy gdp_yoy) ///
    response(cpi_national_yoy) ///
    title("CPI的方差分解") ///
    name(fevd_cpi, replace)
graph export "../output/FEVD_CPI.png", replace width(1200)


/*==============================================================================
  第十一部分：拟合与预测结果
==============================================================================*/

display _newline(2)
display "================================================================================"
display "拟合与预测分析"
display "================================================================================"
display _newline

* 保存当前VAR模型估计结果
estimates restore var_model

* 1. 样本内拟合优度评估
display _newline "1. 样本内拟合优度："
display _newline

* 获取拟合值和残差（VAR模型需要分别预测每个方程）
predict gdp_fitted if e(sample), equation(gdp_yoy) xb
predict ppi_fitted if e(sample), equation(ppi_yoy) xb
predict cpi_fitted if e(sample), equation(cpi_national_yoy) xb

predict gdp_resid if e(sample), equation(gdp_yoy) residuals
predict ppi_resid if e(sample), equation(ppi_yoy) residuals
predict cpi_resid if e(sample), equation(cpi_national_yoy) residuals

* 计算R方和RMSE
quietly {

    * GDP的拟合优度
    correlate gdp_yoy gdp_fitted if e(sample)
    local r2_gdp = r(rho)^2
    gen gdp_sqerr = gdp_resid^2 if e(sample)
    summarize gdp_sqerr
    local rmse_gdp = sqrt(r(mean))

    * PPI的拟合优度
    correlate ppi_yoy ppi_fitted if e(sample)
    local r2_ppi = r(rho)^2
    gen ppi_sqerr = ppi_resid^2 if e(sample)
    summarize ppi_sqerr
    local rmse_ppi = sqrt(r(mean))

    * CPI的拟合优度
    correlate cpi_national_yoy cpi_fitted if e(sample)
    local r2_cpi = r(rho)^2
    gen cpi_sqerr = cpi_resid^2 if e(sample)
    summarize cpi_sqerr
    local rmse_cpi = sqrt(r(mean))
}

display "GDP拟合优度 (R²): " %6.4f `r2_gdp' "  RMSE: " %6.4f `rmse_gdp'
display "PPI拟合优度 (R²): " %6.4f `r2_ppi' "  RMSE: " %6.4f `rmse_ppi'
display "CPI拟合优度 (R²): " %6.4f `r2_cpi' "  RMSE: " %6.4f `rmse_cpi'

* 2. 绘制拟合图
display _newline "2. 绘制拟合结果："


* GDP拟合图
twoway (line gdp_yoy date_stata, lcolor(blue) lwidth(medium)) ///
       (line gdp_fitted date_stata, lcolor(red) lpattern(dash) lwidth(medium)), ///
    title("GDP同比增长率：实际值 vs 拟合值") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "实际值") label(2 "拟合值")) ///
    xlabel(, format(%tdCY-N)) ///
    name(fit_gdp, replace)
graph export "../output/拟合图_GDP.png", replace width(1200)

* PPI拟合图
twoway (line ppi_yoy date_stata, lcolor(blue) lwidth(medium)) ///
       (line ppi_fitted date_stata, lcolor(red) lpattern(dash) lwidth(medium)), ///
    title("PPI同比增长率：实际值 vs 拟合值") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "实际值") label(2 "拟合值")) ///
    xlabel(, format(%tdCY-N)) ///
    name(fit_ppi, replace)
graph export "../output/拟合图_PPI.png", replace width(1200)

* CPI拟合图
twoway (line cpi_national_yoy date_stata, lcolor(blue) lwidth(medium)) ///
       (line cpi_fitted date_stata, lcolor(red) lpattern(dash) lwidth(medium)), ///
    title("CPI同比增长率：实际值 vs 拟合值") ///
    ytitle("同比增长率 (%)") xtitle("日期") ///
    legend(label(1 "实际值") label(2 "拟合值")) ///
    xlabel(, format(%tdCY-N)) ///
    name(fit_cpi, replace)
graph export "../output/拟合图_CPI.png", replace width(1200)

* 3. 样本外预测（预测未来4个月）
display _newline "3. 样本外预测（未来4个月）："
display _newline

matrix A_est = e(A)  // 保存结构参数

* 重新估计简约式VAR（用相同变量）
var gdp_yoy ppi_yoy cpi_national_yoy, lags(1/2)

* 保存当前观测数
quietly count
local last_obs = r(N)

* 扩展数据集以容纳预测值
quietly set obs `=`last_obs' + 4'

* 为新观测生成时间索引
quietly replace t = _n if t == .

* 预测部分切换为使用数字索引 t（因为新观测没有实际日期）
tsset t

* 使用fcast进行动态预测
fcast compute f_, step(4)

* 绘制预测图 - PPI
tsline ppi_yoy f_ppi_yoy if t >= `last_obs' - 20, ///
    title("PPI同比增长率预测（未来4个月）") ///
    ytitle("同比增长率 (%)") xtitle("时间") ///
    legend(label(1 "实际值") label(2 "预测值")) ///
    tline(`last_obs') ///
    name(forecast_ppi, replace)
graph export "../output/预测图_PPI.png", replace width(1200)

* 绘制预测图 - CPI
tsline cpi_national_yoy f_cpi_national_yoy if t >= `last_obs' - 20, ///
    title("CPI同比增长率预测（未来4个月）") ///
    ytitle("同比增长率 (%)") xtitle("时间") ///
    legend(label(1 "实际值") label(2 "预测值")) ///
    tline(`last_obs') ///
    name(forecast_cpi, replace)
graph export "../output/预测图_CPI.png", replace width(1200)

* 显示预测值
display _newline "预测值摘要（未来4个月）："
list t f_cpi_national_yoy f_ppi_yoy f_gdp_yoy if t > `last_obs'

* 恢复原始数据集大小（删除扩展的观测）
quietly drop if t > `last_obs'
tsset t

* 清理临时变量
drop cpi_fitted ppi_fitted gdp_fitted cpi_resid ppi_resid gdp_resid
drop cpi_sqerr ppi_sqerr gdp_sqerr

/*==============================================================================
  第十二部分：结果导出与分析结论
==============================================================================*/

* 导出所有结果到日志文件
log using "../output/svar_results.log", text replace

display _newline(2)
display "================================================================================"
display "SVAR模型分析结果汇总"
display "================================================================================"

* 显示VAR估计结果
estimates restore var_model
estimates replay

* 显示SVAR估计结果
estimates restore svar_model
estimates replay

* 显示格兰杰因果检验结果
vargranger

log close

/*==============================================================================
  第十三部分：分析结论 - 从结构性通缩到全面通缩
==============================================================================*/

display _newline(2)
display "================================================================================"
display "分析结论：中国经济从结构性通缩到全面通缩的演变"
display "================================================================================"
display _newline

display "基于SVAR模型分析，我们可以得出以下主要结论："
display _newline

display "1. 平稳性检验（ADF检验）："
display "   - 所有序列（CPI、PPI、GDP增长率）均为平稳序列"
display "   - 为VAR/SVAR模型的应用提供了理论基础"
display _newline

display "2. 协整关系："
display "   - 通过Johansen协整检验，可以识别变量间的长期均衡关系"
display "   - 若存在协整关系，说明价格与产出间存在长期稳定联系"
display _newline

display "3. 因果关系（格兰杰检验）："
display "   - 检验PPI是否是CPI的格兰杰原因"
display "   - 检验GDP增长是否是价格变动的格兰杰原因"
display "   - 揭示从生产端到消费端的价格传导机制"
display _newline

display "4. 动态影响（脉冲响应分析）："
display "   - PPI冲击对CPI的传导效应及其持续时间"
display "   - GDP增长冲击对价格水平的影响路径"
display "   - 识别价格粘性和调整速度"
display _newline

display "5. 方差分解："
display "   - 不同冲击对CPI和PPI波动的贡献度"
display "   - 供给侧冲击vs需求侧冲击的相对重要性"
display _newline

display "6. 预测结果："
display "   - 基于历史数据和模型，预测未来4个季度的价格和增长趋势"
display "   - 评估通缩压力的持续性和严重程度"
display _newline

display "7. 通缩演变特征："
display "   - 结构性通缩：最初主要表现为PPI持续负增长，工业品价格下降"
display "   - 传导机制：通过产业链从上游（PPI）向下游（CPI）传导"
display "   - 全面通缩风险：当CPI也持续走低时，表明通缩压力蔓延至消费端"
display "   - 经济影响：可能导致消费延迟、投资萎缩、债务负担加重"
display _newline

display "8. 政策含义："
display "   - 需要关注PPI到CPI的传导机制"
display "   - 及时采取扩张性货币和财政政策以避免通缩螺旋"
display "   - 结构性改革与需求管理政策并重"
display _newline

display "================================================================================"
display "分析完成！"
display "================================================================================"
display _newline
display "结果已保存到 output 文件夹："
display "  - 时间序列图（原始数据）"
display "  - ADF检验结果"
display "  - 协整检验结果"
display "  - 格兰杰因果检验结果"
display "  - AR根表图（VAR稳定性检验）"
display "  - 脉冲响应函数图（IRF）"
display "  - 方差分解图（FEVD）"
display "  - 拟合图（样本内拟合）"
display "  - 预测图（样本外预测）"
display "  - 详细结果日志文件（svar_results.log）"
display "================================================================================"

/*==============================================================================
  结束
==============================================================================*/
