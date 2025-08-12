import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time

# --- 新增和修改的部分 ---

def _get_config_path():
    """获取跨平台的用户特定应用配置路径"""
    # macOS: ~/Library/Application Support/AppName/config.json
    # Windows: %APPDATA%/AppName/config.json
    # Linux: ~/.config/AppName/config.json
    
    app_name = "QinglongJDCookieHelper" # 为应用创建一个文件夹
    
    if os.name == 'darwin': # macOS
        path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    elif os.name == 'nt': # Windows
        path = os.path.join(os.getenv('APPDATA'), app_name)
    else: # Linux and other OS
        path = os.path.join(os.path.expanduser('~'), '.config', app_name)
        
    # 确保目录存在
    os.makedirs(path, exist_ok=True)
    
    return os.path.join(path, "config.json")

# --------------------------


class QLHelper:
    """
    与青龙面板 API 交互的类
    复刻自原始 C# 代码中的 QLHelp.cs
    """
    def __init__(self, url, client_id, client_secret):
        self.url = url.strip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = ""
        self.id_name = "id"  # 默认 id 字段名

    def login(self):
        try:
            full_url = f"{self.url}/open/auth/token?client_id={self.client_id}&client_secret={self.client_secret}"
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                self.token = f"{data['data']['token_type']} {data['data']['token']}"
                # 检查环境变量接口以确定 id 字段是 'id' 还是 '_id'
                self.check_id_field()
                return "青龙登录成功"
            else:
                raise Exception(data.get("message", "未知错误"))
        except Exception as e:
            raise Exception(f"青龙登录失败: {e}")

    def check_id_field(self):
        """探测环境变量接口以确定主键字段名"""
        try:
            headers = {'Authorization': self.token}
            # 使用一个几乎不可能存在的searchValue来获取一个空列表，只看结构
            response = requests.get(f"{self.url}/open/envs?searchValue=___check___", headers=headers, timeout=10)
            data = response.json()
            if data.get('code') == 200 and data.get('data'):
                if '_id' in data['data'][0]:
                    self.id_name = '_id'
                elif 'id' in data['data'][0]:
                    self.id_name = 'id'
        except Exception:
            # 探测失败则使用默认值 'id'
            pass


    def get_envs(self, search_value):
        headers = {'Authorization': self.token}
        response = requests.get(f"{self.url}/open/envs?searchValue={search_value}", headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200 and data.get("data"):
            return data["data"][0].get(self.id_name)
        return None

    def add_envs(self, name, value, remarks):
        headers = {'Authorization': self.token, 'Content-Type': 'application/json'}
        payload = [{'name': name, 'value': value, 'remarks': remarks}]
        response = requests.post(f"{self.url}/open/envs", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def update_envs(self, env_id, name, value, remarks):
        headers = {'Authorization': self.token, 'Content-Type': 'application/json'}
        payload = {'name': name, 'value': value, 'remarks': remarks, self.id_name: env_id}
        response = requests.put(f"{self.url}/open/envs", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    def enable_envs(self, env_id):
        headers = {'Authorization': self.token, 'Content-Type': 'application/json'}
        payload = [env_id]
        response = requests.put(f"{self.url}/open/envs/enable", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 青龙京东助手 v2.0 - macOS")
        self.geometry("850x900")
        self.resizable(True, True)  # 允许调整窗口大小
        self.driver = None
        
        # 设置窗口图标和样式
        try:
            # 设置窗口居中显示
            self.center_window()
        except:
            pass
        
        # 配置暗色主题颜色
        self.configure(bg='#1a1a1a')
        
        # --- 修改的部分 ---
        self.config_file_path = _get_config_path()
        # 初始化状态变量
        self.connection_status = "未连接"
        self.login_status = "未登录"
        self.cookie_status = "未获取"
        # -----------------

        # 创建主框架 - 暗色专业风格
        main_frame = tk.Frame(self, bg='#1a1a1a', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 应用标题区域 - 暗黑渐变
        title_frame = tk.Frame(main_frame, bg='#2d2d2d', height=60)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        title_frame.pack_propagate(False)
        
        # 创建渐变标题背景
        gradient_frame = tk.Frame(title_frame, height=60)
        gradient_frame.pack(fill=tk.X)
        gradient_frame.configure(bg='#fa709a')  # 粉色到黄色渐变的起始色
        
        title_label = tk.Label(gradient_frame, text="青龙助手 - forMac", 
                              font=('SF Pro Display', 24, 'bold'),
                              fg='#333333', bg='#fa709a')
        title_label.pack(expand=True)
        
        # 状态指示器区域
        status_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='flat', bd=1, highlightbackground='#404040')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 创建状态指示器
        self.create_status_indicators(status_frame)

        # 青龙配置部分 - 暗色卡片样式
        config_card = tk.Frame(main_frame, bg='#2d2d2d', relief='flat', bd=1, highlightbackground='#404040')
        config_card.pack(fill=tk.X, pady=(0, 15))
        
        # 配置卡片左边框装饰
        left_border = tk.Frame(config_card, bg='#fa709a', width=4)
        left_border.pack(side=tk.LEFT, fill=tk.Y)
        
        # 配置内容区域
        config_content = tk.Frame(config_card, bg='#2d2d2d')
        config_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置标题
        config_title = tk.Label(config_content, text="青龙面板配置", 
                               font=('SF Pro Display', 14, 'bold'),
                               fg='#fa709a', bg='#2d2d2d')
        config_title.pack(anchor='w', padx=15, pady=(15, 10))
        
        # 配置表单区域
        config_form = tk.Frame(config_content, bg='#2d2d2d')
        config_form.pack(fill=tk.X, padx=15, pady=(0, 15))

        # URL配置
        self.ql_url = tk.Entry(config_form, font=('Monaco', 11),
                              bg='#3a3a3a', fg='#e0e0e0', relief='flat', bd=0,
                              highlightthickness=1, highlightcolor='#fa709a',
                              highlightbackground='#555', insertbackground='#e0e0e0')
        self.ql_url.pack(fill=tk.X, pady=(0, 10), ipady=10)
        self.ql_url.insert(0, "http://面板地址:5700")
        self.ql_url.bind('<FocusIn>', lambda e: self.clear_placeholder(e, "http://面板地址:5700"))

        # Client ID和Secret - 并排布局
        credentials_frame = tk.Frame(config_form, bg='#2d2d2d')
        credentials_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Client ID
        self.ql_client_id = tk.Entry(credentials_frame, font=('Monaco', 11),
                                    bg='#3a3a3a', fg='#e0e0e0', relief='flat', bd=0,
                                    highlightthickness=1, highlightcolor='#fa709a',
                                    highlightbackground='#555', insertbackground='#e0e0e0')
        self.ql_client_id.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), ipady=10)
        self.ql_client_id.insert(0, "Client ID")
        self.ql_client_id.bind('<FocusIn>', lambda e: self.clear_placeholder(e, "Client ID"))
        
        # Client Secret
        self.ql_client_secret = tk.Entry(credentials_frame, font=('Monaco', 11),
                                        bg='#3a3a3a', fg='#e0e0e0', relief='flat', bd=0, show='*',
                                        highlightthickness=1, highlightcolor='#fa709a',
                                        highlightbackground='#555', insertbackground='#e0e0e0')
        self.ql_client_secret.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), ipady=10)
        self.ql_client_secret.insert(0, "Client Secret")
        self.ql_client_secret.bind('<FocusIn>', lambda e: self.clear_placeholder(e, "Client Secret"))

        # 操作部分 - 暗色按钮卡片
        action_card = tk.Frame(main_frame, bg='#2d2d2d', relief='flat', bd=1, highlightbackground='#404040')
        action_card.pack(fill=tk.X, pady=(0, 15))
        
        # 操作卡片左边框装饰
        action_left_border = tk.Frame(action_card, bg='#fee140', width=4)
        action_left_border.pack(side=tk.LEFT, fill=tk.Y)
        
        # 操作内容区域
        action_content = tk.Frame(action_card, bg='#2d2d2d')
        action_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 操作标题
        action_title = tk.Label(action_content, text="操作中心", 
                               font=('SF Pro Display', 14, 'bold'),
                               fg='#fee140', bg='#2d2d2d')
        action_title.pack(anchor='w', padx=15, pady=(15, 10))
        
        # 操作按钮区域
        action_buttons_frame = tk.Frame(action_content, bg='#2d2d2d')
        action_buttons_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # 暗色按钮样式
        button_style = {
            'font': ('SF Pro Display', 11, 'bold'),
            'relief': 'flat',
            'bd': 0,
            'cursor': 'hand2'
        }
        
        self.login_button = tk.Button(action_buttons_frame, text="🌐 登录", 
                                     command=self.open_jd_login,
                                     bg='#fa709a', fg='white',
                                     activebackground='#f85d92',
                                     activeforeground='white',
                                     **button_style)
        self.login_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), ipady=10)

        self.get_cookie_button = tk.Button(action_buttons_frame, text="🍪 获取", 
                                          command=self.get_cookies,
                                          bg='#fee140', fg='#333',
                                          activebackground='#fed93c',
                                          activeforeground='#333',
                                          **button_style)
        self.get_cookie_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 5), ipady=10)

        self.send_to_ql_button = tk.Button(action_buttons_frame, text="🚀 发送", 
                                          command=self.send_to_ql,
                                          bg='#4facfe', fg='white',
                                          activebackground='#3a96fd',
                                          activeforeground='white',
                                          **button_style)
        self.send_to_ql_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), ipady=10)

        # 系统监控部分 - 暗色卡片
        monitor_card = tk.Frame(main_frame, bg='#2d2d2d', relief='flat', bd=1, highlightbackground='#404040')
        monitor_card.pack(fill=tk.BOTH, expand=True)
        
        # 监控卡片左边框装饰
        monitor_left_border = tk.Frame(monitor_card, bg='#4facfe', width=4)
        monitor_left_border.pack(side=tk.LEFT, fill=tk.Y)
        
        # 监控内容区域
        monitor_content = tk.Frame(monitor_card, bg='#2d2d2d')
        monitor_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 监控标题和状态
        monitor_header = tk.Frame(monitor_content, bg='#2d2d2d', padx=15, pady=15)
        monitor_header.pack(fill=tk.X)
        
        monitor_title = tk.Label(monitor_header, text="系统监控", 
                                font=('SF Pro Display', 14, 'bold'),
                                fg='#4facfe', bg='#2d2d2d')
        monitor_title.pack(side=tk.LEFT)
        
        # 右侧状态信息
        status_info = tk.Frame(monitor_header, bg='#2d2d2d')
        status_info.pack(side=tk.RIGHT)
        
        # 连接状态
        connect_status = tk.Label(status_info, text="连接状态:", 
                                 font=('SF Pro Display', 10), 
                                 fg='#666', bg='#2d2d2d')
        connect_status.pack(side=tk.LEFT)
        
        connect_indicator = tk.Label(status_info, text="● 未连接", 
                                    font=('SF Pro Display', 10), 
                                    fg='#dc3545', bg='#2d2d2d')
        connect_indicator.pack(side=tk.LEFT, padx=(5, 20))
        
        # 用户状态
        user_status_label = tk.Label(status_info, text="用户:", 
                                    font=('SF Pro Display', 10), 
                                    fg='#666', bg='#2d2d2d')
        user_status_label.pack(side=tk.LEFT)
        
        self.pin_label = tk.Label(status_info, text="N/A", 
                                 font=('SF Pro Display', 10, 'bold'),
                                 fg='#ffc107', bg='#2d2d2d')
        self.pin_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志内容区域
        log_content_frame = tk.Frame(monitor_content, bg='#2d2d2d')
        log_content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.log_area = scrolledtext.ScrolledText(log_content_frame, 
                                                 wrap=tk.WORD, height=8,
                                                 font=('Monaco', 10),
                                                 bg='#1a1a1a', fg='#00ff00',
                                                 relief='flat', bd=0,
                                                 highlightthickness=0,
                                                 insertbackground='#00ff00')
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Cookie 文本框（隐藏但保留功能）
        self.cookie_text = tk.Text(self, height=1, width=1)
        self.cookie_text.pack_forget()  # 隐藏但保留引用

        self.load_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        pos_x = (self.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{pos_x}+{pos_y}')
    
    def clear_placeholder(self, event, placeholder_text):
        """清除输入框占位符文本"""
        widget = event.widget
        if widget.get() == placeholder_text:
            widget.delete(0, tk.END)
    
    def create_status_indicators(self, parent_frame):
        """创建暗色主题的状态指示器"""
        # 状态指示器容器
        indicators_frame = tk.Frame(parent_frame, bg='#2d2d2d', padx=20, pady=15)
        indicators_frame.pack(fill=tk.X)
        
        # 标题
        status_title = tk.Label(indicators_frame, text="📊 系统状态", 
                               font=('SF Pro Display', 14, 'bold'),
                               fg='#e0e0e0', bg='#2d2d2d')
        status_title.pack(anchor='w', pady=(0, 10))
        
        # 状态指示器网格
        status_grid = tk.Frame(indicators_frame, bg='#2d2d2d')
        status_grid.pack(fill=tk.X)
        
        # 创建三个状态指示器
        self.create_single_indicator(status_grid, "面板连接", "未连接", "#dc3545", 0)
        self.create_single_indicator(status_grid, "登录状态", "未登录", "#ffc107", 1)
        self.create_single_indicator(status_grid, "Cookie状态", "未获取", "#6c757d", 2)
    
    def create_single_indicator(self, parent, title, status, color, column):
        """创建单个暗色主题状态指示器"""
        indicator_frame = tk.Frame(parent, bg='#2d2d2d')
        indicator_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if column == 0 else 10, 0))
        
        # 状态圆圈
        circle_frame = tk.Frame(indicator_frame, bg='#2d2d2d', height=50)
        circle_frame.pack(fill=tk.X)
        circle_frame.pack_propagate(False)
        
        status_circle = tk.Label(circle_frame, text="●", 
                                font=('SF Pro Display', 40),
                                fg=color, bg='#2d2d2d')
        status_circle.pack(expand=True)
        
        # 状态标题
        title_label = tk.Label(indicator_frame, text=title,
                              font=('SF Pro Display', 11, 'bold'),
                              fg='#e0e0e0', bg='#2d2d2d')
        title_label.pack(pady=(5, 2))
        
        # 状态值
        status_label = tk.Label(indicator_frame, text=status,
                               font=('SF Pro Display', 10),
                               fg='#aaa', bg='#2d2d2d')
        status_label.pack()
        
        # 存储引用以便更新
        setattr(self, f'status_circle_{column}', status_circle)
        setattr(self, f'status_label_{column}', status_label)
    
    def update_status_indicator(self, indicator_id, status, color):
        """更新状态指示器"""
        try:
            circle = getattr(self, f'status_circle_{indicator_id}')
            label = getattr(self, f'status_label_{indicator_id}')
            circle.config(fg=color)
            label.config(text=status)
        except AttributeError:
            pass

    def log(self, message, level="INFO"):
        """现代化的日志显示方法"""
        timestamp = time.strftime('%H:%M:%S')
        
        # 根据日志级别设置颜色
        colors = {
            "INFO": "#00ff00",    # 绿色
            "WARN": "#ffff00",    # 黄色  
            "ERROR": "#ff4444",   # 红色
            "SUCCESS": "#00ffff"  # 青色
        }
        
        color = colors.get(level, "#00ff00")
        
        # 添加图标
        icons = {
            "INFO": "ℹ️",
            "WARN": "⚠️", 
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        
        icon = icons.get(level, "ℹ️")
        
        # 插入格式化的日志
        self.log_area.insert(tk.END, f"{icon} [{timestamp}] {level}: {message}\n")
        self.log_area.see(tk.END)
        
        # 确保GUI更新
        self.update_idletasks()

    def save_config(self):
        """保存配置并更新状态"""
        # 获取配置值，过滤掉占位符文本
        url = self.ql_url.get()
        client_id = self.ql_client_id.get()
        client_secret = self.ql_client_secret.get()
        
        # 过滤占位符
        if url == "http://面板地址:5700":
            url = ""
        if client_id == "Client ID":
            client_id = ""
        if client_secret == "Client Secret":
            client_secret = ""
            
        config = {
            "ql_url": url,
            "ql_client_id": client_id,
            "ql_client_secret": client_secret
        }
        
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(config, f, indent=4)
            
            self.log(f"配置已保存", "SUCCESS")
            
            # 更新连接状态
            if config["ql_url"] and config["ql_client_id"] and config["ql_client_secret"]:
                self.update_status_indicator(0, "已配置", "#28a745")
                self.connection_status = "已配置"
            else:
                self.update_status_indicator(0, "待完善", "#ffc107")
            
            messagebox.showinfo("✅ 保存成功", "配置信息已成功保存！")
            
        except Exception as e:
            self.log(f"保存配置失败: {e}", "ERROR")
            messagebox.showerror("❌ 保存失败", f"配置保存失败:\n{e}")
    
    def load_config(self):
        """加载配置并更新状态"""
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, "r") as f:
                    config = json.load(f)
                
                # 清除占位符并加载实际配置
                if config.get("ql_url"):
                    self.ql_url.delete(0, tk.END)
                    self.ql_url.insert(0, config["ql_url"])
                
                if config.get("ql_client_id"):
                    self.ql_client_id.delete(0, tk.END) 
                    self.ql_client_id.insert(0, config["ql_client_id"])
                
                if config.get("ql_client_secret"):
                    self.ql_client_secret.delete(0, tk.END)
                    self.ql_client_secret.insert(0, config["ql_client_secret"])
                
                self.log(f"已从本地加载配置文件", "SUCCESS")
                
                # 检查配置完整性并更新状态
                if all([config.get("ql_url"), config.get("ql_client_id"), config.get("ql_client_secret")]):
                    self.update_status_indicator(0, "已配置", "#28a745")
                    self.connection_status = "已配置"
                else:
                    self.update_status_indicator(0, "待配置", "#ffc107")
                    
            else:
                self.log("未找到配置文件，请先配置青龙面板信息", "WARN")
                
        except Exception as e:
            self.log(f"加载配置失败: {e}", "ERROR")

    def open_jd_login(self):
        """打开浏览器进行京东登录"""
        self.log("正在初始化Chrome浏览器...", "INFO")
        self.update_status_indicator(1, "初始化中", "#ffc107")
        
        def run():
            try:
                # 使用 webdriver-manager 自动管理 ChromeDriver
                self.log("正在下载/更新ChromeDriver...", "INFO")
                service = ChromeService(executable_path=ChromeDriverManager().install())
                
                self.log("正在启动Chrome浏览器...", "INFO")
                
                # 配置Chrome浏览器选项
                chrome_options = webdriver.ChromeOptions()
                # 设置窗口大小和位置
                # chrome_options.add_argument("--window-size=500,1000")  # 宽度500px，高度1000px
                chrome_options.add_argument("--window-position=200,100")  # 距离屏幕左边200px，顶部100px
                
                # 可选的其他设置（你可以根据需要启用）
                # chrome_options.add_argument("--start-maximized")  # 最大化启动
                # chrome_options.add_argument("--force-device-scale-factor=1.1")  # 缩放110%
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.get("https://home.m.jd.com/myJd/home.action")
                
                self.log("🌐 浏览器已成功打开", "SUCCESS")
                self.log("📱 请在浏览器中手动登录京东账号", "INFO")
                self.log("✅ 登录完成后点击 '🍪 获取Cookie' 按钮", "INFO")
                
                # 更新登录状态
                self.update_status_indicator(1, "待登录", "#ffc107")
                
            except Exception as e:
                self.log(f"浏览器启动失败: {e}", "ERROR")
                self.update_status_indicator(1, "启动失败", "#dc3545")
                messagebox.showerror("🌐 浏览器启动失败", 
                                   f"无法启动Chrome浏览器，请确保：\n"
                                   f"1. 已安装Chrome浏览器\n"
                                   f"2. 网络连接正常\n\n"
                                   f"错误详情: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def get_cookies(self):
        """从浏览器获取京东Cookie"""
        if not self.driver:
            messagebox.showerror("🌐 浏览器未启动", "请先点击 '🌐 打开京东登录' 启动浏览器！")
            return

        self.log("正在从浏览器获取Cookie信息...", "INFO")
        self.update_status_indicator(2, "获取中", "#ffc107")
        
        try:
            cookies = self.driver.get_cookies()
            pt_key = ""
            pt_pin = ""
            
            for cookie in cookies:
                if cookie['name'] == 'pt_key':
                    pt_key = cookie['value']
                elif cookie['name'] == 'pt_pin':
                    pt_pin = cookie['value']

            if pt_key and pt_pin:
                # 更新Cookie显示
                cookie_value = f"pt_key={pt_key};pt_pin={pt_pin};"
                self.cookie_text.delete('1.0', tk.END)
                self.cookie_text.insert('1.0', cookie_value)
                
                # 更新用户名显示
                self.pin_label.config(text=pt_pin, fg='#28a745')
                
                # 更新状态
                self.update_status_indicator(1, "已登录", "#28a745")
                self.update_status_indicator(2, "已获取", "#28a745")
                self.login_status = "已登录"
                self.cookie_status = "已获取"
                
                self.log(f"✅ Cookie获取成功！用户: {pt_pin}", "SUCCESS")
                self.log(f"🔑 pt_key长度: {len(pt_key)} 字符", "INFO")
                
                messagebox.showinfo("🍪 Cookie获取成功", 
                                  f"已成功获取用户 {pt_pin} 的Cookie信息！\n"
                                  f"现在可以点击 '🚀 发送到青龙' 按钮。")
                
            else:
                self.log("❌ 未找到有效的Cookie信息", "ERROR")
                self.update_status_indicator(2, "获取失败", "#dc3545")
                
                messagebox.showwarning("🔐 登录检查", 
                                     "未检测到有效的登录Cookie！\n\n"
                                     "请确保：\n"
                                     "1. 已在浏览器中成功登录京东\n"
                                     "2. 页面加载完成\n"
                                     "3. 未使用无痕模式")
                                     
        except Exception as e:
            self.log(f"Cookie获取过程出错: {e}", "ERROR")
            self.update_status_indicator(2, "获取异常", "#dc3545")
            messagebox.showerror("🍪 获取失败", f"Cookie获取失败:\n{e}")

    def send_to_ql(self):
        """将Cookie发送到青龙面板"""
        # 获取配置并过滤占位符
        url = self.ql_url.get()
        client_id = self.ql_client_id.get() 
        client_secret = self.ql_client_secret.get()
        
        # 过滤占位符
        if url == "http://面板地址:5700":
            url = ""
        if client_id == "Client ID":
            client_id = ""
        if client_secret == "Client Secret":
            client_secret = ""
        
        cookie_value = self.cookie_text.get('1.0', tk.END).strip()
        pin = self.pin_label.cget("text")

        # 验证配置完整性
        if not all([url, client_id, client_secret]):
            messagebox.showerror("⚠️ 配置不完整", 
                               "青龙面板配置信息不完整！\n\n"
                               "请确保填写：\n"
                               "• 面板地址\n"
                               "• Client ID\n"
                               "• Client Secret")
            return
        
        # 验证Cookie是否存在
        if "N/A" in pin or not cookie_value:
            messagebox.showerror("🍪 Cookie未获取", 
                               "请先获取Cookie！\n\n"
                               "步骤：\n"
                               "1. 点击 '🌐 登录'\n"
                               "2. 在浏览器中登录京东\n"
                               "3. 点击 '🍪 获取'")
            return
            
        self.log("🚀 开始向青龙面板发送Cookie...", "INFO")
        self.update_status_indicator(0, "连接中", "#ffc107")
        
        def run():
            try:
                # 连接青龙面板
                self.log("🔐 正在连接青龙面板...", "INFO")
                ql = QLHelper(url, client_id, client_secret)
                
                # 登录青龙面板
                login_result = ql.login()
                self.log(f"✅ {login_result}", "SUCCESS")
                self.update_status_indicator(0, "已连接", "#28a745")
                
                # 查找现有环境变量
                search_value = f"pt_pin={pin}"
                self.log(f"🔍 正在查找用户 {pin} 的环境变量...", "INFO")
                env_id = ql.get_envs(search_value)
                
                remarks = f"macOS助手v2.0_{pin}_{time.strftime('%Y%m%d_%H%M')}"
                
                if env_id:
                    # 更新现有环境变量
                    self.log(f"📝 找到现有环境变量 ID: {env_id}，准备更新...", "INFO")
                    ql.update_envs(env_id, "JD_COOKIE", cookie_value, remarks)
                    ql.enable_envs(env_id)  # 确保启用状态
                    self.log(f"🔄 用户 {pin} 的Cookie已更新", "SUCCESS")
                    operation = "更新"
                else:
                    # 新增环境变量
                    self.log(f"➕ 未找到现有变量，准备为用户 {pin} 新增...", "INFO")
                    ql.add_envs("JD_COOKIE", cookie_value, remarks)
                    self.log(f"✨ 用户 {pin} 的Cookie已新增", "SUCCESS")
                    operation = "添加"
                
                # 操作完成
                self.log(f"🎉 Cookie {operation}操作完成！", "SUCCESS")
                
                messagebox.showinfo("🎉 操作成功", 
                                  f"用户 {pin} 的Cookie已成功{operation}到青龙面板！\n\n"
                                  f"📊 操作详情：\n"
                                  f"• 用户: {pin}\n"
                                  f"• 操作: {operation}\n"
                                  f"• 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                self.log(f"❌ 发送失败: {e}", "ERROR")
                self.update_status_indicator(0, "连接失败", "#dc3545")
                messagebox.showerror("🚀 发送失败", 
                                   f"Cookie发送失败！\n\n"
                                   f"可能的原因：\n"
                                   f"• 网络连接问题\n"
                                   f"• 青龙面板配置错误\n"
                                   f"• 服务器响应异常\n\n"
                                   f"错误详情: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def on_closing(self):
        if self.driver:
            self.driver.quit()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()