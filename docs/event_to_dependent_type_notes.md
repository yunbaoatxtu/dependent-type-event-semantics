# 事件语义到依赖类型语义的自动翻译方案

目标：把 Davidson/neo-Davidsonian 事件语义中用于处理可变配价的事件变量自动消去，改用依赖类型、自然数类型和时间算子表达。

## 依据

Luo 和 Shi 的论文 *Variable polyadicity without events: a type-theoretic analysis of event semantics* 的核心思路是：事件语义的收益可分成两类。第一类是可变配价，尤其是动词可带任意多个副词修饰语；这可以不用事件本体，而用依赖类型解决。论文把 Church 简单类型论扩展为带 `Pi` 类型和自然数类型 `N` 的 `C+`，并引入：

```text
ADV = (e -> t) -> (e -> t)
TV-ADV(0) = e -> e -> t
TV-ADV(1) = ADV -> e -> e -> t
TV-ADV(2) = ADV -> ADV -> e -> e -> t

IV-ADV(0) = e -> t
IV-ADV(1) = ADV -> e -> t
IV-ADV(2) = ADV -> ADV -> e -> t
```

因此一个及物动词可给成：

```text
butter : Pi n : N. TV-ADV(n)
```

这让副词数量由自然数 `n` 控制，不需要引入 `exists e` 的事件变量。时间表达不作为事件实体保留，而转成命题层时间算子。

## 自动翻译规则

输入采用事件语义的合取范式：

```text
exists e.
  Verb(e)
  and Role1(e, x1)
  and ...
  and Adv1(e)
  and ...
  and TimeRel(e, tau)
```

输出采用依赖类型式语义：

```text
Verb(n)(Adv1, ..., x1, ..., xk)
```

其中：

```text
n = 副词修饰语数量
Verb : Pi n : N. Vk-ADV(n)
Vk-ADV(n) = ADV^n -> e^k -> t
```

时间谓词提升为命题层算子：

```text
at(e, noon) + P  ==>  at_T(noon, P)
during(e, i) + P ==> during_T(i, P)
```

## 示例

输入：

```text
exists e.
  butter(e)
  and Agent(e, John)
  and Theme(e, toast)
  and slowly(e)
  and in(e, bathroom)
  and at(e, noon)
```

输出：

```text
butter : Pi n : N. TV-ADV(n)
at_T(noon, butter(2)(slowly, in(bathroom), John, toast))
```

这里 `slowly` 和 `in(bathroom)` 都作为 `ADV` 项计数，所以 `n = 2`；`at(noon)` 作为时间算子作用在整句命题上。

## 运行

```bash
python3 dependent_type_event_translator.py example_butter.json --pretty
```

该原型目前处理：一个存在量化事件变量、一个核心动词谓词、常见语义角色、一元事件副词、带参数的修饰语，以及 `at`、`during`、`before`、`after` 等时间关系。未能翻译的残余原子会保留在 `residual_atoms_not_translated` 中，方便人工检查。
