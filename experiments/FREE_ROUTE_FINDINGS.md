# openrouter/free 批量采样发现

采样脚本：[scripts/run_free_route_experiment.py](../scripts/run_free_route_experiment.py)

原始数据在本地 `artifacts/experiments/`（按设计不提交仓库）；本文只沉淀
可复现的结论、失败模式和默认策略。

## 批次 1：72 次，并发 3，超时 15s

| 指标 | 结果 |
| --- | --- |
| 总运行 | 72 |
| 模型结果被接受 | 20（27.8%） |
| 走确定性兜底 | 52（72.2%） |
| 上游超时 | 23 |
| HTTP 429 | 16 |
| 客户端/响应结构错误 | 5 |
| 解析失败 | 4 |
| 本地修补失败 | 4 |
| 端到端延迟 p50 / p90 / p95 | 8.1s / 15.5s / 15.5s |
| 模型请求延迟 p50 / p90 | 3.5s / 13.0s |
| 有 usage 的运行 | 28 次，平均 1474.6 Token，最大 3919 |

命中的模型全部是 `:free` 路由，例如 `nex-agi/nex-n2.5-mini:free`、
`inclusionai/ling-3.0-flash-*:free`、`liquid/lfm-2.5-2.6b:free`、
`nvidia/nemotron-3-*:free`、`cohere/north-mini-code:free` 等。

## 批次 2：72 次，并发 2，超时 20s（紧跟批次 1）

| 指标 | 结果 |
| --- | --- |
| 总运行 | 72 |
| HTTP 429 | 72（100%） |
| 最终合规 | 72 / 72 |
| 429 快速失败延迟 p50 | 0.54s |

说明：批次 2 全部请求都在上游被限流，返回信息类似
`Provider returned error / temporarily rate-limited upstream ... add your own key`。
后续单独复测确认，这不是短暂冷却，而是免费档的**每日配额**：

```text
Rate limit exceeded: free-models-per-day.
Add 10 credits to unlock 1000 free model requests per day
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1789084800000  (2026-09-11 08:00 Asia/Shanghai)
```

即：每个免费 Key 每天最多约 50 次免费模型请求，当天用完后需等到次日
08:00（北京时间）重置，或在 OpenRouter 账户充值 10 credits 解锁 1000 次/天。

因此无法用这批数据评价并发数本身的影响，但可以确认两件事：

1. 免费 Key 存在每日 50 次的硬配额，连续大批量请求会整体进入 429；
2. 限流发生时系统以约 0.5s 完成降级，仍然 100% 返回合规结果。

## 已观察到的失败模式

| 现象 | 典型表现 | 当前处理 |
| --- | --- | --- |
| SSL read 挂死 | `urlopen(timeout=)` 未按期返回，卡在 SSL read | 客户端增加硬看门狗，超时返回 `TIMEOUT`，Harness 立即兜底 |
| 上游限流 | HTTP 429，`temporarily rate-limited upstream` | 不重试，快速走兜底（评测更看 100% 合规） |
| 200 但无 `choices` | 响应是元数据/错误对象，取 `choices` 抛 KeyError | 客户端识别为 `NO_CHOICES`，不再落入未分类异常 |
| 安全模型误路由 | 返回 `User Safety: safe`，完全不是诗 | 解析失败 → 兜底；实验统计归为 `non_poem_output` |
| 行数/字数不合规 | 4 字句、6 字句、5 句、`lines` 为对象 | 能修则修，结构烂直接兜底 |
| 韵脚不合规 | 例如 空(ong) / 光(uang)、幽(iou) / 收(ou) | 先用句料库同韵整句替换第 3 句，再用末两字白名单替换 |
| 极端 topic | 空串、纯空格、纯标点、emoji、超长文本、孤立代理字符 | 规范化不抛异常；seed 用 blake2s + surrogatepass；全部正常兜底 |

## 结论与默认策略

1. `openrouter/free` 的成功率高度依赖上游状态：同一批 topic 在不同时间
   可能 100% 成功，也可能 100% 429。系统必须在两种状态下都保持合规。
2. 默认保持“一次调用、绝不重试、失败即兜底”。429 时等待与重试只会
   增加延迟；快速兜底约 0.5s，比再赌一次更符合效率要求。
3. 单次超时保持 15s（可按 12–20s 配置）。模型成功请求的 p90 约 13s，
   再放大收益有限；硬看门狗必须存在。
4. 免费路由会路由到非诗歌模型（例如内容安全模型）。Prompt 不能解决
   路由选择，只能靠本地解析与兜底收口。
5. 两批 144 次运行中，最终结果合规率 100%；所有失败都在返回前被
   本地兜底吸收。
6. 大批量实验需要按天分批；复测前先看 429 响应的
   `X-RateLimit-Remaining`，避免整天都处于限流状态。

## 复现

```bash
export OPENROUTER_API_KEY=你的Key

# 小批量
python scripts/run_free_route_experiment.py --repeats 1 --concurrency 2 --timeout 15

# 大批量（注意会消耗免费路由配额）
python scripts/run_free_route_experiment.py --repeats 3 --concurrency 3 --timeout 15
```

## DeepSeek flash 对照批次

OpenRouter 免费额度耗尽后，改用显式 provider：

```bash
POEM_PROVIDER=deepseek DEEPSEEK_API_KEY=xxx DEEPSEEK_THINKING=disabled \
python scripts/run_free_route_experiment.py --repeats 2 --concurrency 3 --timeout 20
```

模型固定为 `deepseek-flash`，`thinking.type=disabled`，因此 usage 中不再出现
reasoning tokens。两个对照批次（各 72 次，同一 topic 矩阵）：

| 指标 | 增强本地修补前 | 增强本地修补后 |
| --- | --- | --- |
| 模型直接采用 | 63 / 72（87.5%） | 70 / 72（97.2%） |
| 走兜底 | 9 | 2 |
| 解析成功率 | 100% | 100% |
| 本地修补触发率 | 41.7% | 54.2% |
| 端到端 p50 | 1.01s | 1.58s |
| 端到端 p90 | 1.48s | 2.50s |
| 平均 Token | 214.3 | 214.5 |
| 命中模型 | 全部 deepseek-flash | 全部 deepseek-flash |

观察：

1. DeepSeek flash 的可用性显著高于免费路由，两批均无 429/超时；
2. 关闭思考后单次约 200 Token、约 1–2.5s，适合批量实验；
3. 剩余兜底主要来自少数结构/韵脚无法本地修复的输出；
4. 提交验收仍默认 `POEM_PROVIDER=openrouter`（不设该变量即默认），
   DeepSeek 只在显式指定时启用。
