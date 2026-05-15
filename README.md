# 📰 News Digest — 每日新闻摘要自动推送

每日自动采集科技/经济/国际新闻，生成精美 HTML 邮件推送到邮箱。

## 功能

- 📡 RSS 采集 + 搜索补充，覆盖中英文新闻源
- 🖼️ 自动生成固定尺寸 Hero 大图（不依赖外部图片）
- 📧 HTML 邮件发送（正文 + HTML 附件）
- ⏰ 定时任务自动执行

## 项目结构

```
news_digest/
├── scripts/
│   ├── fetch_news.py      # 主脚本：采集 + 生成 + 发送
│   ├── generate_hero.py   # Hero 大图生成
│   └── send_email.py      # 邮件发送（含附件）
├── config/
│   └── sources.json       # RSS 源配置
├── templates/
│   └── email.html         # HTML 邮件模板（Python 格式化用）
├── output/                # 生成的文件（.gitignore）
├── .env                   # 邮箱配置（不入库）
├── .gitignore
└── README.md
```

## 使用

```bash
# 手动执行一次
python3 scripts/fetch_news.py

# 仅生成 Hero 图
python3 scripts/generate_hero.py "今日头条标题"
```

## 定时任务

通过 OpenClaw cron 每天 9:00 自动执行，任务 ID: `63b87cca-f097-4ed9-ace4-dc1d8af50f9b`

## 数据源

| 分类 | 来源 | 类型 |
|------|------|------|
| 科技 | 36氪、TechCrunch、NPR Tech | RSS |
| 经济 | NPR Business | RSS |
| 国际 | NPR World | RSS |
| 补充 | prosearch 搜索 | API |

## 邮箱配置

首次使用需配置 `.env`：

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=806176940@qq.com
SMTP_PASS=你的授权码
```
