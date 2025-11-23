# 视频中文字幕工具

自动为视频添加中文字幕

## 功能
- 输入：MP4或其他视频格式
- 输出：带有中文字幕的视频
- 使用OpenAI Whisper进行语音识别
- 自动生成SRT字幕文件
- 使用FFmpeg将字幕烧录到视频

## 安装

### 1. 安装依赖

```bash
# 安装FFmpeg（必需）
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# MacOS
brew install ffmpeg

# Windows - 下载自 https://ffmpeg.org/download.html

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 使用方法

```bash
python add_chinese_subtitle.py <视频文件路径> [模型路径]
```

**示例：**
```bash
# 使用本地large-v3模型（推荐，不需要下载）
python add_chinese_subtitle.py video.mp4 /path/to/large-v3.pt

# 或使用默认base模型（首次会自动下载）
python add_chinese_subtitle.py video.mp4
```

输出文件：`video_字幕版.mp4`

## 工作流程

1. **提取音频** - 从视频中提取音频流
2. **语音识别** - 使用Whisper识别音频内容并转为中文文字
3. **生成字幕** - 创建SRT格式字幕文件
4. **合成视频** - 使用FFmpeg将字幕烧录到视频中

## 支持的格式

- 输入：MP4, AVI, MOV, MKV等常见视频格式
- 输出：MP4格式（带嵌入式字幕）

## 注意事项

- **推荐使用本地模型**：如果你已有 `large-v3.pt` 模型文件，直接指定路径即可，无需下载
- 如不指定模型路径，首次运行会自动下载base模型（约140MB）
- large-v3 模型识别准确率更高，适合生产使用
- 处理时间取决于视频长度和模型大小
- 需要足够的磁盘空间存储临时音频文件

## 许可

MIT License
