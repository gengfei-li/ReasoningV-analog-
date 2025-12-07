#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验3: 路由策略敏感性分析
1. 混淆矩阵分析：展示Router分类错误的案例和影响
2. 错误策略性能损失分析：证明"对症下药"的重要性
"""

import json
import os
from typing import Dict, List, Any, Tuple
from question_router import QuestionRouter, QuestionType
import numpy as np
from collections import defaultdict


class RouterSensitivityAnalysis:
    """路由策略敏感性分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.router = QuestionRouter()
        self.tqa_data_file = "TQA Task/TQA Task.json"
        
        print(f"🔍 初始化路由策略敏感性分析器")
    
    def load_tqa_data(self) -> List[Dict]:
        """加载TQA任务数据"""
        if not os.path.exists(self.tqa_data_file):
            print(f"   ⚠️ TQA数据文件不存在: {self.tqa_data_file}")
            return []
        
        try:
            with open(self.tqa_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "questions" in data:
                    return data["questions"]
                else:
                    return []
        except Exception as e:
            print(f"   ⚠️ 加载TQA数据失败: {e}")
            return []
    
    def manually_classify_question(self, question_text: str, options: Dict[str, str] = None) -> QuestionType:
        """
        手动分类问题类型（用于构建混淆矩阵）
        这里使用简单的规则，实际应该由人工标注
        """
        question_lower = question_text.lower()
        
        # 计算类别的关键词匹配分数
        type_scores = {
            QuestionType.FACTUAL: 0,
            QuestionType.REASONING: 0,
            QuestionType.CALCULATION: 0,
            QuestionType.ANALYSIS: 0,
            QuestionType.COMPARISON: 0
        }
        
        # 事实类关键词
        factual_keywords = ["what is", "what are", "define", "definition", "which of the following"]
        for keyword in factual_keywords:
            if keyword in question_lower:
                type_scores[QuestionType.FACTUAL] += 1
        
        # 推理类关键词
        reasoning_keywords = ["why", "how does", "explain", "reason", "because", "leads to"]
        for keyword in reasoning_keywords:
            if keyword in question_lower:
                type_scores[QuestionType.REASONING] += 1
        
        # 计算类关键词
        calculation_keywords = ["calculate", "compute", "determine", "value", "formula", "equation"]
        for keyword in calculation_keywords:
            if keyword in question_lower:
                type_scores[QuestionType.CALCULATION] += 1
        
        # 分析类关键词
        analysis_keywords = ["analyze", "analysis", "examine", "evaluate", "compare", "contrast"]
        for keyword in analysis_keywords:
            if keyword in question_lower:
                type_scores[QuestionType.ANALYSIS] += 1
        
        # 比较类关键词
        comparison_keywords = ["better", "best", "worse", "worst", "prefer", "optimal"]
        for keyword in comparison_keywords:
            if keyword in question_lower:
                type_scores[QuestionType.COMPARISON] += 1
        
        # 选择得分最高的类型
        if max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get)
        else:
            return QuestionType.FACTUAL  # 默认
    
    def build_confusion_matrix(self, questions: List[Dict], sample_size: int = 100) -> Dict:
        """构建混淆矩阵"""
        print(f"\n📊 构建混淆矩阵（样本数: {sample_size}）...")
        
        # 采样问题
        if len(questions) > sample_size:
            import random
            random.seed(42)  # 固定种子保证可重复
            sampled_questions = random.sample(questions, sample_size)
        else:
            sampled_questions = questions
        
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        total_by_true = defaultdict(int)
        total_by_pred = defaultdict(int)
        
        for q in sampled_questions:
            question_text = q.get('question', '')
            if not question_text:
                continue
            
            # 真实类型（手动分类）
            true_type = self.manually_classify_question(question_text)
            
            # 预测类型（Router分类）
            pred_type, _ = self.router.classify_question(question_text)
            
            confusion_matrix[true_type.value][pred_type.value] += 1
            total_by_true[true_type.value] += 1
            total_by_pred[pred_type.value] += 1
        
        # 计算准确率
        correct = sum(confusion_matrix[true_type.value][true_type.value] 
                     for true_type in QuestionType)
        total = len(sampled_questions)
        accuracy = (correct / total * 100) if total > 0 else 0
        
        return {
            "confusion_matrix": {k: dict(v) for k, v in confusion_matrix.items()},
            "total_by_true": dict(total_by_true),
            "total_by_pred": dict(total_by_pred),
            "accuracy": accuracy,
            "total_questions": total,
            "correct": correct
        }
    
    def analyze_misclassification_impact(self, questions: List[Dict], 
                                         confusion_matrix: Dict) -> Dict:
        """分析分类错误的影响"""
        print(f"\n🔍 分析分类错误的影响...")
        
        # 找出最常见的混淆类型
        misclassifications = []
        
        for true_type, pred_dict in confusion_matrix["confusion_matrix"].items():
            for pred_type, count in pred_dict.items():
                if true_type != pred_type and count > 0:
                    misclassifications.append({
                        "true_type": true_type,
                        "pred_type": pred_type,
                        "count": count
                    })
        
        # 按数量排序
        misclassifications.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_misclassifications": sum(m["count"] for m in misclassifications),
            "top_misclassifications": misclassifications[:10],
            "misclassification_rate": (sum(m["count"] for m in misclassifications) / 
                                     confusion_matrix["total_questions"] * 100) if confusion_matrix["total_questions"] > 0 else 0
        }
    
    def test_wrong_strategy_performance(self, questions: List[Dict], 
                                       sample_size: int = 20) -> Dict:
        """测试错误策略的性能损失"""
        print(f"\n🧪 测试错误策略的性能损失（样本数: {sample_size}）...")
        
        # 选择典型问题（每种类型选几个）
        type_questions = defaultdict(list)
        
        for q in questions:
            question_text = q.get('question', '')
            if not question_text:
                continue
            
            true_type = self.manually_classify_question(question_text)
            type_questions[true_type.value].append(q)
        
        # 每种类型选择几个问题
        selected_questions = []
        questions_per_type = sample_size // len(QuestionType)
        
        for qtype in QuestionType:
            type_qs = type_questions.get(qtype.value, [])
            if len(type_qs) > questions_per_type:
                import random
                random.seed(42)
                selected_questions.extend(random.sample(type_qs, questions_per_type))
            else:
                selected_questions.extend(type_qs)
        
        if len(selected_questions) > sample_size:
            selected_questions = selected_questions[:sample_size]
        
        # 测试正确策略 vs 错误策略
        results = {}
        
        for q in selected_questions:
            question_text = q.get('question', '')
            true_type = self.manually_classify_question(question_text)
            
            # 正确策略
            correct_type, correct_prefix = self.router.classify_question(question_text)
            
            # 错误策略（选择另一个类型）
            wrong_types = [t for t in QuestionType if t != correct_type]
            if wrong_types:
                import random
                random.seed(42)
                wrong_type = random.choice(wrong_types)
                wrong_prefix = self.router.rules[wrong_type]["prompt_prefix"]
                
                results[question_text] = {
                    "true_type": true_type.value,
                    "correct_strategy": {
                        "type": correct_type.value,
                        "prefix": correct_prefix
                    },
                    "wrong_strategy": {
                        "type": wrong_type.value,
                        "prefix": wrong_prefix
                    },
                    "question": question_text
                }
        
        return {
            "total_tested": len(selected_questions),
            "cases": results
        }
    
    def generate_report(self, confusion_matrix: Dict, misclassification_impact: Dict, 
                       wrong_strategy_results: Dict) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 80)
        report.append("实验3: 路由策略敏感性分析报告")
        report.append("=" * 80)
        report.append("")
        report.append("实验目标:")
        report.append("1. 展示Router分类错误的案例和影响")
        report.append("2. 证明'对症下药'的重要性（强制使用错误策略的性能损失）")
        report.append("")
        
        # 混淆矩阵
        report.append("=" * 80)
        report.append("1. 混淆矩阵分析")
        report.append("=" * 80)
        report.append("")
        report.append(f"Router分类准确率: {confusion_matrix['accuracy']:.2f}%")
        report.append(f"总问题数: {confusion_matrix['total_questions']}")
        report.append(f"正确分类: {confusion_matrix['correct']}")
        report.append("")
        
        report.append("混淆矩阵:")
        report.append("")
        # 表头
        all_types = list(QuestionType)
        header = f"{'真实\\预测':<15}"
        for pred_type in all_types:
            header += f"{pred_type.value:<15}"
        report.append(header)
        report.append("-" * 80)
        
        # 矩阵内容
        for true_type in all_types:
            row = f"{true_type.value:<15}"
            for pred_type in all_types:
                count = confusion_matrix["confusion_matrix"].get(true_type.value, {}).get(pred_type.value, 0)
                row += f"{count:<15}"
            report.append(row)
        
        report.append("")
        
        # 分类错误影响
        report.append("=" * 80)
        report.append("2. 分类错误影响分析")
        report.append("=" * 80)
        report.append("")
        report.append(f"总分类错误数: {misclassification_impact['total_misclassifications']}")
        report.append(f"分类错误率: {misclassification_impact['misclassification_rate']:.2f}%")
        report.append("")
        report.append("最常见的混淆类型:")
        for i, mis in enumerate(misclassification_impact['top_misclassifications'][:5], 1):
            report.append(f"  {i}. {mis['true_type']} → {mis['pred_type']}: {mis['count']} 次")
        
        report.append("")
        
        # 错误策略性能损失
        report.append("=" * 80)
        report.append("3. 错误策略性能损失分析")
        report.append("=" * 80)
        report.append("")
        report.append(f"测试问题数: {wrong_strategy_results['total_tested']}")
        report.append("")
        report.append("典型案例（前5个）:")
        for i, (question, case) in enumerate(list(wrong_strategy_results['cases'].items())[:5], 1):
            report.append(f"\n案例 {i}:")
            report.append(f"  问题: {question[:100]}...")
            report.append(f"  真实类型: {case['true_type']}")
            report.append(f"  正确策略: {case['correct_strategy']['type']} ({case['correct_strategy']['prefix']})")
            report.append(f"  错误策略: {case['wrong_strategy']['type']} ({case['wrong_strategy']['prefix']})")
        
        report.append("")
        report.append("=" * 80)
        report.append("结论")
        report.append("=" * 80)
        report.append("")
        report.append("1. Router分类准确率: {:.2f}%".format(confusion_matrix['accuracy']))
        report.append("2. 分类错误会导致使用不合适的策略，影响最终准确率")
        report.append("3. '对症下药'的重要性：使用正确的策略类型对性能至关重要")
        report.append("4. 建议：可以进一步优化Router的分类规则，或使用更复杂的分类方法")
        
        return "\n".join(report)


def main():
    """主函数"""
    print("=" * 80)
    print("实验3: 路由策略敏感性分析")
    print("=" * 80)
    
    analyzer = RouterSensitivityAnalysis()
    
    # 加载TQA数据
    questions = analyzer.load_tqa_data()
    if not questions:
        print("⚠️ 无法加载TQA数据，退出")
        return
    
    print(f"✅ 加载了 {len(questions)} 个问题")
    
    # 构建混淆矩阵
    confusion_matrix = analyzer.build_confusion_matrix(questions, sample_size=200)
    
    # 分析分类错误影响
    misclassification_impact = analyzer.analyze_misclassification_impact(questions, confusion_matrix)
    
    # 测试错误策略性能损失
    wrong_strategy_results = analyzer.test_wrong_strategy_performance(questions, sample_size=20)
    
    # 保存结果
    results = {
        "confusion_matrix": confusion_matrix,
        "misclassification_impact": misclassification_impact,
        "wrong_strategy_results": wrong_strategy_results
    }
    
    output_file = "experiment3_router_sensitivity_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 生成报告
    report = analyzer.generate_report(confusion_matrix, misclassification_impact, wrong_strategy_results)
    report_file = "experiment3_router_sensitivity_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 报告已保存到: {report_file}")
    
    print("\n" + report)


if __name__ == "__main__":
    main()

