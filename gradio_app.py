#!/usr/bin/env python3
"""
视频中文字幕工具 - Gradio Web界面
使用阿里云语音识别服务
端口: 19977
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import socket
from pathlib import Path
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

try:
    from aliyun_transcription import AliyunTranscription
except ImportError as e:
    print("=" * 60)
    print("❌ 错误: 缺少必要的依赖库")
    print("=" * 60)
    print("\n请运行以下命令安装:")
    print("  pip install aliyun-python-sdk-core oss2")
    print("=" * 60)
    sys.exit(1)


def get_audio_duration(audio_path):
    """获取音频文件时长（秒）"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def extract_audio(video_path, audio_path):
    """从视频中提取音频为MP3格式"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame',
        '-ar', '16000', '-ac', '1',
        '-b:a', '64k',
        audio_path, '-y'
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg提取音频失败: {result.stderr.decode()}")




def parse_result_to_srt(result_json, srt_path):
    """将阿里云识别结果转换为SRT字幕格式"""
    # 解析JSON结果（兼容不同的数据类型）
    if isinstance(result_json, dict):
        result = result_json
    elif isinstance(result_json, str):
        result = json.loads(result_json)
    elif isinstance(result_json, bytes):
        result = json.loads(result_json.decode('utf-8'))
    else:
        raise TypeError(f"不支持的结果类型: {type(result_json)}")

    sentences = result.get('Sentences', [])

    if not sentences:
        raise Exception("识别结果为空，可能音频没有语音内容")

    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, sentence in enumerate(sentences, 1):
            # 获取时间戳（单位：毫秒）
            begin_time = sentence['BeginTime'] / 1000  # 转换为秒
            end_time = sentence['EndTime'] / 1000
            text = sentence['Text']

            # 格式化时间戳
            start = format_timestamp(begin_time)
            end = format_timestamp(end_time)

            # 写入SRT格式
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
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg烧录字幕失败: {result.stderr.decode()}")




def process_video(video_path, access_key_id, access_key_secret, app_key, bucket_name, region, progress=gr.Progress()):
    """
    处理视频的主函数

    Args:
        video_path: 视频文件路径
        access_key_id: 阿里云AccessKey ID
        access_key_secret: 阿里云AccessKey Secret
        app_key: 语音识别应用AppKey
        bucket_name: OSS存储桶名称
        region: 地域
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

        if not access_key_id or not access_key_secret or not app_key or not bucket_name:
            return None, None, "❌ 错误：请填写完整的阿里云配置信息"

        # 设置输出路径
        base_name = Path(video_path).stem
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, f"{base_name}_audio.mp3")
        srt_path = os.path.join(temp_dir, f"{base_name}_zh.srt")
        output_path = os.path.join(temp_dir, f"{base_name}_字幕版.mp4")

        # 创建阿里云语音识别客户端
        progress(0.05, desc="[0/5] 初始化阿里云客户端...")
        transcription = AliyunTranscription(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            app_key=app_key,
            bucket_name=bucket_name,
            region=region
        )

        # 步骤1: 提取音频
        progress(0.1, desc="[1/5] 提取音频...")
        extract_audio(video_path, audio_path)

        # 获取音频时长（用于动态设置超时）
        audio_duration = get_audio_duration(audio_path)

        # 步骤2: 生成固定的OSS对象名称（基于视频文件哈希）
        progress(0.2, desc="[2/5] 准备上传音频...")
        object_name = transcription.get_audio_object_name(video_path)

        # 步骤3: 上传到OSS（如果已存在则跳过）
        progress(0.25, desc="[3/5] 上传音频到OSS...")
        file_url = transcription.upload_audio_to_oss(audio_path, object_name)

        # 步骤4: 提交识别任务并等待完成
        progress(0.3, desc="[4/5] 提交识别任务...")
        result_json = transcription.transcribe_file(file_url, audio_duration)
        progress(0.7, desc="✓ 识别完成！")

        # 步骤5: 生成SRT字幕文件
        progress(0.7, desc="[5/5] 生成字幕文件...")
        parse_result_to_srt(result_json, srt_path)

        # 步骤6: 将字幕烧录到视频
        progress(0.9, desc="将字幕烧录到视频...")
        add_subtitle_to_video(video_path, srt_path, output_path)

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)

        progress(1.0, desc="✓ 完成！")

        return output_path, srt_path, "✓ 处理完成！视频和字幕文件已生成。"

    except Exception as e:
        return None, None, f"❌ 处理失败：{str(e)}"


# 创建Gradio界面
def create_interface():
    # 加载配置文件
    default_config = {
        "video_path": os.getenv("FILE_PATH"),
        "access_key_id": os.getenv("ACCESS_KEY_ID"),
        "access_key_secret": os.getenv("ACCESS_KEY_SECRET"),
        "app_key": os.getenv("APP_KEY"),
        "bucket_name": os.getenv("BUCKET_NAME"),
        "region": os.getenv("REGION"),
    }

    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                default_config = json.load(f)
        except Exception:
            pass  # 使用默认配置

    # 兼容不同版本的Gradio
    try:
        demo = gr.Blocks(title="视频中文字幕工具 - 阿里云", theme=gr.themes.Soft())
    except TypeError:
        demo = gr.Blocks(title="视频中文字幕工具 - 阿里云")

    with demo:
        gr.Markdown("""
        # 🎬 视频中文字幕工具

        自动为视频添加中文字幕，使用阿里云语音识别服务
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📥 视频输入")

                video_input = gr.Textbox(
                    label="视频文件路径",
                    value=default_config.get("video_path"),
                    placeholder=r"例如: C:\Users\YourName\Videos\video.mp4",
                    info="输入完整的视频文件路径"
                )

                gr.Markdown("### 🔑 阿里云配置")

                access_key_id_input = gr.Textbox(
                    label="AccessKey ID",
                    value=default_config.get("access_key_id", os.getenv("ACCESS_KEY_SECRET", "")),
                    placeholder="您的阿里云AccessKey ID",
                    type="password"
                )

                access_key_secret_input = gr.Textbox(
                    label="AccessKey Secret",
                    value=default_config.get("access_key_secret", ""),
                    placeholder="您的阿里云AccessKey Secret",
                    type="password"
                )

                app_key_input = gr.Textbox(
                    label="语音识别AppKey",
                    value=default_config.get("app_key", os.getenv("APP_KEY", "")),
                    placeholder="语音识别应用的AppKey"
                )

                bucket_name_input = gr.Textbox(
                    label="OSS存储桶名称",
                    value=default_config.get("OSS_BUCKET_NAME", "money-oss"),
                    placeholder="例如: my-bucket"
                )

                region_input = gr.Textbox(
                    label="地域",
                    value=default_config.get("region", "cn-shanghai"),
                    placeholder="例如: cn-shanghai"
                )

                process_btn = gr.Button("🚀 开始处理", variant="primary", size="lg")

            with gr.Column():
                gr.Markdown("### 📤 输出结果")

                status_output = gr.Textbox(
                    label="处理状态",
                    lines=8,
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

        # 绑定处理函数
        process_btn.click(
            fn=process_video,
            inputs=[
                video_input,
                access_key_id_input,
                access_key_secret_input,
                app_key_input,
                bucket_name_input,
                region_input
            ],
            outputs=[video_output, srt_output, status_output]
        )

    return demo


if __name__ == "__main__":
    print("=" * 60)
    print("视频中文字幕工具 - 使用阿里云语音识别服务")
    print("=" * 60)

    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",  # 允许外部访问
        server_port=19977,  # 指定端口
        share=False,  # 不创建公共链接
        inbrowser=False  # 不自动打开浏览器
    )

    print("🚀 Gradio应用已启动，访问地址：http://localhost:19977")
