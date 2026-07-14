---
title: 'vLLM Scheduler 架构与连续批处理机制'
date: 2026-07-15
permalink: /blogs/vllm-scheduler
tags:
  - vllm
  - llm
  - scheduler
  - system-design
---

## 架构鸟瞰

```
请求进来
  │
  ▼
API Server ──→ LLM Engine ──→ Scheduler ──→ Model Runner ──→ GPU Worker
                    ▲              │
                    │              ▼
                KvCacheManager  BlockAllocator(PagedAttention)
```

Scheduler 是引擎内部的"交通指挥"。每个 step 被调用一次，决定：
- 哪个 request 本轮能跑（分配 token budget）
- 哪个 request 要等等（留在 waiting）
- 哪个 request 要被挤出去（preempt）

## 五个探索方向

### A — Scheduler 的资源调度逻辑

- scheduler 到底在调度什么？算力、显存还是 token？
- token budget 是什么，怎么分给每个 request 的？
- 为什么 v1 scheduler 说"没有 prefill 和 decode 的区分"？

### B — 三个队列的流转

- running / waiting / preempted 三个队列的关系
- 什么时候 waiting 的 request 会被跳过？
- running → preempted 的触发条件

### C — 一个 request 的完整旅程

1. `add_request` 进来 → 放哪？
2. `schedule()` 的每一步做了什么？
3. 什么时候从 waiting 变成 running？
4. 结束之后怎么清理？

### D — Preempt 策略

- 什么时候需要 preempt？
- preempt 选谁？（什么策略）
- preempt 之后 request 去哪？

### E — PagedAttention + Scheduler

- PagedAttention 解决什么问题？
- scheduler 分配 token 时，KV cache block 怎么分配？
- preempt 释放的 block 怎么回收？

## 调度器的核心哲学

vLLM v1 调度器**没有显式的 prefill/decode 分支**，只有 `num_new_tokens` 的差值计算：

```
Running 队列遍历每个 request:
  num_new_tokens = min(token_budget 余量, request 需要的 token 数)
  
  if num_new_tokens > 1 → 本质是 prefill（计算多个 token）
  if num_new_tokens = 1 → 本质是 decode（只算 1 个）
```

这种设计的优势：调度器不需要知道模型执行器的内部细节，两者通过 `num_scheduled_tokens` 一个数字解耦。

## 三阶段调度

Token Budget 是有限的资源，三个阶段共享（Running 优先）：

1. **Running 队列**（`scheduler.py:387-522`）：遍历 running，算 `num_new_tokens`，分配 KV cache。不够就踢人（preempt）
2. **Waiting 队列**（`scheduler.py:567-840`）：新请求首次分配，prefix cache 匹配，`long_prefill_token_threshold` 截断
3. **Preemption**（`scheduler.py:965-985`）：踢人 → `kv_cache_manager.free()` → 放回 waiting

## Chunked Prefill

当请求的 prompt 非常长时，如果一次 prefill 全部 token，会阻塞其他请求太长时间。Chunked Prefill 把这个长 prefill 拆成多步：

- `long_prefill_token_threshold`：单步 prefill 的最大 token 数
- `enable_chunked_prefill`：控制是否允许分批

每次 schedule 只 prefill 一部分，把 GPU 时间片让给其他请求，提升整体吞吐。

## 关键配置项

| 配置 | 说明 |
|---|---|
| `max_num_batched_tokens` | 单步最大 token 总数 |
| `max_num_seqs` | 单步最大序列数 |
| `long_prefill_token_threshold` | 单请求单步 prefill 上限 |
| `enable_chunked_prefill` | 是否启用 Chunked Prefill |

## 总结

vLLM v1 调度器的设计亮点：

1. **隐式区分 prefill/decode**：通过 `num_new_tokens` 的数值，而非显式 if/else
2. **三阶段调度**：Running → Waiting → Preempt，Token Budget 统一分配
3. **Chunked Prefill**：长 prompt 分步执行，防止个别请求霸占 GPU
4. **与 PagedAttention 协同**：调度器只决定 token 分配，block 管理交由 KV Cache Manager
