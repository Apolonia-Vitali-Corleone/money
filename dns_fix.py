"""
DNS解析修复模块
解决socket.gethostbyname()失败但urllib可以访问URL的问题
"""

import socket
import urllib.request
import ssl
import re

# 保存原始函数
_original_gethostbyname = socket.gethostbyname
_original_getaddrinfo = socket.getaddrinfo

# DNS缓存
_dns_cache = {}


def _resolve_with_urllib(hostname):
    """使用urllib解析域名获取IP"""
    if hostname in _dns_cache:
        return _dns_cache[hostname]

    try:
        # 尝试通过访问URL来获取IP
        url = f'https://{hostname}'
        req = urllib.request.Request(url, headers={'User-Agent': 'AliyunSDK'})
        context = ssl.create_default_context()

        # 尝试建立连接
        with urllib.request.urlopen(req, timeout=10, context=context) as response:
            # 从socket获取peer地址
            sock = response.fp.raw._sock
            if hasattr(sock, 'getpeername'):
                ip, _ = sock.getpeername()
                _dns_cache[hostname] = ip
                return ip
    except urllib.error.HTTPError as e:
        # HTTP错误但连接成功，从socket获取IP
        if hasattr(e, 'fp') and hasattr(e.fp, 'raw') and hasattr(e.fp.raw, '_sock'):
            try:
                sock = e.fp.raw._sock
                if hasattr(sock, 'getpeername'):
                    ip, _ = sock.getpeername()
                    _dns_cache[hostname] = ip
                    return ip
            except:
                pass
    except urllib.error.URLError as e:
        # 尝试从错误信息中提取IP
        if hasattr(e, 'reason') and hasattr(e.reason, 'errno'):
            pass
    except Exception as e:
        pass

    # 如果urllib也失败，使用一些已知的映射
    known_hosts = {
        'nls-filetrans.cn-shanghai.aliyuncs.com': '47.98.42.42',
        'oss-cn-shanghai.aliyuncs.com': '139.224.251.229',
    }

    if hostname in known_hosts:
        ip = known_hosts[hostname]
        _dns_cache[hostname] = ip
        return ip

    # 最后尝试原始方法
    return _original_gethostbyname(hostname)


def patched_gethostbyname(hostname):
    """替换socket.gethostbyname的版本"""
    try:
        # 先尝试原始方法
        return _original_gethostbyname(hostname)
    except socket.gaierror:
        # 如果失败，使用urllib方法
        return _resolve_with_urllib(hostname)


def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """替换socket.getaddrinfo的版本"""
    try:
        # 先尝试原始方法
        return _original_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        # 如果失败，手动构造结果
        try:
            ip = _resolve_with_urllib(host)
            # 返回getaddrinfo格式的结果
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))
            ]
        except:
            raise socket.gaierror(f"无法解析主机名: {host}")


def apply_dns_fix():
    """应用DNS修复补丁"""
    socket.gethostbyname = patched_gethostbyname
    socket.getaddrinfo = patched_getaddrinfo
    print("✓ DNS修复补丁已应用")


def restore_dns():
    """恢复原始DNS函数"""
    socket.gethostbyname = _original_gethostbyname
    socket.getaddrinfo = _original_getaddrinfo
    print("✓ DNS函数已恢复")


# 自动应用补丁
if __name__ != "__main__":
    apply_dns_fix()
