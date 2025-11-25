#!/usr/bin/env python3
"""
视频中文字幕工具 - 使用阿里云语音识别服务
输入：视频文件（MP4等格式）
输出：带中文字幕的视频
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from aliyun_transcription import AliyunTranscription
except ImportError:
    print("❌ 错误: 需要安装阿里云SDK")
    print("运行: pip install aliyun-python-sdk-core oss2")
    sys.exit(1)


def extract_audio(video_path, audio_path):
    """从视频中提取音频为MP3格式（高质量设置）"""
    print("[1/5] 提取音频...")
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


def parse_result_to_srt(result_json, srt_path):
    """将阿里云识别结果转换为SRT字幕格式（支持说话人分离）"""
    print("[5/5] 生成SRT字幕文件...")

    import json
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

    # 处理说话人分离：当说话人切换时，自动分段
    merged_segments = []
    current_segment = None

    for sentence in sentences:
        # 获取时间戳和文本
        begin_time = sentence['BeginTime'] / 1000  # 转换为秒
        end_time = sentence['EndTime'] / 1000
        text = sentence['Text']

        # 获取说话人ID（如果启用了说话人分离）
        speaker_id = sentence.get('SpeakerId') or sentence.get('ChannelId')

        # 如果没有当前段，或说话人切换了，创建新段
        if current_segment is None or (speaker_id and speaker_id != current_segment.get('speaker_id')):
            if current_segment:
                merged_segments.append(current_segment)
            current_segment = {
                'begin_time': begin_time,
                'end_time': end_time,
                'text': text,
                'speaker_id': speaker_id
            }
        else:
            # 同一说话人，合并到当前段（但保持独立，便于区分）
            # 为了清晰，每句话仍然独立成段
            merged_segments.append(current_segment)
            current_segment = {
                'begin_time': begin_time,
                'end_time': end_time,
                'text': text,
                'speaker_id': speaker_id
            }

    # 添加最后一段
    if current_segment:
        merged_segments.append(current_segment)

    # 写入SRT文件
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(merged_segments, 1):
            # 格式化时间戳
            start = format_timestamp(segment['begin_time'])
            end = format_timestamp(segment['end_time'])

            # 写入SRT格式（不显示说话人标签，只通过分段区分）
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment['text']}\n\n")

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
    # 将反斜杠替换为正斜杠
    srt_path_normalized = srt_path.replace('\\', '/')

    # Windows路径需要转义盘符冒号（C: → C\\:）
    if len(srt_path_normalized) > 1 and srt_path_normalized[1] == ':':
        # 盘符冒号需要双反斜杠转义
        srt_path_escaped = srt_path_normalized[0] + '\\\\:' + srt_path_normalized[2:]
    else:
        # Unix路径或相对路径，转义所有冒号
        srt_path_escaped = srt_path_normalized.replace(':', '\\:')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"subtitles={srt_path_escaped}",
        '-c:a', 'copy',
        output_path, '-y'
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg烧录字幕失败: {result.stderr.decode()}")




def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("视频字幕工具 - 使用阿里云语音识别服务")
        print("=" * 60)
        print("\n用法:")
        print("  python add_chinese_subtitle.py <视频文件路径> [语言]\n")
        print("示例:")
        print("  python add_chinese_subtitle.py video.mp4         # 中文识别（默认）")
        print("  python add_chinese_subtitle.py video.mp4 zh      # 中文识别")
        print("  python add_chinese_subtitle.py video.mp4 en      # 英语识别\n")
        print("环境变量配置:")
        print("  ALIBABA_ACCESS_KEY_ID      - 阿里云AccessKey ID")
        print("  ALIBABA_ACCESS_KEY_SECRET  - 阿里云AccessKey Secret")
        print("  ALIBABA_APP_KEY            - 语音识别应用AppKey")
        print("  ALIBABA_OSS_BUCKET         - OSS存储桶名称")
        print("  ALIBABA_REGION             - 地域（可选，默认: cn-shanghai）")
        print("=" * 60)
        sys.exit(1)

    video_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'zh'  # 默认中文

    # 验证语言参数
    if language not in ['zh', 'en']:
        print(f"❌ 错误: 不支持的语言 '{language}'，请使用 'zh'（中文）或 'en'（英语）")
        sys.exit(1)

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
    lang_suffix = "en" if language == "en" else "zh"
    srt_path = f"{base_name}_{lang_suffix}.srt"
    output_path = f"{base_name}_字幕版.mp4"

    print("\n" + "=" * 60)
    print("开始处理视频...")
    print("=" * 60)
    print(f"输入视频: {video_path}")
    print(f"识别语言: {'英语 (English)' if language == 'en' else '中文 (Chinese)'}")
    print(f"输出视频: {output_path}")
    print(f"字幕文件: {srt_path}")
    print("=" * 60 + "\n")

    try:
        # 创建阿里云语音识别客户端
        transcription = AliyunTranscription(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            app_key=app_key,
            bucket_name=bucket_name,
            region=region,
            language=language
        )

        # 步骤1: 生成固定的OSS对象名称（基于视频文件哈希）
        print("[1/5] 检查云端是否已有音频文件...")
        object_name = transcription.get_audio_object_name(video_path)
        print(f"  OSS对象名称: {object_name}")

        # 步骤2: 检查OSS是否已存在，避免重复提取和上传
        audio_duration = None
        if transcription.bucket.object_exists(object_name):
            print("  ✓ 音频文件已存在于OSS，跳过提取和上传")
            # 直接生成访问URL
            file_url = transcription.bucket.sign_url('GET', object_name, 3600)
        else:
            print("[2/5] 提取音频...")
            # 提取音频
            extract_audio(video_path, audio_path)
            # 获取音频时长（用于动态设置超时）
            audio_duration = get_audio_duration(audio_path)

            # 步骤3: 上传到OSS
            print("[3/5] 上传音频到OSS...")
            transcription.bucket.put_object_from_file(object_name, audio_path)
            print(f"  ✓ 音频文件已上传: {object_name}")
            file_url = transcription.bucket.sign_url('GET', object_name, 3600)

        print(f"  文件URL: {file_url[:80]}...")

        # 步骤4: 提交识别任务并等待完成
        print("[4/5] 提交语音识别任务...")
        result_json = transcription.transcribe_file(file_url, audio_duration)

        # 步骤5: 生成SRT字幕文件
        parse_result_to_srt(result_json, srt_path)

        # 步骤6: 将字幕烧录到视频
        add_subtitle_to_video(video_path, srt_path, output_path)

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("✓ 临时音频文件已清理")

        # 可选：清理OSS文件（默认不清理，方便重复使用）
        # transcription.cleanup_oss_file(object_name)

        print("\n" + "=" * 60)
        print("✓ 处理完成！")
        print("=" * 60)
        print(f"输出视频: {output_path}")
        print(f"字幕文件: {srt_path}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
