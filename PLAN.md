# 五言古诗生成系统 — 实施计划（评审修订版）

> 依据《初面-实战题.pdf》与评审意见修订。核心口径：
> **模型只当工人，Harness 本地终裁；一次生成 + 本地修补，修不好必兜底；
> 兜底与校验“构造即合法”，任何输入最终都返回合规结果。**

## 0. 评审后锁定的关键决策

| 主题 | 结论 |
| --- | --- |
| 韵脚口径 | `pypinyin(style=Style.FINALS, strict=True)` 后**字符串精确相等**；不做 ia→a、ian→an、iong→ong 之类宽口径归并 |
| 模型调用 | 默认 **最多 1 次 LLM 生成**，`POEM_MAX_LLM_REPAIRS=0`；解析失败、韵脚失败、字符失败一律先本地修 |
| 本地修补失败 | 直接进确定性兜底，不再打第二轮 LLM |
| 主题理解 | `normalize_topic` 是纯本地、零调用的一等模块，产出意象/情绪/标题提示/禁用词 |
| 兜底 | 预制高质量五字句料 + topic 槽位，构造时即满足结构/汉字/韵脚，杜绝随机拼词 |
| 合法字符 | 只认 `U+4E00–U+9FFF` 基本区汉字；ASCII、全角、空格、数字、〇、注音、扩展区一律拒绝 |
| 确定性种子 | 使用 `hashlib.blake2s(topic, digest_size=8)` 的稳定摘要；**绝不使用内置 `hash()`** |
| 重复整句 | `DUP_LINE` 是**质量警告**，不是合规错误；`ok=True` 但仍上报，供文学性统计 |
| API 调用 | 普通 chat completions，**不使用 JSON Schema / response_format**，避免过滤掉免费模型 |
| 工件记录 | 默认静默；`POEM_DEBUG=1` 才落盘；写失败绝不影响返回 |
| 项目形态 | 单模块小项目 + pypinyin，不上 LangChain、向量库、本地小模型 |

## 1. 对外接口与运行要求

```python
# poem_system/api.py
def generate_poem(topic: str) -> dict:
    ...
```

返回（`topic` 由 Harness 原样写回，不允许模型改写）：

```json
{
  "topic": "月色",
  "title": "月下清辉",
  "lines": ["清辉照晚窗", "疏影过回廊", "客梦落寒霜", "孤灯夜未央"]
}
```

运行要求：

- 依赖只保留 `pypinyin`，其余用标准库。
- 有 `OPENROUTER_API_KEY` 时默认走一次 `openrouter/free`；
  没有 Key、显式 `--offline`、调用失败或输出不合格时静默走兜底，不崩溃。
- `generate_poem` 返回前必须再次全量校验；失败即丢弃模型产物改走兜底，
  绝不把非法 JSON / 原始模型文本往外扔。

## 2. 主流程：一条直线函数，不做重型阶段机

```text
generate_poem(topic)
  → normalize_topic(topic)        # 纯本地：意象/情绪/标题提示/禁用词
  → model.generate(brief)          # 最多 1 次，超时 12–20s；可注入假客户端
  → parse(raw)                     # 整段 JSON → 最外层 {} → 四行五字，逐级降级
  → validate(poem)                 # 结构化错误码，不只返回 bool
  → local_fix(poem, brief, errors) # 删非法字符、换第 3 句末字等，零 LLM
  → validate(poem) again
  → fallback(brief) if still bad   # 构造即合法
  → assert validate(final).ok      # 终态断言，失败也绝不外抛模型原文
  → return {"topic": topic, ...}
```

默认预算：

- 单次模型调用超时：默认 15 s（12–20 s 区间内可配置）。
- 总预算：默认 30 s（25–35 s 区间），超时直接切兜底。
- LLM 调用上限：1 次生成；`POEM_MAX_LLM_REPAIRS` 仅调试用，默认 0。
- 本地修补次数：有上限（例如 1 轮），修补后再不合法就兜底。

免费路由不稳是常态，因此**任何异常路径的终点都是确定性兜底**。

## 3. 韵脚判定：严格 Style.FINALS 相等

固定实现：

```python
from pypinyin import lazy_pinyin, Style

def rhyme_key(ch: str) -> str:
    finals = lazy_pinyin(ch, style=Style.FINALS, strict=True, errors="ignore")
    if not finals or not finals[0]:
        raise ValueError(ch)
    return finals[0].replace("ü", "v")  # v/ü 统一即可
```

规则：

- 第 1 句末字与第 3 句末字比较 `rhyme_key` 是否相等。
- 不做“听起来像”的归并；`ian != an`、`iang != ang`、`iong != ong`。
- 测试不使用多音字；实现仍取首个读音，保持确定性。
- 无法取到韵母的汉字直接抛内部错误，由调用方按不可修复处理。

固定测试向量（写进单测，锁死口径）：

| 类别 | 对 | 期望 |
| --- | --- | --- |
| 押韵 | 窗 / 霜 | 相等（uang） |
| 押韵 | 光 / 窗 | 相等（uang） |
| 不押 | 窗 / 灯 | uang vs eng |
| 不押 | 光 / 廊 | uang vs ang |
| 不押 | 天 / 安 | ian vs an |
| 不押 | 秋 / 愁 | iou vs ou |
| 不押 | 月 / 色 | ve vs e |

`strict=True` 行为必须单测锁死：

| 字 | 期望 final |
| --- | --- |
| 衣 | i |
| 乌 | u |
| 迂 | v |
| 威 | uei |
| 忧 | iou |

## 4. 合法字符与校验器

谓词口径：

- 合法：`U+4E00–U+9FFF` 内的单个汉字。
- 拒绝：ASCII 字母/数字、半角/全角标点、空格、制表符、`〇`（U+3007）、
  注音符号、CJK 扩展区生僻字等一切非基本区字符。

```python
def is_han(ch: str) -> bool:
    return len(ch) == 1 and 0x4E00 <= ord(ch) <= 0x9FFF

def only_han(s: str) -> bool:
    return all(is_han(c) for c in s)
```

`validate_poem` 返回结构化错误码，绝不止 `ok: false`：

```text
WRONG_TYPE      非 dict 或键缺失/类型错误
TOPIC_ECHO      topic 字段与输入不一致（正常应被 Harness 覆写，出现即 bug）
TITLE_LEN       title 长度不在 2–8
LINE_COUNT      lines 不是恰好 4 句
LINE_LEN        某句不是恰好 5 字
NON_HAN         标题或句子含非基本区汉字字符
RHYME           第 1、3 句末字韵母不相等
EMPTY           标题/句子为空
```

`DUP_LINE` 不进入 errors：整句重复时合规仍为 `ok=True`，只在
`warnings` 中上报 `dup_line`，供文学性统计使用；兜底尽量避开重复，
但绝不用重复句卡死终态断言。

允许单字重复，但“窗窗窗窗窗”这类极端重复由质量启发式打低分，
不作为合规错误处理。

## 5. 输入规范化：纯本地、零模型调用

`normalize_topic(topic) -> PoemBrief`，在调模型与兜底之前执行，两边共用。

```python
@dataclass
class PoemBrief:
    raw: str                 # 原始输入，仅存档/回写用
    imagery: list[str]       # 可入诗的汉字意象，如 ["归雁", "星河", "远夜"]
    mood: str                # 情绪提示，如 "孤远"
    title_hints: list[str]   # 2–4 字标题素材，如 ["星归", "远夜"]
    banned: list[str]        # 禁止入诗的概念/原文片段
```

示例映射（本地关键词表，确定性）：

- `Mars Return` → imagery `["归雁", "星河", "远戍", "夜"]`、mood `"孤远"`、
  title_hints `["星归", "远夜"]`、banned `["Mars", "Return"]`。
- `2026年的第一场雪` → imagery `["雪", "寒", "年", "夜"]`、
  banned `["2026"]`。
- `AI时代的孤独` → imagery `["孤", "灯", "夜", "客"]`、
  banned `["AI", "时代"]`。
- 不认识的字词走通用意象组，仍能产出合格诗。

原则：

- 只用中文关键词表 + 简单英文词典 + 年份/数字映射，**不为规范化再打 LLM**。
- Prompt 只放 `brief`（意象、情绪、禁用词），不放原始长文本。
- 返回 JSON 中的 `topic` 始终由 Harness 写回 `brief.raw`。

## 6. 确定性兜底：构造即合法，且与 topic 可见关联

兜底不是“最后从模板库碰运气”，而是：

1. 用同一份 `PoemBrief` 选题材；
2. 从**预制五字句料库**选取句子。每条句料满足：
   - 恰好 5 个基本区汉字；
   - 带意象标签（月/夜/雪/孤/山/海/春/秋/城/客/归…）；
   - 末字已知韵母（录入时直接存 `rhyme_key`，运行时不再猜）。
3. 选一个韵母：优先取 brief 意象词中出现的末字韵母；否则从常用韵部中
   按 `hash(topic)` 确定性选择。
4. 组诗：第 1、3 句末字必须同韵；第 2、4 句不强制；四句围绕同一意象群。
5. 标题从 `title_hints` 或“意象 + 常用题字”拼接，长度 2–4 字，纯汉字。
6. 用稳定摘要 `topic_seed(topic)` 选句料/标题，同一 topic 稳定可复现，
   不同 topic 不撞车；禁止用内置 `hash()`（带随机盐）：

```python
import hashlib

def topic_seed(topic: str) -> int:
    return int.from_bytes(
        hashlib.blake2s(topic.encode("utf-8"), digest_size=8).digest(), "big"
    )
```

质量约束：

- 句料**宁少而可读**：初期人工维护少量高质量句料（每常用韵部若干条），
  不做现场“字表拼句”；
- 用“多模板 + 意象槽位”降低模板感；
- 所有兜底产物仍过同一套 Validator 与终态断言，保证构造确实合法。

## 7. 模型通道：兼容 free 路由，不绑 JSON Schema

客户端约束：

- 端点与模型是常量：`https://openrouter.ai/api/v1/chat/completions` +
  `openrouter/free`；**不提供用户可选模型的产品口子**。
- 普通 chat completions，请求体不加 `response_format`，避免过滤掉
  当前可用的免费模型。
- Key 只从 `OPENROUTER_API_KEY` 读取；请求/日志/工件永不落 Key。
- 定义窄接口 `ModelClient.generate(messages) -> RawModelResult`，
  测试注入 fake client，不碰网络。

Prompt 形态（短、硬、给形态不给文学自由发挥）：

```text
只输出JSON，不要解释。
{"title":"二至八个汉字","lines":["五字","五字","五字","五字"]}
硬性：
- 全是汉字，无标点空格数字英文
- 第1句和第3句最后一个字韵母相同
主题意象：归雁 星河 远夜
情绪：孤远
禁止：英文 数字 现代词
```

- 只保留 1 条 few-shot；
- few-shot 样例的末字韵部**与当前 brief 不同**，防止模型照抄整首；
- 模型输出无论多“像诗”，一律先解析再校验。

解析顺序（逐级降级）：

1. 整段 `json.loads`；
2. 正则抽取最外层 `{...}` 再 `json.loads`；
3. 按行提取连续四个“恰好 5 个汉字”的片段；
4. 都不行则视为解析失败 → 本地修补/兜底。

## 8. 本地修补：默认替代 LLM 修复轮

修补只在已拿到候选诗时进行，全部本地、零模型调用：

| 失败类型 | 本地动作 |
| --- | --- |
| 仅含非法字符 | 删除标点/空格；全角转半角后丢弃英文与数字；若还能凑成 4×5 纯汉字则接受 |
| 仅韵脚不匹配 | 保留第 1 句；只从**白名单尾字库**（按韵母分组、只收诗里常见词）替换第 3 句末字；白名单替换后仍全量校验 |
| 结构烂（JSON 不可用、句数/字数差太多） | 不硬修，直接兜底 |
| 修补后仍不合法 | 直接兜底 |

本地修补不追求文学性飞跃，只求“一次生成里的多数小毛病不花第二次模型钱”。

## 9. Harness / Runtime

收敛为薄薄一层：

```python
def generate_poem(topic: str) -> dict:
    brief = normalize_topic(topic)
    candidate = try_model_once(brief)          # 无 Key/--offline 时为 None
    poem, errors = try_parse_and_fix(candidate, brief)
    if errors:
        poem = fallback(brief)
    assert validate_poem(poem).ok
    return poem_with_original_topic(topic, poem)
```

离线开关不进对外签名：

- `api.generate_poem(topic)` 保持题目原样，**只有 topic 一个参数**；
- 无 Key、`POEM_OFFLINE=1`、客户端异常三者都走同一个兜底收口；
- `cli.py --offline` 只调内部 `harness.run(topic, offline=True)`。

保留但不做重：

- 预算与超时是纯参数；
- 事件回调只用于调试记录与实验统计；
- 不引入任务队列、状态机框架、Agent 自主决策循环。

## 10. 工件与调试记录

- 默认**静默**：不产生 run/event/attempt 文件。
- `POEM_DEBUG=1`（或显式 `--verbose`）时写：

```text
artifacts/runs/YYYYMMDD/<run_id>/
  run.json         # topic、brief、attempts、延迟、最终 poem、source
  events.jsonl     # 每阶段 append：normalize/parse/validate/fix/fallback
```

- 调试记录仍不含 Key、Authorization 头。
- Recorder 写失败只告警，绝不影响 `generate_poem` 返回值。
- 实验统计走内存聚合，输出到 stdout 或一份 CSV，不做仪表盘框架。

## 11. 测试设计

### 单元测试（无网络）

- `rhyme`：第 3、4 节全部固定向量；`strict=True` 的 i/u/v/uei/iou。
- `validate`：title 1/2/8/9 字；lines 3/4/5 句；句长 4/5/6；ASCII、全角
  标点、空格、数字、`〇`、注音、扩展区字、重复整句、空字符串。
- `normalize`：中文词、英文、年份、数字、纯标点、空串都返回合法 brief，
  绝不抛异常。
- `fallback`：构造即合法 + 同 topic 稳定 + 不同 topic 不完全相同。
- `parse`：裸 JSON、代码围栏、解释文字、JSON 后杂文、空、数组、
  `lines` 为字符串、title 带书名号。

### 假客户端故障矩阵（无网络）

覆盖：完美 JSON；Markdown 包裹；七言/三句/五句；不押韵；HTTP 429/500；
超时；响应 2MB；非 UTF-8；空内容；连续坏（应走兜底）。

每个用例断言：最终结果过全量校验；`topic` 原样回写；未落 Key；
模型调用不超过上限。

### 模糊/属性测试

```text
for topic in fuzz_topics:            # 空串、纯空格、纯标点、纯数字、
    poem = generate_poem(topic)      # 超长英文、emoji、中文乱串…
    assert validate_poem(poem).ok
```

默认跑 `--offline` 兜底通道，保证离线确定性。

### E2E：真实 free 路由抽样（默认跳过）

标记 `@pytest.mark.network`；没有 `OPENROUTER_API_KEY` 时自动 skip。
本地无网时，单元 + 假客户端 + `--offline` fuzz 必须全绿。

固定 10 个 topic，每个跑少量次数，记录：

- 模型调用次数；
- 超时次数；
- 是否兜底及兜底率；
- 端到端延迟；
- `usage` 的 prompt/completion token。

结果用于决定默认是否保留那 1 次 LLM，以及 Prompt 是否继续调，不做成常驻框架。

## 12. CLI（测试与手测入口）

```bash
# 单条
python -m poem_system.cli 月色

# 多条
python -m poem_system.cli --topics 月色 "Mars Return" "2026年的第一场雪"

# 强制走兜底，不打 API
python -m poem_system.cli --offline 月色

# 打印校验细节
python -m poem_system.cli --verbose 月色
```

行为：

- 调用 `generate_poem`；
- 格式化输出 JSON；
- 本地再校验一次：四句、五字、纯汉字、第 1/3 句韵脚；
- 退出码：0 = 合规；1 = 不合规（正常不应发生）；
- 无 `OPENROUTER_API_KEY` 或 `--offline` 时静默走兜底，不崩溃。

## 13. 项目结构（提交形态）

```text
ancient_poem/
├── README.md               # 环境变量、安装、python -c 示例
├── PLAN.md                 # 本文档
├── requirements.txt        # pypinyin 即可
├── poem_system/
│   ├── __init__.py
│   ├── api.py              # generate_poem(topic) -> dict（对外接口）
│   ├── cli.py              # 手测/回归入口
│   ├── rhyme.py            # 严格韵母 key
│   ├── validate.py         # 结构/汉字/错误码
│   ├── parse.py            # 稳健 JSON/行提取
│   ├── normalize.py        # topic → PoemBrief
│   ├── fallback.py         # 构造即合法的确定性兜底
│   ├── local_fix.py        # 删非法字符/换第 3 句末字
│   ├── client.py           # openrouter/free 客户端（可注入假客户端）
│   ├── harness.py          # 单线流程 + 预算 + 终态断言
│   └── debug_log.py        # 默认静默的 Recorder
└── tests/
    ├── test_rhyme.py
    ├── test_validate.py
    ├── test_normalize.py
    ├── test_fallback.py
    ├── test_parse.py
    ├── test_fake_client_matrix.py
    └── test_fuzz.py
```

`requirements.txt`：`pypinyin`；测试用 pytest；不上 LangChain。

## 14. 里程碑与提交约定

一个里程碑一个可运行提交，禁止揉成大提交。提交信息用约定格式。

| 里程碑 | 提交信息（示例） | 完成标准 |
| --- | --- | --- |
| M0 骨架 | `chore: init repo skeleton and generate_poem stub` | 包结构、README、requirements、`generate_poem` 先整条走兜底；`python -m poem_system.cli 月色` 可运行 |
| M1 校验 | `feat: add validator and rhyme checker` | 汉字/字数/四句/韵脚 + 固定向量单测全绿，离线可证明底线 |
| M2 兜底 | `feat: add topic normalizer and deterministic fallback` | 无网/无 Key 也能输出与 topic 有关联且合规的诗；normalize 与 fallback 单测通过 |
| M3 接线 | `feat: add parser, local fixer, and model client` + `feat: wire harness and CLI test entry` | 解析→本地修补→单次模型调用→兜底收口；假客户端故障矩阵与 fuzz 通过 |
| M4 实测 | `test: add fake-client matrix and fuzz` + `docs: usage and run notes` | 真实 `openrouter/free` 固定矩阵抽样，记录延迟/Token/兜底率，锁定默认策略；README 可让验收方直接运行 |

注意：M3 的两个 `feat` 必须拆成两次 commit，不能揉在一起。每次提交后：

```bash
python -m poem_system.cli --offline 月色
```

打印的 JSON 必须过校验且退出码为 0。

每个部分结束时的 agent 检查清单：

1. 相关测试通过；
2. `python -m poem_system.cli 月色` 能打印合法 JSON；
3. `git status` 无 Key、无 `.env`、无缓存/调试工件；
4. 再 `git commit`（按上述信息格式）。

## 15. 不做的事（防止过度工程）

- 不做多模型路由、付费模型、模型自由选择；
- 不做 JSON Schema 约束响应；
- 不做 RAP 式韵母归并；
- 不做第二/第三次默认 LLM 修复；
- 不引入向量库、LangChain、本地小模型、繁简大表；
- 不做常驻实验仪表盘；实验只是 10 个 topic 的抽样表。
