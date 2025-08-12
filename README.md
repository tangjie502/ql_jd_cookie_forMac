# 青龙京东助手 for macOS

这是一个为 macOS 用户开发的桌面工具，旨在简化获取京东（JD.com）Cookie 并将其同步到青龙面板的过程。

**本工具的开发参考了 Windows 平台的优秀项目 [yclown/ql_jd_cookie](https://github.com/yclown/ql_jd_cookie)，并在其核心原理的基础上，使用 Python 为 macOS 平台进行了原生实现。**

## 功能特性

- **图形用户界面**：提供简洁直观的图形界面，方便操作。
- **配置持久化**：支持输入和保存青龙面板的 URL、Client ID 和 Client Secret。配置将安全地存储在 macOS 标准的应用支持目录中。
- **安全的 Cookie 获取**：通过内嵌的浏览器引擎（Selenium），用户可以在一个隔离的浏览器会话中安全登录京东，程序仅在用户授权后提取必要的 Cookie (`pt_pin` 和 `pt_key`)。
- **一键同步**：自动判断青龙面板中是否已存在该账户的环境变量，并执行新增或更新操作。
- **实时日志**：在界面提供日志窗口，显示所有操作的执行状态和结果，便于追踪和排查问题。

## 技术栈

- **编程语言**: Python 3
- **图形界面 (GUI)**: Tkinter (Python 标准库)
- **Web 自动化**: Selenium
- **浏览器驱动管理**: webdriver-manager
- **HTTP 网络请求**: requests

---

## 环境准备与开发

本部分适用于需要从源码运行或进行二次开发的开发者。

### 1. 系统依赖安装

首先，确保您的 macOS 系统已安装 `Homebrew` 和 `Google Chrome` 浏览器。

- **安装 Homebrew** (如果尚未安装):
  ```bash
  /bin/bash -c "$(curl -fsSL [https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh](https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh))"
  ```

- **安装 Python 3 和 Google Chrome**:
  ```bash
  brew install python
  brew install --cask google-chrome
  ```

### 2. Python 依赖安装

为了方便管理，建议将依赖项写入 `requirements.txt` 文件。

- **创建 `requirements.txt` 文件**，内容如下:
  ```text
  selenium
  webdriver-manager
  requests
  ```

- **使用 pip 安装依赖**:
  在项目目录下打开终端，运行：
  ```bash
  pip3 install -r requirements.txt
  ```

### 3. 从源码运行

将项目代码保存为 `jd_cookie_macos.py`，然后在终端中运行：

```bash
python3 jd_cookie_macos.py
```

---

## 打包与分发

如果您想将此工具分发给其他用户，可以按照以下步骤将其打包成一个独立的 macOS 应用。

### 第一步：打包成 `.app` 应用

我们将使用 `PyInstaller` 来完成这一步。

- **安装 PyInstaller**:
  ```bash
  pip3 install pyinstaller
  ```

- **执行打包命令**:
  在项目目录下运行以下命令，它会将 Python 脚本和所有依赖打包成一个 `.app` 文件。
  ```bash
  pyinstaller --noconfirm --onefile --windowed \
  --add-data "$(pip3 show webdriver-manager | grep Location | cut -d ' ' -f2)/webdriver_manager:webdriver_manager" \
  --name "青龙京东助手" \
  "jd_cookie_macos.py"
  ```
  打包成功后，`青龙京东助手.app` 会出现在 `dist` 文件夹中。

### 第二步：制作 `.dmg` 安装包

为了方便用户安装，我们使用 `create-dmg` 工具将 `.app` 文件制作成标准的磁盘映像文件。

- **安装 create-dmg**:
  ```bash
  brew install create-dmg
  ```

- **执行制作命令**:
  在项目目录下运行以下命令。
  
  **简单方式（推荐）**：
  ```bash
  create-dmg "青龙京东助手.dmg" "dist/青龙京东助手.app"
  ```
  
  **专业方式（可自定义背景和图标）**：
  如果您准备了背景图 `background.png` 等素材，可以使用更复杂的命令来美化安装界面。
  ```bash
  create-dmg \
    --volname "青龙京东助手" \
    --background "background.png" \
    --window-size 600 400 \
    --icon-size 128 \
    --app-drop-link 420 240 \
    --icon "青龙京东助手.app" 180 240 \
    "青龙京东助手.dmg" \
    "dist/"
  ```

---

## 使用说明 (最终用户)

1.  **安装**: 打开 `.dmg` 文件，将“青龙京东助手”图标拖拽到“应用程序”文件夹中。
2.  **配置青龙**: 打开应用，在界面上方输入您的青龙面板 URL、Client ID 和 Client Secret，然后点击 **保存配置**。
3.  **登录京东**: 点击 **打开浏览器登录京东** 按钮。 应用会自动打开一个 Chrome 浏览器窗口，请在此窗口中完成登录。
4.  **获取 Cookie**: 在浏览器中成功登录后，返回应用界面，点击 **从浏览器获取Cookie**。您的京东用户名和 Cookie 将会自动填充到界面中。
5.  **发送到青龙**: 确认信息无误后，点击 **一键发送到青龙**。应用会将 Cookie 同步到您的青龙面板。

## 配置文件

本应用的配置文件 `config.json` 被保存在以下用户专属目录中，并不会随应用移动而丢失：

`~/Library/Application Support/QinglongJDCookieHelper/config.json`

您可以通过访达的“前往文件夹”功能访问此路径。