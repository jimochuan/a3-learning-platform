"""
=============================================================================
main.py — A3 v3 个性化学习多智能体系统 主入口
=============================================================================
六智能体协作 · DeepSeek 主力模型 · 讯飞星火交叉验证

用法:
    python main.py              # 启动 Web 界面（默认）
    python main.py --web        # 启动 Web 界面
    python main.py --help       # 查看帮助

=============================================================================
"""

import argparse
import logging
import subprocess
import sys
import os

# 把项目根目录加入 sys.path，确保模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==========================================================================
# 命令行参数
# ==========================================================================
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="A3 v3 个性化学习多智能体系统 — 六智能体 · DeepSeek + 讯飞星火",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                     启动 Web 界面（默认）
  python main.py --web               启动 Web 界面
  python main.py --port 8502         指定端口启动
        """,
    )

    parser.add_argument(
        "--web",
        action="store_true",
        default=True,
        help="启动 Streamlit Web 界面（默认模式）",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Web 服务端口号（默认 8501）",
    )

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="启动服务但不自动打开浏览器",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细日志输出",
    )

    return parser.parse_args()


# ==========================================================================
# 主函数
# ==========================================================================
def main():
    """程序主入口"""
    args = parse_args()

    # ---- 日志配置 ----
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger(__name__)

    # ---- 构建 streamlit 命令 ----
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]

    if args.no_browser:
        cmd.append("--server.headless")
        cmd.append("true")

    if args.port != 8501:
        cmd.extend(["--server.port", str(args.port)])

    logger.info("启动 Web 界面: http://localhost:%s", args.port)
    print(f"\n  A3 v3 学习系统启动中...")
    print(f"  浏览器将自动打开，如未打开请手动访问: http://localhost:{args.port}\n")

    subprocess.run(cmd)


# ==========================================================================
# 入口
# ==========================================================================
if __name__ == "__main__":
    main()
