---
title: 'vLLM Function Call 全链路深度解析'
date: 2026-07-15
permalink: /blogs/vllm-function-call
tags:
  - vllm
  - llm
  - function-call
  - tool-use
---

> vLLM v0.20.2，聚焦 function call 的主链路分析。
> 版本与模型：Qwen3CoderToolParser（XML 格式工具调用）

## 目录

1. [入口链路](#1-入口链路)
2. [Jinja 渲染链](#2-jinja-渲染链)
3. [adjust_request——请求参数调整](#3-adjust_request请求参数调整)
4. [engine_client.generate——发往引擎](#4-engine_clientgenerate发往引擎)
5. [Streaming vs 非流式输出处理](#5-streaming-vs-非流式输出处理)
6. [tool_parser 实现](#6-tool_parser-实现)
7. [JSON Schema 构建（guided decoding）](#7-json-schema-构建guided-decoding)
8. [投机解码对 tool parser 的影响](#8-投机解码对-tool-parser-的影响)
9. [影响 function call 的特性清单](#9-影响-function-call-的特性清单)

---

## 1. 入口链路

```
vllm serve <model>
  └→ cli/main.py:main() → cli/serve.py:ServeSubcommand.cmd()
      └→ api_server.py:run_server() → setup_server()
          └→ 初始化 EngineClient (AsyncLLM)
          └→ 初始化 OpenAIServingRender
          └→ 初始化 OpenAIServingChat
          └→ 注册路由 /v1/chat/completions
```

```
create_chat_completion()                      # chat_completion/serving.py:229
  ├→ render_chat_request(request)             # line 251
  │   └→ render_chat(request)                 # line 184
  │       └→ preprocess_chat()                # line 523
  │           ├→ renderer.render_chat_async() # HfRenderer
  │           ├→ reasoning_parser.adjust_request()
  │           └→ tool_parser.adjust_request()
  │
  ├→ engine_client.generate(engine_input, ...)# line 341 → AsyncLLM
  │
  ├─ [stream=True]
  │   └→ chat_completion_stream_generator()   # line 363
  │
  └─ [stream=False]
      └→ chat_completion_full_generator()     # line 375
```

---

## 2. Jinja 渲染链

### 调用链

```
render_chat()
  └→ preprocess_chat()
      └→ renderer.render_chat_async()
          └→ render_messages_async()
              └→ safe_apply_chat_template()
                  ├→ resolve_chat_template()       # 4 优先级找模板字符串
                  ├→ resolve_chat_template_kwargs() # 解析 jinja 模板变量
                  └→ tokenizer.apply_chat_template() # HuggingFace → 实际 jinja 渲染
```

### 模板字符串的加载

```python
resolved_chat_template = load_chat_template(args.chat_template)
# → cached_lru_cache(_load_chat_template)
# → 读文件 / 内置模板 / 字面量
```

`load_chat_template` 只返回纯字符串。真正编译和执行 jinja 模板发生在 HuggingFace 的 `apply_chat_template` 里。

### 不走 jinja 的模型

| 模型族 | 渲染方式 | 原因 |
|---|---|---|
| Qwen/LLaMA/GLM 等 | `apply_chat_template()` → jinja | 标准 HuggingFace 路径 |
| DeepSeek V4 | `encode_messages()` 自定义编码 | 自研 tokenizer |
| GPT-OSS | `_make_request_with_harmony()` | Harmony 格式，不走 jinja |
| Mistral | `MistralRenderer` | 使用 `mistral_common` 自研编码 |

---

## 3. adjust_request——请求参数调整

**作用：在 prompt 渲染之前修改请求参数，不是后处理。**

### tool_parser.adjust_request()

```python
def adjust_request(self, request):
    json_schema = get_json_schema_from_tools(tool_choice, tools)
    if json_schema is not None:
        request.structured_outputs = StructuredOutputsParams(json=json_schema)
    return request
```

当 `tool_choice="required"` 或指定了函数名称时，构建 JSON Schema 约束模型输出。

各模型子类在此基础上加定制：

| 模型 | 定制 |
|---|---|
| Hermes | `request.skip_special_tokens = False` |
| GLM-4-MoE | required/named 时不调 super()（GLM 输出 XML 不是 JSON） |
| DeepSeek V3.2 | `request.skip_special_tokens = False` |

### 调用顺序

```python
# preprocess_chat() 里
request = reasoning_parser.adjust_request(request)   # 先改 reasoning 参数
request = tool_parser.adjust_request(request)         # 再加工具约束
```

---

## 4. engine_client.generate——发往引擎

`engine_client` 的实际类型是 `AsyncLLM`（`v1/engine/async_llm.py`）。

```python
async def generate(self, prompt, sampling_params, request_id, ...):
    q = await self.add_request(request_id, prompt, params, ...)
    # output_handler 后台 task 从 EngineCore 拉结果塞进队列
    while not finished:
        out = q.get_nowait() or await q.get()
        finished = out.finished
        yield out
```

### add_request 内部

```python
async def add_request(self, ...):
    # 1. input_processor.process_inputs(prompt) → EngineCoreRequest
    request = self.input_processor.process_inputs(request_id, prompt, params, ...)
    # 2. output_processor.add_request(request)  → 登记 output 处理
    self.output_processor.add_request(request, ...)
    # 3. engine_core.add_request_async(request) → 发送到 EngineCore 进程
    await self.engine_core.add_request_async(request)
```

### 进程架构

```
AsyncLLM (API server 进程)
  ├─ engine_core = EngineCoreClient (IPC 代理) → EngineCoreProc (独立进程)
  │                                                    ├─ Scheduler
  │                                                    └─ Model Runner
  └─ output_processor (独立进程内)
       └─ 后台 output_handler loop
            ├─ engine_core.get_outputs_async()
            └─ output_processor.process_outputs() → queue
```

---

## 5. Streaming vs 非流式输出处理

### 非流式

```python
async for res in result_generator:
    # 等待完整输出

# 收集完整文本后
tool_call_info = tool_parser.extract_tool_calls(model_output, request)
# 一行提取，不需要状态
```

### 流式

```python
async for res in result_generator:          # 每个 step 迭代一次
    delta_text = output.text                # 本轮新增文本
    current_text = previous_text + delta_text

    # 按模型路径分流
    if is_mistral_grammar_path:
        result = tool_parser.extract_maybe_reasoning_and_tool_streaming(...)
    elif tool_choice_auto:
        result = tool_parser.extract_tool_calls_streaming(
            previous_text, current_text)
```

`delta_text` 是每个 step 的增量文本，在投机解码场景下可能一次包含多个 token。

---

## 6. tool_parser 实现

### 模型输出格式（XML）

```xml
<tool_call>
  <function=get_weather>
    <parameter=location>北京</parameter>
    <parameter=unit>celsius</parameter>
  </function>
</tool_call>
```

### Sentinel tokens

```python
self.tool_call_start_token = "<tool_call>"
self.tool_call_end_token   = "</tool_call>"
self.tool_call_prefix      = "<function="
self.function_end_token    = "</function>"
self.parameter_prefix      = "<parameter="
self.parameter_end_token   = "</parameter>"
```

### 非流式 extract_tool_calls

```python
def extract_tool_calls(self, model_output, request):
    # 1. 快速过滤
    if self.tool_call_prefix not in model_output:
        return ExtractedToolCallInformation(tools_called=False, content=model_output)
    # 2. 正则找 <tool_call>...</tool_call>
    function_calls = self._get_function_calls(model_output)
    # 3. 逐个解析 XML → ToolCall
    tool_calls = [self._parse_xml_function_call(fc, request.tools) for fc in function_calls]
    # 4. 提取 tool_call 前面的内容
    content = model_output[:找到第一个 <tool_call> 的位置]
    return ExtractedToolCallInformation(tools_called=True, tool_calls=tool_calls, content=content)
```

### 流式 extract_tool_calls_streaming——状态机

状态变量：

```python
is_tool_call_started: bool      # 是否已开始 tool call
in_function: bool               # 是否在 <function=...> 内部
in_param: bool                  # 是否在 <parameter=...> 内部
current_tool_index: int         # 当前处理第几个 tool call
header_sent: bool               # 函数名 header 是否已发
param_count: int                # 当前函数已处理完的参数个数
accumulated_params: dict        # 累积的参数名→值
```

每次收到新 token，状态机推进一个状态。这种设计在投机解码场景下容易出现状态不同步的问题（详见第 8 节）。

---

## 7. JSON Schema 构建（guided decoding）

```python
def _get_tool_schema_from_tool(tool):
    name, params = _extract_tool_info(tool)
    return {
        "properties": {
            "name": {"type": "string", "enum": [name]},
            "parameters": params,
        },
        "required": ["name", "parameters"],
    }
```

| `tool_choice` | guided decoding | 原因 |
|---|---|---|
| `"none"` | ❌ | 无工具调用 |
| `"auto"` | ❌ | 模型自由选择 |
| `"required"` | ✅ | 必须输出工具调用，需要 JSON 约束 |
| 指定某函数 | ✅ | 必须输出指定格式 |

---

## 8. 投机解码对 tool parser 的影响

### 根因

投机解码在一个 step 内接受多个 draft token，导致 `delta_text` 一次包含多个 XML 标记：

```
正常解码:
  delta_text: "<" → "f" → "u" → "n" → "c" → ... → ">"
  状态机逐字符推进

投机解码（接受 5 个 draft token）:
  delta_text: "<function=get_weather>"
  状态机直接从 False 跳到 "完整标签"
```

### 为什么还存在问题

状态机依赖多步 `if/else` 链推进。投机场景下一个 `delta_text` 可能跨越多个状态（`is_tool_call_started` → `in_function` → `param_count++`），但代码里仍有依赖单步推进的路径没覆盖到。

### 推荐修复策略：无状态解析 + diff

```python
def extract_tool_calls_streaming(self, previous_text, current_text, delta_text, ...):
    # 阶段 1: 无状态完整解析 current_text
    full_state = self._parse_full_text(current_text)
    # 阶段 2: 对比缓存的上次状态 → 计算 delta
    delta = self._diff_state(self._cached_state, full_state)
    # 阶段 3: 更新缓存
    self._cached_state = full_state
    return self._delta_to_message(delta)
```

`_parse_full_text` 是纯函数，不依赖状态变量，`delta_text` 一次来几个 token 都不影响正确性。

---

## 9. 影响 function call 的特性清单

| 特性 | 影响等级 | 说明 |
|---|---|---|
| **投机解码（Speculative decoding）** | 🔴 高 | `delta_text` 批量化导致状态机不同步，XML 类 parser 尤其脆弱 |
| **Chunked prefill** | 🟡 中 | prefill 阶段 `delta_text=""` 但可能有 token_ids，parser 需正确处理空 delta |
| **并行 tool call（单请求多调用）** | 🔴 高 | 单个请求内连续多个 `<tool_call>`，需管理多个调用的状态边界 |
| **Reasoning + tool 混合** | 🔴 高 | 模型先输出 reasoning 再输出 tool call，两个 parser 共享 delta_message 流 |
| **n > 1（multiple choices）** | 🟡 中 | 每个 choice 独立维护 parser 状态 |
| **Grammar / Guided decoding** | 🔴 高 | grammar 约束输出格式，和 tool parser 解析逻辑必须一致 |
| **EOS token 处理** | 🟡 中 | 模型可能在 tool call 中间输出 EOS，需要截断处理 |
| **Multi-modal（图片/视频/音频）** | 🟡 中 | 多模态 token 穿插在 tool call 中，影响 delta_text 分割 |
