#!/usr/bin/env python3
"""
视频中文字幕工具 - Gradio Web界面
端口: 19977
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import gradio as gr
import whisper


def extract_audio(video_path, audio_path):
    """从视频中提取音频"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        audio_path, '-y'
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_audio(audio_path, model_path=None):
    """使用Whisper识别音频并生成中文字幕"""
    print("加载Whisper模型...")

    if model_path and os.path.exists(model_path):
        # 使用本地模型文件
        print(f"使用本地模型: {model_path}")
        model = whisper.load_model(model_path)
    else:
        # 默认使用base模型
        print("使用默认base模型")
        model = whisper.load_model("base")

    print("识别音频中...")
    result = model.transcribe(audio_path, language="zh")

    return result["segments"]


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
    # Windows路径处理
    srt_path_escaped = srt_path.replace('\\', '/').replace(':', '\\:')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"subtitles={srt_path_escaped}",
        '-c:a', 'copy',
        output_path, '-y'
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def process_video(video_path, model_path, progress=gr.Progress()):
    """
    处理视频的主函数

    Args:
        video_path: 视频文件路径
        model_path: Whisper模型路径（可选）
        progress: Gradio进度条

    Returns:
        output_video_path: 带字幕的视频路径
        srt_path: 字幕文件路径
        status_message: 处理状态消息
    """
    try:
        # 验证输入
        if not video_path or not os.path.exists(video_path):
            return None, None, "❌ 错误：请提供有效的视频文件路径"

        if model_path and not os.path.exists(model_path):
            return None, None, f"❌ 错误：找不到模型文件 {model_path}"

        # 设置输出路径
        base_name = Path(video_path).stem
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, f"{base_name}_audio.wav")
        srt_path = os.path.join(temp_dir, f"{base_name}_zh.srt")
        output_path = os.path.join(temp_dir, f"{base_name}_字幕版.mp4")

        # 步骤1: 提取音频
        progress(0.1, desc="[1/4] 提取音频...")
        extract_audio(video_path, audio_path)

        # 步骤2: 语音识别生成中文字幕
        progress(0.3, desc="[2/4] 识别语音并生成中文字幕...")
        segments = transcribe_audio(audio_path, model_path if model_path else None)

        # 步骤3: 生成SRT字幕文件
        progress(0.6, desc="[3/4] 生成字幕文件...")
        segments_to_srt(segments, srt_path)

        # 步骤4: 将字幕烧录到视频
        progress(0.8, desc="[4/4] 将字幕添加到视频...")
        add_subtitle_to_video(video_path, srt_path, output_path)

        # 清理临时音频文件
        if os.path.exists(audio_path):
            os.remove(audio_path)

        progress(1.0, desc="✓ 完成！")

        return output_path, srt_path, "✓ 处理完成！视频和字幕文件已生成。"

    except subprocess.CalledProcessError as e:
        return None, None, f"❌ FFmpeg错误：{str(e)}"
    except Exception as e:
        return None, None, f"❌ 处理失败：{str(e)}"


# 创建Gradio界面
def create_interface():
    with gr.Blocks(title="视频中文字幕工具", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎬 视频中文字幕工具

        自动为视频添加中文字幕，使用OpenAI Whisper进行语音识别
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📥 输入设置")

                video_input = gr.Textbox(
                    label="视频文件路径",
                    placeholder=r"例如: C:\Users\YourName\Videos\video.mp4",
                    info="输入完整的MP4视频文件路径"
                )

                model_input = gr.Textbox(
                    label="Whisper模型路径（可选）",
                    placeholder=r"例如: C:\Models\large-v3.pt",
                    info="留空则使用默认base模型（首次会自动下载）"
                )

                process_btn = gr.Button("🚀 开始处理", variant="primary", size="lg")

            with gr.Column():
                gr.Markdown("### 📤 输出结果")

                status_output = gr.Textbox(
                    label="处理状态",
                    interactive=False
                )

                video_output = gr.File(
                    label="带字幕的视频文件",
                    interactive=False
                )

                srt_output = gr.File(
                    label="字幕文件（SRT格式）",
                    interactive=False
                )

        gr.Markdown("""
        ---
        ### 💡 使用说明

        1. **视频文件路径**：输入要添加字幕的MP4视频文件的完整路径
        2. **模型路径**（可选）：
           - 如果有本地的Whisper模型文件（如large-v3.pt），输入其完整路径
           - 留空则使用默认的base模型（首次运行会自动下载约140MB）
           - large-v3模型识别准确率更高，推荐使用
        3. 点击"开始处理"按钮，等待处理完成
        4. 处理完成后，可以下载带字幕的视频和字幕文件

        ### 📋 处理流程

        1. 从视频中提取音频
        2. 使用Whisper识别音频内容并转为中文文字
        3. 生成SRT格式字幕文件
        4. 使用FFmpeg将字幕烧录到视频中

        ### ⚠️ 注意事项

        - 确保已安装FFmpeg（Windows用户需要下载并配置环境变量）
        - 处理时间取决于视频长度和模型大小
        - 需要足够的磁盘空间存储临时文件
        """)

        # 绑定处理函数
        process_btn.click(
            fn=process_video,
            inputs=[video_input, model_input],
            outputs=[video_output, srt_output, status_output]
        )

    return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",  # 允许外部访问
        server_port=19977,       # 指定端口
        share=False,             # 不创建公共链接
        inbrowser=False          # 不自动打开浏览器
    )
    print("🚀 Gradio应用已启动，访问地址：http://localhost:19977")
