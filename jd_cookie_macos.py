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
        self.title("青龙京东助手 for macOS")
        self.geometry("800x600")
        self.driver = None
        
        # --- 修改的部分 ---
        self.config_file_path = _get_config_path()
        # -----------------

        # 创建主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 青龙配置部分
        ql_frame = ttk.LabelFrame(main_frame, text="青龙面板配置")
        ql_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ql_frame, text="URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ql_url = ttk.Entry(ql_frame, width=40)
        self.ql_url.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(ql_frame, text="Client ID:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ql_client_id = ttk.Entry(ql_frame, width=40)
        self.ql_client_id.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(ql_frame, text="Client Secret:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.ql_client_secret = ttk.Entry(ql_frame, width=40)
        self.ql_client_secret.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.save_ql_button = ttk.Button(ql_frame, text="保存配置", command=self.save_config)
        self.save_ql_button.grid(row=1, column=2, padx=10, pady=5)
        
        ql_frame.columnconfigure(1, weight=1)

        # 操作部分
        action_frame = ttk.LabelFrame(main_frame, text="操作")
        action_frame.pack(fill=tk.X, pady=5)
        
        self.login_button = ttk.Button(action_frame, text="打开浏览器登录京东", command=self.open_jd_login)
        self.login_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.get_cookie_button = ttk.Button(action_frame, text="从浏览器获取Cookie", command=self.get_cookies)
        self.get_cookie_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.send_to_ql_button = ttk.Button(action_frame, text="一键发送到青龙", command=self.send_to_ql)
        self.send_to_ql_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Cookie 显示部分
        cookie_frame = ttk.LabelFrame(main_frame, text="获取到的Cookie")
        cookie_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cookie_frame, text="pt_pin:").pack(side=tk.LEFT, padx=5)
        self.pin_label = ttk.Label(cookie_frame, text="N/A", foreground="blue")
        self.pin_label.pack(side=tk.LEFT, padx=5)
        
        self.cookie_text = tk.Text(cookie_frame, height=4, width=80)
        self.cookie_text.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # 日志部分
        log_frame = ttk.LabelFrame(main_frame, text="日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.load_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        self.log_area.insert(tk.END, f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)

    def save_config(self):
        # --- 修改的部分 ---
        config = {
            "ql_url": self.ql_url.get(),
            "ql_client_id": self.ql_client_id.get(),
            "ql_client_secret": self.ql_client_secret.get()
        }
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(config, f, indent=4)
            self.log(f"配置已成功保存到: {self.config_file_path}")
            messagebox.showinfo("成功", "配置已保存！")
        except Exception as e:
            self.log(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def load_config(self):
        # --- 修改的部分 ---
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, "r") as f:
                    config = json.load(f)
                self.ql_url.insert(0, config.get("ql_url", ""))
                self.ql_client_id.insert(0, config.get("ql_client_id", ""))
                self.ql_client_secret.insert(0, config.get("ql_client_secret", ""))
                self.log(f"已从 {self.config_file_path} 加载本地配置。")
        except Exception as e:
            self.log(f"加载配置失败: {e}")

    def open_jd_login(self):
        self.log("正在初始化浏览器...")
        def run():
            try:
                # 使用 webdriver-manager 自动管理 ChromeDriver
                service = ChromeService(executable_path=ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service)
                self.driver.get("https://home.m.jd.com/myJd/home.action")
                self.log("浏览器已打开，请手动登录京东。登录成功后，点击 '从浏览器获取Cookie' 按钮。")
            except Exception as e:
                self.log(f"打开浏览器失败: {e}")
                messagebox.showerror("错误", f"无法打开浏览器，请确保 Chrome 浏览器已安装。\n错误详情: {e}")
        
        threading.Thread(target=run).start()

    def get_cookies(self):
        if not self.driver:
            messagebox.showerror("错误", "浏览器未运行，请先点击 '打开浏览器登录京东'。")
            return

        self.log("正在尝试获取 Cookies...")
        cookies = self.driver.get_cookies()
        pt_key = ""
        pt_pin = ""
        for cookie in cookies:
            if cookie['name'] == 'pt_key':
                pt_key = cookie['value']
            if cookie['name'] == 'pt_pin':
                pt_pin = cookie['value']

        if pt_key and pt_pin:
            self.cookie_text.delete('1.0', tk.END)
            self.cookie_text.insert('1.0', f"pt_key={pt_key};pt_pin={pt_pin};")
            self.pin_label.config(text=pt_pin)
            self.log(f"成功获取到 Cookie，用户名为: {pt_pin}")
        else:
            self.log("获取 Cookie 失败，请确认您已在打开的浏览器中成功登录。")
            messagebox.showwarning("警告", "未能找到 pt_key 或 pt_pin，请确保您已登录。")

    def send_to_ql(self):
        url = self.ql_url.get()
        client_id = self.ql_client_id.get()
        client_secret = self.ql_client_secret.get()
        
        cookie_value = self.cookie_text.get('1.0', tk.END).strip()
        pin = self.pin_label.cget("text")

        if not all([url, client_id, client_secret]):
            messagebox.showerror("错误", "青龙面板配置不完整！")
            return
        
        if "N/A" in pin or not cookie_value:
            messagebox.showerror("错误", "请先获取 Cookie！")
            return
            
        self.log("开始将 Cookie 发送到青龙面板...")
        def run():
            try:
                ql = QLHelper(url, client_id, client_secret)
                self.log(ql.login())
                
                search_value = f"pt_pin={pin}"
                env_id = ql.get_envs(search_value)
                
                if env_id:
                    self.log(f"找到已存在的环境变量，ID: {env_id}，准备更新...")
                    # 备注里加上来源
                    remarks = f"from_macos_tool_{pin}"
                    ql.update_envs(env_id, "JD_COOKIE", cookie_value, remarks)
                    ql.enable_envs(env_id) # 确保是启用状态
                    self.log(f"用户 {pin} 的 Cookie 更新成功！")
                else:
                    self.log(f"未找到用户 {pin} 的环境变量，准备新增...")
                    remarks = f"from_macos_tool_{pin}"
                    ql.add_envs("JD_COOKIE", cookie_value, remarks)
                    self.log(f"用户 {pin} 的 Cookie 新增成功！")
                
                messagebox.showinfo("成功", f"用户 {pin} 的 Cookie 已成功发送到青龙面板！")

            except Exception as e:
                self.log(f"发送失败: {e}")
                messagebox.showerror("发送失败", f"错误详情: {e}")
        
        threading.Thread(target=run).start()

    def on_closing(self):
        if self.driver:
            self.driver.quit()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()