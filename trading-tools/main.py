"""
交易复盘工具 - CLI入口
"""
import os
import sys
import json
import argparse
from datetime import datetime, date
from typing import Optional, Dict, List

from src.core import TradingToolsConfig, TradeReviewGenerator, MarketData, TradeRecord
from src.tdx_reader import TdxDataReader, get_market_status
from src.network_api import MarketDataAggregator
from src.trade_parser import TradeRecordParser, ReviewGenerator

def setup_config(config_path: Optional[str] = None) -> TradingToolsConfig:
    """初始化配置"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config/settings.json')

    config = TradingToolsConfig(config_path)

    print("=== 交易复盘工具配置 ===")
    print(f"通达信数据路径: {config.config.get('tdx_data_path', '未设置')}")
    print(f"指南针API: {'已配置' if config.config.get('compass_api', {}).get('api_key') else '未配置'}")
    print()

    return config

def cmd_fetch_market(date_str: Optional[str] = None) -> Dict:
    """获取市场数据"""
    date_str = date_str or datetime.now().strftime('%Y-%m-%d')
    print(f"正在获取市场数据: {date_str}...")

    aggregator = MarketDataAggregator()

    try:
        summary = aggregator.get_daily_summary(date_str)

        # 用通达信本地数据覆盖上证指数（可获取精确的历史日线数据）
        try:
            reader = TdxDataReader()
            df = reader.read_day_file('000001', 'sh')
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            row = df[df['date'] == target_date]
            if not row.empty:
                r = row.iloc[0]
                summary['shanghai_index'] = float(r['close'])
                summary['shanghai_open'] = float(r['open'])
                summary['shanghai_high'] = float(r['high'])
                summary['shanghai_low'] = float(r['low'])
                # 指数成交额从新浪获取（更准确）
                idx = df[df['date'] == target_date].index[0]
                if idx > 0:
                    prev_close = float(df.iloc[idx - 1]['close'])
                    if prev_close:
                        summary['shanghai_change_pct'] = round(
                            (float(r['close']) - prev_close) / prev_close * 100, 2
                        )
        except (FileNotFoundError, Exception):
            pass

        print("\n=== 市场数据 ===")
        print(f"上证指数: {summary.get('shanghai_index', 0):.2f}")
        print(f"涨跌幅: {summary.get('shanghai_change_pct', 0):+.2f}%")
        print(f"活跃市值变化: {summary.get('active_market_value_change', 0):+.2f}%")
        print(f"涨停家数: {summary.get('limit_up_count', 0)}")
        print(f"跌停家数: {summary.get('limit_down_count', 0)}")
        print(f"主线板块: {', '.join(summary.get('main_sectors', []))}")
        print(f"市场阶段: {summary.get('market_stage', '未知')}")

        return summary
    except Exception as e:
        print(f"获取市场数据失败: {e}")
        return {}

def cmd_fetch_stock(code: str, market: str = "sh", data_type: str = "day") -> Dict:
    """获取个股数据"""
    print(f"正在获取个股数据: {code} ({market})...")

    reader = TdxDataReader()

    try:
        if data_type == "day":
            df = reader.read_day_file(code, market)
            print(f"\n获取到 {len(df)} 条日线数据")

            if not df.empty:
                latest = df.iloc[-1]
                print(f"最新数据: {latest['date']}")
                print(f"收盘价: {latest['close']:.2f}")

                if len(df) > 1:
                    prev = df.iloc[-2]
                    change = (latest['close'] - prev['close']) / prev['close'] * 100
                    print(f"涨跌幅: {change:+.2f}%")

            return {"status": "success", "data": df.tail(10).to_dict('records')}

        elif data_type == "minute1":
            df = reader.read_minute_file(code, market, 1)
            print(f"\n获取到 {len(df)} 条1分钟数据")
            return {"status": "success", "data": df.tail(30).to_dict('records')}

        else:
            print(f"不支持的数据类型: {data_type}")
            return {"status": "failed", "error": f"Unsupported data type: {data_type}"}

    except FileNotFoundError:
        print(f"找不到数据文件，请检查通达信数据路径是否正确")
        return {"status": "failed", "error": "Data file not found"}
    except Exception as e:
        print(f"获取数据失败: {e}")
        return {"status": "failed", "error": str(e)}

def cmd_parse_trades(text: str) -> List[TradeRecord]:
    """解析交易记录"""
    print("正在解析交易记录...")

    parser = TradeRecordParser()
    records = parser.parse_from_text(text)

    print(f"\n解析到 {len(records)} 条交易记录:")
    for i, record in enumerate(records):
        print(f"  {i+1}. {record.time} | {record.code} {record.name} | {record.direction} @ {record.price} x {record.quantity}")

    return records

def cmd_generate_review(
    date_str: str,
    market_data: Dict,
    trades: List[TradeRecord],
    pre_plan: Optional[Dict] = None,
    output_path: Optional[str] = None
) -> str:
    """生成复盘报告"""
    print(f"正在生成复盘报告: {date_str}...")

    generator = ReviewGenerator()
    review = generator.generate_daily_review(date_str, market_data, trades, pre_plan)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(review)
        print(f"复盘报告已保存到: {output_path}")

    return review

def cmd_full_review(date_str: Optional[str] = None) -> str:
    """完整复盘流程"""
    date_str = date_str or datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*50}")
    print(f"开始生成复盘报告: {date_str}")
    print(f"{'='*50}\n")

    market_data = cmd_fetch_market(date_str)

    print("\n" + "-"*50)
    print("请粘贴交易记录（Markdown表格格式）:")
    print("按 Ctrl+D (Linux/Mac) 或 Ctrl+Z (Windows) 结束输入")
    print("-"*50 + "\n")

    try:
        lines = []
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        trade_text = '\n'.join(lines)

    if not trade_text.strip():
        print("未输入交易记录")
        return ""

    trades = cmd_parse_trades(trade_text)

    if trades:
        output_path = os.path.join(os.path.dirname(__file__), f'../_posts/{date_str}-auto-review.md')
        review = cmd_generate_review(date_str, market_data, trades, output_path=output_path)

        print("\n" + "="*50)
        print("复盘报告预览:")
        print("="*50)
        print(review)

        return review

    return ""

POST_PATH = os.path.join(os.path.dirname(__file__), '../_posts/2026-04-16-blog-post-trade-record.md')

def cmd_append_review(date_str: Optional[str] = None) -> str:
    """
    生成当日复盘模板并追加到博客文件
    工作流：获取TDX大盘数据 → 生成复盘模板 → 追加到 _posts/2026-04-16-blog-post-trade-record.md
    """
    date_str = date_str or datetime.now().strftime('%Y-%m-%d')
    today = datetime.now()

    weekday_map = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday_str = weekday_map[today.weekday()]

    print(f"正在为 {date_str} ({weekday_str}) 生成复盘模板...")

    agg = MarketDataAggregator()
    market_data = agg.get_daily_summary(date_str)

    gen = ReviewGenerator()
    review = gen.generate_daily_review(date_str, market_data, [])

    lines = review.strip().split('\n')
    lines[0] = f"### {date_str} {weekday_str} | 市场阶段：{market_data.get('market_stage', '')} | 个人状态："
    review = '\n'.join(lines)

    print("\n=== 复盘模板预览 ===")
    print(review)

    post_path = os.path.abspath(POST_PATH)
    if not os.path.exists(post_path):
        print(f"错误：找不到博客文件 {post_path}")
        return review

    with open(post_path, 'r', encoding='utf-8') as f:
        content = f.read()

    insert_marker = f"### {date_str}"
    if insert_marker in content:
        print(f"文件已包含 {date_str} 的复盘记录，更新中...")
        start = content.index(insert_marker)
        next_section = content.find("\n### ", start + 1)
        if next_section == -1:
            content = content[:start] + review.strip() + "\n\n"
        else:
            content = content[:start] + review.strip() + "\n\n" + content[next_section:]
    else:
        first_section = content.find("\n### 20")
        if first_section == -1:
            content += "\n\n" + review.strip() + "\n"
        else:
            content = content[:first_section] + "\n\n" + review.strip() + "\n\n" + content[first_section:].lstrip('\n')

    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n复盘模板已追加到: {post_path}")
    return review

def main():
    parser = argparse.ArgumentParser(
        description='交易复盘工具 - 自动获取市场数据、解析交易记录、生成复盘报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py fetch-market --date 2026-05-12
  python main.py fetch-stock 600312 --market sh --type day
  python main.py parse-trades < trades.txt
  python main.py generate-review --date 2026-05-12 --market-data data.json
  python main.py full-review --date 2026-05-12
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    fetch_market_parser = subparsers.add_parser('fetch-market', help='获取市场数据')
    fetch_market_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')

    fetch_stock_parser = subparsers.add_parser('fetch-stock', help='获取个股数据')
    fetch_stock_parser.add_argument('code', help='股票代码')
    fetch_stock_parser.add_argument('--market', '-m', default='sh', choices=['sh', 'sz'], help='市场')
    fetch_stock_parser.add_argument('--type', '-t', default='day', choices=['day', 'minute1', 'minute5', 'realtime'], help='数据类型')

    parse_trades_parser = subparsers.add_parser('parse-trades', help='解析交易记录')
    parse_trades_parser.add_argument('file', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help='交易记录文件')

    gen_review_parser = subparsers.add_parser('generate-review', help='生成复盘报告')
    gen_review_parser.add_argument('--date', '-d', required=True, help='复盘日期')
    gen_review_parser.add_argument('--market-data', '-m', help='市场数据JSON文件')
    gen_review_parser.add_argument('--trades-file', '-t', help='交易记录文件')
    gen_review_parser.add_argument('--output', '-o', help='输出路径')

    full_review_parser = subparsers.add_parser('full-review', help='完整复盘流程（交互式）')
    full_review_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)')

    append_parser = subparsers.add_parser('append-review', help='生成今日复盘模板并追加到博客')
    append_parser.add_argument('--date', '-d', help='日期 (YYYY-MM-DD)，默认今天')

    args = parser.parse_args()

    if args.command == 'fetch-market':
        cmd_fetch_market(args.date)

    elif args.command == 'fetch-stock':
        cmd_fetch_stock(args.code, args.market, args.type)

    elif args.command == 'parse-trades':
        if hasattr(args, 'file') and hasattr(args.file, 'read'):
            text = args.file.read()
            cmd_parse_trades(text)

    elif args.command == 'generate-review':
        market_data = {}
        if args.market_data and os.path.exists(args.market_data):
            with open(args.market_data, 'r', encoding='utf-8') as f:
                market_data = json.load(f)

        trades = []
        if args.trades_file and os.path.exists(args.trades_file):
            with open(args.trades_file, 'r', encoding='utf-8') as f:
                parser = TradeRecordParser()
                trades = parser.parse_from_text(f.read())

        cmd_generate_review(args.date, market_data, trades, output_path=args.output)

    elif args.command == 'full-review':
        cmd_full_review(args.date)

    elif args.command == 'append-review':
        cmd_append_review(args.date)

    else:
        parser.print_help()

if __name__ == '__main__':
    main()