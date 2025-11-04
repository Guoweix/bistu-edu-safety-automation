# 微伴学习平台自动化脚本

本脚本适用于北京信息科技大学的研究生安全教育学习,全部内容由ai完成,此readme也是如此.只保证2025年11月4日这个时间点可用,不会有后续更新.


自动完成微伴学习平台（weiban.mycourse.cn）的课程学习任务。

## 功能特性

- ✅ 支持手动登录（网站不保持Cookie会话）
- ✅ 自动遍历所有课程模块
- ✅ 自动识别未完成的课程
- ✅ 自动点击课程并执行完成操作
- ✅ 支持视频课程和交互式课程两种类型
- ✅ 自动处理 iframe 内容
- ✅ DOM 刷新自动恢复

## 环境要求

- Python 3.8+
- 推荐使用 Python 3.13

## 安装步骤

### 1. 克隆或下载项目

```bash
cd /path/to/your/project
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv spider_venv
source spider_venv/bin/activate  # Linux/Mac
# 或
spider_venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装 Chromium 浏览器

```bash
playwright install chromium
```

## 使用方法

### 运行脚本

```bash
python weiban_spider.py
```

### 操作流程

1. 脚本会自动打开浏览器
2. **手动完成登录**（网站每次都需要重新登录）
3. 脚本自动检测登录状态（最多等待120秒）
4. 登录成功后自动开始处理课程
5. 脚本会：
   - 自动点击实验室图片
   - 选择目标课程
   - 遍历所有模块
   - 查找未完成的课程项
   - 自动点击并完成课程
   - 处理完成后返回列表
   - 继续下一个课程



## 项目结构

```
.
├── weiban_spider.py      # 主脚本
├── requirements.txt      # Python依赖
├── README.md            # 说明文档
└── spider_venv/         # 虚拟环境目录（可选）
```

## 依赖说明

- **playwright**: 浏览器自动化框架
  - 版本要求: >=1.48.0（兼容 Python 3.13）

## 常见问题

### 1. 安装 playwright 时出错

确保 Python 版本 >= 3.8，推荐使用 3.13。

### 2. Chromium 下载失败

可以手动指定下载源：

```bash
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/ playwright install chromium
```

### 3. 登录超时

脚本默认等待120秒，如果网络较慢可以修改 `login_timeout` 参数：

```python
spider = WeibanSpider(headless=False, login_timeout=300)  # 改为5分钟
```

### 4. 课程点击失败

脚本已内置多种点击方法（直接点击、强制点击、JavaScript点击），如仍失败可能是：
- 页面结构变化
- 网络延迟过大
- 元素被其他内容遮挡

建议检查脚本输出的调试信息。

## 注意事项

⚠️ **重要提醒**：

1. 本脚本仅供学习交流使用
2. 请遵守平台使用规则
3. 不要频繁运行，避免对服务器造成压力
4. 建议在课程处理间隔中适当增加等待时间

## 技术栈

- Python 3.13
- Playwright (异步API)
- Chromium 浏览器

## 许可证

MIT License


