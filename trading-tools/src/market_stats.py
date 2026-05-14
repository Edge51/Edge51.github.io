"""
通达信市场统计模块
从本地 TDX 数据计算：
- 涨停/跌停家数
- 主线板块排行
"""
import os
import json
import struct
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from .tdx_reader import TdxDataReader

def _get_limit_pct(code: str) -> float:
    """根据股票代码返回涨跌幅限制比例。"""
    if code.startswith('688') or code.startswith('689'):
        return 0.20
    if code.startswith('300') or code.startswith('301'):
        return 0.20
    if code.startswith('8'):
        return 0.30
    if code.startswith('4'):
        return 0.30
    return 0.10

def _is_a_share_stock(code: str, market: str) -> bool:
    """判断是否为A股股票（排除指数、债券、ETF、基金、权证等）。"""
    if market == 'sh':
        return any(code.startswith(p) for p in ['600','601','602','603','604','605','688','689'])
    elif market == 'sz':
        return any(code.startswith(p) for p in ['000','001','002','003','300','301'])
    elif market == 'bj':
        return code.startswith('920') and code != '899050'
    return False


CACHE_DIR = os.path.join(os.path.dirname(__file__), '../data/cache')


class MarketStatsCalculator:
    """从TDX本地数据计算市场统计指标。"""

    def __init__(self, reader: Optional[TdxDataReader] = None):
        self.reader = reader or TdxDataReader()
        self._cache = {}
        self._st_codes = self._load_st_codes()

    def _load_st_codes(self) -> set:
        """从TDX名称数据库加载ST股票代码集合。"""
        base = self.reader.data_path
        paths = [
            os.path.join(base, 'T0002', 'hq_cache', 'infoharbor_ex.code'),
            os.path.join(base, 'hq_cache', 'infoharbor_ex.code'),
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    text = f.read().decode('gbk', errors='replace')
                st_codes = set()
                for line in text.split('\n'):
                    parts = line.split('|')
                    if len(parts) >= 2 and ('ST' in parts[1].upper()):
                        st_codes.add(parts[0].strip())
                return st_codes
        return set()

    # ── 涨停/跌停家数 ──────────────────────────────────────

    def _stock_dirs(self) -> List[Tuple[str, str]]:
        """返回 (market_prefix, day_dir) 列表。"""
        base = self.reader.data_path
        candidates = [
            ('sh', os.path.join(base, 'vipdoc', 'sh', 'lday')),
            ('sz', os.path.join(base, 'vipdoc', 'sz', 'lday')),
            ('bj', os.path.join(base, 'vipdoc', 'bj', 'lday')),
            ('sh', os.path.join(base, 'sh', 'lday')),
            ('sz', os.path.join(base, 'sz', 'lday')),
            ('sh', base),
        ]
        seen = set()
        dirs = []
        for market, d in candidates:
            if os.path.isdir(d) and d not in seen:
                seen.add(d)
                dirs.append((market, d))
        return dirs

    def compute_limit_stats(self, target_date: Optional[str] = None) -> Dict:
        """
        扫描所有A股 .day 文件，计算涨停/跌停家数 + 涨:平:跌。
        """
        target_date = target_date or datetime.now().strftime('%Y-%m-%d')
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        target_num = int(target_dt.strftime('%Y%m%d'))

        cache_file = os.path.join(CACHE_DIR, f'limit_{target_date.replace("-","")}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                if cached.get('date') == target_date:
                    return cached

        limit_up = 0
        limit_down = 0
        up_count = 0
        flat_count = 0
        down_count = 0
        total_stocks = 0

        for market, day_dir in self._stock_dirs():
            if not os.path.isdir(day_dir):
                continue
            for fname in os.listdir(day_dir):
                if not fname.endswith('.day') or len(fname) < 7:
                    continue
                code_part = fname.replace('.day', '')
                code = code_part[len(market):] if code_part.startswith(market) else code_part

                if not _is_a_share_stock(code, market):
                    continue

                fpath = os.path.join(day_dir, fname)
                try:
                    last_two = self.reader.read_last_records(code, market, n=2)
                except Exception:
                    continue
                if last_two.empty or len(last_two) < 2:
                    continue

                today = last_two.iloc[-1]
                yesterday = last_two.iloc[-2]

                t_date = today['date']
                if isinstance(t_date, datetime):
                    t_num = int(t_date.strftime('%Y%m%d'))
                else:
                    continue
                if t_num != target_num:
                    continue

                prev_close = yesterday['close']
                if prev_close <= 0:
                    continue

                total_stocks += 1

                limit_pct = 0.05 if code in self._st_codes else _get_limit_pct(code)
                limit_up_price = round(prev_close * (1 + limit_pct), 2)
                limit_down_price = round(prev_close * (1 - limit_pct), 2)

                if today['close'] >= limit_up_price:
                    limit_up += 1
                if today['close'] <= limit_down_price:
                    limit_down += 1

                if today['close'] > prev_close:
                    up_count += 1
                elif today['close'] < prev_close:
                    down_count += 1
                else:
                    flat_count += 1

        result = {
            "date": target_date,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "up_count": up_count,
            "flat_count": flat_count,
            "down_count": down_count,
            "total_stocks": total_stocks,
        }

        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    # ── 主线板块 ──────────────────────────────────────────

    def _read_tdxzs_cfg(self) -> Dict[str, str]:
        """解析 tdxzs.cfg → {code: name}，返回行业板块 (type=2,level=1)。"""
        cfg_path = self._locate_hqcache_file('tdxzs.cfg')

        with open(cfg_path, 'rb') as f:
            text = f.read().decode('gbk', errors='replace')

        sectors = {}
        for line in text.strip().split('\n'):
            line = line.strip().strip('\r')
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 4 and parts[2] == '2' and parts[3] == '1':
                sectors[parts[1]] = parts[0]
        return sectors

    def _read_tdxzsbase_cfg(self, target_num: int) -> Dict[str, float]:
        """解析 tdxzsbase.cfg → {code: change_pct}，筛选目标日期。"""
        cfg_path = self._locate_hqcache_file('tdxzsbase.cfg')
        if not cfg_path:
            return {}

        best_date = target_num
        best_changes = {}

        with open(cfg_path, 'r', encoding='gbk', errors='replace') as f:
            all_data = defaultdict(dict)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) < 10:
                    continue
                try:
                    code = parts[1]
                    line_date = int(parts[7])
                    change_pct = float(parts[9])
                    all_data[line_date][code] = change_pct
                except (ValueError, IndexError):
                    continue

        if target_num in all_data:
            return all_data[target_num]

        available = sorted(all_data.keys())
        if not available:
            return {}
        from datetime import datetime
        target_dt = datetime.strptime(str(target_num), '%Y%m%d')
        for d in reversed(available):
            d_dt = datetime.strptime(str(d), '%Y%m%d')
            if d_dt <= target_dt:
                best_changes = all_data[d]
                break
        if not best_changes and available:
            best_changes = all_data[available[-1]]
        return best_changes

    def _locate_hqcache_file(self, filename: str) -> Optional[str]:
        """在多个可能路径中查找 hq_cache 下的文件。"""
        base = self.reader.data_path
        candidates = [
            os.path.join(base, 'T0002', 'hq_cache', filename),
            os.path.join(base, 'hq_cache', filename),
            os.path.join(os.path.dirname(base), 'T0002', 'hq_cache', filename),
            os.path.join(os.path.dirname(os.path.dirname(base)), 'T0002', 'hq_cache', filename),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def compute_top_sectors(self, target_date: Optional[str] = None, top_n: int = 5) -> Dict:
        """
        计算涨幅前 N 的行业板块。
        Returns:
            {"date": "YYYY-MM-DD", "sectors": [{"name": ..., "change_pct": ...}, ...]}
        """
        target_date = target_date or datetime.now().strftime('%Y-%m-%d')
        target_num = int(target_date.replace('-', ''))

        sector_names = self._read_tdxzs_cfg()
        sector_changes = self._read_tdxzsbase_cfg(target_num)

        ranked = []
        for code, name in sector_names.items():
            if code in sector_changes and name:
                ranked.append((name, sector_changes[code]))

        ranked.sort(key=lambda x: x[1], reverse=True)

        return {
            "date": target_date,
            "sectors": [
                {"name": name, "change_pct": round(pct, 2)}
                for name, pct in ranked[:top_n]
            ],
            "all_sorted": [
                {"name": name, "change_pct": round(pct, 2)}
                for name, pct in ranked
            ]
        }


def get_limit_stats(reader: Optional[TdxDataReader] = None, target_date: Optional[str] = None) -> Dict:
    """便捷接口：获取涨跌停家数。"""
    return MarketStatsCalculator(reader).compute_limit_stats(target_date)


def get_top_sectors(reader: Optional[TdxDataReader] = None, target_date: Optional[str] = None, top_n: int = 5) -> Dict:
    """便捷接口：获取主线板块排行。"""
    return MarketStatsCalculator(reader).compute_top_sectors(target_date, top_n)