#!/usr/bin/env python3
"""
视频中文字幕工具
输入：视频文件（MP4等格式）
输出：带中文字幕的视频
"""

import os
import sys
import subprocess
from pathlib import Path

def extract_audio(video_path, audio_path):
    """从视频中提取音频"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        audio_path, '-y'
    ]
    subprocess.run(cmd, check=True)

def transcribe_audio(audio_path, model_path=None):
    """使用Whisper识别音频并生成中文字幕"""
    try:
        import whisper
        print("加载Whisper模型...")

        if model_path and os.path.exists(model_path):
            # 使用本地模型文件
            print(f"使用本地模型: {model_path}")
            model = whisper.load_model(model_path)
        else:
            # 默认使用base模型
            model = whisper.load_model("base")

        print("识别音频中...")
        result = model.transcribe(audio_path, language="zh")

        return result["segments"]
    except ImportError:
        print("错误: 需要安装openai-whisper")
        print("运行: pip install openai-whisper")
        sys.exit(1)

def segments_to_srt(segments, srt_path):
    """将识别结果转换为SRT字幕格式"""
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = format_timestamp(segment['start'])
            end = format_timestamp(segment['end'])
            text = segment['text'].strip()

            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")

def format_timestamp(seconds):
    """格式化时间戳为SRT格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def add_subtitle_to_video(video_path, srt_path, output_path):
    """将字幕烧录到视频中"""
    # 转义字幕路径（Windows兼容）
    srt_path_escaped = srt_path.replace('\\', '/').replace(':', '\\:')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"subtitles={srt_path_escaped}",
        '-c:a', 'copy',
        output_path, '-y'
    ]
    subprocess.run(cmd, check=True)

def main():
    if len(sys.argv) < 2:
        print("用法: python add_chinese_subtitle.py <视频文件> [模型路径]")
        print("示例: python add_chinese_subtitle.py input.mp4")
        print("      python add_chinese_subtitle.py input.mp4 /path/to/large-v3.pt")
        sys.exit(1)

    video_path = sys.argv[1]
    model_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 {video_path}")
        sys.exit(1)

    if model_path and not os.path.exists(model_path):
        print(f"错误: 找不到模型文件 {model_path}")
        sys.exit(1)

    # 设置输出路径
    base_name = Path(video_path).stem
    audio_path = f"{base_name}_audio.wav"
    srt_path = f"{base_name}_zh.srt"
    output_path = f"{base_name}_字幕版.mp4"

    print(f"处理视频: {video_path}")

    # 步骤1: 提取音频
    print("\n[1/4] 提取音频...")
    extract_audio(video_path, audio_path)

    # 步骤2: 语音识别生成中文字幕
    print("\n[2/4] 识别语音并生成中文字幕...")
    segments = transcribe_audio(audio_path, model_path)

    # 步骤3: 生成SRT字幕文件
    print("\n[3/4] 生成字幕文件...")
    segments_to_srt(segments, srt_path)
    print(f"字幕已保存: {srt_path}")

    # 步骤4: 将字幕烧录到视频
    print("\n[4/4] 将字幕添加到视频...")
    add_subtitle_to_video(video_path, srt_path, output_path)

    # 清理临时文件
    os.remove(audio_path)

    print(f"\n✓ 完成！输出文件: {output_path}")

if __name__ == "__main__":
    main()
