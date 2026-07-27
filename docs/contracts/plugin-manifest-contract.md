# Plugin Manifest Contract — 插件清单契约

> **Depends on**: `adapter-spi.md`, `judge-spi.md`, `domain-model.md`  
> **Referenced by**: `../phases/phase-7-plugin.md`  
> **ADR**: `../decisions/0003-plugin-concept-frontload.md`

## 1. 定位

定义 AgentEval 外部插件的清单文件格式。本契约是 Plugin Loader 发现、校验、加载插件的依据。Phase 1 内置实现不使用清单文件（通过 `Registry.register()` 静态注册），本契约仅适用于 Phase 7 管理的外部插件。

### Schema 优先原则

> **Manifest 以 JSON Schema 为主定义，YAML / JSON / 数据库存储 / HTTP API 均为同一 Schema 的合法实例。**
>
> 新增字段时，先修改 JSON Schema，再更新 YAML 示例。Loader 直接使用 JSON Schema 校验，不依赖 YAML 解析逻辑。

## 2. 文件规范

- **文件名**: `plugin.yaml`（MUST）
- **位置**: 插件包根目录
- **格式**: YAML 1.2 或 JSON（两者均为合法实例）
- **编码**: UTF-8
- **校验**: Loader 使用 §3.1 的 JSON Schema 校验，不依赖文件格式

## 3. Manifest Schema

### 3.1 JSON Schema (主定义)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PluginManifest",
  "type": "object",
  "required": ["api_version", "metadata", "type", "entry_point"],
  "additionalProperties": false,
  "properties": {
    "api_version": {
      "type": "string",
      "enum": ["1.0"],
      "description": "Manifest Schema 版本"
    },
    "metadata": {
      "$ref": "#/$defs/Metadata"
    },
    "type": {
      "enum": ["adapter", "judge", "dataset", "metrics", "report"],
      "description": "插件类型，对应各 SPI"
    },
    "entry_point": {
      "type": "string",
      "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$",
      "description": "Python 入口点 {module}:{class}"
    },
    "capabilities": {
      "$ref": "#/$defs/Capabilities",
      "description": "引用各 SPI 的 Capability 定义，不重复维护"
    },
    "config_schema": {
      "type": "object",
      "description": "JSON Schema Draft 2020-12 子集，定义插件配置项"
    },
    "dependencies": {
      "type": "array",
      "items": { "$ref": "#/$defs/Dependency" }
    },
    "permissions": { "$ref": "#/$defs/Permissions" },
    "lifecycle": { "$ref": "#/$defs/Lifecycle" },
    "compatibility": { "$ref": "#/$defs/Compatibility" }
  },
  "$defs": {
    "Metadata": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": { "type": "string", "pattern": "^[a-z0-9-]+$", "minLength": 1, "maxLength": 64 },
        "display_name": { "type": "string", "maxLength": 128 },
        "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
        "description": { "type": "string", "maxLength": 512 },
        "author": { "type": "string" },
        "homepage": { "type": "string", "format": "uri" },
        "license": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } }
      }
    },
    "Capabilities": {
      "type": "object",
      "description": "引用各 SPI 已定义的 Capability，不在 Manifest 中重复定义",
      "properties": {
        "adapter": {
          "type": "object",
          "description": "引用 adapter-spi.md 的 AgentAdapter.capabilities (set[str])",
          "properties": {
            "capabilities": {
              "type": "array",
              "items": { "type": "string" },
              "description": "复用 adapter-spi.md 定义的标识: stateful, tools, streaming, vision, audio, mcp"
            }
          }
        },
        "judge": {
          "type": "object",
          "description": "引用 judge-spi.md 的 Judge.supported_metrics + judge_type",
          "properties": {
            "supported_metrics": { "type": "array", "items": { "type": "string" } },
            "judge_type": { "enum": ["rule", "llm", "embedding"] }
          }
        },
        "metrics": {
          "type": "object",
          "properties": {
            "metric_names": { "type": "array", "items": { "type": "string" } }
          }
        },
        "report": {
          "type": "object",
          "properties": {
            "formats": { "type": "array", "items": { "enum": ["html", "json"] } },
            "template_file": { "type": "string" }
          }
        },
        "dataset": {
          "type": "object",
          "properties": {
            "formats": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    },
    "Dependency": {
      "type": "object",
      "required": ["package"],
      "properties": {
        "package": { "type": "string", "description": "PyPI 包名" },
        "version": { "type": "string", "description": "PEP 440 版本约束" },
        "optional": { "type": "boolean", "default": false }
      }
    },
    "Permissions": {
      "type": "object",
      "properties": {
        "network": { "type": "boolean", "default": false },
        "filesystem": {
          "type": "object",
          "properties": {
            "read": { "type": "array", "items": { "type": "string" } },
            "write": { "type": "array", "items": { "type": "string" } }
          }
        },
        "env_vars": { "type": "array", "items": { "type": "string" } },
        "subprocess": { "type": "boolean", "default": false }
      }
    },
    "Lifecycle": {
      "type": "object",
      "properties": {
        "on_load": { "type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$" },
        "on_unload": { "type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$" }
      }
    },
    "Compatibility": {
      "type": "object",
      "properties": {
        "agenteval_version": { "type": "string" },
        "python_version": { "type": "string" }
      }
    }
  }
}
```

### 3.2 YAML 实例（示例）

> 以下 YAML 是上述 JSON Schema 的一个合法实例。Loader 不特殊对待 YAML——解析后转换为 dict，再由 JSON Schema 校验。

```yaml
# plugin.yaml — Plugin Manifest (合法实例)
api_version: "1.0"

metadata:
  name: "my-custom-judge"
  display_name: "My Custom Judge"
  version: "1.2.0"
  description: "A custom LLM-based judge for domain-specific evaluation"
  author: "zhangsan"
  homepage: "https://github.com/example/my-custom-judge"
  license: "MIT"
  tags: ["judge", "llm", "domain-specific"]

type: "judge"
entry_point: "my_custom_judge:MyCustomJudge"

capabilities:
  judge:
    supported_metrics: ["domain_accuracy", "compliance_score"]
    judge_type: "llm"

config_schema:
  type: "object"
  properties:
    api_key_ref:
      type: "string"
      description: "API Key reference (vault://...)"
      required: true
    model:
      type: "string"
      default: "gpt-4o"
    temperature:
      type: "number"
      default: 0.0
      minimum: 0.0
      maximum: 2.0
  required: ["api_key_ref"]

dependencies:
  - package: "openai"
    version: ">=1.0,<2.0"
  - package: "numpy"
    version: ">=1.24"

permissions:
  network: true
  filesystem:
    read: ["/tmp/agenteval/"]
    write: ["/tmp/agenteval/"]
  env_vars:
    - "OPENAI_API_KEY"
    - "AGENTEVAL_*"

lifecycle:
  on_load: "my_custom_judge:on_load"
  on_unload: "my_custom_judge:on_unload"

compatibility:
  agenteval_version: ">=0.1.0"
  python_version: ">=3.11"
```

### 3.3 字段定义

#### 顶层字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| api_version | str | MUST, `"1.0"` | Manifest Schema 版本 |
| metadata | Metadata | MUST | 插件元数据 |
| type | PluginType | MUST | 插件类型 |
| entry_point | str | MUST | Python 入口点 `{module}:{class}` |
| capabilities | dict | SHOULD | 插件能力声明 |
| config_schema | JSONSchema | SHOULD | 配置项 Schema |
| dependencies | list[Dependency] | SHOULD | Python 依赖声明 |
| permissions | Permissions | SHOULD | 运行时权限声明 |
| lifecycle | Lifecycle | MAY | 生命周期钩子 |
| compatibility | Compatibility | SHOULD | 兼容性声明 |

#### Metadata

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| name | str | MUST, `^[a-z0-9-]+$`, 1-64字符 | 插件唯一标识，全局唯一 |
| display_name | str | SHOULD, 1-128字符 | 展示名称 |
| version | str | MUST, 语义化版本 `^\d+\.\d+\.\d+$` | 插件版本 |
| description | str | SHOULD, max 512 | 描述 |
| author | str | SHOULD | 作者 |
| homepage | str | MAY | 主页 URL |
| license | str | MAY | 许可证 |
| tags | list[str] | 默认 [] | 分类标签 |

#### PluginType (enum)

| 值 | 对应 SPI | 说明 |
|----|----------|------|
| `adapter` | AgentAdapter | Agent 适配器插件 |
| `judge` | Judge | 评分器插件 |
| `dataset` | DSLParser | 数据集导入插件 |
| `metrics` | DerivedMetricProvider | 衍生指标插件 |
| `report` | ReportTemplate | 报告模板插件 |

#### entry_point 格式

```
{module_path}:{class_or_function_name}
```

示例:
- `my_judge:MyCustomJudge` — 从 `my_judge` 模块导入 `MyCustomJudge` 类
- `my_pkg.adapters:HTTPAdapter` — 从 `my_pkg.adapters` 模块导入 `HTTPAdapter` 类

Loader 使用 `importlib.import_module(module)` + `getattr(module, name)` 解析。

#### Capabilities（引用各 SPI，不重复定义）

> **原则**：Plugin Manifest 的 capabilities **引用**各 SPI 已定义的 Capability 集合，不在 Manifest 中维护另一套定义。各 SPI 的 Capability 变更自动反映到 Manifest 校验中。

根据 `type` 不同，capabilities 引用不同的 SPI：

| type | 引用 SPI | 引用字段 | 说明 |
|------|----------|----------|------|
| `adapter` | `adapter-spi.md` | `AgentAdapter.capabilities` (`set[str]`) | 复用已定义标识: `stateful`, `tools`, `streaming`, `vision`, `audio`, `mcp` |
| `judge` | `judge-spi.md` | `Judge.supported_metrics` + `judge_type` | 复用 Judge SPI 的指标和类型枚举 |
| `metrics` | `phase-5-report.md` | `DerivedMetricProvider.name()` | 复用 Provider 注册的 metric name |
| `report` | `phase-5-report.md` | `ReportTemplate.formats` | 复用报告格式枚举 |
| `dataset` | `scenario-dsl.md` | `DSLParser.formats` | 复用 DSL 格式枚举 |

**YAML 示例（adapter 类型，引用 adapter-spi.md 的 capabilities）**:
```yaml
capabilities:
  adapter:
    capabilities: ["tools", "streaming"]  # 引用 adapter-spi.md §Capability 模型
```

**YAML 示例（judge 类型，引用 judge-spi.md 的 supported_metrics）**:
```yaml
capabilities:
  judge:
    supported_metrics: ["domain_accuracy", "compliance_score"]
    judge_type: "llm"  # 引用 judge-spi.md §JudgeType 枚举
```

#### ConfigSchema

使用 JSON Schema Draft 2020-12 子集：

```yaml
config_schema:
  type: "object"
  properties:
    {field_name}:
      type: "string" | "number" | "boolean" | "array" | "object"
      default: {default_value}
      description: "{description}"
      required: true | false
      minimum: {number}      # number 类型
      maximum: {number}      # number 类型
      enum: [...]            # 枚举值
      pattern: "{regex}"     # string 类型
  required: ["{required_field_names}"]
```

Loader 在加载插件时使用 ConfigSchema 校验用户配置，不符合则拒绝加载。

#### Dependency

```yaml
dependencies:
  - package: "openai"           # MUST, PyPI 包名
    version: ">=1.0,<2.0"       # SHOULD, PEP 440 版本约束
    optional: false              # MAY, 默认 false
```

Loader **SHOULD** 在加载前检查依赖是否已安装；缺失可选依赖时记录警告但不阻止加载。

#### Permissions

```yaml
permissions:
  network: true                  # MUST 声明, 默认 false
  filesystem:
    read: ["/tmp/agenteval/"]    # 允许读取的目录
    write: ["/tmp/agenteval/"]   # 允许写入的目录
  env_vars:                      # 允许访问的环境变量名 (支持通配符)
    - "OPENAI_API_KEY"
    - "AGENTEVAL_*"
  subprocess: false              # 是否允许子进程, 默认 false
```

> **安全沙箱 (MAY)**: MVP 阶段 permissions 仅声明不强制执行。安全沙箱实现后，Loader 将根据 permissions 限制插件运行时行为。

#### Lifecycle

```yaml
lifecycle:
  on_load: "my_plugin:on_load"       # 插件加载时调用 (可选)
  on_unload: "my_plugin:on_unload"   # 插件卸载时调用 (可选)
```

钩子函数签名：
```python
def on_load(config: dict) -> None: ...
def on_unload() -> None: ...
```

#### Compatibility

```yaml
compatibility:
  agenteval_version: ">=0.1.0"   # AgentEval 版本约束
  python_version: ">=3.11"       # Python 版本约束
```

## 4. 插件包结构

```
my-custom-judge/
├── plugin.yaml              # MUST — 清单文件
├── my_custom_judge/
│   ├── __init__.py          # MUST — Python 包
│   ├── judge.py             # Judge 实现
│   └── prompts/
│       └── default.txt
├── tests/
│   └── test_judge.py
├── README.md                # SHOULD
├── LICENSE                  # SHOULD
└── pyproject.toml           # SHOULD — 如果有独立依赖管理
```

## 5. 加载流程

```
1. Discovery: 扫描插件目录，查找 plugin.yaml
2. Parse: 解析 YAML，校验 api_version 和必填字段
3. Validate:
   a. 检查 compatibility (agenteval_version, python_version)
   b. 检查 dependencies 是否已安装
   c. 检查 config_schema 校验用户配置
   d. 检查 entry_point 可解析
4. Import: importlib 加载 entry_point
5. Register: 将插件实例注册到对应 Registry
6. Lifecycle: 调用 on_load(config) (如果声明)
7. Ready: 插件可用
```

加载失败时，Loader 记录错误日志，不阻止其他插件加载。

## 6. 版本管理

### 6.1 插件版本

- 遵循语义化版本 (SemVer)
- 同 name 不同 version 可共存
- 启用时指定版本，未指定则使用最新

### 6.2 Manifest api_version

| api_version | 变更类型 | 说明 |
|-------------|----------|------|
| 1.0 | 初始版本 | 当前版本 |

api_version 变更规则：
- **不兼容变更**（字段重命名、类型变更、必填字段新增）→ 主版本号 +1
- **兼容新增**（新增可选字段）→ 不变
- Loader 检查 api_version，不兼容则拒绝加载

## 7. MUST / SHOULD / MAY 规范

| 规范级别 | 要求 |
|----------|------|
| **MUST** | plugin.yaml 存在、api_version、metadata.name/version、type、entry_point |
| **SHOULD** | metadata.display_name/description、capabilities、config_schema、dependencies、compatibility |
| **MAY** | permissions 强制执行、lifecycle 钩子、homepage/license |

## 8. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|----------|
| AC-PMF-01 | 合法 plugin.yaml 可被 Loader 解析 | 单元测试 |
| AC-PMF-02 | 缺少必填字段的 plugin.yaml 被拒绝 | 单元测试 |
| AC-PMF-03 | entry_point 格式错误时返回明确错误 | 单元测试 |
| AC-PMF-04 | config_schema 校验用户配置，不合法则拒绝加载 | 集成测试 |
| AC-PMF-05 | 同 name 不同 version 可共存且可指定版本启用 | 集成测试 |
| AC-PMF-06 | compatibility.agenteval_version 不匹配时拒绝加载 | 单元测试 |
| AC-PMF-07 | on_load 钩子在插件注册后调用 | 集成测试 |
| AC-PMF-08 | 一个插件加载失败不影响其他插件 | 集成测试 |
| AC-PMF-09 | permissions.network=false 的插件不可发起网络请求 (MAY, 待沙箱实现) | 集成测试 |
