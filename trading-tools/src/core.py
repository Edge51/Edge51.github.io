"""
交易工具核心模块 - 数据源集成与复盘生成
"""
import os
import json
import re
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class TradeRecord:
    time: str
    code: str
    name: str
    direction: str  # 买入/卖出
    price: float
    quantity: int
    position_ratio: str  # 仓位
    mode: str  # 模式: 止损/低吸/半路
    description: str  # 买卖点描述
    trade_id: str

@dataclass
class MarketData:
    date: str
    shanghai_index: float
    shanghai_change: float
    volume: float
    active_market_value_change: float
    limit_up_count: int
    limit_down_count: int
    main_sectors: str
    interpretation: str

class TradingToolsConfig:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '../config/settings.json')
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self) -> Dict:
        return {
            "tdx_data_path": "C:/TdxW/data",
            "compass_api": {
                "enabled": True,
                "api_url": "https://api.compass.com",
                "api_key": ""
            },
            "output_format": "markdown",
            "auto_backup": True
        }

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

def parse_trade_table(table_content: str) -> List[TradeRecord]:
    records = []
    lines = table_content.strip().split('\n')

    for line in lines:
        if not line.strip() or '时间' in line or '---' in line:
            continue

        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 10:
            continue

        try:
            record = TradeRecord(
                time=parts[1],
                code=parts[2],
                name=parts[3],
                direction=parts[4],
                price=float(parts[5]),
                quantity=int(parts[6]),
                position_ratio=parts[7],
                mode=parts[8],
                description=parts[9],
                trade_id=parts[10] if len(parts) > 10 else ""
            )
            records.append(record)
        except (ValueError, IndexError):
            continue

    return records

def parse_market_data_table(table_content: str) -> MarketData:
    lines = table_content.strip().split('\n')

    data = {
        "date": "",
        "shanghai_index": 0.0,
        "shanghai_change": 0.0,
        "volume": 0.0,
        "active_market_value_change": 0.0,
        "limit_up_count": 0,
        "limit_down_count": 0,
        "main_sectors": "",
        "interpretation": ""
    }

    for line in lines:
        if '上证指数' in line:
            match = re.search(r'(\d+\.?\d*)\s*\(?([+-]?\d+\.?\d*)%?\)?', line)
            if match:
                data["shanghai_index"] = float(match.group(1))
                change_str = match.group(2)
                data["shanghai_change"] = float(change_str.replace('%', ''))

        if '活跃市值' in line:
            match = re.search(r'([+-]?\d+\.?\d+)%', line)
            if match:
                data["active_market_value_change"] = float(match.group(1))

        if '涨停家数' in line:
            match = re.search(r'(\d+)', line)
            if match:
                data["limit_up_count"] = int(match.group(1))

        if '跌停家数' in line:
            match = re.search(r'(\d+)', line)
            if match:
                data["limit_down_count"] = int(match.group(1))

        if '主线板块' in line:
            parts = line.split('|')
            if len(parts) > 1:
                data["main_sectors"] = parts[1].strip()

    return MarketData(**data)

def generate_review_markdown(
    date_str: str,
    market_data: MarketData,
    trades: List[TradeRecord],
    market_stage: str = "",
    personal_state: str = "",
    pre_plan: Dict = None
) -> str:
    trade_rows = []
    for trade in trades:
        trade_rows.append(f"| {trade.time} | {trade.code} | {trade.name} | "
                         f"{trade.direction} | {trade.price} | {trade.quantity} | "
                         f"{trade.position_ratio} | {trade.mode} | {trade.description} | {trade.trade_id} |")

    trade_table = "\n".join(trade_rows) if trade_rows else "| | | | | | | | | | |"

    pre_plan_section = pre_plan or {}
    market_stage_str = market_stage or pre_plan_section.get('market_stage', '')
    personal_state_str = personal_state or pre_plan_section.get('personal_state', '')

    markdown = f"""---
title: 'Trade Record'
date: {date_str}
permalink: /blogs/trade-record
tags:
  - stock
---

# Trading Record
### {date_str} | 市场阶段：{market_stage_str} | 个人状态：{personal_state_str}

#### 一、盘前计划
- **大盘预判**：{pre_plan_section.get('market_prediction', '。')}
- **关注方向**：{pre_plan_section.get('focus_areas', '。')}
- **今日策略**：{pre_plan_section.get('strategy', '。')}
- **风险警示**：{pre_plan_section.get('risk_warning', '。')}

#### 二、市场数据（盘后更新）

| 指标 | 数值 | 解读 |
| :--- | :--- | :--- |
| 上证指数 | {market_data.shanghai_index} ({market_data.shanghai_change:+.2f}%) | {market_data.interpretation} |
| 活跃市值 | {market_data.active_market_value_change:+.2f}% | {'多头' if market_data.active_market_value_change > 0 else '空头'} |
| 涨停家数 | {market_data.limit_up_count} | |
| 跌停家数 | {market_data.limit_down_count} | |
| 主线板块 | {market_data.main_sectors} | |

#### 三、交易记录

| 时间 | 代码 | 名称 | 方向 | 价格 | 数量 | 仓位 | 模式 | 买卖点描述（关键！） | 交易ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
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

    return markdown

class TradeReviewGenerator:
    def __init__(self, config: Optional[TradingToolsConfig] = None):
        self.config = config or TradingToolsConfig()

    def load_existing_review(self, file_path: str) -> str:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def generate_daily_review(
        self,
        date_str: str,
        market_data: MarketData,
        trades: List[TradeRecord],
        pre_plan: Dict = None
    ) -> str:
        return generate_review_markdown(date_str, market_data, trades, pre_plan=pre_plan)

    def save_review(self, content: str, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Review saved to: {output_path}")