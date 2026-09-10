# 五言古诗生成系统

基于「初面-实战题」实现的一个可运行的**五言古诗生成系统**：

输入任意 `topic`（例如 `月色`），系统返回一首四句五言古诗，并且无论模型
输出或 API 状态如何，最终结果都 100% 满足格式、字数与韵脚要求。

## 当前状态

- M0–M3 已实现：校验器、韵脚判定、主题规范化、确定性兜底、
  一次模型调用 + 本地修补 + 兜底收口；
- M4 已用真实 `openrouter/free` 冒烟通过；
- 实施计划见 [PLAN.md](PLAN.md)（评审修订版）。

## 设计原则

- 大语言模型仅作为受控生成组件，输出不被直接信任。
- 系统自行完成结果解析、格式检查、韵脚检查、失败恢复与最终输出保证。
- 实验与测试统一使用 OpenRouter 免费模型 `openrouter/free`。
- 无 API Key、`POEM_OFFLINE=1` 或客户端异常时，静默走本地确定性兜底。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # 运行依赖
pip install -r requirements-dev.txt      # 测试依赖（可选）
export OPENROUTER_API_KEY=你的Key
```

> macOS 上使用 python.org 安装的 Python 若报
> `SSL: CERTIFICATE_VERIFY_FAILED`，`certifi` 已在 requirements 中，
> 重新 `pip install -r requirements.txt` 即可。

## 使用

```bash
# 单条
python -m poem_system.cli 月色

# 多条
python -m poem_system.cli --topics 月色 "Mars Return" "2026年的第一场雪"

# 强制离线（不打 API，走确定性兜底）
python -m poem_system.cli --offline 月色

# 打印来源、调用次数、耗时与校验细节
python -m poem_system.cli --verbose 月色

# 或直接 import（保持题目给的接口）
python -c "from poem_system import generate_poem; print(generate_poem('月色'))"
```

CLI 会把返回 JSON 打印到 stdout，并在本地再校验一次：
退出码 0 表示合规，1 表示不合规（正常不应发生）。

## 测试

```bash
python -m pytest -q                      # 单元 + 假客户端 + 离线 fuzz，默认不联网
OPENROUTER_API_KEY=xxx python -m pytest -m network -q   # 真实免费路由冒烟
```

## 免费路由批量采样

```bash
OPENROUTER_API_KEY=xxx python scripts/run_free_route_experiment.py \
    --repeats 3 --concurrency 3 --timeout 15
```

输出在 `artifacts/experiments/free_route_<timestamp>/`：
`runs.jsonl`（每次运行）、`summary.json`、`summary.md`。
常用 topic、英文/数字/emoji/超长文本等 edge case 都在固定矩阵内。

已积累的失败模式与结论见
[experiments/FREE_ROUTE_FINDINGS.md](experiments/FREE_ROUTE_FINDINGS.md)。
注意 OpenRouter 免费档每天约 50 次免费模型请求，额度用完后返回 HTTP 429，
次日 08:00（北京时间）重置；此时系统会自动走本地兜底。

环境变量：

- `OPENROUTER_API_KEY`：真实模型调用；
- `POEM_OFFLINE=1`：即使有 Key 也强制兜底；
- `POEM_DEBUG=1`：把运行记录写入 `artifacts/runs/`（默认静默）。
