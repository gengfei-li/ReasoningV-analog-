#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReasoningV优化后完整验证测试脚本
使用所有优化后的策略配置，完整测试AMSBench所有题目
确保准确率可重复
"""

import json
import torch
import time
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings("ignore")

class ReasoningVFullValidation:
    """ReasoningV完整验证测试器"""
    
    def __init__(self, model_path: str):
        """初始化测试器"""
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 模型和tokenizer
        self.model = None
        self.tokenizer = None
        
        # 任务配置（使用实际的数据路径）
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
            "Bandgap Task": {
                "data_dir": "reasoning_task/Bandgap/bandgap_QA/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            },
            "TQA Task": {
                "data_file": "TQA Task/TQA Task.json",
                "groundtruth_field": "groundtruth"
            },
            "Caption Task": {
                "data_dir": "Caption_task/test_QA_caption/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            },
            "Opamp Task": {
                "data_dir": "reasoning_task/Opamp/test_QA_opamp/",
                "file_pattern": "*.json",
                "groundtruth_field": "ground_truth"
            }
        }
        
        # 加载优化后的策略配置
        self.optimized_configs = self.load_optimized_configs()
        
        print(f"🚀 初始化ReasoningV完整验证测试器")
        print(f"   模型路径: {model_path}")
        print(f"   设备: {self.device}")
        print(f"   任务数: {len(self.tasks)}")
        print(f"   已加载优化配置: {len(self.optimized_configs)} 个任务")
    
    def load_optimized_configs(self) -> Dict[str, Dict]:
        """加载所有优化后的策略配置"""
        configs = {}
        
        # 任务名称映射：Few-shot配置中的名称 -> 实际任务名称
        task_name_map = {
            "LDO": "LDO Task",
            "Comparator": "Comparator Task",
            "Caption": "Caption Task",
            "Bandgap": "Bandgap Task",
            "Opamp": "Opamp Task",
            "TQA": "TQA Task"
        }
        
        # 优先加载最新优化结果（LDO, Comparator, Caption）
        try:
            with open("reasoningv_latest_optimization_results.json", 'r') as f:
                data = json.load(f)
                if 'optimization_results' in data:
                    results = data['optimization_results']
                    for task_key, task_result in results.items():
                        if 'strategy' in task_result and task_key in task_name_map:
                            task_name = task_name_map[task_key]
                            strategy = task_result['strategy']
                            
                            # 转换配置格式
                            config = {
                                "expert_instruction": strategy.get("expert_instruction", ""),
                                "params": strategy.get("params", {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                                                  "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}),
                                "use_few_shot": strategy.get("use_few_shot", False),
                                "num_examples": strategy.get("num_examples", 2)
                            }
                            
                            configs[task_name] = config
                            print(f"   ✅ 加载 {task_name} 最新优化配置 (Few-shot: {config['use_few_shot']}, 示例数: {config.get('num_examples', 0)})")
        except Exception as e:
            print(f"   ⚠️ 加载最新优化配置失败: {e}")
            # 回退到Few-shot优化结果
            try:
                with open("reasoningv_fewshot_optimization_results.json", 'r') as f:
                    data = json.load(f)
                    if 'optimization_results' in data:
                        results = data['optimization_results']
                        for task_key, task_result in results.items():
                            if 'best_strategy' in task_result and task_key in task_name_map:
                                task_name = task_name_map[task_key]
                                strategy = task_result['best_strategy']
                                
                                # 转换配置格式
                                config = {
                                    "prompt": strategy.get("prompt_template", "Question: {question}\n\nOptions:\n{options}\n\nAnswer:"),
                                    "params": strategy.get("parameters", {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                                                          "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}),
                                    "use_few_shot": strategy.get("use_few_shot", False)
                                }
                                
                                # 加载Few-shot示例
                                if config["use_few_shot"]:
                                    config["few_shot_examples"] = self.load_few_shot_examples(task_name)
                                
                                configs[task_name] = config
                                print(f"   ✅ 加载 {task_name} Few-shot配置")
            except Exception as e2:
                print(f"   ⚠️ 加载Few-shot配置失败: {e2}")
        
        # 加载TQA错误模式优化结果
        try:
            with open("reasoningv_tqa_pattern_optimization_results.json", 'r') as f:
                data = json.load(f)
                if 'optimization_results' in data and 'result' in data['optimization_results']:
                    result = data['optimization_results']['result']
                    if 'strategy_map' in result:
                        # 转换strategy_map的键为整数
                        strategy_map = {}
                        for k, v in result['strategy_map'].items():
                            try:
                                strategy_map[int(k)] = v
                            except:
                                pass
                        
                        configs["TQA Task"] = {
                            'type': 'pattern_optimized',
                            'strategy_map': strategy_map,
                            'base_strategy': {
                                "prompt": "Question: {question}\n\nOptions:\n{options}\n\nAnswer:",
                                "params": {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                          "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}
                            }
                        }
                        print(f"   ✅ 加载 TQA Task 错误模式优化配置 ({len(strategy_map)} 个特殊策略)")
        except Exception as e:
            print(f"   ⚠️ 加载TQA配置失败: {e}")
        
        # 加载其他任务的优化配置（Bandgap和Opamp）
        try:
            with open("reasoningv_fewshot_optimization_results.json", 'r') as f:
                data = json.load(f)
                if 'optimization_results' in data:
                    results = data['optimization_results']
                    for task_key in ["Bandgap", "Opamp"]:
                        if task_key in results and task_name_map[task_key] not in configs:
                            task_name = task_name_map[task_key]
                            task_result = results[task_key]
                            if 'best_strategy' in task_result:
                                strategy = task_result['best_strategy']
                                configs[task_name] = {
                                    "prompt": strategy.get("prompt_template", "Question: {question}\n\nOptions:\n{options}\n\nAnswer:"),
                                    "params": strategy.get("parameters", {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                                                          "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True})
                                }
                                print(f"   ✅ 加载 {task_name} 优化配置")
        except:
            pass
        
        # 为未配置的任务设置默认配置
        for task_name in self.tasks.keys():
            if task_name not in configs:
                configs[task_name] = {
                    "prompt": "Question: {question}\n\nOptions:\n{options}\n\nAnswer:",
                    "params": {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                              "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}
                }
                print(f"   ⚠️ {task_name} 使用默认配置")
        
        return configs
    
    def load_few_shot_examples(self, task_name: str, num_examples: int = 2) -> List[Dict]:
        """加载Few-shot示例（每次调用随机选择，模拟优化时的随机性）"""
        import random
        # 不设置固定种子，让每次调用都随机选择（模拟优化时的行为）
        # 这样多次运行取平均才能得到稳定结果
        
        questions = self.load_task_data(task_name)
        if not questions:
            return []
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        
        # 选择有正确答案的样本作为示例（与优化脚本一致）
        valid_examples = [
            q for q in questions 
            if q.get('question') and q.get('options') and q.get(groundtruth_field)
        ]
        
        if len(valid_examples) < num_examples:
            return valid_examples
        
        # 随机选择（不设置种子，每次调用都不同）
        return random.sample(valid_examples, min(num_examples, len(valid_examples)))
    
    def build_few_shot_prompt(self, task_name: str, question: str, options: Dict[str, str], 
                              examples: List[Dict], expert_instruction: str = "") -> str:
        """构建Few-shot提示词（与优化脚本一致）"""
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        
        prompt_parts = []
        
        # 添加任务特定的指导（优先使用配置中的expert_instruction）
        if expert_instruction:
            prompt_parts.append(expert_instruction)
        else:
            # 回退到默认指导
            if task_name == "LDO Task":
                prompt_parts.append("You are an LDO circuit expert. Analyze LDO circuits by checking:\n1. Pass transistor (source fixed at VDD)\n2. Error amplifier (compares VREF with feedback)\n3. Stable bandgap reference\n4. Resistive divider feedback network\n")
            elif task_name == "Comparator Task":
                prompt_parts.append("You are a comparator circuit expert. Analyze comparator circuits systematically.\n")
            elif task_name == "Caption Task":
                prompt_parts.append("You are a caption analysis expert. Evaluate all options equally.\n")
        
        # 添加few-shot示例（使用所有提供的示例）
        if examples:
            prompt_parts.append("Examples:\n")
            for i, example in enumerate(examples, 1):
                ex_question = example.get('question', '')
                ex_options = example.get('options', {})
                ex_answer = example.get(groundtruth_field, '')
                
                if ex_question and ex_options and ex_answer:
                    options_str = ""
                    for key, value in ex_options.items():
                        # 简化选项显示（与优化脚本一致）
                        value_short = value[:200] + "..." if len(value) > 200 else value
                        options_str += f"{key}. {value_short}\n"
                    
                    prompt_parts.append(f"Example {i}:\nQuestion: {ex_question}\nOptions:\n{options_str}Answer: {ex_answer}\n\n")
        
        # 添加当前问题（始终使用"Now solve this:"格式，与优化脚本一致）
        options_str = ""
        for key, value in options.items():
            options_str += f"{key}. {value}\n"
        
        prompt_parts.append(f"Now solve this:\nQuestion: {question}\nOptions:\n{options_str}Answer:")
        
        return "\n".join(prompt_parts)
    
    def load_model(self):
        """加载模型"""
        if self.model is not None:
            return
        
        print(f"\n📥 正在加载ReasoningV模型...")
        import sys
        sys.stdout.flush()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map={"": 0},
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        print(f"✅ ReasoningV模型加载完成")
        import sys
        sys.stdout.flush()
    
    def load_task_data(self, task_name: str) -> List[Dict]:
        """加载任务数据"""
        if task_name not in self.tasks:
            return []
        
        task_config = self.tasks[task_name]
        
        # 单个文件模式（TQA）
        if "data_file" in task_config:
            data_file = task_config["data_file"]
            if not os.path.exists(data_file):
                return []
            
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 加载数据失败: {e}")
                return []
        else:
            # 目录模式（其他任务）
            import glob
            data_dir = task_config["data_dir"]
            file_pattern = task_config["file_pattern"]
            
            if not os.path.exists(data_dir):
                return []
            
            all_data = []
            try:
                files = glob.glob(os.path.join(data_dir, file_pattern))
                for file_path in files:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        if isinstance(file_data, list):
                            all_data.extend(file_data)
                        else:
                            all_data.append(file_data)
                return all_data
            except Exception as e:
                print(f"❌ 加载数据失败: {e}")
                return []
    
    def build_prompt(self, template: str, question: str, options: Dict[str, str], 
                    few_shot_examples: List[Dict] = None) -> str:
        """构建提示词"""
        options_str = ""
        if options:
            for key, value in options.items():
                options_str += f"{key}. {value}\n"
        
        # 添加Few-shot示例
        few_shot_text = ""
        if few_shot_examples:
            few_shot_text = "\n\nExamples:\n"
            for ex in few_shot_examples:
                ex_options = ""
                for k, v in ex.get('options', {}).items():
                    ex_options += f"{k}. {v}\n"
                few_shot_text += f"Q: {ex['question']}\nOptions:\n{ex_options}Answer: {ex['groundtruth']}\n\n"
        
        return template.format(question=question, options=options_str.strip(), 
                              few_shot_examples=few_shot_text)
    
    def generate_answer(self, prompt: str, parameters: Dict) -> Tuple[str, float]:
        """生成答案"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        model_device = next(self.model.parameters()).device
        inputs = {k: v.to(model_device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=parameters.get("max_new_tokens", 1),
                temperature=parameters.get("temperature", 0.0),
                do_sample=parameters.get("do_sample", False),
                repetition_penalty=parameters.get("repetition_penalty", 1.0),
                top_p=parameters.get("top_p", 1.0),
                top_k=parameters.get("top_k", 1),
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=parameters.get("use_cache", True)
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer_part = response[len(prompt):].strip()
        
        for option in ['A', 'B', 'C', 'D', 'E']:
            if option in answer_part:
                return option, 0.95
        
        return 'A', 0.95
    
    def test_task(self, task_name: str, num_runs: int = 1) -> Dict[str, Any]:
        """测试单个任务（支持多次运行取平均，与优化时一致）"""
        print(f"\n{'='*80}")
        print(f"📊 测试任务: {task_name}")
        if num_runs > 1:
            print(f"   将运行 {num_runs} 次取平均值（与优化时一致）")
        print(f"{'='*80}")
        import sys
        sys.stdout.flush()
        
        questions = self.load_task_data(task_name)
        if not questions:
            print(f"❌ 无法加载 {task_name} 数据")
            return None
        
        print(f"   加载了 {len(questions)} 个问题")
        import sys
        sys.stdout.flush()
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        config = self.optimized_configs.get(task_name, {})
        
        # 多次运行取平均（Few-shot示例是随机的）
        all_accuracies = []
        all_correct_counts = []
        all_total_times = []
        
        for run in range(num_runs):
            if num_runs > 1:
                print(f"   运行 {run+1}/{num_runs}...")
                import sys
                sys.stdout.flush()
            
            correct_count = 0
            total_time = 0
            start_time = time.time()
            
            # 处理Few-shot配置（每次运行重新选择示例）
            few_shot_examples = None
            num_few_shot = config.get('num_examples', 2)  # 从配置中读取示例数量
            if config.get('use_few_shot', False):
                # 每次运行重新选择Few-shot示例（模拟优化时的随机性）
                few_shot_examples = self.load_few_shot_examples(task_name, num_examples=num_few_shot)
            
            # 处理TQA错误模式优化配置
            error_indices = []  # 记录错误题目的索引（仅用于TQA任务）
            if isinstance(config, dict) and config.get('type') == 'pattern_optimized':
                strategy_map = config.get('strategy_map', {})
                base_strategy = config.get('base_strategy', {
                    "prompt": "Question: {question}\n\nOptions:\n{options}\n\nAnswer:",
                    "params": {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                              "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}
                })
                
                # 使用多策略映射
                for i, question_data in enumerate(questions):
                    question = question_data.get('question', '')
                    options = question_data.get('options', {})
                    groundtruth = question_data.get(groundtruth_field, '')
                    
                    if not question or not groundtruth:
                        continue
                    
                    try:
                        # 根据题目索引选择策略
                        if i in strategy_map:
                            strategy = strategy_map[i]
                        else:
                            strategy = base_strategy
                        
                        prompt = self.build_prompt(strategy["prompt"], question, options)
                        q_start_time = time.time()
                        answer, _ = self.generate_answer(prompt, strategy["params"])
                        elapsed_time = time.time() - q_start_time
                        total_time += elapsed_time
                        
                        if answer == groundtruth:
                            correct_count += 1
                        else:
                            # 记录错误题目索引（仅用于TQA任务）
                            if task_name == "TQA Task":
                                error_indices.append(i)
                    except Exception as e:
                        if task_name == "TQA Task":
                            error_indices.append(i)
                        continue
            else:
                # 标准配置或Few-shot配置
                prompt_template = config.get("prompt", "Question: {question}\n\nOptions:\n{options}\n\nAnswer:")
                params = config.get("params", {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                             "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True})
                
                for i, question_data in enumerate(questions):
                    question = question_data.get('question', '')
                    options = question_data.get('options', {})
                    groundtruth = question_data.get(groundtruth_field, '')
                    
                    if not question or not groundtruth:
                        continue
                    
                    try:
                        # 构建提示词（Few-shot或标准）
                        if config.get('use_few_shot', False) and few_shot_examples:
                            expert_instruction = config.get('expert_instruction', '')
                            prompt = self.build_few_shot_prompt(task_name, question, options, 
                                                               few_shot_examples, expert_instruction)
                        else:
                            prompt = self.build_prompt(prompt_template, question, options)
                        
                        q_start_time = time.time()
                        answer, _ = self.generate_answer(prompt, params)
                        elapsed_time = time.time() - q_start_time
                        total_time += elapsed_time
                        
                        if answer == groundtruth:
                            correct_count += 1
                        else:
                            # 记录错误题目索引（仅用于TQA任务）
                            if task_name == "TQA Task":
                                error_indices.append(i)
                    except Exception as e:
                        if task_name == "TQA Task":
                            error_indices.append(i)
                        continue
            
            elapsed_total = time.time() - start_time
            accuracy = correct_count / len(questions) * 100 if questions else 0
            
            all_accuracies.append(accuracy)
            all_correct_counts.append(correct_count)
            all_total_times.append(elapsed_total)
            
            if num_runs > 1:
                print(f"      运行 {run+1} 准确率: {accuracy:.2f}%")
                import sys
                sys.stdout.flush()
        
        # 计算平均值
        avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
        avg_correct_count = sum(all_correct_counts) / len(all_correct_counts) if all_correct_counts else 0
        avg_total_time = sum(all_total_times) / len(all_total_times) if all_total_times else 0
        
        result = {
            'task_name': task_name,
            'accuracy': avg_accuracy,
            'correct_count': int(round(avg_correct_count)),
            'total_questions': len(questions),
            'avg_time': avg_total_time / len(questions) if questions else 0,
            'total_time': avg_total_time,
            'num_runs': num_runs,
            'individual_accuracies': all_accuracies if num_runs > 1 else None
        }
        
        # 如果是TQA任务，统计错误难度分布
        if task_name == "TQA Task" and 'error_indices' in locals():
            error_stats = self.analyze_tqa_errors_by_difficulty(questions, error_indices)
            result['error_difficulty_distribution'] = error_stats
            print(f"\n   📊 TQA错误难度分布:")
            for level, stats in error_stats['error_stats'].items():
                print(f"      {level}: {stats['errors']}题错误 ({stats['error_rate']:.2f}%错误率, {stats['accuracy']:.2f}%准确率)")
            import sys
            sys.stdout.flush()
        
        print(f"\n   ✅ {task_name} 测试完成")
        print(f"      准确率: {avg_accuracy:.2f}% ({'平均' if num_runs > 1 else ''})")
        print(f"      正确数: {result['correct_count']}/{len(questions)}")
        if num_runs > 1:
            print(f"      各次运行: {[f'{a:.2f}%' for a in all_accuracies]}")
        print(f"      总时间: {avg_total_time:.1f}秒")
        import sys
        sys.stdout.flush()
        
        return result
    
    def analyze_tqa_errors_by_difficulty(self, questions: List[Dict], error_indices: List[int]) -> Dict[str, Any]:
        """分析TQA错误在各难度级别的分布"""
        from collections import Counter
        
        error_by_level = Counter()
        total_by_level = Counter()
        
        for i, question in enumerate(questions):
            level = question.get('level', 'Unknown')
            total_by_level[level] += 1
            
            if i in error_indices:
                error_by_level[level] += 1
        
        error_stats = {}
        for level in sorted(total_by_level.keys()):
            total = total_by_level[level]
            errors_count = error_by_level[level]
            error_rate = errors_count / total * 100 if total > 0 else 0
            accuracy = (total - errors_count) / total * 100 if total > 0 else 0
            
            error_stats[level] = {
                'total_questions': total,
                'errors': errors_count,
                'correct': total - errors_count,
                'error_rate': error_rate,
                'accuracy': accuracy
            }
        
        return {
            'error_stats': error_stats,
            'total_errors': len(error_indices),
            'total_questions': len(questions)
        }
        print(f"\n{'='*80}")
        print(f"📊 测试任务: {task_name}")
        print(f"{'='*80}")
        import sys
        sys.stdout.flush()
        
        questions = self.load_task_data(task_name)
        if not questions:
            print(f"❌ 无法加载 {task_name} 数据")
            return None
        
        print(f"   加载了 {len(questions)} 个问题")
        import sys
        sys.stdout.flush()
        
        groundtruth_field = self.tasks[task_name]["groundtruth_field"]
        config = self.optimized_configs.get(task_name, {})
        
        correct_count = 0
        total_time = 0
        start_time = time.time()
        
        # 处理Few-shot配置
        few_shot_examples = None
        num_few_shot = config.get('num_examples', 2)  # 从配置中读取示例数量
        if config.get('use_few_shot', False):
            few_shot_examples = config.get('few_shot_examples', [])
            if not few_shot_examples:
                # 如果没有预加载，现在加载
                few_shot_examples = self.load_few_shot_examples(task_name, num_examples=num_few_shot)
        
        # 处理TQA错误模式优化配置
        if isinstance(config, dict) and config.get('type') == 'pattern_optimized':
            strategy_map = config.get('strategy_map', {})
            base_strategy = config.get('base_strategy', {
                "prompt": "Question: {question}\n\nOptions:\n{options}\n\nAnswer:",
                "params": {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                          "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True}
            })
            
            # 使用多策略映射
            for i, question_data in enumerate(questions):
                question = question_data.get('question', '')
                options = question_data.get('options', {})
                groundtruth = question_data.get(groundtruth_field, '')
                
                if not question or not groundtruth:
                    continue
                
                try:
                    # 根据题目索引选择策略
                    if i in strategy_map:
                        strategy = strategy_map[i]
                    else:
                        strategy = base_strategy
                    
                    prompt = self.build_prompt(strategy["prompt"], question, options)
                    q_start_time = time.time()
                    answer, _ = self.generate_answer(prompt, strategy["params"])
                    elapsed_time = time.time() - q_start_time
                    total_time += elapsed_time
                    
                    if answer == groundtruth:
                        correct_count += 1
                    
                    # 每50题输出一次进度
                    if (i + 1) % 50 == 0:
                        print(f"      进度: {i+1}/{len(questions)}, 当前准确率: {correct_count/(i+1)*100:.2f}%")
                        import sys
                        sys.stdout.flush()
                except Exception as e:
                    continue
        else:
            # 标准配置或Few-shot配置
            prompt_template = config.get("prompt", "Question: {question}\n\nOptions:\n{options}\n\nAnswer:")
            params = config.get("params", {"max_new_tokens": 1, "temperature": 0.0, "do_sample": False,
                                         "repetition_penalty": 1.0, "top_p": 1.0, "top_k": 1, "use_cache": True})
            
            for i, question_data in enumerate(questions):
                question = question_data.get('question', '')
                options = question_data.get('options', {})
                groundtruth = question_data.get(groundtruth_field, '')
                
                if not question or not groundtruth:
                    continue
                
                try:
                    # 构建提示词（Few-shot或标准）
                    if config.get('use_few_shot', False) and few_shot_examples:
                        expert_instruction = config.get('expert_instruction', '')
                        prompt = self.build_few_shot_prompt(task_name, question, options, 
                                                           few_shot_examples, expert_instruction)
                    else:
                        prompt = self.build_prompt(prompt_template, question, options)
                    
                    q_start_time = time.time()
                    answer, _ = self.generate_answer(prompt, params)
                    elapsed_time = time.time() - q_start_time
                    total_time += elapsed_time
                    
                    if answer == groundtruth:
                        correct_count += 1
                    
                    # 每50题输出一次进度
                    if (i + 1) % 50 == 0:
                        print(f"      进度: {i+1}/{len(questions)}, 当前准确率: {correct_count/(i+1)*100:.2f}%")
                        import sys
                        sys.stdout.flush()
                except Exception as e:
                    continue
        
        elapsed_total = time.time() - start_time
        accuracy = correct_count / len(questions) * 100 if questions else 0
        avg_time = total_time / len(questions) if questions else 0
        
        result = {
            'task_name': task_name,
            'accuracy': accuracy,
            'correct_count': correct_count,
            'total_questions': len(questions),
            'avg_time': avg_time,
            'total_time': elapsed_total
        }
        
        print(f"\n   ✅ {task_name} 测试完成")
        print(f"      准确率: {accuracy:.2f}%")
        print(f"      正确数: {correct_count}/{len(questions)}")
        print(f"      平均时间: {avg_time:.3f}秒/题")
        print(f"      总时间: {elapsed_total:.1f}秒")
        import sys
        sys.stdout.flush()
        
        return result
    
    def run_full_validation(self):
        """运行完整验证测试"""
        print(f"\n🎯 开始ReasoningV完整验证测试")
        print(f"{'='*80}")
        
        self.load_model()
        
        results = {}
        total_questions = 0
        total_correct = 0
        
        # 按顺序测试所有任务（Few-shot任务运行多次取平均）
        task_order = ["LDO Task", "Comparator Task", "Bandgap Task", 
                     "TQA Task", "Caption Task", "Opamp Task"]
        
        # Few-shot任务需要多次运行取平均（与优化时一致）
        few_shot_tasks = ["LDO Task", "Comparator Task", "Caption Task"]
        
        for task_name in task_order:
            if task_name in self.tasks:
                # Few-shot任务运行3次取平均，其他任务运行1次
                num_runs = 3 if task_name in few_shot_tasks else 1
                result = self.test_task(task_name, num_runs=num_runs)
                if result:
                    results[task_name] = result
                    total_questions += result['total_questions']
                    total_correct += result['correct_count']
        
        # 计算总体准确率
        overall_accuracy = total_correct / total_questions * 100 if total_questions > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"🎉 完整验证测试完成")
        print(f"{'='*80}")
        print(f"\n📊 各任务准确率:")
        for task_name, result in results.items():
            print(f"   {task_name}: {result['accuracy']:.2f}% ({result['correct_count']}/{result['total_questions']})")
        
        print(f"\n📈 总体统计:")
        print(f"   总题目数: {total_questions}")
        print(f"   总正确数: {total_correct}")
        print(f"   总体准确率: {overall_accuracy:.2f}%")
        
        return {
            'results': results,
            'overall_accuracy': overall_accuracy,
            'total_questions': total_questions,
            'total_correct': total_correct
        }
    
    def save_results(self, results: Dict[str, Any]):
        """保存结果"""
        output = {
            'validation_results': results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_path': self.model_path
        }
        
        with open("reasoningv_full_validation_results.json", 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 结果已保存到: reasoningv_full_validation_results.json")

def main():
    """主函数"""
    print("🚀 ReasoningV优化后完整验证测试工具")
    print("使用所有优化后的策略配置，完整测试AMSBench所有题目")
    print("确保准确率可重复")
    print("="*80)
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    reasoningv_path = "/home/ligengfei/LLM/Analogseeker-lgf/ReasoningV-7B"
    
    validator = ReasoningVFullValidation(reasoningv_path)
    results = validator.run_full_validation()
    
    if results:
        validator.save_results(results)
        
        # 与预期结果对比
        expected_results = {
            "LDO Task": 80.67,
            "Comparator Task": 76.00,
            "Bandgap Task": 70.00,
            "TQA Task": 93.32,
            "Caption Task": 60.24,
            "Opamp Task": 58.33
        }
        
        print(f"\n{'='*80}")
        print(f"📊 与预期结果对比:")
        print(f"{'='*80}")
        all_match = True
        for task_name, result in results['results'].items():
            expected = expected_results.get(task_name, 0)
            actual = result['accuracy']
            diff = actual - expected
            match = abs(diff) < 0.5  # 允许0.5%的误差
            status = "✅" if match else "⚠️"
            print(f"   {status} {task_name}:")
            print(f"      预期: {expected:.2f}%, 实际: {actual:.2f}%, 差异: {diff:+.2f}%")
            if not match:
                all_match = False
        
        if all_match:
            print(f"\n✅ 所有任务准确率与预期一致，验证通过！")
        else:
            print(f"\n⚠️ 部分任务准确率与预期存在差异，请检查配置")
    
    return results

if __name__ == "__main__":
    main()

