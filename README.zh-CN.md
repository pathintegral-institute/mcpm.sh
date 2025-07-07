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

MCPM 是一个开源的 CLI 工具，用于管理 MCP 服务器。它提供了简化的全局配置方法，让您一次安装服务器并使用配置文件进行组织，然后将它们集成到任何 MCP 客户端中。功能包括通过中央注册表发现服务器、直接执行、分享功能和客户端集成工具。

![MCPM 运行演示](.github/readme/demo.gif)

## 🤝 社区贡献

> 💡 **壮大 MCP 生态系统！** 我们欢迎对我们的 [MCP 注册表](mcp-registry/README.md) 进行贡献。添加你自己的服务器，改进文档，或建议功能。开源在社区参与下蓬勃发展！

## 🚀 快速安装

### 推荐：

```bash
curl -sSL https://mcpm.sh/install | bash
```

或选择其他安装方式，如 [其他安装方式](#-其他安装方式) 中的 `brew`、`pipx`、`uv` 等。

## 📦 其他安装方式

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

## 更多安装方式

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

MCPM v2.0 采用全局配置模型提供了管理 MCP 服务器的简化方法。主要功能包括：

- ✨ **全局服务器管理**：一次安装，到处使用
- 📋 **虚拟配置文件**：使用标签为不同工作流组织服务器
- 🔍 **服务器发现**：从 MCP 注册表浏览和安装
- 🚀 **直接执行**：通过 stdio 或 HTTP 运行服务器进行测试
- 🌐 **公共分享**：通过安全隧道分享服务器
- 🎛️ **客户端集成**：管理 Claude Desktop、Cursor、Windsurf 等的配置
- 💻 **精美的 CLI**：丰富的格式化和交互式界面
- 📊 **使用分析**：监控服务器使用情况和性能

MCPM v2.0 摆脱了 v1 基于目标系统的复杂性，转而采用清晰的全局工作空间模型。

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

MCPM 提供了一个具有清晰、有组织界面的全面 CLI。v2.0 架构使用全局配置模型，其中服务器安装一次，可以使用配置文件进行组织，然后根据需要集成到特定的 MCP 客户端中。

### ℹ️ 一般

```bash
mcpm --help          # 显示帮助信息和可用命令
mcpm --version       # 显示 MCPM 的当前版本
```

### 🌐 服务器管理

全局服务器安装和管理命令：

```bash
# 🔍 搜索和安装
mcpm search [QUERY]           # 在 MCP 注册表中搜索可用服务器
mcpm info SERVER_NAME         # 显示服务器的详细信息
mcpm install SERVER_NAME      # 从注册表安装服务器到全局配置
mcpm uninstall SERVER_NAME    # 从全局配置中删除服务器

# 📋 列出和检查
mcpm ls                       # 列出所有已安装的服务器及其配置文件分配
mcpm edit SERVER_NAME         # 编辑服务器配置
mcpm inspect SERVER_NAME      # 启动 MCP Inspector 来测试/调试服务器
```

### 🚀 服务器执行

直接执行服务器进行测试或集成：

```bash
mcpm run SERVER_NAME          # 通过 stdio 直接执行服务器
mcpm run SERVER_NAME --http   # 通过 HTTP 执行服务器进行测试
mcpm share SERVER_NAME        # 通过安全隧道分享服务器进行远程访问
mcpm usage                    # 显示全面的分析和使用数据
```

### 📂 配置文件管理

配置文件是将服务器组织成不同工作流的逻辑组的虚拟标签：

```bash
# 🔄 配置文件操作
mcpm profile ls               # 列出所有配置文件及其标记的服务器
mcpm profile create PROFILE   # 创建新配置文件
mcpm profile rm PROFILE       # 删除配置文件（服务器保持安装）
mcpm profile edit PROFILE     # 为配置文件进行交互式服务器选择

# 🚀 配置文件执行
mcpm profile run PROFILE      # 通过 stdio 或 HTTP 执行配置文件中的所有服务器
mcpm profile share PROFILE    # 通过安全隧道分享配置文件中的所有服务器
mcpm profile inspect PROFILE  # 为配置文件中的所有服务器启动 MCP Inspector
```

### 🖥️ 客户端集成

管理 MCP 客户端配置（Claude Desktop、Cursor、Windsurf 等）：

```bash
mcpm client ls                 # 列出所有支持的 MCP 客户端及其状态
mcpm client edit CLIENT_NAME   # 为客户端交互式启用/禁用服务器
mcpm client edit CLIENT_NAME -e # 在外部编辑器中打开客户端配置
mcpm client import CLIENT_NAME  # 从客户端导入服务器配置
```

### 🛠️ 系统与配置

```bash
mcpm doctor                   # 检查系统健康状况和服务器状态
mcpm config                   # 管理 MCPM 配置和设置
mcpm migrate                  # 从 v1 迁移到 v2 配置
```

### 📚 注册表

MCP 注册表是可使用 MCPM 安装的可用 MCP 服务器的中央存储库。注册表位于 [mcpm.sh/registry](https://mcpm.sh/registry)。

## 🗺️ 路线图

### ✅ v2.0 已完成
- [x] 全局服务器配置模型
- [x] 基于配置文件的服务器标记和组织
- [x] 交互式命令界面
- [x] 客户端集成管理 (`mcpm client edit`)
- [x] 具有一致 UX 的现代 CLI
- [x] 注册表集成和服务器发现
- [x] 直接服务器执行和分享
- [x] 从现有客户端配置导入

### 🔮 未来增强
- [ ] 高级服务器访问监控和分析
- [ ] 额外的客户端支持（gemini-cli、codex 等）
- [ ] 在 docker 中执行

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