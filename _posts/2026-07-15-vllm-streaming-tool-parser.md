---
title: 'vLLM 流式输出架构与 Tool Parser 分支决策'
date: 2026-07-15
permalink: /blogs/vllm-streaming-tool-parser
tags:
  - vllm
  - llm
  - streaming
  - tool-use
---

## 流式输出的分支架构

`chat_completion_stream_generator` 是流式输出的核心，内部维护了一个分支决策树。

## 入口判断变量

```
is_mistral_grammar_path = request._grammar_from_tool_parser
```
由 Mistral 的 `grammar_from_tool_parser` 触发，走自定义 grammar 约束解码。

```
tool_choice_function_name = request.tool_choice.function.name  # 或 None
```
`tool_choice: {type: "function", function: {name: "get_weather"}}` 时取到名称。

```
tool_choice_auto = (not tool_choice_function_name
                    and request.tools
                    and self.tool_parser
                    and self.enable_auto_tools
                    and request.tool_choice in ["auto", None])
```
"auto" 模式 + 有 tool_parser + enable_auto_tools = True。

```
tool_choice_uses_parser = (self.tool_parser is not None
                           and not self.tool_parser.supports_required_and_named
                           and request.tools
                           and (tool_choice == "required"
                                or isinstance(tool_choice, NamedToolChoice)))
```
当 tool_choice 是 required/named，但 parser 不能输出 JSON（如 XML 格式），降级到 parser 路径。

## 3 个分类

| 分类 | tool_choice | parser 注册 | 走哪条路径 |
|---|---|---|---|
| **auto** | "auto"/None | 有 | `parser.parse_delta()` |
| **named** | `{function: {name: "..."}}` | — | `extract_tool_call_required_streaming()` |
| **required** | "required" | — | `extract_tool_call_required_streaming()` |
| **required (XML)** | "required" | 有且不支持 JSON | `parser.parse_delta()`（降级） |

## 分支决策树

主循环每步迭代、每个 `output.index` 独立执行以下分支（互斥）：

```
          ┌─ use_harmony ── extract_harmony_streaming_delta()
          │                  （token 级状态机）
          │
          ├─ is_mistral_grammar_path ── MistralToolParser
          │                            .extract_maybe_reasoning_and_tool_streaming()
          │
          ├─ tool_choice_function_name ── named tool_choice
          │   AND not tool_choice_uses_parser
          │   ├─ reasoning_parser active → extract_reasoning_streaming()
          │   └─ else → 构造 DeltaToolCall {id, type, name, arguments}
          │
          ├─ tool_choice == "required" ── required tool_choice
          │   AND not tool_choice_uses_parser
          │   └─ extract_tool_call_required_streaming()
          │
          └─ tool_choice_auto ── parser.extract_tool_calls_streaming()
              OR tool_choice_uses_parser
```

## 架构设计讨论

### Mistral / Harmony 的 if/else 分支

Mistral 和 GPT-OSS（`use_harmony`）的代码嵌入在主线流程中，原因是：

- `mistral_common` 不是 HuggingFace tokenizer，有自研的 grammar 约束和 prompt 编码
- 引入时没有重构插件架构，走了 `if/else` 最小改动路径
- 目前没有第三个模型族进来，重构动力不足

影响：`chat_completion_stream_generator` 里约多处 `is_mistral_*` 分支，代码可读性差。

更好的设计：入口分叉 → 两个独立的 pipeline（prompt 编码 + output 提取）→ 公用 SSE 组装。

### MoE（Mixture of Experts）

```python
class MoE(nn.Module):
    def forward(self, x):
        weights, indices = self.router(x)        # 每个 token 选 top-2 专家
        return fused_moe(x, self.experts, indices, weights)
```

- 总参数量大（如 DeepSeek V3: 256 × ~5.5B = 1.4T）
- 推理时只激活 2 个专家，计算量 ≈ 2× 普通模型
- 专家可以分到多张 GPU（vLLM 的 DP/EP 做这个）

### `DeltaToolCall` 的构造

流式场景下，工具调用信息是按 `delta`（增量）逐片发送的：

1. **首次检测到函数名称**：发送 `DeltaToolCall(id=新 UUID, type="function", name="get_weather", arguments="")`
2. **后续参数到达**：只发送 `DeltaToolCall(arguments='{"location": "北')` 等增量片段
3. **函数结束**：关闭 arguments JSON

客户端收到这些 delta 后，逐片拼接还原完整的工具调用。

## 相关文件索引

```
# 入口与服务
vllm/entrypoints/openai/chat_completion/serving.py
  └─ create_chat_completion()
  └─ chat_completion_stream_generator()
  └─ chat_completion_full_generator()
  └─ extract_tool_call_required_streaming()
  └─ _filter_delta_text()

# 渲染
vllm/entrypoints/serve/render/serving.py
  └─ OpenAIServingRender
      └─ render_chat_request()
      └─ render_chat()
      └─ preprocess_chat()

vllm/renderers/hf.py
  └─ HfRenderer
      └─ render_messages_async()
      └─ safe_apply_chat_template()

# 引擎
vllm/v1/engine/async_llm.py
  └─ AsyncLLM
  └─ generate()
  └─ add_request()

# Tool Parsers（主线）
vllm/tool_parsers/abstract_tool_parser.py
  └─ ToolParser (ABC)
  └─ adjust_request()
  └─ extract_tool_calls()
  └─ extract_tool_calls_streaming()

vllm/tool_parsers/utils.py
  └─ _get_tool_schema_from_tool()
  └─ _get_json_schema_from_tools()
```
