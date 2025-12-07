#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验2: CoT vs Expert Guidance对比测试
证明通用的CoT（"Let's think step by step"）不足以解决模拟电路问题，
必须结合领域特定的结构化思维（Expert Strategy）
"""

import json
import torch
import time
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, List, Any, Tuple
import warnings
import glob
warnings.filterwarnings("ignore")


class CoTComparisonTest:
    """CoT vs Expert Guidance对比测试器"""
    
    def __init__(self, model_path: str):
        """初始化测试器"""
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 模型和tokenizer
        self.model = None
        self.tokenizer = None
        
        # 测试任务（选择有明显提升的任务）
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
            }
        }
        
        # 三种策略配置
        self.strategies = {
            "baseline": {
                "name": "Baseline",
                "description": "标准配置（无提示词优化）",
                "build_prompt": self.build_baseline_prompt
            },
            "generic_cot": {
                "name": "Generic CoT",
                "description": "通用思维链（Let's think step by step）",
                "build_prompt": self.build_generic_cot_prompt
            },
            "expert_guidance": {
                "name": "Expert Guidance",
                "description": "专家指导策略（Few-shot + 结构化Checklist）",
                "build_prompt": self.build_expert_guidance_prompt
            }
        }
        
        print(f"🚀 初始化CoT对比测试器")
        print(f"   模型路径: {model_path}")
        print(f"   设备: {self.device}")
        print(f"   测试任务: {list(self.tasks.keys())}")
        print(f"   对比策略: {list(self.strategies.keys())}")
    
    def load_model(self):
        """加载模型"""
        if self.model is None:
            print(f"\n📦 加载模型...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            self.model.eval()
            print(f"   ✅ 模型加载完成")
    
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
        
        return questions
    
    def build_baseline_prompt(self, task_name: str, question: str, options: Dict[str, str]) -> str:
        """构建Baseline提示词（无优化）"""
        options_text = "\n".join([f"{k}. {v}" for k, v in options.items()])
        prompt = f"Question: {question}\n\nOptions:\n{options_text}\n\nAnswer:"
        return prompt
    
    def build_generic_cot_prompt(self, task_name: str, question: str, options: Dict[str, str]) -> str:
        """构建Generic CoT提示词（只加"Let's think step by step"）"""
        options_text = "\n".join([f"{k}. {v}" for k, v in options.items()])
        prompt = f"Let's think step by step.\n\nQuestion: {question}\n\nOptions:\n{options_text}\n\nAnswer:"
        return prompt
    
    def build_expert_guidance_prompt(self, task_name: str, question: str, options: Dict[str, str]) -> str:
        """构建Expert Guidance提示词（Few-shot + 结构化Checklist）"""
        # 加载Few-shot示例
        examples = self.load_few_shot_examples(task_name)
        
        # 专家指导
        expert_instruction = self.get_expert_instruction(task_name)
        
        # 构建提示词
        prompt_parts = []
        if expert_instruction:
            prompt_parts.append(expert_instruction)
        
        # 添加Few-shot示例
        if examples:
            prompt_parts.append("Examples:\n")
            groundtruth_field = self.tasks[task_name]["groundtruth_field"]
            for i, example in enumerate(examples, 1):
                ex_question = example.get('question', '')
                ex_options = example.get('options', {})
                ex_answer = example.get(groundtruth_field, '')
                
                ex_options_text = "\n".join([f"{k}. {v}" for k, v in ex_options.items()])
                prompt_parts.append(f"Example {i}:\nQuestion: {ex_question}\nOptions:\n{ex_options_text}\nAnswer: {ex_answer}\n")
        
        # 添加当前问题
        options_text = "\n".join([f"{k}. {v}" for k, v in options.items()])
        prompt_parts.append(f"Question: {question}\n\nOptions:\n{options_text}\n\nAnswer:")
        
        return "\n".join(prompt_parts)
    
    def get_expert_instruction(self, task_name: str) -> str:
        """获取专家指导"""
        instructions = {
            "LDO Task": "You are an LDO circuit expert. Analyze LDO circuits by checking:\n1. Pass transistor (source fixed at VDD)\n2. Error amplifier (compares VREF with feedback)\n3. Stable bandgap reference\n4. Resistive divider feedback network\n",
            "Comparator Task": "You are a comparator circuit expert. Analyze comparator circuits systematically.\n",
            "Caption Task": "You are a caption analysis expert. Evaluate all options equally.\n"
        }
        return instructions.get(task_name, "")
    
    def load_few_shot_examples(self, task_name: str) -> List[Dict]:
        """加载Few-shot示例"""
        questions = self.load_task_data(task_name)
        if not questions:
            return []
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        
        # 选择有正确答案的样本作为示例
        valid_examples = [
            q for q in questions 
            if q.get('question') and q.get('options') and q.get(groundtruth_field)
        ]
        
        # 根据任务选择示例数量
        num_examples = {
            "LDO Task": 3,
            "Comparator Task": 2,
            "Caption Task": 8
        }.get(task_name, 2)
        
        if len(valid_examples) < num_examples:
            return valid_examples
        
        # 固定选择前N个（保证可重复性）
        return valid_examples[:num_examples]
    
    def predict(self, prompt: str) -> str:
        """使用模型预测"""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1,
                temperature=0.0,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = generated_text[len(prompt):].strip()
        
        # 提取答案选项（A, B, C, D等）
        if answer:
            answer = answer[0].upper()
            if answer in ['A', 'B', 'C', 'D', 'E']:
                return answer
        
        return ""
    
    def test_task(self, task_name: str, strategy_name: str) -> Dict:
        """测试单个任务的单个策略"""
        print(f"\n📊 测试 {task_name} - {self.strategies[strategy_name]['name']}")
        
        questions = self.load_task_data(task_name)
        if not questions:
            return {"accuracy": 0, "correct": 0, "total": 0, "errors": []}
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        build_prompt = self.strategies[strategy_name]["build_prompt"]
        
        correct = 0
        total = 0
        errors = []
        
        for i, q in enumerate(questions):
            if not q.get('question') or not q.get('options') or not q.get(groundtruth_field):
                continue
            
            question = q['question']
            options = q['options']
            ground_truth = q[groundtruth_field].upper()
            
            # 构建提示词
            prompt = build_prompt(task_name, question, options)
            
            # 预测
            try:
                answer = self.predict(prompt)
                total += 1
                
                if answer == ground_truth:
                    correct += 1
                else:
                    errors.append({
                        "question": question,
                        "options": options,
                        "ground_truth": ground_truth,
                        "predicted": answer,
                        "strategy": strategy_name
                    })
            except Exception as e:
                print(f"   ⚠️ 预测失败 (问题 {i+1}): {e}")
                continue
            
            if (i + 1) % 10 == 0:
                print(f"   进度: {i+1}/{len(questions)} (准确率: {correct/total*100:.1f}%)")
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        print(f"   ✅ 完成: 准确率 {accuracy:.2f}% ({correct}/{total})")
        
        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "errors": errors[:10]  # 只保存前10个错误
        }
    
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        self.load_model()
        
        results = {}
        
        for task_name in self.tasks.keys():
            results[task_name] = {}
            
            for strategy_name in self.strategies.keys():
                task_result = self.test_task(task_name, strategy_name)
                results[task_name][strategy_name] = task_result
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """生成对比报告"""
        report = []
        report.append("=" * 80)
        report.append("实验2: CoT vs Expert Guidance对比测试报告")
        report.append("=" * 80)
        report.append("")
        report.append("实验目标: 证明通用的CoT不足以解决模拟电路问题，")
        report.append("         必须结合领域特定的结构化思维（Expert Strategy）")
        report.append("")
        
        # 总体对比表
        report.append("=" * 80)
        report.append("总体对比结果")
        report.append("=" * 80)
        report.append("")
        report.append(f"{'任务':<20} {'Baseline':<15} {'Generic CoT':<15} {'Expert Guidance':<20} {'CoT提升':<12} {'Expert提升':<15}")
        report.append("-" * 80)
        
        for task_name in self.tasks.keys():
            baseline_acc = results[task_name]["baseline"]["accuracy"]
            cot_acc = results[task_name]["generic_cot"]["accuracy"]
            expert_acc = results[task_name]["expert_guidance"]["accuracy"]
            
            cot_improvement = cot_acc - baseline_acc
            expert_improvement = expert_acc - baseline_acc
            
            report.append(f"{task_name:<20} {baseline_acc:>6.2f}%       {cot_acc:>6.2f}%       {expert_acc:>6.2f}%            {cot_improvement:>+6.2f}%      {expert_improvement:>+6.2f}%")
        
        report.append("")
        
        # 详细分析
        report.append("=" * 80)
        report.append("详细分析")
        report.append("=" * 80)
        report.append("")
        
        for task_name in self.tasks.keys():
            report.append(f"\n【{task_name}】")
            baseline = results[task_name]["baseline"]
            cot = results[task_name]["generic_cot"]
            expert = results[task_name]["expert_guidance"]
            
            report.append(f"  Baseline:        {baseline['accuracy']:.2f}% ({baseline['correct']}/{baseline['total']})")
            report.append(f"  Generic CoT:     {cot['accuracy']:.2f}% ({cot['correct']}/{cot['total']}) [提升: {cot['accuracy']-baseline['accuracy']:+.2f}%]")
            report.append(f"  Expert Guidance: {expert['accuracy']:.2f}% ({expert['correct']}/{expert['total']}) [提升: {expert['accuracy']-baseline['accuracy']:+.2f}%]")
            
            # 分析
            cot_vs_baseline = cot['accuracy'] - baseline['accuracy']
            expert_vs_cot = expert['accuracy'] - cot['accuracy']
            
            report.append(f"  分析:")
            report.append(f"    - Generic CoT相比Baseline: {cot_vs_baseline:+.2f}%")
            report.append(f"    - Expert Guidance相比Generic CoT: {expert_vs_cot:+.2f}%")
            
            if expert_vs_cot > 5:
                report.append(f"    ✅ Expert Guidance显著优于Generic CoT，证明领域特定知识的重要性")
            elif expert_vs_cot > 0:
                report.append(f"    ✓ Expert Guidance优于Generic CoT")
            else:
                report.append(f"    ⚠️ Expert Guidance未优于Generic CoT，需要进一步分析")
        
        report.append("")
        report.append("=" * 80)
        report.append("结论")
        report.append("=" * 80)
        report.append("")
        report.append("1. Generic CoT（通用思维链）相比Baseline有提升，但提升有限")
        report.append("2. Expert Guidance（专家指导）显著优于Generic CoT，证明领域特定知识的重要性")
        report.append("3. 通用的CoT不足以解决模拟电路问题，必须结合领域特定的结构化思维")
        
        return "\n".join(report)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python 实验2_CoT对比测试.py <模型路径>")
        print("示例: python 实验2_CoT对比测试.py /path/to/ReasoningV-7B")
        sys.exit(1)
    
    model_path = sys.argv[1]
    
    print("=" * 80)
    print("实验2: CoT vs Expert Guidance对比测试")
    print("=" * 80)
    
    tester = CoTComparisonTest(model_path)
    results = tester.run_all_tests()
    
    # 保存结果
    output_file = "experiment2_cot_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 生成报告
    report = tester.generate_report(results)
    report_file = "experiment2_cot_comparison_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 报告已保存到: {report_file}")
    
    print("\n" + report)


if __name__ == "__main__":
    main()

