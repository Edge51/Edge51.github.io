"""
通达信数据读取模块
支持读取通达信本地数据文件(.dat)和Level2数据
"""
import os
import struct
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd

class TdxDataReader:
    """
    通达信数据读取器
    支持读取:
    - 日线/分时数据 (.day, .lc, .lc1)
    - 分时成交数据
    - Level2逐笔数据
    """

    BLOCK_HEADER_SIZE = 52
    RECORD_SIZE = 32

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self._detect_tdx_path()

    def _locate_file(self, code: str, market: str = "sh") -> Optional[str]:
        """在多个可能的目录结构中查找通达信数据文件。"""
        filename = f"{market}{code}.day"
        search_paths = [
            # 1. 平铺结构: {data_path}/sh000001.day
            os.path.join(self.data_path, filename),
            # 2. {data_path}/lday/sh000001.day
            os.path.join(self.data_path, "lday", filename),
            # 3. vipdoc结构: {data_path}/vipdoc/sh/lday/sh000001.day
            os.path.join(self.data_path, "vipdoc", market, "lday", filename),
            # 4. {data_path}/../{market}{code}.day (data_path可能是sh/lday)
            os.path.join(os.path.dirname(self.data_path), filename),
            # 5. {data_path}/../{market}/lday/{filename} (data_path可能是vipdoc)
            os.path.join(self.data_path, market, "lday", filename),
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path
        return None

    def _detect_tdx_path(self) -> str:
        # Linux TDX (tdx-bin from AUR, Wine bottle)
        xdg_data = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        linux_root = os.path.join(xdg_data, 'tdxcfv/drive_c/tc')
        if os.path.exists(os.path.join(linux_root, 'vipdoc/sh/lday/sh000001.day')):
            return linux_root

        # Windows TDX paths  
        possible_paths = [
            "C:/TdxW/data",
            "C:/通达信/data",
            "D:/TdxW/data",
            "D:/通达信/data",
            os.path.expanduser("~/TdxW/data"),
        ]

        for path in possible_paths:
            sh_path = os.path.join(path, 'sh000001.day')
            if os.path.exists(sh_path):
                return path

        # hikyuu test data
        hikyuu_root = os.path.expanduser('~/Projects/hikyuu')
        if os.path.exists(os.path.join(hikyuu_root, 'test_data/vipdoc/sh/lday/sh000001.day')):
            return os.path.join(hikyuu_root, 'test_data')

        return linux_root

    @staticmethod
    def _detect_header_size(file_path: str) -> int:
        """检测 .day 文件是否有文件头。Linux版无头，Windows版有52字节头。"""
        with open(file_path, 'rb') as f:
            first_four = f.read(4)
        if len(first_four) < 4:
            return 0
        val = struct.unpack('<I', first_four)[0]
        # Linux版通达信数据从偏移0开始，第一字段是日期(YYYYMMDD)
        if 19900101 <= val <= 20261231:
            return 0
        return 52

    def read_day_file(self, code: str, market: str = "sh") -> pd.DataFrame:
        file_path = self._locate_file(code, market)

        if not file_path:
            raise FileNotFoundError(f"Data file not found for {market}{code}.day (searched multiple paths under {self.data_path})")

        header_size = self._detect_header_size(file_path)

        with open(file_path, 'rb') as f:
            f.read(header_size)

            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            amounts = []

            while True:
                data = f.read(self.RECORD_SIZE)
                if len(data) < self.RECORD_SIZE:
                    break

                try:
                    date = datetime.strptime(str(struct.unpack('<I', data[0:4])[0]), '%Y%m%d')
                    o = struct.unpack('<I', data[4:8])[0] / 100.0
                    h = struct.unpack('<I', data[8:12])[0] / 100.0
                    l = struct.unpack('<I', data[12:16])[0] / 100.0
                    c = struct.unpack('<I', data[16:20])[0] / 100.0
                    v = struct.unpack('<I', data[20:24])[0]
                    a = struct.unpack('<I', data[24:28])[0]

                    dates.append(date)
                    opens.append(o)
                    highs.append(h)
                    lows.append(l)
                    closes.append(c)
                    volumes.append(v)
                    amounts.append(a)
                except:
                    continue

        df = pd.DataFrame({
            'date': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
            'amount': amounts
        })

        return df

    def read_minute_file(self, code: str, market: str = "sh", minute_type: int = 1) -> pd.DataFrame:
        """
        读取分时数据

        Args:
            code: 股票代码
            market: 市场
            minute_type: 分时类型 (1=1分钟, 5=5分钟, etc.)

        Returns:
            DataFrame with columns: date, time, open, high, low, close, volume
        """
        ext = f".lc{minute_type}" if minute_type > 1 else ".lc1"
        file_path = os.path.join(self.data_path, f"{market}{code}{ext}")

        if not os.path.exists(file_path):
            file_path = os.path.join(self.data_path, f"{code}{ext}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")

        with open(file_path, 'rb') as f:
            header = f.read(32)
            info = struct.unpack('<12sIHiII', header)

            dates = []
            times = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []

            while True:
                data = f.read(32)
                if len(data) < 32:
                    break

                try:
                    date_val = struct.unpack('<H', data[0:2])[0]
                    time_val = struct.unpack('<H', data[2:4])[0]

                    year = (date_val // 2048) + 2004
                    month = (date_val % 2048) // 100
                    day = date_val % 100

                    hour = time_val // 60
                    minute = time_val % 60

                    date = datetime(year, month, day, hour, minute)

                    o = struct.unpack('<I', data[4:8])[0] / 100.0
                    h = struct.unpack('<I', data[8:12])[0] / 100.0
                    l = struct.unpack('<I', data[12:16])[0] / 100.0
                    c = struct.unpack('<I', data[16:20])[0] / 100.0
                    v = struct.unpack('<I', data[20:24])[0]

                    dates.append(date.strftime('%Y-%m-%d'))
                    times.append(date.strftime('%H:%M'))
                    opens.append(o)
                    highs.append(h)
                    lows.append(l)
                    closes.append(c)
                    volumes.append(v)
                except:
                    continue

        df = pd.DataFrame({
            'date': dates,
            'time': times,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

        return df

    def get_stock_info(self, code: str, market: str = "sh") -> Dict:
        """
        获取股票基本信息
        """
        file_path = os.path.join(self.data_path, f"{market}{code}.day")

        if not os.path.exists(file_path):
            return {"code": code, "market": market, "found": False}

        df = self.read_day_file(code, market)

        if df.empty:
            return {"code": code, "market": market, "found": False}

        latest = df.iloc[-1]

        return {
            "code": code,
            "market": market,
            "found": True,
            "name": self._get_stock_name(code, market),
            "latest_date": latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], datetime) else str(latest['date']),
            "close": latest['close'],
            "change": ((latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100) if len(df) > 1 else 0,
            "volume": latest['volume'],
            "high_52w": df['high'].tail(250).max(),
            "low_52w": df['low'].tail(250).min(),
        }

    def _get_stock_name(self, code: str, market: str) -> str:
        name_file = os.path.join(self.data_path, "tdsc.list")

        if os.path.exists(name_file):
            try:
                with open(name_file, 'r', encoding='gbk') as f:
                    for line in f:
                        if code in line:
                            parts = line.split(',')
                            if len(parts) > 1:
                                return parts[1].strip()
            except:
                pass

        return code

    def batch_get_stocks(self, codes: List[str], market: str = "sh") -> List[Dict]:
        """
        批量获取股票信息
        """
        results = []
        for code in codes:
            try:
                info = self.get_stock_info(code, market)
                results.append(info)
            except Exception as e:
                results.append({"code": code, "market": market, "found": False, "error": str(e)})
        return results

    def get_market_index(self, index_code: str = "999999", market: str = "sh") -> Dict:
        """
        获取大盘指数数据
        """
        try:
            df = self.read_day_file(index_code, market)

            if df.empty:
                return {}

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            return {
                "index_code": index_code,
                "date": latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], datetime) else str(latest['date']),
                "close": latest['close'],
                "open": latest['open'],
                "high": latest['high'],
                "low": latest['low'],
                "change_pct": ((latest['close'] - prev['close']) / prev['close'] * 100),
                "volume": latest['volume'],
                "amount": latest['amount'],
            }
        except Exception as e:
            return {"error": str(e)}

class TdxConnector:
    """
    通达信API连接器 (需要通达信开放接口支持)
    用于获取实时数据和Level2数据
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7709):
        self.host = host
        self.port = port
        self.connected = False

    def connect(self) -> bool:
        """
        连接通达信
        需要通达信客户端开启数据服务
        """
        try:
            import socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to TDX: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connected and hasattr(self, 'sock'):
            self.sock.close()
            self.connected = False

    def get_realtime_quote(self, code: str, market: str = "0") -> Optional[Dict]:
        """
        获取实时行情
        """
        if not self.connected:
            return None

        try:
            cmd = f"0101{market}{code}   ".encode('gbk')[:16]
            self.sock.send(cmd)

            data = self.sock.recv(1024)
            return self._parse_realtime_data(data)
        except Exception as e:
            print(f"Failed to get quote: {e}")
            return None

    def _parse_realtime_data(self, data: bytes) -> Dict:
        return {}

def get_market_status(active_market_value_change: float) -> str:
    """
    根据活跃市值变化判断市场状态
    """
    if active_market_value_change > 5:
        return "创新高，高潮"
    elif active_market_value_change > 2:
        return "上升趋势，人声鼎沸"
    elif active_market_value_change > 0:
        return "多头区间"
    elif active_market_value_change > -2:
        return "震荡市"
    else:
        return "空头区间"