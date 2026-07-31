#!/usr/bin/env python3
"""
测试运行脚本
支持多种测试模式和配置
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(test_type="all", coverage=False, verbose=True, markers=None):
    """
    运行测试
    
    Args:
        test_type: 测试类型 (unit, integration, e2e, security, all)
        coverage: 是否生成覆盖率报告
        verbose: 是否详细输出
        markers: pytest标记过滤
    """
    cmd = ["python", "-m", "pytest"]
    
    # 测试路径和标记过滤
    # 使用 markers 进行精确过滤，而不是依赖目录结构
    if test_type == "unit":
        cmd.extend(["tests/", "-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["tests/", "-m", "integration"])
    elif test_type == "e2e":
        cmd.extend(["tests/", "-m", "e2e"])
    elif test_type == "security":
        cmd.extend(["tests/", "-m", "security"])
    elif test_type == "all":
        cmd.extend(["tests/"])
    
    # 覆盖率
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term", "--cov-report=xml"])
    
    # 详细输出
    if verbose:
        cmd.append("-v")
    
    # 自定义标记（可以覆盖 test_type 的过滤）
    if markers:
        cmd.extend(["-m", markers])
    
    # 添加 JUnit XML 输出用于 CI
    cmd.extend(["--junitxml=test_results.xml"])
    
    # 运行测试
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd="backend")
    
    return result.returncode


def run_specific_marker(marker, coverage=False, verbose=True):
    """
    按指定 marker 运行测试
    
    Args:
        marker: pytest marker 名称
        coverage: 是否生成覆盖率报告
        verbose: 是否详细输出
    """
    return run_tests(test_type="all", coverage=coverage, verbose=verbose, markers=marker)


def list_markers():
    """列出所有已注册的 markers"""
    cmd = ["python", "-m", "pytest", "--markers"]
    print(f"运行命令: {' '.join(cmd)}")
    subprocess.run(cmd, cwd="backend")


def collect_tests(test_type="all"):
    """
    收集（不执行）测试列表，用于验证过滤是否正确
    
    Args:
        test_type: 测试类型
    """
    cmd = ["python", "-m", "pytest", "--collect-only", "-q"]
    
    if test_type == "unit":
        cmd.extend(["tests/", "-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["tests/", "-m", "integration"])
    elif test_type == "e2e":
        cmd.extend(["tests/", "-m", "e2e"])
    elif test_type == "security":
        cmd.extend(["tests/", "-m", "security"])
    elif test_type == "all":
        cmd.extend(["tests/"])
    
    print(f"收集测试: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd="backend")
    return result.returncode


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试运行脚本")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "e2e", "security", "all"],
        default="all",
        help="测试类型"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="详细输出"
    )
    parser.add_argument(
        "--markers",
        type=str,
        help="pytest标记过滤（可覆盖 --type）"
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="仅收集测试，不执行"
    )
    parser.add_argument(
        "--list-markers",
        action="store_true",
        help="列出所有已注册的markers"
    )
    
    args = parser.parse_args()
    
    # 列出 markers
    if args.list_markers:
        list_markers()
        sys.exit(0)
    
    # 仅收集测试
    if args.collect_only:
        exit_code = collect_tests(test_type=args.type)
        sys.exit(exit_code)
    
    # 运行测试
    exit_code = run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        markers=args.markers
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
