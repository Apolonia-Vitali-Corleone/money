# 视频字幕工具

自动为视频添加字幕，支持中文和英语识别（阿里云语音识别服务）

## 功能特性

- 📹 支持多种视频格式（MP4, AVI, MOV, MKV等）
- 🎤 使用阿里云语音识别服务，识别准确率高
- 🌍 支持中文和英语识别，可扩展更多语言
- 📝 自动生成SRT字幕文件
- 🎬 使用FFmpeg将字幕烧录到视频
- 🌐 提供Web界面（Gradio），操作简单
- 🖥️ 支持命令行工具，适合批处理
- ⚡ 智能缓存：自动检测已处理文件，避免重复上传
- 🎯 高质量音频：优化采样率和比特率，提升识别准确度

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

3. 输出文件：`video_字幕版.mp4` 和 `video_zh.srt`（或 `video_en.srt`）

## 系统架构

### 设计原则

本项目遵循**最小化云端操作**的原则：
- ✅ **本地处理**：音频提取、字幕烧录、文件管理全部在本地完成
- ☁️ **云端识别**：只有语音转文字这一步使用阿里云服务（本地ASR准确度不足）
- 💰 **成本优化**：智能缓存，避免重复上传和识别，节省费用
- 🔒 **数据安全**：视频文件不上传，只上传提取的音频

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户本地环境                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣ 输入视频 (video.mp4)                                        │
│       ↓                                                         │
│  2️⃣ 【本地】生成OSS对象名称 (基于视频hash)                        │
│       ↓                                                         │
│  3️⃣ 【检查】OSS是否已有该音频？                                   │
│       ├─ 是 → 跳过步骤4，直接获取URL                              │
│       └─ 否 → 继续                                               │
│             ↓                                                   │
│  4️⃣ 【本地】用FFmpeg提取音频 → audio.mp3                         │
│       ↓         (16kHz, 单声道, 128kbps, 高质量)                 │
│  5️⃣ 【上传】音频到阿里云OSS                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                         阿里云服务                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  6️⃣ 【云端】提交语音识别任务                                     │
│       - 语言：中文/英语                                          │
│       - 参数：标点符号、语义断句、ITN等                           │
│       ↓                                                         │
│  7️⃣ 【云端】等待识别完成（轮询状态）                              │
│       ↓                                                         │
│  8️⃣ 【云端】返回识别结果（JSON格式）                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                         用户本地环境                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  9️⃣ 【本地】解析JSON，生成SRT字幕文件                            │
│       ↓                                                         │
│  🔟 【本地】用FFmpeg将字幕烧录到视频                              │
│       ↓                                                         │
│  ✅ 输出：video_字幕版.mp4 + video_zh.srt                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 核心优化

#### 1. 智能缓存机制
- **问题**：同一视频多次处理会浪费时间和金钱
- **方案**：基于视频文件MD5生成唯一的OSS对象名称
- **效果**：第二次处理同一视频时，直接复用云端音频，跳过提取和上传

#### 2. 先检查后提取
- **问题**：传统流程是"提取 → 上传 → 检查是否重复"
- **方案**：先检查OSS，确认不存在才提取音频
- **效果**：避免不必要的FFmpeg操作，节省本地计算资源

#### 3. 高质量音频参数
| 参数 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| 采样率 | 16kHz | 16kHz | 语音识别标准（保持不变） |
| 比特率 | 64kbps | 128kbps | **提升2倍**，保留更多音频细节 |
| 质量等级 | 无 | 2 | MP3高质量编码（0-9，2为高质量） |

#### 4. 识别参数优化
```python
{
    "enable_words": True,                      # 词级时间戳
    "enable_punctuation_prediction": True,     # 自动标点
    "enable_semantic_sentence_detection": True,# 语义断句
    "enable_inverse_text_normalization": True, # 数字格式化
    "max_single_segment_time": 15000,          # 长句支持（15秒）
    "language_hints": ["en-US"]                # 英语优化（针对英语视频）
}
```

## 工作流程（详细）

### 命令行工具

```bash
# 中文识别（默认）
python add_chinese_subtitle.py video.mp4

# 英语识别
python add_chinese_subtitle.py video.mp4 en
```

**处理流程：**
1. 检查云端是否已有音频文件（基于视频MD5）
2. 如果没有：本地提取音频 → 上传到OSS
3. 如果有：跳过提取和上传，直接使用
4. 提交阿里云语音识别任务
5. 轮询等待识别完成
6. 本地生成SRT字幕文件
7. 本地用FFmpeg烧录字幕到视频
8. 清理临时文件

### Web界面

1. 启动服务：`python gradio_app.py`
2. 访问：`http://localhost:19977`
3. 填写配置并上传视频
4. 选择识别语言（中文/英语）
5. 等待处理完成
6. 下载带字幕视频和SRT文件

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

A: 当前支持中文和英语。通过命令行指定语言参数：
```bash
python add_chinese_subtitle.py video.mp4 zh  # 中文
python add_chinese_subtitle.py video.mp4 en  # 英语
```
阿里云还支持其他语言（日语、韩语等），可以修改 `aliyun_transcription.py` 中的 `language_hints` 参数扩展。

### Q: 可以批量处理视频吗？

A: 可以，使用命令行工具配合shell脚本即可批量处理。

### Q: 为什么需要OSS？

A: 阿里云语音识别服务要求音频文件通过URL访问，因此需要先上传到OSS。

### Q: 识别准确度如何提升？

A: 本项目已做以下优化：
- **音频质量**：128kbps比特率，保留更多音频细节
- **高级参数**：启用标点符号、语义断句、ITN格式化
- **语言指定**：明确指定语言（中文/英语），避免混淆

如识别效果仍不理想，建议：
1. 确保视频音频清晰，无严重背景噪音
2. 对于专业术语，可联系开发者添加热词支持
3. 尝试提高视频原始音质

### Q: 为什么要上传音频到云端？

A: 本地语音识别模型（如Whisper）准确度不足，特别是对中文、专业术语的识别。阿里云ASR服务具有：
- 大规模训练数据（数百万小时）
- 持续更新的语言模型
- 针对中文优化的声学模型
- 标点符号、语义断句等高级功能

**隐私保护**：只上传音频（不上传视频），且可随时从OSS删除。

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
