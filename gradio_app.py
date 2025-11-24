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
from pathlib import Path
import gradio as gr

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    import oss2
except ImportError as e:
    print("=" * 60)
    print("❌ 错误: 缺少必要的依赖库")
    print("=" * 60)
    print("\n请运行以下命令安装:")
    print("  pip install aliyun-python-sdk-core oss2")
    print("=" * 60)
    sys.exit(1)


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


def upload_to_oss(audio_path, access_key_id, access_key_secret, bucket_name, region='cn-shanghai'):
    """上传音频文件到阿里云OSS"""
    # 创建OSS客户端
    auth = oss2.Auth(access_key_id, access_key_secret)
    endpoint = f'https://oss-{region}.aliyuncs.com'
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 生成唯一的对象名称
    object_name = f"audio/{int(time.time())}_{Path(audio_path).name}"

    # 上传文件
    bucket.put_object_from_file(object_name, audio_path)

    # 生成文件URL
    file_url = f"https://{bucket_name}.oss-{region}.aliyuncs.com/{object_name}"
    return file_url, object_name


def submit_transcription_task(file_url, access_key_id, access_key_secret, app_key, region='cn-shanghai'):
    """提交语音识别任务到阿里云"""
    client = AcsClient(access_key_id, access_key_secret, region)

    # 创建POST请求
    request = CommonRequest()
    request.set_method('POST')
    request.set_domain(f'nls-filetrans.{region}.aliyuncs.com')
    request.set_version('2018-08-17')
    request.set_action_name('SubmitTask')
    request.set_protocol('https')

    # 设置请求参数
    task_params = {
        "appkey": app_key,
        "file_link": file_url,
        "version": "4.0",
        "enable_words": False
    }

    request.add_body_params('Task', json.dumps(task_params))

    # 发送请求
    response = client.do_action_with_exception(request)
    result = json.loads(response)

    if result.get('StatusCode') != 21050000:
        raise Exception(f"提交任务失败: {result.get('StatusText')}")

    return result.get('TaskId')


def wait_for_task_completion(task_id, access_key_id, access_key_secret, region='cn-shanghai'):
    """等待识别任务完成"""
    client = AcsClient(access_key_id, access_key_secret, region)

    max_retries = 60  # 最多等待5分钟
    retry_count = 0

    while retry_count < max_retries:
        # 创建GET请求
        request = CommonRequest()
        request.set_method('GET')
        request.set_domain(f'nls-filetrans.{region}.aliyuncs.com')
        request.set_version('2018-08-17')
        request.set_action_name('GetTaskResult')
        request.set_protocol('https')
        request.add_query_param('TaskId', task_id)

        # 发送请求
        response = client.do_action_with_exception(request)
        result = json.loads(response)

        status_code = result.get('StatusCode')

        if status_code == 21050002:  # 成功
            return result.get('Result')
        elif status_code == 21050003:  # 失败
            raise Exception(f"识别任务失败: {result.get('StatusText')}")
        elif status_code == 21050000:  # 进行中
            time.sleep(5)
            retry_count += 1
        else:
            raise Exception(f"未知状态: {result.get('StatusText')}")

    raise Exception("识别任务超时")


def parse_result_to_srt(result_json, srt_path):
    """将阿里云识别结果转换为SRT字幕格式"""
    # 解析JSON结果
    result = json.loads(result_json)
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


def cleanup_oss(access_key_id, access_key_secret, bucket_name, object_name, region='cn-shanghai'):
    """清理OSS上的临时文件"""
    try:
        auth = oss2.Auth(access_key_id, access_key_secret)
        endpoint = f'https://oss-{region}.aliyuncs.com'
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        bucket.delete_object(object_name)
    except Exception:
        pass  # 忽略清理错误


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
    object_name = None

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

        # 步骤1: 提取音频
        progress(0.1, desc="[1/5] 提取音频...")
        extract_audio(video_path, audio_path)

        # 步骤2: 上传到OSS
        progress(0.2, desc="[2/5] 上传音频到阿里云OSS...")
        file_url, object_name = upload_to_oss(
            audio_path, access_key_id, access_key_secret, bucket_name, region
        )

        # 步骤3: 提交识别任务
        progress(0.3, desc="[3/5] 提交语音识别任务...")
        task_id = submit_transcription_task(
            file_url, access_key_id, access_key_secret, app_key, region
        )

        # 步骤4: 等待任务完成
        progress(0.5, desc="[4/5] 等待识别任务完成（可能需要几分钟）...")
        result_json = wait_for_task_completion(
            task_id, access_key_id, access_key_secret, region
        )

        # 步骤5: 生成SRT字幕文件
        progress(0.7, desc="[5/5] 生成字幕文件...")
        parse_result_to_srt(result_json, srt_path)

        # 步骤6: 将字幕烧录到视频
        progress(0.9, desc="将字幕烧录到视频...")
        add_subtitle_to_video(video_path, srt_path, output_path)

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # 清理OSS文件
        if object_name:
            cleanup_oss(access_key_id, access_key_secret, bucket_name, object_name, region)

        progress(1.0, desc="✓ 完成！")

        return output_path, srt_path, "✓ 处理完成！视频和字幕文件已生成。"

    except Exception as e:
        # 尝试清理
        if object_name:
            try:
                cleanup_oss(access_key_id, access_key_secret, bucket_name, object_name, region)
            except:
                pass

        return None, None, f"❌ 处理失败：{str(e)}"


# 创建Gradio界面
def create_interface():
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
                    placeholder=r"例如: C:\Users\YourName\Videos\video.mp4",
                    info="输入完整的视频文件路径"
                )

                gr.Markdown("### 🔑 阿里云配置")

                access_key_id_input = gr.Textbox(
                    label="AccessKey ID",
                    placeholder="您的阿里云AccessKey ID",
                    type="password"
                )

                access_key_secret_input = gr.Textbox(
                    label="AccessKey Secret",
                    placeholder="您的阿里云AccessKey Secret",
                    type="password"
                )

                app_key_input = gr.Textbox(
                    label="语音识别AppKey",
                    placeholder="语音识别应用的AppKey"
                )

                bucket_name_input = gr.Textbox(
                    label="OSS存储桶名称",
                    placeholder="例如: my-bucket"
                )

                region_input = gr.Textbox(
                    label="地域",
                    value="cn-shanghai",
                    placeholder="例如: cn-shanghai"
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

        1. **视频文件路径**：输入要添加字幕的视频文件的完整路径
        2. **阿里云配置**：
           - **AccessKey ID & Secret**：在阿里云控制台获取
           - **语音识别AppKey**：在语音识别服务控制台创建应用后获取
           - **OSS存储桶名称**：需要一个OSS存储桶用于临时存储音频文件
           - **地域**：选择与OSS存储桶相同的地域（默认：cn-shanghai）
        3. 点击"开始处理"按钮，等待处理完成
        4. 处理完成后，可以下载带字幕的视频和字幕文件

        ### 📋 处理流程

        1. 从视频中提取音频
        2. 上传音频到阿里云OSS
        3. 提交语音识别任务到阿里云
        4. 等待识别完成（可能需要几分钟）
        5. 生成SRT格式字幕文件
        6. 使用FFmpeg将字幕烧录到视频中

        ### ⚠️ 注意事项

        - 确保已安装FFmpeg
        - 需要有效的阿里云账号和语音识别服务权限
        - 处理时间取决于视频长度和网络速度
        - 音频文件会临时上传到OSS，处理完成后自动删除

        ### 🔗 相关链接

        - [阿里云语音识别服务](https://www.aliyun.com/product/nls)
        - [如何获取AccessKey](https://help.aliyun.com/document_detail/53045.html)
        - [如何创建OSS存储桶](https://help.aliyun.com/document_detail/31885.html)
        """)

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
        server_port=19977,       # 指定端口
        share=False,             # 不创建公共链接
        inbrowser=False          # 不自动打开浏览器
    )

    print("🚀 Gradio应用已启动，访问地址：http://localhost:19977")
