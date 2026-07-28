# Design Tokens — 设计令牌契约

> **Depends on**: `../architecture/design-principles.md`
> **Referenced by**: 所有 `phases/*.md`（UI 实现）

## 1. 实现方式

令牌分两类，均定义在 `src/theme/tokens.ts`（唯一定义点）：

1. **antd 标准 token**（§2.1、§3、§4）：通过 `ConfigProvider theme.token` 注入，antd 组件自动生效
2. **业务语义色（§2.2）**：antd token 不支持自定义键名，以 `export const bizTokens = {...}` 常量导出，业务组件/ECharts 配置从这里 import（仍禁止就地硬编码色值）

业务组件取色优先级：antd `theme.useToken()` > `bizTokens` > 禁止其他来源。

## 2. 色彩

### 2.1 品牌色

| Token | 值 | 用途 |
|-------|-----|------|
| colorPrimary | `#2F54EB` | 主操作、链接、选中态（深蓝，中后台工具感） |
| colorSuccess | `#52C41A` | pass / completed / improved |
| colorWarning | `#FAAD14` | partial / cancelled / unchanged |
| colorError | `#F5222D` | fail / failed / regressed |
| colorInfo | `#1677FF` | running / processing |

### 2.2 语义色（业务专属，bizTokens 常量导出，非 antd token）

| Token | 值 | 用途 |
|-------|-----|------|
| colorFlaky | `#722ED1` | flaky 场景标记（紫） |
| colorScoreHigh | `#52C41A` | score ≥ 0.8 |
| colorScoreMid | `#FAAD14` | 0.5 ≤ score < 0.8 |
| colorScoreLow | `#F5222D` | score < 0.5 |
| colorTraceLLM | `#1677FF` | Trace 时间线 llm_call span |
| colorTraceTool | `#13C2C2` | tool_call span |
| colorTraceOther | `#8C8C8C` | 其他 span |

## 3. 字体

| Token | 值 |
|-------|-----|
| fontFamily | `-apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif` |
| fontFamilyCode | `'SF Mono', Menlo, Consolas, monospace`（对话内容/DSL/JSON 展示） |
| fontSize | 14（基准） |
| fontSizeHeading3 | 20（页面标题） |

## 4. 间距与圆角

| Token | 值 | 用途 |
|-------|-----|------|
| padding | 16 | 卡片内边距基准 |
| paddingLG | 24 | 页面容器边距 |
| borderRadius | 6 | 全局圆角 |
| borderRadiusLG | 8 | 卡片圆角 |

## 5. 布局尺寸

| Token | 值 |
|-------|-----|
| 侧边栏宽度 | 220px（折叠 64px） |
| 顶栏高度 | 56px |
| 内容区最大宽度 | 无限制（数据密集型工具，全宽） |
| 表格行高 | 默认（antd middle size） |

## 6. 暗色模式

MVP 不实现暗色模式。令牌体系已预留：切换 antd `theme.darkAlgorithm` 即可，业务代码不感知（这是禁止硬编码色值的原因）。
