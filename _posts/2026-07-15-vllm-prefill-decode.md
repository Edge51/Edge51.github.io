---
title: 'LLM 推理基础：Prefill / Decode 与 KV Cache'
date: 2026-07-15
permalink: /blogs/vllm-prefill-decode
tags:
  - vllm
  - llm
  - transformer
---

## Prefill vs Decode

| | Prefill | Decode |
|---|---|---|
| 何时发生 | 请求第一次进入 | 已有 KV cache 后 |
| 计算量 | 大量（并行算所有 token 的 KV） | 小（只算 1 个新 token） |
| GPU 用途 | 矩阵乘法（计算密集型） | 显存读取（带宽密集型） |
| `num_scheduled_tokens` | > 1（通常几百） | = 1 |

### Prefill 阶段

当一个新的请求到达时，模型需要先处理完整的输入 prompt。这个过程称为 **prefill**（预填充）。输入的 prompt 可能包含几百甚至几千个 token，模型需要并行计算所有 token 的注意力表示，并生成第一个输出 token。

由于可以并行计算，prefill 是**计算密集型**的，能够充分利用 GPU 的矩阵计算能力。

### Decode 阶段

生成第一个 token 之后，进入 **decode**（解码）阶段。模型一次只生成 1 个 token，生成的 token 会追加到序列末尾，作为下一轮解码的输入。

decode 是**带宽密集型**的——主要瓶颈在于从显存中读取 KV cache，而不是计算本身。

## KV Cache

KV cache 是 LLM 推理中最重要的优化手段之一：

- 缓存的是每层 attention 的 **K 和 V**（不是 Q）
- 一旦算好，后续 decode 直接读取，不用重算
- Q 每轮都变，不能缓存

### 为什么需要 KV Cache？

如果不使用 KV cache，每生成一个 token 都需要重新计算之前所有 token 的注意力。对于长度为 L 的序列，这会导致计算量从 O(L²) 变为 O(L³) —— 随着序列变长，计算量呈立方增长。

使用 KV cache 后，每步 decode 只计算最新 token 的注意力，计算量降为 O(L)，大幅提升推理速度和吞吐量。

### KV Cache 的代价

KV cache 虽然提升了速度，但消耗了大量显存。对于大模型（如 70B 参数），一个长序列的 KV cache 可能占用几十 GB 显存。这也是 vLLM 的 **PagedAttention** 要解决的问题——通过分页管理来减少显存碎片，提高利用率。

## 核心问题

1. 模型生成第一个 token 和后续 token 的计算过程有什么不同？
2. 为什么不能每生成一个 token 就重算一遍前面的注意力？
3. KV cache 到底 cache 了什么？cache 在哪？
4. Prefill 阶段和 decode 阶段的计算量差异在哪？
