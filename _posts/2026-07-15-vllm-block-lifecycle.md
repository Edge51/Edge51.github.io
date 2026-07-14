---
title: 'vLLM PagedAttention：Block 的完整生命周期'
date: 2026-07-15
permalink: /blogs/vllm-block-lifecycle
tags:
  - vllm
  - llm
  - pagedattention
  - system-design
---

vLLM v0.20.2 · block_size = 16

## 调用链总览

```
Scheduler.schedule()
  │
  ├─ Running
  │   └─ kv_cache_manager.allocate_slots(request, num_new_tokens, ...)
  │       │
  │       ├─ coordinator.get_num_blocks_to_allocate()        ← 先算要多少
  │       │
  │       ├─ 检查 pool 够不够: num_blocks > block_pool.get_num_free_blocks()?
  │       │   └─ 不够 → return None → scheduler 开始踢人
  │       │
  │       └─ coordinator.allocate_new_blocks()
  │           └─ SingleTypeKVCacheManager.allocate_new_blocks()
  │               └─ block_pool.get_new_blocks(num_new_blocks)
  │                   └─ FreeKVCacheBlockQueue.popleft_n(num_blocks)
  │
  ├─ Waiting
  │   └─ 同上 allocate_slots（首次 prefill 走这里）
  │
  └─ Preempt
      └─ kv_cache_manager.free(request)
          └─ coordinator.free(request_id)
              └─ SingleTypeKVCacheManager.free()
                  └─ block_pool.free_blocks(ordered_blocks)
                      └─ FreeKVCacheBlockQueue.append_n()
```

## Part 1 — Block 怎么生

### 1. 真正的分配入口：BlockPool.get_new_blocks()

```python
def get_new_blocks(self, num_blocks: int) -> list[KVCacheBlock]:
    if num_blocks > self.get_num_free_blocks():
        raise ValueError(...)

    ret = self.free_block_queue.popleft_n(num_blocks)

    for block in ret:
        assert block.ref_cnt == 0
        block.ref_cnt += 1    # ★ 分配时 ref_cnt 置为 1
    return ret
```

- **参数**: `num_blocks: int` — 要几个 block
- **返回**: `list[KVCacheBlock]` — 从 free list 头部 pop 出来的 block
- **ref_cnt**: 拿出来的 block `ref_cnt = 0 → 1`，标记为"被占用"

### 2. 去重逻辑

`scheduler.py` 里的 `_dedup_blocks()` 保证同一个 block 不会重复分配。对每个 request 已有的 block，算出差集 `num_new_blocks = num_required_blocks - num_existing_blocks`，只申请差额。

```
allocate_slots() 入口
  → coordinator.get_num_blocks_to_allocate()
    → 内部调用已分配的 num_blocks 查表
    → num_blocks_to_allocate = num_required - num_existing
    → 如果是 0，直接 return 不调 allocate_new_blocks()
```

## Part 2 — Block 怎么死

### Preempt 触发

当资源不足时，调度器踢人：

```python
# scheduler.py:965
def _preempt_request(self, request):
    # 1. kv_cache_manager.free(request)
    # 2. request 从 running → waiting
```

### Free 链路

```python
# block_pool.py:408
def free_blocks(self, ordered_blocks: list[KVCacheBlock]):
    for block in ordered_blocks:
        block.ref_cnt -= 1         # ref_cnt--
        if block.ref_cnt == 0:     # 没人用了，回 free list
            self.free_block_queue.append_n([block])
            block.kvcache_block_id = None  # 清除物理块 ID
```

### 难点：哪些 block 要 free？

一个 request 可能有多个 block。preempt 时需要**全部释放**。`kv_cache_manager.free(request_id)` 会查出这个 request 对应的所有 block ID，逐个释放。

## Part 3 — Block 的"起死回生"

**Prefix cache 场景**：

```python
# scheduler.py:758 (Waiting 队列)
existing_blocks = self.kv_cache_manager.get_blocks_by_hash_prefix(prefix_hash)
# 返回已缓存的 block 列表
```

当新请求的 prefix 与缓存命中时，这些 block 的 `ref_cnt > 1`，不会被 free。多个请求**共享**同一块物理显存，直到所有共享者都释放后才回 free list。

## 关键数据结构

| 结构 | 作用 |
|---|---|
| `FreeKVCacheBlockQueue` | 空闲 block 的双向链表，支持 O(1) 头部 pop 和尾部 append |
| `KVCacheBlock` | 单个 block：`block_id`, `ref_cnt`, `kvcache_block_id`, 双向链表指针 |
| `req_to_blocks: dict[str, list[KVCacheBlock]]` | request → 其占用的 block 列表 |

## 总结

Block 的完整生命周期：

```
free list → get_new_blocks() → ref_cnt=1 → 被使用
  → preempt → free_blocks() → ref_cnt-- → ref_cnt==0 → 回 free list
  → prefix cache 共享 → ref_cnt>1 → 最后一个释放才回 free list
```

vLLM 通过这种分页管理方式，将 KV cache 的利用率从传统方法的 20-40% 提升到 90% 以上，这是它能够支持高吞吐推理的核心原因。
