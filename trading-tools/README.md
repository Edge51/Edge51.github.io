# 交易复盘工具 (Trading Tools)

基于OpenClaw框架的交易复盘自动化工具，集成通达信本地数据和网络API，自动生成复盘报告。

## 功能特性

- **市场数据获取**: 集成通达信、东方财富、新浪财经等多个数据源
- **指南针活跃市值**: 获取指南针平台的活跃市值数据
- **交易记录解析**: 自动解析Markdown表格格式的交易记录
- **复盘报告生成**: 自动生成结构化的复盘报告

## 目录结构

```
trading-tools/
├── config/              # 配置文件
│   ├── skill.json       # OpenClaw skill配置
│   └── tools.json       # 数据源配置
├── src/                 # 核心模块
│   ├── core.py          # 核心类和工具函数
│   ├── tdx_reader.py    # 通达信数据读取
│   ├── network_api.py   # 网络API数据获取
│   └── trade_parser.py  # 交易记录解析
├── skills/              # OpenClaw skills (待扩展)
├── data/                # 本地数据存储
├── main.py              # CLI入口
└── requirements.txt     # Python依赖
```

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 获取市场数据

```bash
python main.py fetch-market --date 2026-05-12
```

### 获取个股数据

```bash
python main.py fetch-stock 600312 --market sh --type day
```

### 解析交易记录

```bash
cat trades.txt | python main.py parse-trades
```

### 完整复盘流程（交互式）

```bash
python main.py full-review --date 2026-05-12
```

### 生成复盘报告

```bash
python main.py generate-review --date 2026-05-12 \
    --market-data data.json --trades-file trades.txt
```

## 配置

编辑 `config/tools.json` 配置数据源:

```json
{
  "data_sources": {
    "tdx": {
      "enabled": true,
      "data_path": "C:/TdxW/data"
    },
    "compass": {
      "enabled": true,
      "api_key_env": "COMPASS_API_KEY"
    }
  }
}
```

## 与OpenClaw集成

1. 将 `config/skill.json` 的内容添加到OpenClaw的skills配置中
2. 在OpenClaw中使用自然语言控制交易复盘流程
3. 示例: "帮我生成2026-05-12的复盘报告"