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
from openai import OpenAI

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
    """从视频中提取音频为MP3格式（高质量设置）"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame',
        '-ar', '16000',  # 阿里云要求8000-48000Hz，16000是语音识别的标准采样率
        '-ac', '1',      # 单声道（语音识别推荐）
        '-b:a', '128k',  # 提高比特率到128k，保留更多音频细节
        '-q:a', '2',     # MP3质量等级（0-9，2为高质量）
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


def translate_srt_with_deepseek(input_srt_path, output_srt_path, deepseek_api_key, deepseek_base_url="https://api.deepseek.com"):
    """
    使用DeepSeek API翻译SRT字幕文件（英文→中文）

    Args:
        input_srt_path: 输入的英文SRT文件路径
        output_srt_path: 输出的中文SRT文件路径
        deepseek_api_key: DeepSeek API密钥
        deepseek_base_url: DeepSeek API基础URL
    """
    # 读取英文字幕
    with open(input_srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析SRT文件
    subtitle_blocks = content.strip().split('\n\n')
    translated_blocks = []

    # 初始化DeepSeek客户端
    client = OpenAI(
        api_key=deepseek_api_key,
        base_url=deepseek_base_url
    )

    for block in subtitle_blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text = '\n'.join(lines[2:])  # 支持多行字幕

            # 调用DeepSeek翻译
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate the following English subtitle to Chinese. Only return the translated text, no explanations."},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.3
                )
                translated_text = response.choices[0].message.content.strip()

                # 重建字幕块
                translated_block = f"{index}\n{timestamp}\n{translated_text}"
                translated_blocks.append(translated_block)

                # 避免API限流
                time.sleep(0.2)

            except Exception as e:
                # 如果翻译失败，保留原文
                print(f"翻译失败，保留原文: {e}")
                translated_blocks.append(block)

    # 写入翻译后的字幕
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(translated_blocks))


def add_subtitle_to_video(video_path, srt_path, output_path):
    """
    将字幕烧录到视频中

    使用简化的方法：直接使用绝对路径，让FFmpeg自己处理路径
    在Windows上，FFmpeg能够正确处理标准路径格式
    """
    # 确保使用绝对路径
    srt_path_abs = os.path.abspath(srt_path)

    # Windows路径转义：需要转义反斜杠和冒号
    if sys.platform.startswith('win'):
        # Windows: 先将反斜杠转为正斜杠，然后转义冒号
        # 使用 filename= 参数来明确指定文件路径
        srt_path_escaped = srt_path_abs.replace('\\', '/').replace(':', r'\:')
        filter_str = f"subtitles=filename='{srt_path_escaped}'"
    else:
        # Unix: 转义冒号
        srt_path_escaped = srt_path_abs.replace(':', r'\:')
        filter_str = f"subtitles='{srt_path_escaped}'"

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', filter_str,
        '-c:a', 'copy',
        output_path, '-y'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg烧录字幕失败: {result.stderr}")




def process_video(video_path, access_key_id, access_key_secret, app_key, bucket_name, region, language, deepseek_api_key=None, progress=gr.Progress()):
    """
    处理视频的主函数

    Args:
        video_path: 视频文件路径
        access_key_id: 阿里云AccessKey ID
        access_key_secret: 阿里云AccessKey Secret
        app_key: 语音识别应用AppKey
        bucket_name: OSS存储桶名称
        region: 地域
        language: 识别语言（zh=中文, en=英语）
        deepseek_api_key: DeepSeek API密钥（用于翻译英文字幕）
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

        # 设置输出路径 - 修改：音频和字幕保存到视频同级目录
        video_dir = Path(video_path).parent
        base_name = Path(video_path).stem
        temp_dir = tempfile.mkdtemp()

        # MP3保存到视频同级目录
        audio_path = os.path.join(video_dir, f"{base_name}_audio.mp3")

        # 字幕和输出视频保存到视频同级目录
        lang_suffix = "en" if language == "en" else "zh"
        srt_path_en = os.path.join(video_dir, f"{base_name}_en.srt")  # 英文字幕
        srt_path_zh = os.path.join(video_dir, f"{base_name}_zh.srt")  # 中文字幕
        output_path = os.path.join(video_dir, f"{base_name}_字幕版.mp4")

        # 创建阿里云语音识别客户端
        lang_name = "英语 (English)" if language == "en" else "中文 (Chinese)"
        progress(0.05, desc=f"[0/5] 初始化阿里云客户端（{lang_name}）...")
        transcription = AliyunTranscription(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            app_key=app_key,
            bucket_name=bucket_name,
            region=region,
            language=language
        )

        # 步骤1: 生成固定的OSS对象名称并检查
        progress(0.1, desc="[1/5] 检查云端是否已有音频...")
        object_name = transcription.get_audio_object_name(video_path)

        # 步骤2: 检查OSS是否已存在，避免重复提取和上传
        audio_duration = None
        if transcription.bucket.object_exists(object_name):
            progress(0.2, desc="✓ 音频已存在，跳过提取和上传")
            file_url = transcription.bucket.sign_url('GET', object_name, 3600)
        else:
            # 提取音频
            progress(0.15, desc="[2/5] 提取音频...")
            extract_audio(video_path, audio_path)
            audio_duration = get_audio_duration(audio_path)

            # 上传到OSS
            progress(0.2, desc="[3/5] 上传音频到OSS...")
            transcription.bucket.put_object_from_file(object_name, audio_path)
            file_url = transcription.bucket.sign_url('GET', object_name, 3600)

        # 步骤4: 提交识别任务并等待完成
        progress(0.3, desc="[4/5] 提交识别任务...")
        result_json = transcription.transcribe_file(file_url, audio_duration)
        progress(0.7, desc="✓ 识别完成！")

        # 步骤5: 生成SRT字幕文件
        progress(0.7, desc="[5/7] 生成字幕文件...")
        if language == "en":
            # 英文识别：生成英文字幕
            parse_result_to_srt(result_json, srt_path_en)

            # 步骤6: 翻译英文字幕为中文（如果提供了DeepSeek API Key）
            if deepseek_api_key:
                progress(0.75, desc="[6/7] 使用DeepSeek翻译字幕（英文→中文）...")
                translate_srt_with_deepseek(srt_path_en, srt_path_zh, deepseek_api_key)
                final_srt = srt_path_zh
                progress(0.85, desc="✓ 翻译完成！")
            else:
                # 没有提供API Key，直接使用英文字幕
                final_srt = srt_path_en
                progress(0.75, desc="⚠ 未提供DeepSeek API Key，将使用英文字幕")
        else:
            # 中文识别：直接生成中文字幕
            parse_result_to_srt(result_json, srt_path_zh)
            final_srt = srt_path_zh

        # 步骤7: 将字幕烧录到视频
        progress(0.9, desc="[7/7] 将字幕烧录到视频...")
        add_subtitle_to_video(video_path, final_srt, output_path)

        # 保留音频文件（不再删除MP3）

        progress(1.0, desc="✓ 完成！")

        # 返回输出视频和最终使用的字幕文件
        return output_path, final_srt, "✓ 处理完成！视频和字幕文件已生成。MP3文件已保存到视频同级目录。"

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
        # 🎬 视频字幕工具

        自动为视频添加字幕，支持中文和英语识别（阿里云语音识别服务）
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

                language_input = gr.Radio(
                    label="识别语言",
                    choices=[("中文 (Chinese)", "zh"), ("英语 (English)", "en")],
                    value="zh",
                    info="选择视频中的音频语言"
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

                gr.Markdown("### 🌐 DeepSeek配置（可选）")
                gr.Markdown("_识别英语视频时，可使用DeepSeek将英文字幕翻译成中文_")

                deepseek_api_key_input = gr.Textbox(
                    label="DeepSeek API Key",
                    value=os.getenv("DEEPSEEK_API_KEY", ""),
                    placeholder="您的DeepSeek API密钥（仅英语视频需要）",
                    type="password",
                    info="可选：用于将英文字幕翻译成中文"
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
                region_input,
                language_input,
                deepseek_api_key_input
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
