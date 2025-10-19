#!/usr/bin/env python3
"""
Gmail SMTP 连接测试脚本
用于诊断邮件发送问题
"""
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 从环境变量或配置文件读取
try:
    from commercial.shared.config import settings
    SMTP_HOST = settings.SMTP_HOST
    SMTP_PORT = settings.SMTP_PORT
    SMTP_USE_SSL = settings.SMTP_USE_SSL
    SMTP_USER = settings.SMTP_USER
    SMTP_PASSWORD = settings.SMTP_PASSWORD
    SMTP_FROM_EMAIL = settings.SMTP_FROM_EMAIL
    SMTP_FROM_NAME = settings.SMTP_FROM_NAME
except Exception as e:
    print(f"❌ 无法加载配置: {e}")
    sys.exit(1)


def test_smtp_connection():
    """测试 SMTP 连接"""
    print("=" * 70)
    print("Gmail SMTP 连接测试")
    print("=" * 70)
    print()

    print("📋 配置信息:")
    print(f"  SMTP 服务器: {SMTP_HOST}:{SMTP_PORT}")
    print(f"  连接方式: {'SSL' if SMTP_USE_SSL else 'STARTTLS'}")
    print(f"  用户名: {SMTP_USER}")
    print(f"  密码: {'*' * 8} (已设置)" if SMTP_PASSWORD else "  密码: ❌ 未设置")
    print(f"  发件人: {SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>")
    print()

    # 检查必要配置
    if not SMTP_USER or not SMTP_PASSWORD:
        print("❌ 错误: SMTP 用户名或密码未配置")
        return False

    # 步骤 1: 测试网络连接
    print("=" * 70)
    print("步骤 1/4: 测试网络连接到 SMTP 服务器")
    print("-" * 70)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((SMTP_HOST, SMTP_PORT))
        sock.close()

        if result == 0:
            print(f"✅ 成功连接到 {SMTP_HOST}:{SMTP_PORT}")
        else:
            print(f"❌ 无法连接到 {SMTP_HOST}:{SMTP_PORT}")
            print(f"   错误代码: {result}")
            print(f"   可能原因: 防火墙封禁、网络不通")
            return False
    except Exception as e:
        print(f"❌ 网络连接失败: {e}")
        return False
    print()

    # 步骤 2: 建立 SMTP 连接
    print("=" * 70)
    print("步骤 2/4: 建立 SMTP 连接")
    print("-" * 70)
    try:
        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
            print(f"✅ SMTP_SSL 连接已建立")
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            print(f"✅ SMTP 连接已建立")
        server.set_debuglevel(1)  # 开启调试信息
    except smtplib.SMTPConnectError as e:
        print(f"❌ SMTP 连接错误: {e}")
        print()
        print("可能的原因:")
        print("  1. 服务器 IP 被标记为可疑")
        print("  2. 防火墙规则阻止")
        print("  3. SMTP 服务器暂时不可用")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {type(e).__name__}: {e}")
        print()
        # 尝试原始 socket 连接获取更多信息
        print("尝试原始 socket 连接诊断...")
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((SMTP_HOST, SMTP_PORT))
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            print(f"服务器响应: {response.strip()}")
            sock.close()
        except Exception as socket_err:
            print(f"Socket 连接也失败: {socket_err}")
        return False
    print()

    # 步骤 3: 启用 TLS（仅STARTTLS需要）
    if not SMTP_USE_SSL:
        print("=" * 70)
        print("步骤 3/4: 启用 TLS 加密")
        print("-" * 70)
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
            print(f"✅ TLS 加密已启用")
        except smtplib.SMTPException as e:
            print(f"❌ TLS 启动失败: {e}")
            server.quit()
            return False
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            server.quit()
            return False
        print()
    else:
        print("=" * 70)
        print("步骤 3/4: SSL 加密")
        print("-" * 70)
        print(f"✅ 已使用 SSL 加密连接（465端口）")
        print()

    # 步骤 4: 登录认证
    print("=" * 70)
    print("步骤 4/4: 登录认证")
    print("-" * 70)
    try:
        server.login(SMTP_USER, SMTP_PASSWORD)
        print(f"✅ 登录成功")
        print()
        print("🎉 所有测试通过！")
        print()

        # 尝试发送测试邮件
        print("=" * 70)
        print("发送测试邮件")
        print("-" * 70)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'SMTP 测试邮件'
        msg['From'] = f'{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>'
        msg['To'] = SMTP_USER  # 发送给自己

        text = f"""
这是一封测试邮件。

如果你收到这封邮件，说明 SMTP 配置正常。

时间: {MIMEText.__module__}
        """

        part = MIMEText(text, 'plain', 'utf-8')
        msg.attach(part)

        server.send_message(msg)
        print(f"✅ 测试邮件已发送到: {SMTP_USER}")
        print(f"   请检查你的邮箱（包括垃圾邮件）")

        server.quit()
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        print()
        print("可能的原因:")
        print("  1. 密码错误")
        print("  2. Gmail 需要使用「应用专用密码」而不是账号密码")
        print("  3. 账号未启用「两步验证」（应用专用密码需要先启用两步验证）")
        print()
        print("解决方案:")
        print("  1. 前往 https://myaccount.google.com/security")
        print("  2. 启用「两步验证」")
        print("  3. 前往 https://myaccount.google.com/apppasswords")
        print("  4. 创建新的应用专用密码")
        print("  5. 使用该密码替换 .env 文件中的 SMTP_PASSWORD")
        server.quit()
        return False

    except smtplib.SMTPException as e:
        print(f"❌ SMTP 错误: {e}")
        server.quit()
        return False

    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        server.quit()
        return False


if __name__ == "__main__":
    print()
    success = test_smtp_connection()
    print()
    print("=" * 70)
    if success:
        print("✅ 测试结果: 通过")
        print("   SMTP 配置正常，可以发送邮件")
    else:
        print("❌ 测试结果: 失败")
        print("   请根据上述错误信息修复配置")
    print("=" * 70)
    print()

    sys.exit(0 if success else 1)
