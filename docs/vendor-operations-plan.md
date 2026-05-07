# 厂商常用指令函数集扩展方案

## 1. 背景

当前 `SwitchBasicTool` 已经具备比较清晰的底座分层：

- `transports/`
  - 负责 SSH / Telnet 协议差异
- `NetworkDeviceClient`
  - 负责建立连接、发送命令、等待提示符、处理分页
- `VendorProfile`
  - 负责厂商 CLI 的默认行为差异，例如提示符、分页关键字、会话初始化命令

这套结构已经适合继续向上扩展“厂商常用指令函数集”。  
建议新增一层“操作层”或“厂商驱动层”，专门承载各厂商常用命令函数，而不是把这些能力继续堆进 `VendorProfile` 或 `NetworkDeviceClient`。

## 2. 目标

- 在现有底座之上补一层统一的厂商常用操作封装。
- 对外暴露“语义化”的函数，而不是让调用方直接拼原始 CLI 字符串。
- 允许同一个语义操作在不同厂商下映射为不同命令。
- 优先支持高频只读查询类能力，再逐步扩展结构化解析与配置类动作。
- 保持现有 `NetworkDeviceClient` 的职责稳定，不让底座和业务命令耦合。

## 3. 非目标

以下内容不建议作为第一阶段目标：

- 把所有厂商命令直接塞进 `VendorProfile`
- 一开始就用 YAML / JSON 完全配置化描述所有操作
- 一开始就覆盖大量配置变更能力
- 一开始就追求所有命令都输出统一结构化结果

原因如下：命令函数通常包含参数校验、命令拼装、返回解析和异常处理，完全配置化方案往往难以长期满足需求；配置类操作还会引入配置模式切换、保存配置、失败回滚等更复杂的问题，适合后续独立推进。

## 4. 推荐分层

推荐把整个项目分为四层：

1. 传输层
   `SSHTransport` / `TelnetTransport`
2. 会话层
   `NetworkDeviceClient`
3. 操作层
   厂商常用指令函数集，例如 `get_version()`、`get_interface_brief()`
4. 解析层
   把高频命令输出逐步转换成结构化数据模型

职责建议如下：

- 传输层：只关心读写和连接状态
- 会话层：只关心“如何稳定发命令并拿到输出”
- 操作层：只关心“某个业务语义在某厂商设备上对应哪些命令”
- 解析层：只关心“如何把文本回显整理成结构化结果”

## 5. 为什么不要把命令函数放进 `VendorProfile`

`VendorProfile` 当前设计得很纯粹，适合保存这类静态默认值：

- `prompt_pattern`
- `more_patterns`
- `username_prompt_pattern`
- `password_prompt_pattern`
- `session_init_commands`

如果把大量操作函数也放进去，会带来几个问题：

- `VendorProfile` 会从“静态厂商特征”变成“厂商行为总入口”，职责变重
- 很多操作函数需要参数校验和命令拼接，不再是静态配置
- 后续如果需要结构化解析，会把 profile 和 parser 混在一起
- 测试粒度会变差，不利于单独验证“某厂商某操作”的行为

因此更合适的做法是：`VendorProfile` 继续只描述 CLI 特征，新增 `operations` 子包专门负责命令函数。

## 6. 推荐目录结构

建议新增如下目录：

```text
switchbasictool/
├── operations/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── models.py
│   ├── huawei.py
│   ├── h3c.py
│   ├── cisco_ios.py
│   ├── arista_eos.py
│   ├── juniper.py
│   └── zte.py
```

职责建议如下：

- `base.py`
  - 定义操作层基类
- `registry.py`
  - 根据 `client.vendor_profile.name` 返回对应厂商的操作类
- `models.py`
  - 存放结构化结果 dataclass
- `huawei.py` / `h3c.py` / `zte.py` 等
  - 各厂商的常用命令实现

## 7. 第一阶段实现方式

第一阶段建议采用“厂商类 + 工厂函数”的轻量方案，避免过度设计。

### 7.1 基类

```python
from switchbasictool import CommandResult, NetworkDeviceClient


class BaseOperations:
    def __init__(self, client: NetworkDeviceClient) -> None:
        self.client = client

    def _run(self, command: str, timeout: float | None = None) -> CommandResult:
        return self.client.send_command(command, timeout=timeout)
```

### 7.2 厂商实现

```python
class HuaweiOperations(BaseOperations):
    def get_version(self) -> CommandResult:
        return self._run("display version")

    def get_hostname(self) -> CommandResult:
        return self._run("display current-configuration | include sysname")

    def get_interface_brief(self) -> CommandResult:
        return self._run("display interface brief")
```

```python
class ZTEOperations(BaseOperations):
    def get_version(self) -> CommandResult:
        return self._run("show version")

    def get_hostname(self) -> CommandResult:
        return self._run("show running-config | include hostname")
```

### 7.3 工厂函数

```python
def get_operations(client: NetworkDeviceClient) -> BaseOperations:
    name = client.vendor_profile.name

    if name == "huawei":
        return HuaweiOperations(client)
    if name == "h3c":
        return H3COperations(client)
    if name == "cisco_ios":
        return CiscoIOSOperations(client)
    if name == "zte":
        return ZTEOperations(client)

    return BaseOperations(client)
```

这种方式的优点是：

- 易于起步
- 易于阅读
- 易于测试
- 不会过早引入复杂抽象

## 8. 接口设计建议

### 8.1 按“语义”命名，而不是按命令命名

推荐：

- `get_version()`
- `get_hostname()`
- `get_interface_brief()`
- `get_vlan_summary()`
- `get_mac_table()`
- `get_arp_table()`
- `get_lldp_neighbors()`

不推荐：

- `display_version()`
- `show_version()`
- `run_display_interface_brief()`

原因是操作层应屏蔽厂商 CLI 差异，让调用方关注“需要获取的信息”，而非“具体厂商命令形式”。

### 8.2 第一阶段优先返回 `CommandResult`

建议第一阶段先返回现有的 `CommandResult`，例如：

```python
ops = get_operations(client)
result = ops.get_version()
print(result.output)
```

这样有两个好处：

- 几乎不需要额外改底座
- 在结构化解析尚未稳定前，保留原始输出更灵活

### 8.3 第二阶段逐步补结构化接口

当高频命令已经收集到足够多真实输出样本后，再新增结构化方法，例如：

```python
version = ops.get_version_info()
interfaces = ops.get_interface_brief_items()
```

对应的数据模型可以放在 `operations/models.py` 里，例如：

```python
from dataclasses import dataclass


@dataclass(slots=True)
class VersionInfo:
    vendor: str
    model: str | None
    version: str | None
    raw_text: str
```

## 9. 常用能力优先级

建议按下面顺序推进：

### 9.1 第一批：高频只读查询

- `get_version()`
- `get_hostname()`
- `get_interface_brief()`
- `get_vlan_summary()`
- `get_mac_table()`
- `get_arp_table()`
- `get_lldp_neighbors()`

### 9.2 第二批：常见配置查询

- `get_running_config()`
- `get_current_config_snippet(keyword)`
- `get_port_config(interface_name)`

### 9.3 第三批：配置类动作

- `create_vlan(vlan_id, name=None)`
- `delete_vlan(vlan_id)`
- `set_interface_description(interface_name, description)`
- `set_interface_access_vlan(interface_name, vlan_id)`
- `save_config()`

配置类动作建议单独推进，因为这一步会牵涉：

- 进入配置模式
- 退出配置模式
- 保存配置命令差异
- 配置失败时的错误处理
- 是否要做幂等检查

## 10. 命令分组建议

为便于后续维护，建议按领域组织命令函数，而不是单纯按文件长度堆积：

- 基础信息
  - 版本、主机名、设备型号
- 二层
  - VLAN、MAC、LLDP
- 三层
  - 接口 IP、ARP、路由
- 配置
  - 查询配置、修改配置、保存配置

如果单个厂商文件后续变大，可以继续拆分，例如：

```text
switchbasictool/operations/huawei/
├── __init__.py
├── base.py
├── facts.py
├── layer2.py
├── layer3.py
└── config.py
```

第一阶段无需拆分过细，待命令函数达到一定数量后再拆分更合理。

## 11. 兼容当前项目的实现原则

为了尽量不破坏现有设计，建议遵守下面几条：

- `NetworkDeviceClient` 不直接内置大量厂商专属方法
- `VendorProfile` 不承载业务命令函数
- `operations` 层只依赖 `NetworkDeviceClient` 的公开接口
- 操作层优先复用 `send_command()`，不自己重复实现读写逻辑
- 如果个别操作需要特殊超时，可以在操作层局部覆盖 `timeout`

## 12. 第二阶段可升级为注册表模式

当厂商和命令函数继续变多后，可以从“厂商类 + 工厂函数”逐步升级到“操作注册表”模式。

例如：

```python
from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class OperationSpec:
    name: str
    command_builder: Callable[..., str]
    read_only: bool = True
```

然后每个厂商注册自己支持的操作名与命令构建器。  
但不建议当前阶段立即实施，因为项目体量仍较小，过早抽象可能导致代码复杂度超过收益。

## 13. 测试建议

建议测试分三层：

### 13.1 单元测试

使用假的 `NetworkDeviceClient` 或 stub，验证：

- 各厂商操作函数发出的命令是否正确
- 参数校验是否生效
- 结构化解析是否符合预期

### 13.2 样本输出测试

收集各厂商真实设备回显样本，放到 `tests/fixtures/` 或 `examples/outputs/` 中，专门验证 parser。

### 13.3 人工联调

继续复用当前 `manual_test.py` 的联调方式，在真实设备上跑常用命令，确认：

- 提示符识别是否稳定
- 分页关闭命令是否生效
- 高层操作函数映射是否正确

## 14. 推荐实施顺序

建议按以下节奏推进：

1. 新增 `operations` 子包和基础骨架
2. 先支持 `huawei`、`h3c`、`zte` 三个当前更贴近现有示例的厂商
3. 每个厂商先落 5 到 8 个高频只读函数
4. 对高频命令逐步补 parser 和 dataclass
5. 最后再评估是否要扩展到配置类动作

## 15. 一个可接受的 v1 目标

如果要控制范围，推荐把 v1 目标收敛为下面这些内容：

- 新增 `operations` 目录
- 提供 `get_operations(client)` 工厂
- 支持 `huawei` / `h3c` / `zte`
- 每个厂商实现：
  - `get_version()`
  - `get_hostname()`
  - `get_interface_brief()`
  - `get_vlan_summary()`
- 返回值统一先用 `CommandResult`

该方案具备较高的投入产出比，并且更易于快速落地。

## 16. 总结

这项扩展很适合建立在当前代码之上推进，关键是继续守住现有分层边界：

- `VendorProfile` 负责静态 CLI 特征
- `NetworkDeviceClient` 负责稳定会话
- `operations` 负责厂商常用指令函数集
- `parsers / models` 负责结构化结果

推荐先用“轻量厂商类 + 工厂函数”的方式启动，先做高频只读查询，再逐步补结构化和配置类动作。  
这样既不会打乱现在的底座，也能给后续 Huawei / H3C / ZTE / Cisco / Juniper / Arista 的扩展留出清晰演进路径。
