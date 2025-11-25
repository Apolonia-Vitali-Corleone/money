# -*- coding: utf8 -*-
"""
阿里云语音识别工具类
按照官方最佳实践实现
https://help.aliyun.com/document_detail/90727.html
"""
import json
import time
import hashlib
import os
from pathlib import Path
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
import oss2


class AliyunTranscription:
    """阿里云语音识别服务封装"""

    # 常量定义（参考官方示例）
    REGION_ID = "cn-shanghai"
    PRODUCT = "nls-filetrans"
    DOMAIN = "filetrans.cn-shanghai.aliyuncs.com"
    API_VERSION = "2018-08-17"
    POST_REQUEST_ACTION = "SubmitTask"
    GET_REQUEST_ACTION = "GetTaskResult"

    # 请求参数
    KEY_APP_KEY = "appkey"
    KEY_FILE_LINK = "file_link"
    KEY_VERSION = "version"
    KEY_ENABLE_WORDS = "enable_words"
    KEY_AUTO_SPLIT = "auto_split"

    # 响应参数
    KEY_TASK = "Task"
    KEY_TASK_ID = "TaskId"
    KEY_STATUS_TEXT = "StatusText"
    KEY_RESULT = "Result"

    # 状态值
    STATUS_SUCCESS = "SUCCESS"
    STATUS_RUNNING = "RUNNING"
    STATUS_QUEUEING = "QUEUEING"

    def __init__(self, access_key_id, access_key_secret, app_key, bucket_name, region="cn-shanghai", language="zh"):
        """
        初始化阿里云语音识别客户端

        Args:
            access_key_id: 阿里云AccessKey ID
            access_key_secret: 阿里云AccessKey Secret
            app_key: 语音识别应用AppKey
            bucket_name: OSS存储桶名称
            region: 地域（默认: cn-shanghai）
            language: 识别语言（zh=中文, en=英语，默认: zh）
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.bucket_name = bucket_name
        self.region = region
        self.language = language

        # 更新地域相关的常量
        if region != "cn-shanghai":
            self.DOMAIN = f"filetrans.{region}.aliyuncs.com"

        # 创建AcsClient实例
        self.client = AcsClient(access_key_id, access_key_secret, region)

        # 创建OSS客户端
        auth = oss2.Auth(access_key_id, access_key_secret)
        endpoint = f'https://oss-{region}.aliyuncs.com'
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

    def get_file_hash(self, file_path):
        """
        计算文件的MD5哈希值
        用于生成唯一的文件标识
        """
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # 分块读取，避免大文件占用过多内存
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_audio_object_name(self, video_path):
        """
        根据视频文件生成固定的音频对象名称
        使用视频文件的MD5哈希确保唯一性
        """
        # 计算视频文件的哈希
        file_hash = self.get_file_hash(video_path)
        # 获取文件扩展名
        ext = Path(video_path).suffix
        # 生成对象名称：audio/hash_原始文件名.mp3
        base_name = Path(video_path).stem
        object_name = f"audio/{file_hash}_{base_name}.mp3"
        return object_name

    def upload_audio_to_oss(self, audio_path, object_name):
        """
        上传音频文件到OSS

        Args:
            audio_path: 本地音频文件路径
            object_name: OSS对象名称

        Returns:
            file_url: 带签名的临时访问URL
        """
        # 检查文件是否已存在
        if self.bucket.object_exists(object_name):
            print(f"  音频文件已存在于OSS，跳过上传: {object_name}")
        else:
            # 上传文件
            self.bucket.put_object_from_file(object_name, audio_path)
            print(f"  音频文件已上传: {object_name}")

        # 生成带签名的临时访问URL（有效期1小时）
        # 使用签名URL可以让语音识别服务访问私有OSS文件
        file_url = self.bucket.sign_url('GET', object_name, 3600)
        return file_url

    def submit_task(self, file_url):
        """
        提交录音文件识别请求（按照官方示例 + 高级参数优化）

        Args:
            file_url: 音频文件的URL

        Returns:
            task_id: 任务ID
        """
        # 创建POST请求
        postRequest = CommonRequest()
        postRequest.set_domain(self.DOMAIN)
        postRequest.set_version(self.API_VERSION)
        postRequest.set_product(self.PRODUCT)
        postRequest.set_action_name(self.POST_REQUEST_ACTION)
        postRequest.set_method('POST')

        # 设置任务参数（优化版，添加高级参数提升识别质量）
        task = {
            self.KEY_APP_KEY: self.app_key,
            self.KEY_FILE_LINK: file_url,
            self.KEY_VERSION: "4.0",
            self.KEY_ENABLE_WORDS: True,  # 启用词级别识别（更精确的时间戳）
            "enable_inverse_text_normalization": True,  # 数字/时间格式化（12点 → 12:00）
            "enable_punctuation_prediction": True,      # 自动标点符号
            "enable_semantic_sentence_detection": True, # 语义断句（更自然）
            "disfluency_removal": False,                # 不删除口语词（保持原意）
            "max_single_segment_time": 15000,           # 最长单句15秒（默认10秒，适合长句）
        }

        # 根据语言添加特定参数
        if self.language == "en":
            # 英语识别优化
            task["language_hints"] = ["en-US"]  # 明确指定英语
            print("  语言设置: 英语 (en-US)")
        else:
            # 中文识别（默认）
            print("  语言设置: 中文 (默认)")

        task_json = json.dumps(task)
        print(f"  提交任务参数: {task_json}")
        postRequest.add_body_params(self.KEY_TASK, task_json)

        # 发送请求
        try:
            postResponse = self.client.do_action_with_exception(postRequest)
            # 处理不同类型的响应（兼容不同SDK版本）
            if isinstance(postResponse, bytes):
                postResponse = json.loads(postResponse.decode('utf-8'))
            elif isinstance(postResponse, str):
                postResponse = json.loads(postResponse)
            # 如果已经是dict，直接使用
            print(f"  服务器响应: {postResponse}")

            statusText = postResponse.get(self.KEY_STATUS_TEXT)
            if statusText == self.STATUS_SUCCESS:
                print("  ✓ 录音文件识别请求成功响应！")
                taskId = postResponse.get(self.KEY_TASK_ID)
                return taskId
            else:
                raise Exception(f"录音文件识别请求失败: {statusText}")

        except ServerException as e:
            raise Exception(f"服务器错误: {e}")
        except ClientException as e:
            raise Exception(f"客户端错误: {e}")

    def get_task_result(self, task_id, max_wait_time=300, poll_interval=10):
        """
        查询识别任务结果（按照官方示例的轮询方式）

        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            result: 识别结果JSON字符串
        """
        # 创建GET请求
        getRequest = CommonRequest()
        getRequest.set_domain(self.DOMAIN)
        getRequest.set_version(self.API_VERSION)
        getRequest.set_product(self.PRODUCT)
        getRequest.set_action_name(self.GET_REQUEST_ACTION)
        getRequest.set_method('GET')
        getRequest.add_query_param(self.KEY_TASK_ID, task_id)

        # 以轮询的方式进行识别结果的查询
        # 直到服务端返回的状态描述符为"SUCCESS"、"SUCCESS_WITH_NO_VALID_FRAGMENT"，
        # 或者为错误描述，则结束轮询
        start_time = time.time()
        statusText = ""

        while True:
            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                raise Exception(f"识别任务超时（等待时间超过{max_wait_time}秒）")

            try:
                getResponse = self.client.do_action_with_exception(getRequest)
                # 处理不同类型的响应（兼容不同SDK版本）
                if isinstance(getResponse, bytes):
                    getResponse = json.loads(getResponse.decode('utf-8'))
                elif isinstance(getResponse, str):
                    getResponse = json.loads(getResponse)
                # 如果已经是dict，直接使用
                print(f"  查询结果: {getResponse}")

                statusText = getResponse.get(self.KEY_STATUS_TEXT)

                if statusText == self.STATUS_RUNNING or statusText == self.STATUS_QUEUEING:
                    # 继续轮询
                    print(f"  任务状态: {statusText}, 等待中... ({int(elapsed_time)}秒/{max_wait_time}秒)")
                    time.sleep(poll_interval)
                else:
                    # 退出轮询
                    break

            except ServerException as e:
                print(f"  服务器错误: {e}")
                time.sleep(poll_interval)
            except ClientException as e:
                print(f"  客户端错误: {e}")
                time.sleep(poll_interval)

        # 检查最终状态
        if statusText == self.STATUS_SUCCESS:
            print("  ✓ 录音文件识别成功！")
            return getResponse.get(self.KEY_RESULT)
        else:
            raise Exception(f"录音文件识别失败: {statusText}")

    def transcribe_file(self, file_url, audio_duration=None):
        """
        完整的文件转录流程

        Args:
            file_url: 音频文件URL
            audio_duration: 音频时长（秒），用于动态计算超时时间

        Returns:
            result: 识别结果JSON字符串
        """
        # 步骤1: 提交任务
        task_id = self.submit_task(file_url)

        # 步骤2: 等待任务完成
        # 动态计算超时时间：音频时长 × 3 + 60秒缓冲，最小120秒，最大600秒
        if audio_duration:
            max_wait_time = max(120, min(600, int(audio_duration * 3 + 60)))
            print(f"  音频时长: {audio_duration:.1f}秒，设置超时: {max_wait_time}秒")
        else:
            max_wait_time = 300  # 默认5分钟
            print(f"  未获取音频时长，使用默认超时: {max_wait_time}秒")

        result = self.get_task_result(task_id, max_wait_time=max_wait_time, poll_interval=10)
        return result

    def cleanup_oss_file(self, object_name):
        """
        清理OSS上的临时文件

        Args:
            object_name: OSS对象名称
        """
        try:
            self.bucket.delete_object(object_name)
            print(f"  ✓ OSS文件已清理: {object_name}")
        except Exception as e:
            print(f"  ⚠ OSS清理失败（可手动删除）: {str(e)}")
