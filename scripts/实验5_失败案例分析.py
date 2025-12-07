#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验5: 失败案例分析
展示AnalogSeeker（SFT模型）产生幻觉或逻辑错误的具体Case，
并对比展示ReasoningV如何通过Few-shot或Checklist避免这个错误
"""

import json
import os
from typing import Dict, List, Any, Tuple
import glob


class FailureCaseAnalysis:
    """失败案例分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.tasks = {
            "LDO Task": {
                "data_dir": "reasoning_task/LDO/LDO_QA/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            },
            "Comparator Task": {
                "data_dir": "reasoning_task/Comparator/comparator_QA/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            },
            "Caption Task": {
                "data_dir": "Caption_task/test_QA_caption/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            },
            "TQA Task": {
                "data_file": "TQA Task/TQA Task.json",
                "groundtruth_field": "groundtruth"
            }
        }
        
        print(f"🔍 初始化失败案例分析器")
        print(f"   分析任务: {list(self.tasks.keys())}")
    
    def load_task_data(self, task_name: str) -> List[Dict]:
        """加载任务数据"""
        task_config = self.tasks[task_name]
        questions = []
        
        if "data_dir" in task_config:
            data_dir = task_config["data_dir"]
            file_pattern = task_config["file_pattern"]
            files = glob.glob(os.path.join(data_dir, file_pattern))
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            questions.extend(data)
                        elif isinstance(data, dict):
                            questions.append(data)
                except Exception as e:
                    print(f"   ⚠️ 加载文件失败 {file_path}: {e}")
        elif "data_file" in task_config:
            data_file = task_config["data_file"]
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        questions = data
                    elif isinstance(data, dict) and "questions" in data:
                        questions = data["questions"]
            except Exception as e:
                print(f"   ⚠️ 加载文件失败 {data_file}: {e}")
        
        return questions
    
    def load_model_results(self, model_name: str) -> Dict:
        """加载模型测试结果"""
        result_files = {
            "ReasoningV": "reasoningv_full_validation_results.json",
            "AnalogSeeker": "analogseeker_full_validation_results.json"
        }
        
        if model_name not in result_files:
            return {}
        
        result_file = result_files[model_name]
        if not os.path.exists(result_file):
            print(f"   ⚠️ 结果文件不存在: {result_file}")
            return {}
        
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"   ⚠️ 加载结果文件失败: {e}")
            return {}
    
    def classify_error_type(self, question: Dict, ground_truth: str, predicted: str, 
                           options: Dict[str, str]) -> str:
        """分类错误类型"""
        # 1. 选项偏见（Option Bias）
        # 如果模型总是选择某个特定选项（如总是选A或总是选D）
        if predicted not in ['A', 'B', 'C', 'D', 'E']:
            return "格式错误"
        
        # 2. 幻觉错误（Hallucination）
        # 如果预测的选项内容与问题完全不相关
        predicted_text = options.get(predicted, "")
        ground_truth_text = options.get(ground_truth, "")
        
        # 简单的相关性检查（可以根据需要扩展）
        if not predicted_text or not ground_truth_text:
            return "未知错误"
        
        # 3. 逻辑错误（Logical Error）
        # 如果预测的选项在逻辑上不合理
        # 这里需要更复杂的分析，暂时标记为"逻辑错误"
        
        # 4. 灾难性遗忘（Catastrophic Forgetting）
        # 如果问题是基础概念但模型答错
        # 需要人工判断，暂时标记为"可能遗忘"
        
        return "逻辑错误"
    
    def find_failure_cases(self) -> Dict:
        """查找失败案例"""
        print("\n🔍 查找失败案例...")
        
        # 加载模型结果
        reasoningv_results = self.load_model_results("ReasoningV")
        analogseeker_results = self.load_model_results("AnalogSeeker")
        
        failure_cases = {}
        
        for task_name in self.tasks.keys():
            print(f"\n📊 分析 {task_name}...")
            
            # 加载任务数据
            questions = self.load_task_data(task_name)
            if not questions:
                continue
            
            groundtruth_field = self.tasks[task_name]["groundtruth_field"]
            
            # 获取模型结果
            rv_task_results = reasoningv_results.get("validation_results", {}).get("results", {}).get(task_name, {})
            as_task_results = analogseeker_results.get("validation_results", {}).get("results", {}).get(task_name, {})
            
            # 这里需要实际的预测结果，但当前结果文件可能不包含每个问题的预测
            # 我们需要重新运行测试或从日志中提取
            
            # 暂时返回空，需要实际运行测试才能获得详细结果
            failure_cases[task_name] = {
                "reasoningv_correct": rv_task_results.get("correct_count", 0),
                "reasoningv_total": rv_task_results.get("total_questions", 0),
                "analogseeker_correct": as_task_results.get("correct_count", 0),
                "analogseeker_total": as_task_results.get("total_questions", 0),
                "cases": []
            }
        
        return failure_cases
    
    def analyze_specific_cases(self, task_name: str, num_cases: int = 5) -> List[Dict]:
        """分析特定任务的失败案例"""
        print(f"\n📋 分析 {task_name} 的失败案例...")
        
        questions = self.load_task_data(task_name)
        if not questions:
            return []
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        
        # 这里需要实际的预测结果
        # 由于当前结果文件可能不包含每个问题的预测，我们需要：
        # 1. 重新运行测试并保存详细结果
        # 2. 或者从日志中提取
        
        # 暂时返回示例结构
        cases = []
        for i, q in enumerate(questions[:num_cases]):
            if not q.get('question') or not q.get('options') or not q.get(groundtruth_field):
                continue
            
            case = {
                "question_id": i + 1,
                "question": q['question'],
                "options": q['options'],
                "ground_truth": q[groundtruth_field],
                "reasoningv_predicted": "待测试",
                "analogseeker_predicted": "待测试",
                "error_type": "待分析",
                "analysis": "需要实际运行测试才能获得详细分析"
            }
            cases.append(case)
        
        return cases
    
    def generate_case_report(self, cases: Dict) -> str:
        """生成案例分析报告"""
        report = []
        report.append("=" * 80)
        report.append("实验5: 失败案例分析报告")
        report.append("=" * 80)
        report.append("")
        report.append("实验目标: 展示AnalogSeeker（SFT模型）产生幻觉或逻辑错误的具体Case，")
        report.append("         并对比展示ReasoningV如何通过Few-shot或Checklist避免这个错误")
        report.append("")
        
        for task_name, task_cases in cases.items():
            report.append("=" * 80)
            report.append(f"【{task_name}】")
            report.append("=" * 80)
            report.append("")
            report.append(f"ReasoningV: {task_cases['reasoningv_correct']}/{task_cases['reasoningv_total']} ({task_cases['reasoningv_correct']/task_cases['reasoningv_total']*100:.2f}%)")
            report.append(f"AnalogSeeker: {task_cases['analogseeker_correct']}/{task_cases['analogseeker_total']} ({task_cases['analogseeker_correct']/task_cases['analogseeker_total']*100:.2f}%)")
            report.append("")
            
            if task_cases['cases']:
                for i, case in enumerate(task_cases['cases'], 1):
                    report.append(f"案例 {i}:")
                    report.append(f"  问题: {case.get('question', 'N/A')}")
                    report.append(f"  正确答案: {case.get('ground_truth', 'N/A')}")
                    report.append(f"  ReasoningV预测: {case.get('reasoningv_predicted', 'N/A')}")
                    report.append(f"  AnalogSeeker预测: {case.get('analogseeker_predicted', 'N/A')}")
                    report.append(f"  错误类型: {case.get('error_type', 'N/A')}")
                    report.append(f"  分析: {case.get('analysis', 'N/A')}")
                    report.append("")
            else:
                report.append("  ⚠️ 需要实际运行测试才能获得详细案例")
                report.append("")
        
        report.append("=" * 80)
        report.append("结论")
        report.append("=" * 80)
        report.append("")
        report.append("1. 需要实际运行测试并保存每个问题的预测结果")
        report.append("2. 对比两个模型的错误案例，找出典型错误类型")
        report.append("3. 分析ReasoningV如何通过Few-shot或Checklist避免错误")
        
        return "\n".join(report)


def main():
    """主函数"""
    print("=" * 80)
    print("实验5: 失败案例分析")
    print("=" * 80)
    
    analyzer = FailureCaseAnalysis()
    cases = analyzer.find_failure_cases()
    
    # 保存结果
    output_file = "experiment5_failure_cases.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 生成报告
    report = analyzer.generate_case_report(cases)
    report_file = "experiment5_failure_cases_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 报告已保存到: {report_file}")
    
    print("\n" + report)
    print("\n⚠️ 注意: 需要实际运行测试并保存每个问题的预测结果才能获得详细分析")


if __name__ == "__main__":
    main()

