"""
网络API数据获取模块
支持获取：
- 指南针平台活跃市值数据
- 其他市场数据API
"""
import os
import json
import requests
from typing import Optional, Dict, List
from datetime import datetime, date
from abc import ABC, abstractmethod

class BaseDataProvider(ABC):
    """数据提供器基类"""

    @abstractmethod
    def fetch(self, **kwargs) -> Dict:
        pass

    def _request(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        通用HTTP请求方法
        """
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        if headers:
            default_headers.update(headers)

        try:
            response = requests.get(url, params=params, headers=default_headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}

class CompassDataProvider(BaseDataProvider):
    """
    指南针平台数据获取
    用于获取活跃市值等关键指标
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        self.api_key = api_key or os.getenv("COMPASS_API_KEY", "")
        self.config = config or {}
        self.base_url = self.config.get("api_url", "https://api.compass.com/v1")

    def fetch(self, data_type: str = "market_summary", date: Optional[str] = None) -> Dict:
        """
        获取指南针数据

        Args:
            data_type: 数据类型 (market_summary, active_value, sector_flow, etc.)
            date: 日期 (YYYY-MM-DD格式)

        Returns:
            市场汇总数据
        """
        if data_type == "market_summary":
            return self._fetch_market_summary(date)
        elif data_type == "active_value":
            return self._fetch_active_market_value(date)
        elif data_type == "sector_flow":
            return self._fetch_sector_money_flow(date)
        else:
            return {"error": f"Unknown data type: {data_type}"}

    def _fetch_market_summary(self, date: Optional[str] = None) -> Dict:
        """
        获取市场汇总数据
        包括：上证指数、活跃市值、涨跌停家数等
        """
        date_str = date or datetime.now().strftime('%Y-%m-%d')

        if not self.api_key:
            return self._mock_market_summary(date_str)

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        url = f"{self.base_url}/market/summary"
        params = {'date': date_str}

        result = self._request(url, params=params, headers=headers)

        if "error" in result:
            return self._mock_market_summary(date_str)

        return result

    def _fetch_active_market_value(self, date: Optional[str] = None) -> Dict:
        """
        获取活跃市值数据
        """
        date_str = date or datetime.now().strftime('%Y-%m-%d')

        if not self.api_key:
            return self._mock_active_value(date_str)

        headers = {'Authorization': f'Bearer {self.api_key}'}
        url = f"{self.base_url}/market/active-value"

        result = self._request(url, params={'date': date_str}, headers=headers)

        if "error" in result:
            return self._mock_active_value(date_str)

        return result

    def _fetch_sector_money_flow(self, date: Optional[str] = None) -> Dict:
        """
        获取板块资金流向
        """
        date_str = date or datetime.now().strftime('%Y-%m-%d')

        if not self.api_key:
            return self._mock_sector_flow(date_str)

        headers = {'Authorization': f'Bearer {self.api_key}'}
        url = f"{self.base_url}/market/sector-flow"

        return self._request(url, params={'date': date_str}, headers=headers)

    def _mock_market_summary(self, date_str: str) -> Dict:
        """
        生成模拟数据（用于测试或API不可用时）
        """
        return {
            "status": "success",
            "date": date_str,
            "data": {
                "shanghai_index": 4200.00,
                "shanghai_change_pct": 0.5,
                "volume": 350000000000,
                "active_market_value_change": 1.5,
                "limit_up_count": 100,
                "limit_down_count": 20,
                "main_sectors": ["半导体", "AI产业链"],
                "market_stage": "上升趋势",
            }
        }

    def _mock_active_value(self, date_str: str) -> Dict:
        """
        生成模拟活跃市值数据
        """
        return {
            "status": "success",
            "date": date_str,
            "active_value": 5200000000000,
            "change_pct": 1.5,
            "change_amount": 78000000000,
            "interpretation": "多头区间",
        }

    def _mock_sector_flow(self, date_str: str) -> Dict:
        """
        生成模拟板块资金流向
        """
        return {
            "status": "success",
            "date": date_str,
            "sectors": [
                {"name": "半导体", "flow": 15000000000, "change_pct": 3.5},
                {"name": "AI算力", "flow": 12000000000, "change_pct": 2.8},
                {"name": "通信设备", "flow": 8000000000, "change_pct": 2.1},
            ]
        }

class EastMoneyProvider(BaseDataProvider):
    """
    东方财富数据获取
    提供免费的市场数据API
    """

    BASE_URL = "https://push2.eastmoney.com/api/qt"

    def fetch(self, data_type: str = "market", **kwargs) -> Dict:
        if data_type == "market":
            return self.get_market_overview()
        elif data_type == "stock":
            code = kwargs.get('code', '')
            return self.get_stock_quote(code)
        elif data_type == "sectors":
            return self.get_sector_ranking()
        return {}

    def get_market_overview(self) -> Dict:
        """
        获取大盘整体情况
        """
        url = f"{self.BASE_URL}/ulist.np/get"
        params = {
            'fltt': 2,
            'invt': 2,
            'ut': 'b2884a393a59ad64002217a3e1738891',
            'fields': 'f1,f2,f3,f4,f12,f13,f14,f15,f16,f17,f18,f20,f21',
            'secids': '1.000001,0.399001,0.399006,1.999999',  # 上证、深证、创业板、科创50
        }

        result = self._request(url, params=params)

        if "error" in result:
            return self._mock_market_overview()

        return result

    def get_stock_quote(self, code: str) -> Dict:
        """
        获取个股行情
        """
        if code.startswith('6'):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        url = f"{self.BASE_URL}/stock.quot/get"
        params = {
            'fltt': 2,
            'invt': 2,
            'ut': 'b2884a393a59ad64002217a3e1738891',
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f107,f169,f170',
            'secid': secid,
        }

        return self._request(url, params=params)

    def get_sector_ranking(self) -> Dict:
        """
        获取板块排名
        """
        url = f"{self.BASE_URL}/clist/get"
        params = {
            'fltt': 2,
            'invt': 2,
            'ut': 'b2884a393a59ad64002217a3e1738891',
            'fields': 'f12,f14,f3,f4,f5,f6,f7,f8,f9,f10',
            'pn': 1,
            'pz': 20,
            'po': 1,
            'np': 1,
            'fid': 'f3',
            'fs': 'm:90+t:2+f:!50',  # 行业板块
        }

        return self._request(url, params=params)

    def _mock_market_overview(self) -> Dict:
        """模拟市场概览数据"""
        return {
            "status": "success",
            "data": {
                "1.000001": {
                    "name": "上证指数",
                    "price": 4200.00,
                    "change_pct": 0.8,
                },
                "0.399001": {
                    "name": "深证成指",
                    "price": 12800.00,
                    "change_pct": 1.0,
                }
            }
        }

class SinaFinanceProvider(BaseDataProvider):
    """
    新浪财经数据获取
    """

    BASE_URL = "https://hq.sinajs.cn/list="

    def fetch(self, data_type: str = "realtime", **kwargs) -> Dict:
        if data_type == "realtime":
            codes = kwargs.get('codes', [])
            return self.get_realtime_quotes(codes)
        return {}

    def get_index_data(self, index_codes: List[str]) -> Dict:
        """
        获取指数行情（使用完整市场代码，如 sh000001/sz399001）
        """
        if not index_codes:
            return {"error": "No index codes provided"}

        url = self.BASE_URL + ','.join(index_codes)
        headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0',
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'
            quotes = self._parse_sina_response(response.text)
            return {"status": "success", "data": quotes}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_realtime_quotes(self, codes: List[str]) -> Dict:
        """
        获取实时行情（批量）
        """
        if not codes:
            return {"error": "No codes provided"}

        query_codes = ','.join([f"sh{code}" if code.startswith('6') else f"sz{code}" for code in codes])
        url = self.BASE_URL + query_codes

        headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0',
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'

            quotes = self._parse_sina_response(response.text)
            return {"status": "success", "data": quotes}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _parse_sina_response(self, text: str) -> List[Dict]:
        """解析新浪财经响应"""
        quotes = []

        for line in text.split('\n'):
            if not line.strip():
                continue

            match = line.find('="')
            if match == -1:
                continue

            code_part = line[:match].split('_')[-1]
            data_part = line[match+1:].rstrip('";')

            if not data_part:
                continue

            parts = data_part.split(',')

            if len(parts) >= 32:
                try:
                    quote = {
                        "code": code_part,
                        "name": parts[0],
                        "open": float(parts[1]),
                        "prev_close": float(parts[2]),
                        "close": float(parts[3]),
                        "high": float(parts[4]),
                        "low": float(parts[5]),
                        "volume": float(parts[8]),
                        "amount": float(parts[9]),
                        "date": parts[30],
                        "time": parts[31] if len(parts) > 31 else "",
                    }
                    quotes.append(quote)
                except (ValueError, IndexError):
                    continue

        return quotes

class MarketDataAggregator:
    """
    市场数据聚合器
    整合多个数据源获取完整的市场信息
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.compass = CompassDataProvider(config=self.config.get('compass', {}))
        self.eastmoney = EastMoneyProvider()
        self.sina = SinaFinanceProvider()

    def _is_eastmoney_real_data(self, eastmoney_data: Dict) -> bool:
        """检测东方财富是否返回真实数据（vs 模拟/错误数据）"""
        try:
            diff = eastmoney_data.get("data", {}).get("diff", None)
            return diff is not None and len(diff) > 0
        except (TypeError, AttributeError):
            return False

    def _eastmoney_extract_index(self, eastmoney_data: Dict) -> Optional[float]:
        """从东方财富响应中提取上证指数"""
        try:
            diff = eastmoney_data.get("data", {}).get("diff", [])
            for item in diff:
                code = item.get("f12", "")
                if code == "000001":
                    return item.get("f2")
        except (TypeError, AttributeError):
            pass
        return None

    def _sina_extract_index(self, sina_data: Dict) -> Optional[Dict]:
        """从新浪财经响应中提取指数数据"""
        try:
            quotes = sina_data.get("data", [])
            for q in quotes:
                if q.get("code") == "sh000001":
                    close = q.get("close", 0)
                    prev_close = q.get("prev_close", 0)
                    change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0
                    return {
                        "shanghai_index": close,
                        "shanghai_change_pct": round(change_pct, 2),
                    }
        except (TypeError, AttributeError):
            pass
        return None

    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        date_str = date or datetime.now().strftime('%Y-%m-%d')

        eastmoney_data = self.eastmoney.get_market_overview()
        compass_data = self.compass.fetch("market_summary", date=date_str)

        summary = {
            "date": date_str,
            "shanghai_index": 0,
            "shanghai_change_pct": 0,
            "volume": 0,
            "active_market_value_change": 0,
            "limit_up_count": 0,
            "limit_down_count": 0,
            "main_sectors": [],
            "market_stage": "未知",
        }

        sh_index = None

        # Tier 1: 东方财富实时数据（最优，含历史数据）
        if self._is_eastmoney_real_data(eastmoney_data):
            sh_index = self._eastmoney_extract_index(eastmoney_data)

        # Tier 2: 新浪财经实时数据（仅当日数据有效）
        if sh_index is None:
            sina_data = self.sina.get_index_data(['sh000001'])
            sina_index = self._sina_extract_index(sina_data)
            if sina_index is not None:
                # 校验新浪返回的日期是否匹配请求的日期
                quotes = sina_data.get("data", [])
                sina_date_match = any(
                    q.get("code") == "sh000001" and q.get("date") == date_str
                    for q in quotes
                )
                if sina_date_match:
                    sh_index = sina_index["shanghai_index"]
                    summary["shanghai_change_pct"] = sina_index["shanghai_change_pct"]

        # Tier 3: 指南针/模拟数据（兜底）
        if "data" in compass_data:
            data = compass_data["data"]
            if sh_index is not None:
                summary["shanghai_index"] = sh_index
            else:
                summary["shanghai_index"] = data.get("shanghai_index", 0)
            if summary["shanghai_change_pct"] == 0:
                summary["shanghai_change_pct"] = data.get("shanghai_change_pct", 0)
            summary.update({
                "shanghai_change_pct": data.get("shanghai_change_pct", 0),
                "volume": data.get("volume", 0),
                "active_market_value_change": data.get("active_market_value_change", 0),
                "limit_up_count": data.get("limit_up_count", 0),
                "limit_down_count": data.get("limit_down_count", 0),
                "main_sectors": data.get("main_sectors", []),
                "market_stage": data.get("market_stage", "未知"),
            })

        return summary

    def get_sector_analysis(self) -> Dict:
        """
        获取板块分析数据
        """
        eastmoney_data = self.eastmoney.get_sector_ranking()

        if "data" in eastmoney_data and "diff" in eastmoney_data["data"]:
            sectors = eastmoney_data["data"]["diff"]
            sorted_sectors = sorted(sectors, key=lambda x: x.get('f3', 0), reverse=True)

            return {
                "status": "success",
                "sectors": sorted_sectors[:10],  # 返回涨幅前10
                "timestamp": datetime.now().isoformat(),
            }

        return {"status": "failed", "error": "No sector data available"}

def get_market_stage(change_pct: float) -> str:
    """
    根据涨跌判断市场阶段
    """
    if change_pct > 2:
        return "创新高，高潮"
    elif change_pct > 1:
        return "上升趋势，人声鼎沸"
    elif change_pct > 0:
        return "温和上涨"
    elif change_pct > -1:
        return "震荡市"
    elif change_pct > -2:
        return "回调"
    else:
        return "下跌趋势"