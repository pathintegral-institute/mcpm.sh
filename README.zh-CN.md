![Homebrew Formula Version](https://img.shields.io/homebrew/v/mcpm?style=flat-square&color=green)
![PyPI - Version](https://img.shields.io/pypi/v/mcpm?style=flat-square&color=green)
![GitHub Release](https://img.shields.io/github/v/release/pathintegral-institute/mcpm.sh?style=flat-square&color=green)
![GitHub License](https://img.shields.io/github/license/pathintegral-institute/mcpm.sh?style=flat-square&color=orange)
![GitHub contributors](https://img.shields.io/github/contributors/pathintegral-institute/mcpm.sh?style=flat-square&color=blue)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mcpm?style=flat-square&color=yellow)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/pathintegral-institute/mcpm.sh?style=flat-square&color=red)

[English](README.md) | 简体中文

![mcpm.sh](https://socialify.git.ci/pathintegral-institute/mcpm.sh/image?custom_description=MCP%E5%91%BD%E4%BB%A4%E8%A1%8C%E7%AE%A1%E5%AE%B6%E3%80%82%E4%B8%80%E7%AB%99%E5%BC%8F%E8%A7%A3%E5%86%B3MCP%E6%9C%8D%E5%8A%A1%E7%9A%84%E6%90%9C%E7%B4%A2%EF%BC%8C%E5%AE%89%E8%A3%85%EF%BC%8C%E7%AE%A1%E7%90%86%E3%80%82%E6%9B%B4%E6%9C%89%E8%B7%AF%E7%94%B1%EF%BC%8C%E5%B7%A5%E5%85%B7%E9%9B%86%EF%BC%8C%E8%BF%9C%E7%A8%8B%E5%88%86%E4%BA%AB%EF%BC%8C%E8%B0%83%E7%94%A8%E5%8E%86%E5%8F%B2%E8%B7%9F%E8%B8%AA%E7%AD%89%E9%AB%98%E9%98%B6%E5%8A%9F%E8%83%BD%E3%80%82&description=1&font=Inter&forks=1&issues=1&name=1&pattern=Floating+Cogs&pulls=1&stargazers=1&theme=Auto)

```
Open Source. Forever Free.
Built with ❤️ by Path Integral Institute
```

# 🌟 MCPM - Model Context Protocol Manager

MCPM 是一个开源的服务和命令行界面(CLI)，用于管理模型上下文协议（MCP）服务器。它简化了跨各种支持的客户端管理服务器配置、允许将服务器分组到配置文件中、通过注册表帮助发现新服务器，并包含一个强大的路由器，该路由器在单个端点后聚合多个 MCP 服务器并共享会话。

![MCPM 运行演示](.github/readme/demo.gif)

## 🤝 社区贡献

> 💡 **壮大 MCP 生态系统！** 我们欢迎对我们的 [MCP 注册表](mcp-registry/README.md) 进行贡献。添加你自己的服务器，改进文档，或建议功能。开源在社区参与下蓬勃发展！

## 🚀 快速安装

### 🔄 Shell 脚本（一行命令）

```bash
curl -sSL https://mcpm.sh/install | bash
```

或选择您喜欢的安装方式：

### 🍺 Homebrew

```bash
brew install mcpm
```

### 📦 pipx（推荐用于 Python 工具）

```bash
pipx install mcpm
```

### 🪄 uv tool

```bash
uv tool install mcpm
```

## 其他安装方式

### 🐍 pip

```bash
pip install mcpm
```

### 🧰 X-CMD

如果你是 [x-cmd](https://x-cmd.com) 用户，可以运行以下命令安装：

```sh
x install mcpm.sh
```

## 🔎 概述

MCPM 简化了 MCP 服务器的安装、配置和管理，以及它们在不同应用程序（客户端）中的配置。主要功能包括：

- ✨ 轻松添加和删除支持的客户端的 MCP 服务器配置。
- 📋 使用配置文件进行集中管理：将服务器配置分组并轻松激活/停用它们。
- 🔍 通过中央注册表发现可用的 MCP 服务器。
- 🔌 MCPM 路由器，用于在单个端点后聚合多个 MCP 服务器并共享会话。
- 💻 用于所有管理任务的命令行界面 (CLI)。

有关共享服务器会话和 MCPM 路由器等更多功能，请参阅 [高级功能](docs/advanced_features.md)。

## 🖥️ 支持的 MCP 客户端

MCPM 将支持为以下客户端管理 MCP 服务器：

- 🤖 Claude Desktop (Anthropic)
- ⌨️ Cursor
- 🏄 Windsurf
- 🧩 Vscode
- 📝 Cline
- ➡️ Continue
- 🦢 Goose
- 🔥 5ire
- 🦘 Roo Code
- ✨ 更多客户端即将推出...

## 🔥 命令行界面 (CLI)

MCPM 提供了一个使用 Python 的 Click 框架构建的全面 CLI。命令通常在当前**活动客户端**上操作。您可以使用 `mcpm client` 查看/设置活动客户端。许多命令还支持作用域修饰符，如 `@CLIENT_NAME/SERVER_NAME` 或 `%PROFILE_NAME/SERVER_NAME`，以直接针对特定客户端或配置文件。

以下是按功能分组的可用命令：

### ℹ️ 一般

```bash
mcpm --help          # 显示帮助信息和可用命令
mcpm --version       # 显示 MCPM 的当前版本
```

### 🖥️ 客户端管理 (`client`)

```bash
mcpm client ls        # 列出所有支持的 MCP 客户端，检测已安装的客户端，并显示活动客户端
mcpm client edit      # 在外部编辑器中打开活动客户端的 MCP 配置文件
```

### 🌐 服务器管理 (`server`)

这些命令在活动客户端上操作，除非提供了特定作用域（`@CLIENT` 或 `%PROFILE`）。

```bash
# 🔍 搜索和添加
mcpm search [QUERY]       # 在 MCP 注册表中搜索可用服务器
mcpm add SERVER_URL       # 添加 MCP 服务器配置（从 URL 或注册表名称）
mcpm add SERVER_URL --alias ALIAS # 添加并使用自定义别名

# 🛠️ 自定义添加
mcpm import stdio SERVER_NAME --command COMMAND --args ARGS --env ENV # 手动添加一个 stdio MCP 服务器
mcpm import remote SERVER_NAME --url URL # 手动添加一个 remote MCP 服务器
mcpm import interact # 通过交互式添加一个服务器

# 📋 列出和删除
mcpm ls                   # 列出活动客户端/配置文件的服务器配置
mcpm rm SERVER_NAME       # 删除服务器配置

# 🔄 修改和组织
mcpm cp SOURCE TARGET     # 复制服务器配置（例如，@client1/serverA %profileB）
mcpm mv SOURCE TARGET     # 移动服务器配置（例如，%profileA/serverX @client2）

# 📦 暂存（临时禁用/启用）
mcpm stash SERVER_NAME    # 临时禁用/存储服务器配置
mcpm pop [SERVER_NAME]    # 恢复最后暂存的服务器，或按名称恢复特定服务器
```

### 📂 配置文件管理 (`profile`)

配置文件是服务器配置的命名集合。它们允许您轻松切换不同的 MCP 服务器集。例如，您可能有一个 `work` 配置文件和一个 `personal` 配置文件，每个都包含不同的服务器。或者，您可能有一个 `production` 配置文件和一个 `development` 配置文件，每个都包含同一服务器的不同配置。

当前*活动*配置文件的服务器通常由 MCPM 路由器等功能使用。使用 `mcpm target set %profile_name` 设置活动配置文件。

```bash
# 🔄 配置文件生命周期
mcpm profile ls              # 列出所有可用的 MCPM 配置文件
mcpm profile add PROFILE_NAME  # 添加新的空配置文件
mcpm profile rm PROFILE_NAME   # 删除配置文件（不删除其中的服务器）
mcpm profile rename OLD_NAME NEW_NAME # 重命名配置文件
```

### 🔌 路由器管理 (`router`)

MCPM 路由器作为后台守护进程运行，充当稳定端点（例如 `http://localhost:6276`），根据当前**活动配置文件**智能地将传入的 MCP 请求路由到适当的服务器。

这允许您通过切换配置文件（使用 `mcpm target set %profile_name`）来更改底层服务器，而无需重新配置客户端应用程序。它们可以始终指向 MCPM 路由器的地址。

路由器还维护与 MCP 服务器的持久连接，使多个客户端能够共享这些服务器会话。这消除了为每个客户端启动单独服务器实例的需要，显著减少资源使用和启动时间。在 [高级功能](docs/advanced_features.md) 中了解有关这些高级功能的更多信息。

有关路由器实现和命名空间的更多技术细节，请参阅 [`docs/router_tech_design.md`](docs/router_tech_design.md)。

Router可以通过命令`mcpm router share`来将router分享到公网。注意确保生成的密钥没有暴露，并只分享给可信用户。有关分享的更多细节，请参阅[分享](docs/router_share.md)。

```bash
mcpm router status                # 检查路由器守护进程是否正在运行
mcpm router on                    # 启动 MCP 路由器守护进程
mcpm router off                   # 停止 MCP 路由器守护进程
mcpm router set --host HOST --port PORT --address ADDRESS  # 设置 MCP 路由器守护进程的主机,端口和分享的远程服务器
mcpm router share                 # 将router分享到公网
mcpm router unshare               # 取消分享
```

### 🤝 共享管理 (`share`)

`mcpm share` 命令允许您将任何启动 MCP 服务器的 shell 命令，并立即将其公开为 SSE (Server-Sent Events) 服务器。它使用 `mcp-proxy` 处理服务器转换，然后创建一个安全隧道进行远程访问，使您的本地 MCP 服务器可以从任何地方访问。

这对于快速共享开发服务器、自定义 MCP 服务器，甚至具有特定配置的标准服务器（无需公开部署）特别有用。

```bash
# 🚀 共享本地 MCP 服务器
mcpm share "COMMAND" # 将 COMMAND 替换为您的实际服务器启动命令

# ⚙️ 选项
# COMMAND: 启动 MCP 服务器的 shell 命令 (例如 "uvx mcp-server-fetch", "npx mcp-server")。如果包含空格，则必须用引号括起来。
# --port PORT: 指定 mcp-proxy 监听的本地端口。默认为随机可用端口。
# --address ADDRESS: 指定隧道的公共地址 (例如 yourdomain.com:7000)。如果未提供，将生成随机隧道 URL。
# --http: 如果设置，隧道将使用 HTTP 而不是 HTTPS。请谨慎使用。
# --timeout TIMEOUT: mcp-proxy 等待服务器启动的超时时间（秒）。默认为 60。
# --retry RETRY: 如果服务器启动失败，重试启动服务器的次数。默认为 0。

# 💡 使用示例
mcpm share "uvx mcp-server-fetch"
mcpm share "npx mcp-server" --port 5000
mcpm share "uv run my-mcp-server" --address myserver.com:7000
mcpm share "npx -y @modelcontextprotocol/server-everything" --retry 3
```

### 🛠️ 实用工具 (`util`)

```bash
mcpm config clear-cache          # 清除 MCPM 的注册表缓存。缓存默认每 1 小时刷新一次。
mcpm config set                  # 设置 MCPM 的全局配置，目前仅支持 node_executable
mcpm config get <name>           # 获取 MCPM 的全局配置
mcpm inspector                   # 启动 MCPM 检查器 UI 以检查服务器配置
```

### 📚 注册表

MCP 注册表是可使用 MCPM 安装的可用 MCP 服务器的中央存储库。注册表位于 [mcpm.sh/registry](https://mcpm.sh/registry)。

## 🗺️ 路线图

- [x] 登陆页面设置 (`mcpm.sh`)
- [x] 核心 CLI 基础 (Click)
- [x] 客户端检测和管理 (`mcpm client`)
- [x] 基本服务器管理 (`mcpm add`, `mcpm ls`, `mcpm rm`)
- [x] 注册表集成 (`mcpm search`, 按名称添加)
- [x] 路由器功能 (`mcpm router`)
- [x] MCP 配置文件 (`mcpm profile`)
- [x] 服务器复制/移动 (`mcpm cp`, `mcpm mv`)
- [x] 服务器暂存 (`mcpm stash`, `mcpm pop`)
- [x] 路由器远程分享 (`mcpm router share`) 远程访问本地路由器和 MCP 服务器
- [x] MCPM 路由器的 MCP 服务器访问监控（仅限本地，绝对不会有数据离开本地机器）
- [ ] 通过 STDIO 的 MCPM 路由器（相同的强大功能集，具有配置文件和监控，但单客户端/租户）
- [ ] MCPM 路由器的 MCP 服务器（实验性，允许 MCP 客户端动态切换配置文件，从注册表建议新的 MCP 服务器等）
- [ ] 附加客户端支持（扩展注册表）

## 👨‍💻 开发

此存储库包含 MCP Manager 的 CLI 和服务组件，使用 Python 和 Click 按照现代包开发实践构建。

### 📋 开发要求

- 🐍 Python 3.10+
- 🚀 uv（用于虚拟环境和依赖管理）
- 🖱️ Click 框架用于 CLI
- ✨ Rich 用于增强控制台输出
- 🌐 Requests 用于 API 交互

### 📁 项目结构

该项目遵循现代基于 src 的布局：

```
mcpm.sh/
├── src/             # 源包目录
│   └── mcpm/        # 主包代码
├── tests/           # 测试目录
├── test_cli.py      # 开发 CLI 运行器
├── pyproject.toml   # 项目配置
├── pages/           # 网站内容
│   └── registry/    # 注册表网站
├── mcp-registry/    # MCP 注册表数据
└── README.md        # 文档
```

### 🚀 开发设置

1. 克隆存储库
   ```
   git clone https://github.com/pathintegral-institute/mcpm.sh.git
   cd mcpm.sh
   ```

2. 使用 uv 设置虚拟环境
   ```
   uv venv --seed
   source .venv/bin/activate  # 在 Unix/Mac 上
   ```

3. 以开发模式安装依赖项
   ```
   uv pip install -e .
   ```

4. 在开发期间直接运行 CLI
   ```
   # 使用已安装的包
   mcpm --help

   # 或使用开发脚本
   ./test_cli.py --help
   ```

5. 运行测试
   ```
   pytest tests/
   ```

### ✅ 最佳实践

- 📁 使用基于 src 的目录结构以防止导入混淆
- 🔧 使用 `uv pip install -e .` 进行可编辑安装开发
- 🧩 在 `src/mcpm/commands/` 目录中保持命令模块化
- 🧪 在 `tests/` 目录中为新功能添加测试
- 💻 使用 `test_cli.py` 脚本进行快速开发测试


### 🔢 版本管理

MCP 使用单一事实来源模式进行版本管理，以确保所有组件之间的一致性。

#### 🏷️ 版本结构

- 📍 规范版本在项目根目录的 `version.py` 中定义
- 📥 `src/mcpm/__init__.py` 导入此版本
- 📄 `pyproject.toml` 使用动态版本控制从 `version.py` 读取
- 🏷️ Git 标签使用相同的版本号，前缀为 'v'（例如，v1.0.0）

#### 🔄 更新版本

发布新版本时：

1. 使用提供的版本升级脚本
   ```
   ./bump_version.sh NEW_VERSION
   # 示例：./bump_version.sh 1.1.0
   ```

2. 推送更改和标签
   ```
   git push && git push --tags
   ```

3. 创建与新版本匹配的 GitHub 发布

此过程确保版本在所有地方保持一致：代码、包元数据和 git 标签。
PyPI 发布由 CI/CD 管道处理，将自动触发。

## 📜 许可证

MIT 

## 💬 加入社区

欢迎反馈问题，贡献代码，讨论新功能。
扫描以下二维码加入 MCPM 开源社区微信群：

<img src=".github/readme/mcpm_wechat.png" alt="MCPM 开源社区微信群" width="300px" />

## 🌟 星标历史

[![Star History Chart](https://api.star-history.com/svg?repos=pathintegral-institute/mcpm.sh&type=Date)](https://www.star-history.com/#pathintegral-institute/mcpm.sh&Date)