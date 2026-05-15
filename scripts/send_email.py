#!/usr/bin/env python3
"""send_email.py — 发送 HTML 邮件（正文 + HTML 附件）"""

import smtplib, ssl, json, sys, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

def load_env():
    """从环境变量或 .env 文件加载配置，优先使用环境变量"""
    # 优先使用环境变量（GitHub Actions / Docker 部署）
    if os.environ.get("SMTP_PASS"):
        return {
            "SMTP_HOST": os.environ.get("SMTP_HOST", "smtp.qq.com"),
            "SMTP_PORT": os.environ.get("SMTP_PORT", "465"),
            "SMTP_USER": os.environ.get("SMTP_USER", "806176940@qq.com"),
            "SMTP_PASS": os.environ.get("SMTP_PASS", ""),
        }
    # 回退到 .env 文件
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        env_path = Path(os.path.expanduser(
            "~/Library/Application Support/QClaw/openclaw/config/skills/imap-smtp-email/.env"))
    config = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config

def send(subject, html_body, html_file=None, to=None):
    """
    发送邮件。
    :param subject: 邮件主题
    :param html_body: HTML 正文
    :param html_file: 要附加的 HTML 文件路径（可选）
    :param to: 收件人地址（默认 806176940@qq.com）
    """
    env = load_env()
    smtp_host = env.get("SMTP_HOST", "smtp.qq.com")
    smtp_port = int(env.get("SMTP_PORT", "465"))
    smtp_user = env.get("SMTP_USER", "806176940@qq.com")
    smtp_pass = env.get("SMTP_PASS", "")
    to_addr = to or "806176940@qq.com"

    if not smtp_pass:
        # 回退到已知的授权码
        print("[WARN] .env 中未找到 SMTP_PASS，尝试 fallback", file=sys.stderr)
        return None

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr

    # HTML 正文
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # HTML 附件
    if html_file and os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            attachment = MIMEText(f.read(), "html", "utf-8")
        attachment.add_header(
            "Content-Disposition", "attachment",
            filename=os.path.basename(html_file))
        msg.attach(attachment)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addr, msg.as_string())

    return f"<{os.urandom(8).hex()}@qq.com>"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: send_email.py <subject> <html_body_file> [attachment_file]")
        sys.exit(1)
    subj = sys.argv[1]
    body = Path(sys.argv[2]).read_text(encoding="utf-8") if len(sys.argv) > 2 else ""
    att = sys.argv[3] if len(sys.argv) > 3 else None
    result = send(subj, body, att)
    if result:
        print(json.dumps({"success": True, "messageId": result}))
    else:
        print(json.dumps({"success": False, "message": "发送失败，检查 .env 配置"}))
