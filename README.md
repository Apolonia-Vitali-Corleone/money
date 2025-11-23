# 视频中文字幕工具

自动为视频添加中文字幕，使用阿里云语音识别服务

## 功能特性

- 📹 支持多种视频格式（MP4, AVI, MOV, MKV等）
- 🎤 使用阿里云语音识别服务，识别准确率高
- 📝 自动生成SRT字幕文件
- 🎬 使用FFmpeg将字幕烧录到视频
- 🌐 提供Web界面（Gradio），操作简单
- 🖥️ 支持命令行工具，适合批处理

## 前置要求

### 系统依赖

- **FFmpeg**（必需）
- **Python 3.7+**

### 阿里云配置

- 阿里云账号
- 开通语音识别服务
- 创建OSS存储桶
- 获取AccessKey和AppKey

详细配置步骤请查看：[阿里云配置指南](ALIBABA_SETUP.md)

## 安装

### 1. 安装FFmpeg

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# MacOS
brew install ffmpeg

# Windows
# 下载自 https://ffmpeg.org/download.html
# 下载后需要添加到系统环境变量PATH中
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法一：Web界面（推荐）

适合Windows用户和不熟悉命令行的用户。

1. 启动Web界面：

```bash
python gradio_app.py
```

2. 在浏览器访问：`http://localhost:19977`

3. 在界面中填写：
   - 视频文件路径
   - 阿里云AccessKey ID
   - 阿里云AccessKey Secret
   - 语音识别AppKey
   - OSS存储桶名称
   - 地域（默认：cn-shanghai）

4. 点击"开始处理"，等待完成后下载结果

### 方法二：命令行工具

适合开发者和需要批处理的场景。

1. 配置环境变量：

```bash
# Linux/Mac
export ALIBABA_ACCESS_KEY_ID='你的AccessKey ID'
export ALIBABA_ACCESS_KEY_SECRET='你的AccessKey Secret'
export ALIBABA_APP_KEY='你的AppKey'
export ALIBABA_OSS_BUCKET='你的Bucket名称'
export ALIBABA_REGION='cn-shanghai'  # 可选
```

```powershell
# Windows PowerShell
$env:ALIBABA_ACCESS_KEY_ID='你的AccessKey ID'
$env:ALIBABA_ACCESS_KEY_SECRET='你的AccessKey Secret'
$env:ALIBABA_APP_KEY='你的AppKey'
$env:ALIBABA_OSS_BUCKET='你的Bucket名称'
$env:ALIBABA_REGION='cn-shanghai'  # 可选
```

2. 运行命令：

```bash
python add_chinese_subtitle.py video.mp4
```

3. 输出文件：`video_字幕版.mp4` 和 `video_zh.srt`

## 工作流程

```
视频输入
  ↓
1. 提取音频（MP3格式）
  ↓
2. 上传音频到阿里云OSS
  ↓
3. 提交语音识别任务
  ↓
4. 等待识别完成
  ↓
5. 生成SRT字幕文件
  ↓
6. 将字幕烧录到视频
  ↓
7. 清理临时文件
  ↓
输出带字幕的视频
```

## 支持的格式

- **输入视频**：MP4, AVI, MOV, MKV等FFmpeg支持的格式
- **输出视频**：MP4格式（带嵌入式字幕）
- **字幕格式**：SRT（SubRip）

## 配置文档

- [阿里云配置指南](ALIBABA_SETUP.md) - 详细的阿里云服务配置步骤
- [GPU加速指南](GPU_SETUP.md) - GPU相关配置（本项目不需要GPU）

## 注意事项

- ⚠️ 使用阿里云服务会产生费用（每月前2小时免费）
- ⚠️ 确保AccessKey安全，不要泄露或提交到代码仓库
- ⚠️ 处理时间取决于视频长度和网络速度
- ⚠️ 音频文件会临时上传到OSS，处理完自动删除
- ⚠️ 需要足够的磁盘空间存储临时文件

## 常见问题

### Q: 为什么选择阿里云语音识别？

A: 阿里云语音识别服务提供高准确率的中文识别，支持多种方言和口音，识别效果优于本地模型。

### Q: 费用如何计算？

A: 每月前2小时免费，超出部分约￥0.025/分钟。详见[费用说明](ALIBABA_SETUP.md#费用说明)。

### Q: 是否支持其他语言？

A: 当前版本专注于中文识别，阿里云也支持其他语言，可以修改代码中的language参数。

### Q: 可以批量处理视频吗？

A: 可以，使用命令行工具配合shell脚本即可批量处理。

### Q: 为什么需要OSS？

A: 阿里云语音识别服务要求音频文件通过URL访问，因此需要先上传到OSS。

## 项目结构

```
.
├── add_chinese_subtitle.py   # 命令行工具
├── gradio_app.py             # Web界面
├── requirements.txt          # Python依赖
├── README.md                 # 项目说明
├── ALIBABA_SETUP.md          # 阿里云配置指南
└── GPU_SETUP.md              # GPU配置（已废弃）
```

## 更新日志

### v2.0.0 (最新)
- 重构项目，使用阿里云语音识别服务
- 移除Whisper本地识别方案
- 更新Web界面配置方式
- 添加详细的阿里云配置文档

### v1.0.0
- 初始版本，使用OpenAI Whisper
- 支持GPU加速
- 提供Web界面

## 技术栈

- **语音识别**：阿里云语音识别服务
- **视频处理**：FFmpeg
- **Web框架**：Gradio
- **开发语言**：Python 3

## 许可证

MIT License

## 相关链接

- [阿里云语音识别服务](https://www.aliyun.com/product/nls)
- [FFmpeg官网](https://ffmpeg.org/)
- [Gradio文档](https://www.gradio.app/docs/)

## 技术支持

如有问题，请：
1. 查看[阿里云配置指南](ALIBABA_SETUP.md)
2. 查看[常见问题](#常见问题)
3. 提交Issue到项目仓库
