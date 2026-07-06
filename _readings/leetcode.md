---
title: "LeetCode Notes"
collection: Learning
permalink: /readings/reading/leetcode-notes
date: 2025-12-03
---


# LeetCode Notes

## Binary Search templates

二分查找的细节确实容易让人混淆，比如中间点计算是否要加一，以及开闭区间如何影响循环条件。不过，一旦理解了其背后的逻辑，就会发现这些规则并非凭空设定，而是为了**确保搜索区间能够被严谨地收缩，并避免死循环**。下面我将通过几个核心模板和记忆口诀，帮你彻底理清这些关系。

### 🧠 掌握三个核心模板

首先，我们来梳理三种最常见且实用的二分查找模板。下表清晰地对比了它们的特点、适用场景和关键细节。

| 模板名称 | 核心特点 | 适用场景 | 循环条件 | 中间点 `mid` 计算 | 关键操作 | 返回值处理 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **模板1：标准查找** | 精确匹配，找到即返回 | 在**无重复元素**或只需找到**任意一个**目标值时使用 | `while (left <= right)` | `left + (right - left) / 2` | 找到`nums[mid] == target`则直接返回`mid` | 未找到返回-1 |
| **模板2：寻找左边界** | 寻找**第一个**满足条件的元素 | 查找插入位置、寻找重复元素的起始索引 | `while (left < right)` | `left + (right - left) / 2` | 收缩右边界：`nums[mid] >= target` 时 `right = mid` | 检查`left`是否有效 |
| **模板3：寻找右边界** | 寻找**最后一个**满足条件的元素 | 寻找重复元素的结束索引 | `while (left < right)` | **`left + (right - left + 1) / 2`** | 收缩左边界：`nums[mid] <= target` 时 `left = mid` | 检查`right`是否有效 |

下面是每个模板的C++代码实现，请注意其中的注释。

**模板1：标准二分查找（精确匹配）**
```cpp
// 适用于无重复或只需找到任意目标值的情况
int binarySearch(vector<int>& nums, int target) {
    int left = 0, right = nums.size() - 1; // 区间定义为[left, right]
    while (left <= right) { // 注意：因为是闭区间，left == right 时区间依然有效
        int mid = left + (right - left) / 2; // 防止溢出
        if (nums[mid] == target) {
            return mid; // 找到目标，立即返回
        } else if (nums[mid] < target) {
            left = mid + 1; // 目标在右侧，收缩左边界
        } else {
            right = mid - 1; // 目标在左侧，收缩右边界
        }
    }
    return -1; // 未找到
}
```

**模板2：寻找左边界（第一个 >= target 的元素）**
```cpp
// 常用于寻找插入位置或重复元素的起始索引
int leftBound(vector<int>& nums, int target) {
    int left = 0, right = nums.size(); // 区间定义为[left, right)
    while (left < right) { // 注意：左闭右开，left == right 时循环终止
        int mid = left + (right - left) / 2;
        if (nums[mid] >= target) {
            right = mid; // 满足条件，收缩右边界（因为右开，所以right=mid是安全的）
        } else {
            left = mid + 1; // 不满足条件，收缩左边界
        }
    }
    // 循环结束时 left == right
    // 后处理：检查left是否越界，以及是否真的等于target
    if (left < nums.size() && nums[left] == target) return left;
    return -1;
}
```

**模板3：寻找右边界（最后一个 <= target 的元素）**
```cpp
// 用于寻找重复元素的结束索引
int rightBound(vector<int>& nums, int target) {
    int left = 0, right = nums.size();
    while (left < right) {
        // 关键区别：计算mid时+1，确保向上取整，避免死循环
        int mid = left + (right - left + 1) / 2;
        if (nums[mid] <= target) {
            left = mid; // 满足条件，收缩左边界
        } else {
            right = mid - 1; // 不满足条件，收缩右边界
        }
    }
    // 循环结束时 left == right
    // 后处理：检查right是否有效
    if (right >= 0 && nums[right] == target) return right;
    return -1;
}
```

### 💡 理解关键细节与记忆口诀

#### 1. **为什么有时 `mid` 要加一，有时不加？**
这完全是为了**防止死循环**。核心规则是：**当有 `left = mid` 这个操作时，计算 `mid` 就必须加一向上取整**。

-   **记忆口诀**：**“左动则加，右动不加”**。即，如果分支中有 `left = mid`（左边界在动），则 `mid` 计算要加一；如果只是 `right = mid`（右边界在动），则 `mid` 计算不加一。
-   **原因**：考虑一个只有两个元素的区间 `[left, right]`，其中 `left + 1 = right`。
    -   如果使用 `mid = left + (right - left) / 2`（向下取整），则 `mid` 等于 `left`。
    -   如果此时执行 `left = mid`，那么新区间仍然是 `[left, right]`，没有发生任何变化，导致**死循环**。
    -   而如果使用 `mid = left + (right - left + 1) / 2`（向上取整），则 `mid` 等于 `right`，执行 `left = mid` 后区间变为 `[right, right]`，循环可以正常结束。

#### 2. **开闭区间如何决定循环条件？**
区间定义直接决定了循环的终止条件。

-   **记忆口诀**：**“有开则小于，全闭则小于等于”**。
    -   **左闭右开 `[left, right)`**：循环条件为 `while (left < right)`。因为当 `left == right` 时，区间 `[left, right)` 已经是一个空区间了，没有继续搜索的必要。
    -   **左闭右闭 `[left, right]`**：循环条件为 `while (left <= right)`。因为当 `left == right` 时，区间 `[left, right]` 仍然包含一个元素（即 `left` 或 `right` 指向的元素），必须进行判断。

选择一种你喜欢的区间定义并始终坚持，可以大大减少混乱。**通常，左闭右开 `[left, right)` 在处理边界时更简洁，是现代C++代码中的流行写法。**

### 🎯 实战练习与记忆巩固

要真正掌握，最好的方法是实践。你可以尝试用不同的模板解决下面这个问题，并一步步跟踪 `left`、`right` 和 `mid` 的变化：

**题目**：在数组 `nums = [1, 2, 2, 2, 3]` 中查找目标值 `target = 2`。
-   用**模板1**：它会直接返回中间某个 `2` 的索引（例如 `2`）。
-   用**模板2**：它应该返回第一个 `2` 的索引（`1`）。
-   用**模板3**：它应该返回最后一个 `2` 的索引（`3`）。

通过手动模拟或调试，你会清晰地看到每个模板是如何一步步收缩搜索区间并得到最终答案的。

### ⚠️ 其他重要技巧与常见陷阱

1.  **防止整数溢出**：永远使用 `mid = left + (right - left) / 2` 来代替 `(left + right) / 2`，因为 `left + right` 在很大时可能会超出整型的最大值 。
2.  理解**搜索区间**的概念：在循环开始时，你的搜索区间是明确的（由 `left` 和 `right` 的初始值定义）。每一轮循环，你都是在根据 `mid` 的值**排除掉一半确定不包含目标的区间**。
3.  **模糊匹配**：二分查找不仅可用于精确匹配，还可用于模糊匹配，例如寻找第一个大于等于某值的元素。这时，关键是设计好 `if` 语句中的判断条件。

希望这份详细的梳理能帮助你攻克二分查找的细节难关！理解其背后的逻辑远比死记硬背要有效得多。如果还有疑问，欢迎继续提出。

您对二分查找的开闭区间细节探究得非常到位，这确实是掌握该算法的关键。标准二分查找（精确匹配）如果使用左闭右开区间 [left, right)，其写法与闭区间版本在边界初始化和更新规则上有所不同。这种写法同样正确且高效，在特定场景下逻辑处理甚至更简洁。

下面是对比表格和详细代码示例，希望能帮助您巩固记忆。

🆚 核心区别一览

特性 左闭右闭区间 [left, right] 左闭右开区间 [left, right)

右边界初始化 right = nums.size() - 1 right = nums.size()

循环条件 while (left <= right) while (left < right)

右边界更新 right = mid - 1 right = mid

左边界更新 left = mid + 1 left = mid + 1

区间含义 搜索范围包含left和right 搜索范围包含left，但不包含right

✨ 左闭右开区间代码实现

int binarySearch_OpenRight(const std::vector<int>& nums, int target) {
    // 初始化：left 指向起始位置（包含），right 指向数组末尾的下一个位置（不包含）
    int left = 0;
    int right = nums.size(); // 注意：右边界是 nums.size()，不是 size()-1

    // 循环条件：只要左边界小于右边界，搜索区间就有效
    while (left < right) {
        // 防止溢出的中间点计算
        int mid = left + (right - left) / 2;

        if (nums[mid] == target) {
            return mid; // 找到目标，直接返回
        } else if (nums[mid] < target) {
            // 目标在右侧，收缩左边界 [mid+1, right)
            left = mid + 1;
        } else {
            // 目标在左侧，收缩右边界 [left, mid)
            // 因为右边界是开区间，所以更新为 mid 即可（mid 本身不会被包含）
            right = mid;
        }
    }
    
    // 循环结束意味着未找到目标
    return -1;
}


💡 关键细节解析与记忆技巧

1.  为什么 right = nums.size()？
    因为这是左闭右开区间，right 指向的是不包含的位置。初始时，有效的搜索范围是从索引 0 到 nums.size()-1，为了让这个范围对应 [left, right)，right 自然应该初始化为 nums.size()，即最后一个有效元素的下一个位置。

2.  为什么循环条件是 left < right？
    在左闭右开区间 [left, right) 中，当 left == right 时，区间变为 [x, x)，这是一个空区间，没有任何元素需要或能够被搜索。因此循环继续的条件是区间内还有元素，即 left < right。

3.  为什么更新右边界是 right = mid？
    这是左闭右开区间逻辑的直接体现。当确定目标值在 mid 左侧时，新的搜索区间应该是 [left, mid)。因为右边界是开的，right 的新值应该设置为 mid，这样新的区间才不会包含 mid 这个已经被判定为无效的元素。可以这样记忆：“右开，故舍其身”，更新时直接指向新的边界点。

🧠 如何选择与记忆

•   记忆口诀：可以记住 “右开大一号，循环无等号，更新右边界，直接等于mid”。

    ◦   “右开大一号”：右边界初始值比闭区间大1（nums.size()）。

    ◦   “循环无等号”：循环条件是 <，而不是 <=。

    ◦   “更新右边界，直接等于mid”：更新右边界时是 right = mid。

•   选择建议：

    ◦   左闭右开区间 在处理“查找插入位置”等问题时，逻辑上通常更顺畅，因为循环终止时 left 和 right 重合，正好就是第一个大于等于目标值的位置，也就是应该插入的位置。

    ◦   左闭右闭区间 的边界定义可能对初学者来说更直观，因为它与数组的索引范围完全对应。

    ◦   关键是选择其中一种你理解最深刻的写法，反复练习直至形成肌肉记忆，并在各种变体问题中熟练应用它。两种写法在正确实现的前提下，效率是相同的。

希望这个详细的解释和对比能帮助您彻底理解并牢固掌握二分查找的开区间写法！如果您在实践中遇到任何特定的问题，我们可以继续深入探讨。