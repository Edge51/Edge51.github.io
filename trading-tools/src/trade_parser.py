"""
交易记录解析和复盘生成模块
支持从多个数据源解析交易记录，自动生成复盘报告
"""
import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class TradeRecord:
    time: str
    code: str
    name: str
    direction: str
    price: float
    quantity: int
    position_ratio: str
    mode: str
    description: str
    trade_id: str

@dataclass
class DailySummary:
    date: str
    total_trades: int
    buy_count: int
    sell_count: int
    total_pnl_pct: float
    position_change: str
    trades: List[TradeRecord]

class TradeRecordParser:
    """
    交易记录解析器
    支持多种格式的交易记录导入
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def parse_from_text(self, text: str) -> List[TradeRecord]:
        """
        从文本中解析交易记录
        支持Markdown表格格式
        """
        records = []

        lines = text.strip().split('\n')
        table_started = False

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if '| 时间 |' in line or '|时间|' in line:
                table_started = True
                continue

            if not table_started:
                continue

            if '---' in line:
                continue

            if line.startswith('|') and '---' not in line:
                parts = [p.strip() for p in line.split('|')]

                if len(parts) < 11:
                    continue

                if parts[1] in ['时间', '']:
                    continue

                try:
                    record = TradeRecord(
                        time=parts[1] or "",
                        code=parts[2] or "",
                        name=parts[3] or "",
                        direction=parts[4] or "",
                        price=float(parts[5]) if parts[5] else 0.0,
                        quantity=int(parts[6]) if parts[6] else 0,
                        position_ratio=parts[7] or "",
                        mode=parts[8] or "",
                        description=parts[9] or "",
                        trade_id=parts[10] or ""
                    )

                    if record.code or record.time:
                        records.append(record)
                except (ValueError, IndexError) as e:
                    continue

        return records

    def parse_from_json(self, json_str: str) -> List[TradeRecord]:
        """
        从JSON字符串解析交易记录
        """
        try:
            data = json.loads(json_str)

            if isinstance(data, list):
                records = []
                for item in data:
                    record = TradeRecord(
                        time=item.get('time', ''),
                        code=item.get('code', ''),
                        name=item.get('name', ''),
                        direction=item.get('direction', ''),
                        price=float(item.get('price', 0)),
                        quantity=int(item.get('quantity', 0)),
                        position_ratio=item.get('position_ratio', ''),
                        mode=item.get('mode', ''),
                        description=item.get('description', ''),
                        trade_id=item.get('trade_id', '')
                    )
                    records.append(record)
                return records
        except json.JSONDecodeError:
            pass

        return []

    def parse_from_csv(self, csv_content: str) -> List[TradeRecord]:
        """
        从CSV内容解析交易记录
        """
        records = []
        lines = csv_content.strip().split('\n')

        for i, line in enumerate(lines):
            if i == 0:
                continue

            parts = line.split(',')
            if len(parts) < 10:
                continue

            try:
                record = TradeRecord(
                    time=parts[0].strip(),
                    code=parts[1].strip(),
                    name=parts[2].strip(),
                    direction=parts[3].strip(),
                    price=float(parts[4].strip()),
                    quantity=int(parts[5].strip()),
                    position_ratio=parts[6].strip(),
                    mode=parts[7].strip(),
                    description=parts[8].strip(),
                    trade_id=parts[9].strip() if len(parts) > 9 else ''
                )
                records.append(record)
            except (ValueError, IndexError):
                continue

        return records

    def group_by_date(self, records: List[TradeRecord]) -> Dict[str, List[TradeRecord]]:
        """
        按日期分组交易记录
        """
        grouped = {}

        for record in records:
            if not record.time:
                continue

            date_str = record.time[:10]

            if date_str not in grouped:
                grouped[date_str] = []

            grouped[date_str].append(record)

        return grouped

class ReviewGenerator:
    """
    复盘报告生成器
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def generate_daily_review(
        self,
        date: str,
        market_data: Dict,
        trades: List[TradeRecord],
        pre_plan: Optional[Dict] = None,
        personal_state: str = ""
    ) -> str:
        market_stage = market_data.get('market_stage', '')
        shanghai_index = market_data.get('shanghai_index', 0)
        shanghai_change = market_data.get('shanghai_change_pct', 0)
        shanghai_open = market_data.get('shanghai_open', 0)
        shanghai_high = market_data.get('shanghai_high', 0)
        shanghai_low = market_data.get('shanghai_low', 0)
        volume = market_data.get('volume', 0)        # 成交量（手）
        amount = market_data.get('amount', 0)         # 成交额（元）
        active_value_change = market_data.get('active_market_value_change', 0)
        limit_up = market_data.get('limit_up_count', 0)
        limit_down = market_data.get('limit_down_count', 0)
        up_count = market_data.get('up_count', 0)
        flat_count = market_data.get('flat_count', 0)
        down_count = market_data.get('down_count', 0)
        main_sectors = market_data.get('main_sectors', [])

        if pre_plan:
            market_prediction = pre_plan.get('market_prediction', '。')
            focus_areas = pre_plan.get('focus_areas', '。')
            strategy = pre_plan.get('strategy', '。')
            risk_warning = pre_plan.get('risk_warning', '。')
        else:
            market_prediction = ""
            focus_areas = ""
            strategy = ""
            risk_warning = ""

        trade_rows = []
        for trade in trades:
            desc_clean = trade.description.replace('\n', ' ').strip()
            row = f"| {trade.name} | {trade.direction} | {trade.mode} | {desc_clean} |"
            trade_rows.append(row)
        trade_table = "\n".join(trade_rows) if trade_rows else "| | | | |"

        sectors_str = '、'.join(main_sectors) if isinstance(main_sectors, list) else str(main_sectors)

        amount_str = f"{float(amount) / 100000000:.0f}亿" if amount and float(amount) > 1000000000 else ""
        change_str = f"{shanghai_change:+.2f}%" if shanghai_change != 0 else ""
        index_str = f"{shanghai_index:.2f} ({change_str})" if change_str else f"{shanghai_index:.2f}"
        active_str = f"{active_value_change:+.2f}%"

        ohlc_str = ""
        if shanghai_open or shanghai_high or shanghai_low:
            amplitude = round(shanghai_high - shanghai_low, 2) if shanghai_high and shanghai_low else 0
            ohlc_str = f"\n| 开盘/最高/最低 | {shanghai_open:.2f}/{shanghai_high:.2f}/{shanghai_low:.2f} | 振幅{amplitude} |"

        review = f"""### {date} | 市场阶段：{market_stage} | 个人状态：{personal_state}

#### 一、盘前计划
- **大盘预判**：{market_prediction}
- **关注方向**：{focus_areas}
- **今日策略**：{strategy}
- **风险警示**：{risk_warning}

#### 二、市场数据（盘后更新）

| 指标 | 数值 | 解读 |
| :--- | :--- | :--- |
| 上证指数 | {index_str} |{amount_str}|
| 开盘/最高/最低 | {shanghai_open:.2f}/{shanghai_high:.2f}/{shanghai_low:.2f} | 振幅{amplitude} |
| 活跃市值 |{active_str} | |
| 涨停家数 | {limit_up} | |
| 跌停家数 | {limit_down} | |
| 涨:平:跌 | {up_count}:{flat_count}:{down_count} | |
| 主线板块 | {sectors_str} | |

#### 三、交易记录

| 名称 | 方向 | 定式 | 买卖点描述（关键！） |
| :--- | :--- | :--- | :--- |
{trade_table}

#### 四、交易逻辑与深度复盘

#### 五、持仓股分析（无持仓则写"空仓"）

#### 六、明日策略
- **核心观察**：。
- **机会方向**：
    1.
    2.
- **风险控制**：。

#### 七、心态与纪律检查
- [ ] 是否按计划交易？
- [ ] 是否执行了止损？
- [ ] 是否有模式外操作？
- [ ] 是否因情绪（贪婪/恐惧）影响了决策？
"""
        return review

    def generate_weekly_summary(self, daily_reviews: List[str]) -> str:
        """
        生成周度总结
        """
        return "\n\n".join(daily_reviews)

    def generate_monthly_summary(self, daily_reviews: List[str]) -> str:
        """
        生成月度总结
        """
        return "\n\n".join(daily_reviews)

class TradeAnalyzer:
    """
    交易分析器
    分析交易记录，生成统计和洞察
    """

    def __init__(self):
        pass

    def analyze_trades(self, trades: List[TradeRecord]) -> Dict:
        """
        分析交易记录
        """
        if not trades:
            return {
                "total_trades": 0,
                "buy_count": 0,
                "sell_count": 0,
                "avg_price": 0,
                "modes": {},
            }

        buy_count = sum(1 for t in trades if '买' in t.direction)
        sell_count = sum(1 for t in trades if '卖' in t.direction)

        modes = {}
        for trade in trades:
            mode = trade.mode
            modes[mode] = modes.get(mode, 0) + 1

        total_value = sum(t.price * t.quantity for t in trades)
        avg_price = total_value / len(trades) if trades else 0

        return {
            "total_trades": len(trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "avg_price": round(avg_price, 2),
            "modes": modes,
        }

    def identify_patterns(self, trades: List[TradeRecord]) -> List[str]:
        """
        识别交易模式
        """
        patterns = []
        stop_trades = [t for t in trades if t.mode == '止损']
        if len(stop_trades) > 2:
            patterns.append(f"止损交易过多: {len(stop_trades)}次")

        buy_trades = [t for t in trades if '买' in t.direction and t.time]
        if len(buy_trades) > 0:
            morning_trades = [t for t in buy_trades if t.time < '10:00']
            if len(morning_trades) > len(buy_trades) / 2:
                patterns.append("偏好早盘交易")

        high_position_trades = [t for t in trades if t.position_ratio in ['100%', '80%', '50%']]
        if len(high_position_trades) > len(trades) / 2:
            patterns.append("仓位普遍较重")

        return patterns

class ReviewTemplateManager:
    """
    复盘模板管理器
    管理不同的复盘模板
    """

    TEMPLATES = {
        "default": """### {date} | 市场阶段：{market_stage} | 个人状态：{personal_state}

#### 一、盘前计划
- **大盘预判**：{market_prediction}
- **关注方向**：{focus_areas}
- **今日策略**：{strategy}
- **风险警示**：{risk_warning}

#### 二、市场数据（盘后更新）
| 指标 | 数值 | 解读 |
| :--- | :--- | :--- |
| 上证指数 | {shanghai_index} | {index_interpretation} |
| 活跃市值 | {active_value_change}% | {active_value_interpretation} |
| 涨停家数 | {limit_up} | {limit_up_interpretation} |
| 跌停家数 | {limit_down} | |
| 主线板块 | {main_sectors} | |

#### 三、交易记录
| 名称 | 方向 | 定式 | 买卖点描述（关键！） |
| :--- | :--- | :--- | :--- |
{trade_table}

#### 四、交易逻辑与深度复盘

#### 五、持仓股分析

#### 六、明日策略

#### 七、心态与纪律检查
- [ ] 是否按计划交易？
- [ ] 是否执行了止损？
- [ ] 是否有模式外操作？
- [ ] 是否因情绪影响了决策？
""",
    }

    def get_template(self, name: str = "default") -> str:
        return self.TEMPLATES.get(name, self.TEMPLATES["default"])

    def add_template(self, name: str, template: str):
        self.TEMPLATES[name] = template

    def render_template(self, name: str, **kwargs) -> str:
        template = self.get_template(name)
        return template.format(**kwargs)