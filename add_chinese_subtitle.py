#!/usr/bin/env python3
"""
视频中文字幕工具 - 使用阿里云语音识别服务
输入：视频文件（MP4等格式）
输出：带中文字幕的视频
"""

import os
import sys
import json
import time
import subprocess
import socket
from pathlib import Path

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
except ImportError:
    print("❌ 错误: 需要安装阿里云SDK")
    print("运行: pip install aliyun-python-sdk-core")
    sys.exit(1)


def check_network_connectivity(region='cn-shanghai'):
    """检查与阿里云服务的网络连接"""
    print("🔍 检查网络连接...")

    # 检查DNS解析
    nls_domain = f'nls-filetrans.{region}.aliyuncs.com'
    oss_domain = f'oss-{region}.aliyuncs.com'

    try:
        print(f"  检查DNS解析: {nls_domain}")
        ip = socket.gethostbyname(nls_domain)
        print(f"  ✓ NLS服务DNS解析成功: {ip}")
    except socket.gaierror as e:
        print(f"  ❌ NLS服务DNS解析失败: {e}")
        print(f"\n可能的原因：")
        print(f"  1. 网络连接问题 - 请检查网络连接是否正常")
        print(f"  2. DNS服务器问题 - 尝试更换DNS服务器（如8.8.8.8）")
        print(f"  3. 防火墙/代理 - 检查防火墙或代理设置")
        print(f"  4. 地域设置错误 - 当前地域: {region}")
        raise Exception(f"无法解析阿里云NLS服务域名: {nls_domain}")

    try:
        print(f"  检查DNS解析: {oss_domain}")
        ip = socket.gethostbyname(oss_domain)
        print(f"  ✓ OSS服务DNS解析成功: {ip}")
    except socket.gaierror as e:
        print(f"  ⚠ OSS服务DNS解析失败: {e}")

    print("  ✓ 网络连接检查完成\n")


def extract_audio(video_path, audio_path):
    """从视频中提取音频为MP3格式"""
    print("[1/5] 提取音频...")
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
    print("[2/5] 上传音频到阿里云OSS...")

    try:
        import oss2
    except ImportError:
        print("❌ 错误: 需要安装OSS SDK")
        print("运行: pip install oss2")
        sys.exit(1)

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
    """提交语音识别任务到阿里云（带重试机制）"""
    print("[3/5] 提交语音识别任务...")

    # 创建客户端，设置超时时间（连接超时30秒，读取超时90秒）
    client = AcsClient(
        access_key_id,
        access_key_secret,
        region,
        timeout=90,  # 设置超时时间
    )

    # 设置重试次数
    max_retries = 3
    retry_delay = 2  # 初始重试延迟（秒）

    for attempt in range(max_retries):
        try:
            # 创建POST请求
            request = CommonRequest()
            request.set_method('POST')
            request.set_domain(f'nls-filetrans.{region}.aliyuncs.com')
            request.set_version('2018-08-17')
            request.set_action_name('SubmitTask')
            request.set_protocol_type('https')

            # 设置请求参数
            task_params = {
                "appkey": app_key,
                "file_link": file_url,
                "version": "4.0",
                "enable_words": False
            }

            request.add_body_params('Task', json.dumps(task_params))

            # 发送请求
            print(f"  尝试提交任务... (尝试 {attempt + 1}/{max_retries})")
            response = client.do_action_with_exception(request)
            result = json.loads(response)

            if result.get('StatusCode') != 21050000:
                raise Exception(f"提交任务失败: {result.get('StatusText')}")

            task_id = result.get('TaskId')
            print(f"✓ 任务已提交，任务ID: {task_id}")
            return task_id

        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                print(f"  ⚠ 提交失败: {error_msg}")
                print(f"  等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                print(f"  ❌ 提交任务最终失败")
                raise Exception(f"提交任务失败（已重试{max_retries}次）: {error_msg}")


def wait_for_task_completion(task_id, access_key_id, access_key_secret, region='cn-shanghai'):
    """等待识别任务完成（带重试机制）"""
    print("[4/5] 等待识别任务完成...")

    # 创建客户端，设置超时时间
    client = AcsClient(
        access_key_id,
        access_key_secret,
        region,
        timeout=90,  # 设置超时时间
    )

    max_wait_time = 600  # 最多等待10分钟
    poll_interval = 5     # 每5秒查询一次
    max_poll_retries = max_wait_time // poll_interval
    poll_count = 0

    while poll_count < max_poll_retries:
        # 每次查询都有重试机制
        query_retries = 3
        query_success = False

        for attempt in range(query_retries):
            try:
                # 创建GET请求
                request = CommonRequest()
                request.set_method('GET')
                request.set_domain(f'nls-filetrans.{region}.aliyuncs.com')
                request.set_version('2018-08-17')
                request.set_action_name('GetTaskResult')
                request.set_protocol_type('https')
                request.add_query_param('TaskId', task_id)

                # 发送请求
                response = client.do_action_with_exception(request)
                result = json.loads(response)
                query_success = True

                status_code = result.get('StatusCode')

                if status_code == 21050002:  # 成功
                    print("\n✓ 识别完成！")
                    return result.get('Result')
                elif status_code == 21050003:  # 失败
                    raise Exception(f"识别任务失败: {result.get('StatusText')}")
                elif status_code == 21050000:  # 进行中
                    elapsed_time = poll_count * poll_interval
                    print(f"  等待中... ({elapsed_time}秒 / {max_wait_time}秒)", end='\r')
                    break  # 跳出重试循环，继续等待
                else:
                    raise Exception(f"未知状态: {result.get('StatusText')}")

            except Exception as e:
                if attempt < query_retries - 1:
                    print(f"\n  ⚠ 查询失败，重试中... ({attempt + 1}/{query_retries})")
                    time.sleep(2)
                else:
                    raise Exception(f"查询任务状态失败（已重试{query_retries}次）: {str(e)}")

        if query_success:
            time.sleep(poll_interval)
            poll_count += 1
        else:
            break

    raise Exception(f"识别任务超时（等待时间超过{max_wait_time}秒）")


def parse_result_to_srt(result_json, srt_path):
    """将阿里云识别结果转换为SRT字幕格式"""
    print("[5/5] 生成SRT字幕文件...")

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

    print(f"✓ 字幕文件已保存: {srt_path}")


def format_timestamp(seconds):
    """格式化时间戳为SRT格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def add_subtitle_to_video(video_path, srt_path, output_path):
    """将字幕烧录到视频中"""
    print("\n将字幕烧录到视频中...")

    # 转义字幕路径（Windows兼容）
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
        import oss2
        auth = oss2.Auth(access_key_id, access_key_secret)
        endpoint = f'https://oss-{region}.aliyuncs.com'
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        bucket.delete_object(object_name)
        print("✓ OSS临时文件已清理")
    except Exception as e:
        print(f"⚠ OSS清理失败（可手动删除）: {str(e)}")


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("视频中文字幕工具 - 使用阿里云语音识别服务")
        print("=" * 60)
        print("\n用法:")
        print("  python add_chinese_subtitle.py <视频文件路径>\n")
        print("示例:")
        print("  python add_chinese_subtitle.py video.mp4\n")
        print("环境变量配置:")
        print("  ALIBABA_ACCESS_KEY_ID      - 阿里云AccessKey ID")
        print("  ALIBABA_ACCESS_KEY_SECRET  - 阿里云AccessKey Secret")
        print("  ALIBABA_APP_KEY            - 语音识别应用AppKey")
        print("  ALIBABA_OSS_BUCKET         - OSS存储桶名称")
        print("  ALIBABA_REGION             - 地域（可选，默认: cn-shanghai）")
        print("=" * 60)
        sys.exit(1)

    video_path = sys.argv[1]

    # 验证视频文件
    if not os.path.exists(video_path):
        print(f"❌ 错误: 找不到视频文件 {video_path}")
        sys.exit(1)

    # 读取配置
    access_key_id = os.getenv('ALIBABA_ACCESS_KEY_ID')
    access_key_secret = os.getenv('ALIBABA_ACCESS_KEY_SECRET')
    app_key = os.getenv('ALIBABA_APP_KEY')
    bucket_name = os.getenv('ALIBABA_OSS_BUCKET')
    region = os.getenv('ALIBABA_REGION', 'cn-shanghai')

    # 验证配置
    missing_configs = []
    if not access_key_id:
        missing_configs.append('ALIBABA_ACCESS_KEY_ID')
    if not access_key_secret:
        missing_configs.append('ALIBABA_ACCESS_KEY_SECRET')
    if not app_key:
        missing_configs.append('ALIBABA_APP_KEY')
    if not bucket_name:
        missing_configs.append('ALIBABA_OSS_BUCKET')

    if missing_configs:
        print(f"❌ 错误: 缺少必要的环境变量配置:")
        for config in missing_configs:
            print(f"   - {config}")
        print("\n请先设置环境变量，例如:")
        print("  export ALIBABA_ACCESS_KEY_ID='your_key_id'")
        print("  export ALIBABA_ACCESS_KEY_SECRET='your_key_secret'")
        print("  export ALIBABA_APP_KEY='your_app_key'")
        print("  export ALIBABA_OSS_BUCKET='your_bucket_name'")
        sys.exit(1)

    # 设置输出路径
    base_name = Path(video_path).stem
    audio_path = f"{base_name}_audio.mp3"
    srt_path = f"{base_name}_zh.srt"
    output_path = f"{base_name}_字幕版.mp4"

    print("\n" + "=" * 60)
    print("开始处理视频...")
    print("=" * 60)
    print(f"输入视频: {video_path}")
    print(f"输出视频: {output_path}")
    print(f"字幕文件: {srt_path}")
    print("=" * 60 + "\n")

    object_name = None

    try:
        # 步骤0: 检查网络连接
        check_network_connectivity(region)

        # 步骤1: 提取音频
        extract_audio(video_path, audio_path)

        # 步骤2: 上传到OSS
        file_url, object_name = upload_to_oss(
            audio_path, access_key_id, access_key_secret, bucket_name, region
        )

        # 步骤3: 提交识别任务
        task_id = submit_transcription_task(
            file_url, access_key_id, access_key_secret, app_key, region
        )

        # 步骤4: 等待任务完成
        result_json = wait_for_task_completion(
            task_id, access_key_id, access_key_secret, region
        )

        # 步骤5: 生成SRT字幕文件
        parse_result_to_srt(result_json, srt_path)

        # 步骤6: 将字幕烧录到视频
        add_subtitle_to_video(video_path, srt_path, output_path)

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("✓ 临时音频文件已清理")

        # 清理OSS文件
        if object_name:
            cleanup_oss(access_key_id, access_key_secret, bucket_name, object_name, region)

        print("\n" + "=" * 60)
        print("✓ 处理完成！")
        print("=" * 60)
        print(f"输出视频: {output_path}")
        print(f"字幕文件: {srt_path}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")

        # 尝试清理
        if object_name:
            try:
                cleanup_oss(access_key_id, access_key_secret, bucket_name, object_name, region)
            except:
                pass

        sys.exit(1)


if __name__ == "__main__":
    main()
