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
python add_chinese_subtitle.py <视频文件路径>
```

**示例：**
```bash
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

- 首次运行会下载Whisper模型（约140MB）
- 处理时间取决于视频长度
- 需要足够的磁盘空间存储临时音频文件

## 许可

MIT License
