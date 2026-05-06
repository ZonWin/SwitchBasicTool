# SwitchBasicTool

一个面向交换机自动化运维场景的 Python 基础库，目标是提供一套可复用、尽量不绑定单一厂商的 SSH / Telnet 会话能力。

当前已经具备这些基础能力：

- SSH / Telnet 远程连接
- 统一的发送命令与接收回显接口
- 基于厂商 profile 的默认提示符、分页和初始化命令
- 适合作为库文件被其他项目直接调用
- 自带一个命令行手工测试脚本，方便拿真实交换机联调

## 适用场景

这个库更适合做“连接层”和“会话层”基础能力，例如：

- 建立交换机 SSH / Telnet 连接
- 连续发送多条命令并获取返回
- 自动等待设备提示符
- 自动处理常见分页提示
- 作为更上层厂商封装的底座

当前版本还没有做这些更高层能力：

- 自动重连
- 连接池
- 按厂商解析结构化命令结果
- 配置变更事务控制

如果后面要扩展 Huawei / H3C / ZTE / Cisco 的专属操作类，建议继续复用现在这层底座。

## 安装

环境要求：

- Python `>= 3.12`

项目依赖：

- `paramiko>=3.4,<5`

在项目根目录执行：

```bash
cd /home/zonwin/projects/SwitchBasicTool
python3 -m pip install -e .
```

如果只想安装依赖，也可以：

```bash
python3 -m pip install paramiko
```

## 目录结构

```text
SwitchBasicTool/
├── manual_test.py
├── README.md
├── pyproject.toml
├── examples/
│   ├── h3c_commands.txt
│   ├── huawei_commands.txt
│   └── zte_commands.txt
└── switchbasictool/
    ├── __init__.py
    ├── __main__.py
    ├── client.py
    ├── exceptions.py
    ├── manual_test.py
    ├── models.py
    ├── vendors.py
    └── transports/
        ├── base.py
        ├── ssh.py
        └── telnet.py
```

## 核心设计

- `NetworkDeviceClient`
  - 对外统一客户端接口
- `SSHTransport` / `TelnetTransport`
  - 负责协议差异
- `ConnectionConfig`
  - 负责连接参数与行为配置
- `VendorProfile`
  - 负责厂商默认行为差异

这个设计的关键点是：厂商差异尽量放在 profile 里，不把核心收发逻辑写死成某一家设备的行为。

## 连接模型

当前实现不是“每发一条命令就新建一次连接”，而是“一个 `NetworkDeviceClient` 对象对应一条会话”。

典型流程是：

1. `connect()` 建立一次连接
2. 连续调用 `send_command()` / `send_commands()`
3. `disconnect()` 断开连接

也就是说，它支持长连接会话模式，适合你后面做批量运维或交互式操作。

## 作为库调用

### 最简单的单条命令示例

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

config = ConnectionConfig(
    host="10.10.10.10",
    protocol="ssh",
    username="admin",
    password="password",
    vendor="huawei",
)

with NetworkDeviceClient(config) as client:
    result = client.send_command("display version")
    print(result.output)
```

### 长连接连续执行多条命令

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

config = ConnectionConfig(
    host="10.10.10.10",
    protocol="ssh",
    username="admin",
    password="password",
    vendor="huawei",
    timeout=15.0,
)

client = NetworkDeviceClient(config)
client.connect()

try:
    print(client.send_command("display version").output)
    print(client.send_command("display interface brief").output)
    print(client.send_command("display current-configuration | include sysname").output)
finally:
    client.disconnect()
```

### 一次执行多条命令

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

config = ConnectionConfig(
    host="10.10.10.20",
    protocol="ssh",
    username="admin",
    password="password",
    vendor="h3c",
)

with NetworkDeviceClient(config) as client:
    results = client.send_commands(
        [
            "display version",
            "display interface brief",
            "display current-configuration | include sysname",
        ]
    )

    for item in results:
        print(f"command: {item.command}")
        print(item.output)
```

### Telnet 示例

```python
from switchbasictool import ConnectionConfig, NetworkDeviceClient

config = ConnectionConfig(
    host="10.10.10.30",
    protocol="telnet",
    username="admin",
    password="password",
    vendor="zte",
)

with NetworkDeviceClient(config) as client:
    print(client.send_command("show version").output)
```

## `ConnectionConfig` 常用参数

最常用的字段有：

- `host`
  - 设备 IP 或主机名
- `protocol`
  - `ssh` 或 `telnet`
- `port`
  - 自定义端口，不传则 SSH 默认 `22`，Telnet 默认 `23`
- `username` / `password`
  - 登录凭据
- `vendor`
  - 厂商名称或别名
- `timeout`
  - 单条命令等待提示符的超时时间
- `read_timeout`
  - 底层读 socket / channel 的超时
- `banner_timeout`
  - SSH banner 等待时间
- `auth_timeout`
  - SSH 认证阶段等待时间
- `prompt_pattern`
  - 自定义设备提示符正则
- `session_init_commands`
  - 自定义会话初始化命令
- `use_vendor_session_init`
  - 是否启用厂商默认初始化命令
- `command_echo`
  - 是否清理命令回显
- `key_filename`
  - SSH 私钥文件路径
- `ssh_local_version`
  - 覆盖本地 SSH 版本串

更完整字段可以参考 [models.py](/home/zonwin/projects/SwitchBasicTool/switchbasictool/models.py:10)。

## 命令结果 `CommandResult`

`send_command()` 返回的是 `CommandResult`，包含：

- `command`
  - 实际执行的命令
- `raw_output`
  - 原始设备回显
- `output`
  - 清洗后的输出
- `duration`
  - 本次命令耗时
- `timed_out`
  - 当前版本固定为 `False`，后续可继续扩展

## 命令行测试工具

项目自带一个手工测试脚本，适合联调真实交换机。

### 推荐运行位置

推荐在项目根目录执行：

```bash
cd /home/zonwin/projects/SwitchBasicTool
```

### 三种启动方式

方式一，直接用包入口：

```bash
python3 -m switchbasictool --list-vendors
```

方式二，直接指定模块：

```bash
python3 -m switchbasictool.manual_test --list-vendors
```

方式三，使用根目录脚本：

```bash
python3 manual_test.py --list-vendors
```

安装后也可以使用控制台脚本：

```bash
switchbasictool-manual-test --list-vendors
```

如果你当前就在 `switchbasictool/` 包目录里，也可以直接运行：

```bash
cd /home/zonwin/projects/SwitchBasicTool/switchbasictool
python3 manual_test.py --list-vendors
```

### 查看帮助

```bash
python3 -m switchbasictool --help
```

### 基础 SSH 示例

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --command "display version"
```

如果不传 `--password`，脚本会交互提示输入密码。

### 一次执行多条命令

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --command "display version" \
  --command "display current-configuration | include sysname" \
  --command "display interface brief"
```

### 通过命令文件执行

Huawei：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --command-file examples/huawei_commands.txt
```

H3C：

```bash
python3 -m switchbasictool \
  --host 10.10.10.20 \
  --protocol ssh \
  --username admin \
  --vendor h3c \
  --command-file examples/h3c_commands.txt
```

ZTE：

```bash
python3 -m switchbasictool \
  --host 10.10.10.30 \
  --protocol ssh \
  --username admin \
  --vendor zte \
  --command-file examples/zte_commands.txt
```

### 进入交互模式

执行完预设命令后继续手工输入：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --command "display version" \
  --interactive
```

### Telnet 示例

```bash
python3 -m switchbasictool \
  --host 10.10.10.30 \
  --protocol telnet \
  --username admin \
  --vendor zte \
  --command "show version"
```

### 不写命令时的默认行为

如果没有传 `--command` 或 `--command-file`，但传了 `--interactive`，脚本会直接进入交互模式。

如果既没有传命令，也没有开启 `--interactive`，脚本会按厂商尝试一组默认 smoke-test 命令：

- `huawei`
  - `display version`
  - `display current-configuration | include sysname`
  - `display interface brief`
- `h3c`
  - `display version`
  - `display current-configuration | include sysname`
  - `display interface brief`
- `zte`
  - `show version`
  - `show running-config | include hostname`
  - `show ip interface brief`
  - `show interface brief`

### 常用参数说明

连接相关：

- `--host`
  - 目标设备地址
- `--protocol`
  - `ssh` 或 `telnet`
- `--port`
  - 自定义端口
- `--username`
  - 登录用户名
- `--password`
  - 登录密码
- `--ask-password`
  - 即使没传 `--password` 也强制交互输入密码
- `--key-file`
  - SSH 私钥文件
- `--allow-agent`
  - 允许使用 SSH agent
- `--look-for-keys`
  - 自动查找本机 SSH key
- `--strict-host-key`
  - 启用严格 host key 校验

厂商与提示符相关：

- `--vendor`
  - 指定厂商名称或别名
- `--prompt-pattern`
  - 覆盖默认提示符匹配
- `--show-profile`
  - 输出当前解析出的 vendor profile
- `--disable-vendor-init`
  - 跳过厂商默认初始化命令
- `--init-command`
  - 追加自定义初始化命令，可重复传入

命令执行相关：

- `--command`
  - 单条命令，可重复传入
- `--command-file`
  - 从文件读取命令，一行一条，空行和 `#` 注释会被忽略
- `--interactive`
  - 进入交互模式
- `--show-raw`
  - 打印原始回显，便于排查命令回显、分页和提示符
- `--no-command-echo`
  - 不自动清理命令回显

超时与诊断相关：

- `--connect-timeout`
  - 建连超时
- `--timeout`
  - 单条命令整体超时
- `--read-timeout`
  - 底层读取超时
- `--banner-timeout`
  - SSH banner 等待超时
- `--auth-timeout`
  - SSH 认证超时
- `--probe-ssh-banner`
  - 只探测是否存在有效 SSH banner，不登录
- `--probe-timeout`
  - `--probe-ssh-banner` 的超时时间
- `--disable-ssh-strict-kex`
  - 兼容部分老 SSH 服务端
- `--ssh-local-version`
  - 自定义本地客户端 SSH banner

### 命令文件格式

命令文件中一行一条命令，支持空行和 `#` 注释：

```text
# Huawei sample
display version
display current-configuration | include sysname
display interface brief
```

## 厂商 profile

当前内置 profile：

- `generic`
- `huawei`
- `h3c`
- `cisco_ios`
- `juniper`
- `arista_eos`
- `zte`

### Huawei

内置 `huawei` profile 的特点：

- 别名：`vrp`、`huawei_vrp`、`hw`
- 提示符兼容用户视图 `<Huawei>` 和系统视图 `[Huawei]`
- 自带分页匹配规则
- 默认初始化命令：`screen-length 0 temporary`

### H3C

内置 `h3c` profile 的特点：

- 别名：`comware`、`h3c_comware`
- 提示符兼容用户视图 `<H3C>` 和系统视图 `[H3C]`
- 自带分页匹配规则
- 默认初始化命令：`screen-length disable`

### ZTE

内置 `zte` profile 的特点：

- 别名：`zxr10`、`zte_zxr10`、`8900e`
- 提示符兼容 `ZXR10#`、`ZXR10(config)#` 等风格
- 自带分页匹配规则
- 默认初始化命令：`no terminal length`

## 自定义厂商 profile

如果某个厂商还没有内置，或者现场设备的提示符比较特殊，可以自己注册：

```python
from switchbasictool import VendorProfile, register_vendor_profile

register_vendor_profile(
    VendorProfile(
        name="my_vendor",
        aliases=("my-switch",),
        prompt_pattern=r"(?m)<MY-SWITCH>\s*$",
        more_patterns=(r"--More--",),
        username_prompt_pattern=r"(?im)(?:username|login)\s*[:>]\s*$",
        password_prompt_pattern=r"(?im)password\s*[:>]\s*$",
        session_init_commands=("screen-length 0 temporary",),
    )
)
```

然后在 `ConnectionConfig` 里直接使用：

```python
config = ConnectionConfig(
    host="10.10.10.99",
    protocol="ssh",
    username="admin",
    password="password",
    vendor="my_vendor",
)
```

如果只想针对当前设备做一点覆盖，也可以直接改配置，不必重新注册：

```python
config = ConnectionConfig(
    host="10.10.10.10",
    protocol="ssh",
    username="admin",
    password="password",
    vendor="huawei",
    prompt_pattern=r"(?m)<Core-SW1>\s*$",
    session_init_commands=("screen-length 0 temporary", "terminal monitor",),
)
```

## 输出清洗说明

`send_command()` 的返回结果会做一些基础清洗：

- 统一换行符
- 去掉常见 ANSI 控制字符
- 去掉常见分页提示
- 默认尝试去掉首行命令回显
- 尝试去掉最后一行设备提示符

如果你想看最原始的设备返回，命令行里可以加 `--show-raw`。

## 常见问题

### 1. 这是短连接还是长连接

当前实现支持长连接。

一个 `NetworkDeviceClient` 建连后，可以持续发送多条命令，直到你显式调用 `disconnect()` 或退出 `with` 上下文。

### 2. 设备提示符识别不对怎么办

优先尝试：

- 命令行加 `--show-raw`
- 命令行加 `--show-profile`
- 用 `prompt_pattern` 覆盖默认正则

例如：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --prompt-pattern '(?m)<Core-SW1>\\s*$' \
  --show-raw \
  --command "display version"
```

### 3. 分页没有被正确处理

可以：

- 通过 `--disable-vendor-init` 先观察设备原始行为
- 用 `--show-raw` 看分页提示长什么样
- 在自定义 `VendorProfile` 里补 `more_patterns`

### 4. SSH 报 `Error reading SSH protocol banner`

这通常说明问题还没到 SSH 算法协商阶段，更常见的是：

- 目标 22 端口不是真 SSH
- 远端在返回 SSH banner 之前就关闭了连接
- 源地址被 ACL / 管理策略限制
- 设备响应过慢

可以先探测目标是否返回有效 SSH banner：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --probe-ssh-banner
```

如果设备只是比较慢，可以增大等待时间：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --banner-timeout 30 \
  --command "display version"
```

如果后续报错变成算法兼容问题，再试：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --protocol ssh \
  --username admin \
  --vendor huawei \
  --disable-ssh-strict-kex \
  --command "display version"
```

如果怀疑设备会根据客户端版本串有特殊兼容行为，可以指定：

```bash
python3 -m switchbasictool \
  --host 10.10.10.10 \
  --probe-ssh-banner \
  --ssh-local-version "SSH-2.0-PuTTY_Release_0.70"
```

## 代码入口参考

如果你后续准备继续扩展，建议先看这几个文件：

- [client.py](/home/zonwin/projects/SwitchBasicTool/switchbasictool/client.py:13)
- [models.py](/home/zonwin/projects/SwitchBasicTool/switchbasictool/models.py:10)
- [vendors.py](/home/zonwin/projects/SwitchBasicTool/switchbasictool/vendors.py:13)
- [switchbasictool/manual_test.py](/home/zonwin/projects/SwitchBasicTool/switchbasictool/manual_test.py:1)

## 后续建议

如果准备继续往生产可用方向走，下一步比较值得补的是：

- 自动重连机制
- 连接健康检查
- 更细的分页处理策略
- 厂商专属高层客户端
- 常见 `show` / `display` 命令的结构化解析
