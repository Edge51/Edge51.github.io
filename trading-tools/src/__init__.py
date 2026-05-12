# -*- coding: utf-8 -*-
"""
交易复盘工具
Trading Review Tools for OpenClaw
"""

__version__ = "1.0.0"
__author__ = "Edge51"

from .core import (
    TradeRecord,
    MarketData,
    TradingToolsConfig,
    TradeReviewGenerator,
    parse_trade_table,
    parse_market_data_table,
)

from .tdx_reader import TdxDataReader, TdxConnector, get_market_status

from .network_api import (
    CompassDataProvider,
    EastMoneyProvider,
    SinaFinanceProvider,
    MarketDataAggregator,
    get_market_stage,
)

from .trade_parser import (
    TradeRecordParser,
    ReviewGenerator,
    TradeAnalyzer,
    ReviewTemplateManager,
)