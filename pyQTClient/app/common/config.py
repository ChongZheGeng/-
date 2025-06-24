# coding:utf-8
import sys
import os
import json
import base64
from enum import Enum
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from PyQt5.QtCore import QLocale
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, Theme, FolderValidator, ConfigSerializer, __version__)


# 加密密钥和初始向量，实际应用中应该使用更安全的方式存储
ENCRYPTION_KEY = b'ComplexKey123456' # 16字节AES-128密钥
ENCRYPTION_IV = b'InitVector987654' # 16字节初始向量

def encrypt_data(data_string):
    """使用AES-CBC模式加密字符串"""
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, ENCRYPTION_IV)
    padded_data = pad(data_string.encode('utf-8'), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted_data).decode('utf-8')

def decrypt_data(encrypted_string):
    """解密AES-CBC加密的字符串"""
    try:
        encrypted_data = base64.b64decode(encrypted_string)
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, ENCRYPTION_IV)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return decrypted_data.decode('utf-8')
    except Exception:
        return ""  # 解密失败则返回空字符串


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class Config(QConfig):
    """ Config of application """

    # folders
    musicFolders = ConfigItem(
        "Folders", "LocalMusic", [], FolderListValidator())
    downloadFolder = ConfigItem(
        "Folders", "Download", "app/download", FolderValidator())

    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # Material
    blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())

    #
    # Login
    #
    rememberMe = ConfigItem("Login", "rememberMe", False)
    username = ConfigItem("Login", "username", "")
    password = ConfigItem("Login", "password", "")
    
    # WebDAV
    webdavEnabled = ConfigItem("WebDAV", "Enabled", False, BoolValidator())
    webdavUrl = ConfigItem("WebDAV", "Url", "")
    webdavUsername = ConfigItem("WebDAV", "Username", "")
    webdavPassword = ConfigItem("WebDAV", "Password", "")  # 加密存储


YEAR = 2023
AUTHOR = "zhiyiYo"
VERSION = __version__
HELP_URL = "https://qfluentwidgets.com"
REPO_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets"
EXAMPLE_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets/tree/master/examples"
FEEDBACK_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets/issues"
RELEASE_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets/releases/latest"
ZH_SUPPORT_URL = "https://qfluentwidgets.com/zh/price/"
EN_SUPPORT_URL = "https://qfluentwidgets.com/price/"


cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load('app/config/config.json', cfg)

# 运行时状态，不保存到文件
IS_ADMIN = False

def set_admin_status(is_admin):
    """设置管理员状态，并打印调试信息"""
    global IS_ADMIN
    IS_ADMIN = bool(is_admin)
    print(f"设置管理员状态: IS_ADMIN = {IS_ADMIN}")

# 添加WebDAV相关的安全方法
def save_webdav_credentials(url, username, password, enabled=True):
    """安全保存WebDAV凭据"""
    cfg.webdavUrl.value = url
    cfg.webdavUsername.value = username
    cfg.webdavPassword.value = encrypt_data(password)
    cfg.webdavEnabled.value = enabled
    qconfig.save()

def get_webdav_credentials():
    """获取WebDAV凭据"""
    if not cfg.webdavEnabled.value:
        return None
    
    return {
        'url': cfg.webdavUrl.value,
        'username': cfg.webdavUsername.value,
        'password': decrypt_data(cfg.webdavPassword.value) if cfg.webdavPassword.value else "",
        'enabled': cfg.webdavEnabled.value
    }

def test_webdav_connection(url, username, password):
    """测试WebDAV连接，返回(bool, str)表示是否成功及错误信息"""
    try:
        from webdav4.client import Client
        
        client = Client(
            base_url=url,
            auth=(username, password),
            timeout=10
        )
        
        # 尝试列出根目录的内容来验证连接
        client.ls("/")
        return True, "连接成功"
    except Exception as e:
        return False, f"连接失败: {str(e)}"