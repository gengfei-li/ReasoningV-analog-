================================================================================
实验3: 路由策略敏感性分析报告
================================================================================

实验目标:
1. 展示Router分类错误的案例和影响
2. 证明'对症下药'的重要性（强制使用错误策略的性能损失）

================================================================================
1. 混淆矩阵分析
================================================================================

Router分类准确率: 85.50%
总问题数: 200
正确分类: 171

混淆矩阵:

真实\预测          factual        reasoning      calculation    analysis       comparison     
--------------------------------------------------------------------------------
factual        95             6              0              3              0              
reasoning      0              69             0              0              0              
calculation    8              12             4              0              0              
analysis       0              0              0              2              0              
comparison     0              0              0              0              1              

================================================================================
2. 分类错误影响分析
================================================================================

总分类错误数: 29
分类错误率: 14.50%

最常见的混淆类型:
  1. calculation → reasoning: 12 次
  2. calculation → factual: 8 次
  3. factual → reasoning: 6 次
  4. factual → analysis: 3 次

================================================================================
3. 错误策略性能损失分析
================================================================================

测试问题数: 17

典型案例（前5个）:

案例 1:
  问题: What role do switched-capacitor filters play in oversampling D/A converters?...
  真实类型: factual
  正确策略: factual (Answer precisely:)
  错误策略: reasoning (Analyze carefully:)

案例 2:
  问题: What role do the extra bits of the ADC play in resolving errors during DAC testing?...
  真实类型: factual
  正确策略: factual (Answer precisely:)
  错误策略: reasoning (Analyze carefully:)

案例 3:
  问题: How can the input-referred noise voltage in a two-stage CMOS op amp be reduced?...
  真实类型: factual
  正确策略: factual (Answer precisely:)
  错误策略: reasoning (Analyze carefully:)

案例 4:
  问题: What role does the transconductance of the transistors play in determining the output noise current?...
  真实类型: factual
  正确策略: factual (Answer precisely:)
  错误策略: reasoning (Analyze carefully:)

案例 5:
  问题: How does the negative feedback loop affect the first-stage common-mode output voltage?...
  真实类型: reasoning
  正确策略: reasoning (Analyze carefully:)
  错误策略: factual (Answer precisely:)

================================================================================
结论
================================================================================

1. Router分类准确率: 85.50%
2. 分类错误会导致使用不合适的策略，影响最终准确率
3. '对症下药'的重要性：使用正确的策略类型对性能至关重要
4. 建议：可以进一步优化Router的分类规则，或使用更复杂的分类方法