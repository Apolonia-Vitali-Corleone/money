#!/usr/bin/env python3
"""
网络诊断工具 - 检查阿里云服务连通性
"""

import socket
import subprocess
import sys

def test_dns_resolution():
    """测试DNS解析"""
    print("=" * 60)
    print("1. DNS解析测试")
    print("=" * 60)

    domains = [
        'nls-filetrans.cn-shanghai.aliyuncs.com',
        'oss-cn-shanghai.aliyuncs.com',
        'www.aliyun.com',
        'www.baidu.com',
        'www.google.com'
    ]

    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"✓ {domain} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ {domain} -> 解析失败: {e}")
    print()


def test_ping():
    """测试网络连通性"""
    print("=" * 60)
    print("2. 网络连通性测试（Ping）")
    print("=" * 60)

    hosts = [
        'nls-filetrans.cn-shanghai.aliyuncs.com',
        'oss-cn-shanghai.aliyuncs.com',
        'www.baidu.com'
    ]

    for host in hosts:
        try:
            # Windows使用 -n，Linux使用 -c
            param = '-n' if sys.platform.startswith('win') else '-c'
            result = subprocess.run(
                ['ping', param, '1', host],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ {host} - 可以连接")
            else:
                print(f"❌ {host} - 无法连接")
        except subprocess.TimeoutExpired:
            print(f"❌ {host} - 超时")
        except Exception as e:
            print(f"❌ {host} - 错误: {e}")
    print()


def test_https_connection():
    """测试HTTPS连接"""
    print("=" * 60)
    print("3. HTTPS连接测试")
    print("=" * 60)

    try:
        import urllib.request
        import ssl

        # 创建SSL上下文
        context = ssl.create_default_context()

        urls = [
            'https://www.aliyun.com',
            'https://oss-cn-shanghai.aliyuncs.com',
        ]

        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10, context=context) as response:
                    status = response.status
                    print(f"✓ {url} - HTTP {status}")
            except Exception as e:
                print(f"❌ {url} - 失败: {e}")
    except ImportError:
        print("urllib不可用，跳过HTTPS测试")
    print()


def check_dns_servers():
    """检查DNS服务器配置"""
    print("=" * 60)
    print("4. DNS服务器配置")
    print("=" * 60)

    if sys.platform.startswith('win'):
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if 'DNS' in line and 'Servers' in line:
                    print(line.strip())
                elif line.strip().startswith('2') or line.strip().startswith('1'):
                    # 可能是DNS服务器IP
                    if '.' in line or ':' in line:
                        print(line.strip())
        except Exception as e:
            print(f"无法获取DNS配置: {e}")
    else:
        try:
            with open('/etc/resolv.conf', 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"无法读取DNS配置: {e}")
    print()


def print_solutions():
    """打印解决方案"""
    print("=" * 60)
    print("解决方案建议")
    print("=" * 60)
    print("""
根据测试结果，尝试以下解决方案：

方案1: 更换DNS服务器
  Windows:
    1. 打开"控制面板" -> "网络和Internet" -> "网络连接"
    2. 右键点击你的网络连接 -> "属性"
    3. 选择"Internet协议版本4(TCP/IPv4)" -> "属性"
    4. 选择"使用下面的DNS服务器地址"
    5. 首选DNS服务器: 8.8.8.8
    6. 备用DNS服务器: 114.114.114.114
    7. 点击"确定"保存

  Linux/Mac:
    sudo nano /etc/resolv.conf
    添加以下行：
    nameserver 8.8.8.8
    nameserver 114.114.114.114

方案2: 检查防火墙/安全软件
  - 暂时关闭防火墙或安全软件测试
  - 将Python添加到白名单

方案3: 检查代理设置
  - 如果你在公司网络，可能需要配置HTTP代理
  - 检查环境变量: HTTP_PROXY, HTTPS_PROXY

方案4: 使用VPN
  - 如果网络限制访问阿里云，尝试使用VPN

方案5: 尝试其他地域
  - 将region从 'cn-shanghai' 改为 'cn-beijing' 或其他地域
  - 修改代码中的region参数

方案6: 检查hosts文件
  - Windows: C:\\Windows\\System32\\drivers\\etc\\hosts
  - Linux/Mac: /etc/hosts
  - 确保没有阻止阿里云域名的条目
""")


def main():
    print("\n" + "=" * 60)
    print("阿里云NLS服务网络诊断工具")
    print("=" * 60 + "\n")

    test_dns_resolution()
    test_ping()
    test_https_connection()
    check_dns_servers()
    print_solutions()

    print("=" * 60)
    print("诊断完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
