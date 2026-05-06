# SwitchBasicTool 库使用文档（独立版）

本文仅面向“作为 Python 库调用”，不涉及 CLI 参数说明。

## 一、对象关系（先看这个）

调用链是：

`ConnectionConfig` -> `NetworkDeviceClient` -> `get_operations(client)`（可选）

- `ConnectionConfig`：连接参数数据对象。
- `NetworkDeviceClient`：负责建立连接、收发命令、返回结果。
- `operations`：在已有 `client` 之上封装厂商预定义命令（华为/H3C/Cisco/Aruba/ZTE）。

## 二、通用准备

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient
```

最小配置示例：

```python
config = ConnectionConfig(
    host="192.168.1.10",
    protocol="ssh",      # "ssh" 或 "telnet"
    username="admin",
    password="your-password",
    vendor="huawei",     # 可用别名：cisco/ios, h3c/comware, aruba/aoscx, zte/zxr10 等
    timeout=10.0,
)
```

返回值类型为 `CommandResult`，常用字段：

- `result.command`：实际发送的命令
- `result.output`：清洗后的输出（推荐使用）
- `result.raw_output`：设备原始输出
- `result.duration`：执行耗时（秒）

## 三、场景 1：直接连接交换机，执行单次命令并返回结果

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

def run_once() -> str:
    config = ConnectionConfig(
        host="192.168.1.10",
        protocol="ssh",
        username="admin",
        password="your-password",
        vendor="huawei",
    )

    with NetworkDeviceClient(config) as client:
        result = client.send_command("display version")
        return result.output

print(run_once())
```

说明：

- `with` 会自动 `connect()` 和 `disconnect()`。
- 只执行一次命令时，推荐这种写法，最不容易漏关连接。

## 四、场景 2：连接交换机后，多次发送命令并返回结果

方式 A：手动连接/断开

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

config = ConnectionConfig(
    host="192.168.1.10",
    protocol="ssh",
    username="admin",
    password="your-password",
    vendor="cisco",
)

client = NetworkDeviceClient(config)
client.connect()
try:
    commands = [
        "show version",
        "show ip interface brief",
        "show running-config | include hostname",
    ]

    for cmd in commands:
        result = client.send_command(cmd)
        print(f"\n>>> {cmd}\n{result.output}")
finally:
    client.disconnect()
```

方式 B：批量发送

```python
with NetworkDeviceClient(config) as client:
    results = client.send_commands(
        ["show version", "show ip interface brief"],
        timeout=8.0,
    )
    for r in results:
        print(r.command, r.output)
```

## 五、场景 3：连接交换机并使用预定义厂商函数

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient, get_operations

config = ConnectionConfig(
    host="192.168.1.10",
    protocol="ssh",
    username="admin",
    password="your-password",
    vendor="huawei",  # 也可写 vrp / hw
)

with NetworkDeviceClient(config) as client:
    ops = get_operations(client)  # 自动映射到对应厂商 Operations 类

    print("支持的方法：", ops.supported_operations())

    print(ops.get_version().output)
    print(ops.get_hostname().output)
    print(ops.get_vlan_summary().output)
    print(ops.get_port_config("GigabitEthernet0/0/1").output)
```

常用预定义方法（按设备支持情况启用）：

- `get_version()`
- `get_hostname()`
- `get_interface_brief()`
- `get_ip_interface_brief()`
- `get_vlan_summary()`
- `get_mac_table()`
- `get_arp_table()`
- `get_lldp_neighbors()`
- `get_running_config()`
- `get_current_config_snippet(keyword)`
- `get_port_config(interface_name)`

建议先调用 `ops.supported_operations()`，再按返回列表选择方法，避免调用未支持操作。

## 六、异常处理建议

```python
from switchbasictool import (
    ConnectionConfig,
    NetworkDeviceClient,
    get_operations,
    SwitchBasicToolError,
    OperationNotSupportedError,
)

config = ConnectionConfig(
    host="192.168.1.10",
    username="admin",
    password="your-password",
    vendor="zte",
)

try:
    with NetworkDeviceClient(config) as client:
        ops = get_operations(client)
        print(ops.get_version().output)
except OperationNotSupportedError as exc:
    print(f"操作不支持: {exc}")
except (SwitchBasicToolError, OSError, ValueError) as exc:
    print(f"连接或执行失败: {exc}")
```

## 七、厂商名称与别名（常用）

- `huawei`: `vrp`, `huawei_vrp`, `hw`
- `h3c`: `comware`, `h3c_comware`
- `cisco_ios`: `cisco`, `ios`
- `aruba_aoscx`: `aruba`, `aruba_cx`, `aoscx`, `hpe_aruba`, `hp_aruba`
- `zte`: `zxr10`, `zte_zxr10`, `8900e`

如果 `vendor` 无法识别，会在 profile 解析阶段抛出 `VendorProfileNotFoundError`。
