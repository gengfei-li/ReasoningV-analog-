"""
分析TQA题目的分布情况：按难度和问题类型分类
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from question_router import QuestionRouter


def analyze_tqa_distribution():
    """分析TQA题目分布"""
    # 加载TQA数据
    amsbench_path = Path("/home/ligengfei/LLM/Analogseeker-lgf/AMSBench")
    tqa_file = amsbench_path / "data" / "TQA" / "test.json"
    
    if not tqa_file.exists():
        # 尝试其他路径
        tqa_file = amsbench_path / "TQA" / "test.json"
    
    if not tqa_file.exists():
        print(f"未找到TQA数据文件: {tqa_file}")
        return None
    
    with open(tqa_file, 'r', encoding='utf-8') as f:
        tqa_data = json.load(f)
    
    router = QuestionRouter()
    
    # 分析统计
    stats = {
        'by_difficulty': defaultdict(lambda: {'total': 0, 'by_type': Counter()}),
        'by_type': Counter(),
        'by_strategy': Counter(),
        'details': []
    }
    
    for i, item in enumerate(tqa_data):
        question = item.get('question', '')
        level = item.get('level', 'Unknown')
        
        # 分类问题类型
        q_type, strategy, confidence = router.classify_question(question)
        
        # 统计
        stats['by_difficulty'][level]['total'] += 1
        stats['by_difficulty'][level]['by_type'][q_type] += 1
        stats['by_type'][q_type] += 1
        stats['by_strategy'][strategy] += 1
        
        stats['details'].append({
            'index': i,
            'level': level,
            'question_type': q_type,
            'strategy': strategy,
            'confidence': confidence,
            'question_preview': question[:80] + '...' if len(question) > 80 else question
        })
    
    return stats


def generate_distribution_report(stats):
    """生成分布报告"""
    if not stats:
        return "无法生成报告：缺少数据"
    
    report = "# TQA题目分布分析报告\n\n"
    report += "本报告分析TQA题目的难度分布和问题类型分布。\n\n"
    
    # 按难度分布
    report += "## 按难度分类分布\n\n"
    report += "| 难度级别 | 题目数量 | 占比 | 问题类型分布 |\n"
    report += "|---------|---------|------|-------------|\n"
    
    total_questions = sum(d['total'] for d in stats['by_difficulty'].values())
    
    for level in ['Undergraduate', 'Graduate', 'Unknown']:
        if level in stats['by_difficulty']:
            level_data = stats['by_difficulty'][level]
            count = level_data['total']
            percentage = count / total_questions * 100 if total_questions > 0 else 0
            
            type_dist = ', '.join([f"{t}: {c}" for t, c in level_data['by_type'].most_common(3)])
            report += f"| {level} | {count} | {percentage:.1f}% | {type_dist} |\n"
    
    # 按问题类型分布
    report += "\n## 按问题类型分布\n\n"
    report += "| 问题类型 | 题目数量 | 占比 | 推荐策略 |\n"
    report += "|---------|---------|------|---------|\n"
    
    for q_type, count in stats['by_type'].most_common():
        percentage = count / total_questions * 100 if total_questions > 0 else 0
        # 获取该类型对应的策略
        strategy = 'answer_precisely'  # 默认
        if q_type == 'reasoning':
            strategy = 'analyze_carefully'
        elif q_type == 'calculation':
            strategy = 'circuit_expert'
        
        report += f"| {q_type} | {count} | {percentage:.1f}% | {strategy} |\n"
    
    # 按策略分布
    report += "\n## 按推荐策略分布\n\n"
    report += "| 策略 | 题目数量 | 占比 |\n"
    report += "|------|---------|------|\n"
    
    for strategy, count in stats['by_strategy'].most_common():
        percentage = count / total_questions * 100 if total_questions > 0 else 0
        report += f"| {strategy} | {count} | {percentage:.1f}% |\n"
    
    return report


if __name__ == '__main__':
    stats = analyze_tqa_distribution()
    
    if stats:
        report = generate_distribution_report(stats)
        print(report)
        
        # 保存报告
        report_path = Path("docs/TQA题目分布分析报告.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到: {report_path}")
        
        # 保存统计数据
        stats_path = Path("results/tqa_distribution_stats.json")
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        # 转换Counter为普通dict以便JSON序列化
        stats_json = {
            'by_difficulty': {
                k: {
                    'total': v['total'],
                    'by_type': dict(v['by_type'])
                } for k, v in stats['by_difficulty'].items()
            },
            'by_type': dict(stats['by_type']),
            'by_strategy': dict(stats['by_strategy']),
            'total_questions': sum(d['total'] for d in stats['by_difficulty'].values())
        }
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats_json, f, indent=2, ensure_ascii=False)
        print(f"统计数据已保存到: {stats_path}")
    else:
        print("无法分析TQA分布：数据文件不存在")

