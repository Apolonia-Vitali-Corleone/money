# 阿里云语音识别服务配置指南

本项目使用阿里云语音识别服务为视频自动添加中文字幕。按照以下步骤配置阿里云服务。

## 前置要求

1. 有效的阿里云账号
2. 开通语音识别服务
3. 创建OSS存储桶

## 配置步骤

### 1. 获取 AccessKey

AccessKey 用于程序访问阿里云API。

1. 登录 [阿里云控制台](https://www.aliyun.com/)
2. 点击右上角头像，选择 **AccessKey 管理**
3. 如果没有AccessKey，点击 **创建 AccessKey**
4. 记录下 **AccessKey ID** 和 **AccessKey Secret**（Secret只显示一次，请妥善保存）

> ⚠️ **安全提示**: AccessKey权限很大，请勿泄露。建议使用RAM子账号的AccessKey。

参考文档：[如何获取AccessKey](https://help.aliyun.com/document_detail/53045.html)

### 2. 开通语音识别服务

1. 访问 [阿里云语音识别服务](https://www.aliyun.com/product/nls)
2. 点击 **立即开通** 或 **管理控制台**
3. 进入 [语音识别控制台](https://nls-portal.console.aliyun.com/)

### 3. 创建语音识别应用

1. 在语音识别控制台，点击 **项目管理**
2. 点击 **创建项目**
3. 填写项目名称（例如：视频字幕生成）
4. 创建成功后，点击项目进入详情页
5. 记录下 **AppKey**（后续需要使用）

### 4. 创建 OSS 存储桶

OSS用于临时存储上传的音频文件（处理完会自动删除）。

1. 访问 [OSS控制台](https://oss.console.aliyun.com/)
2. 点击 **创建 Bucket**
3. 配置：
   - **Bucket名称**：自定义（例如：my-video-subtitle）
   - **地域**：建议选择 **华东1（杭州）** 或 **华东2（上海）**
   - **存储类型**：标准存储
   - **读写权限**：私有（推荐）
4. 点击 **确定** 创建
5. 记录下 **Bucket名称** 和 **地域**（例如：cn-shanghai）

参考文档：[如何创建OSS存储桶](https://help.aliyun.com/document_detail/31885.html)

### 5. 配置环境变量（命令行工具）

如果使用命令行工具 `add_chinese_subtitle.py`，需要设置环境变量：

#### Linux/Mac

```bash
export ALIBABA_ACCESS_KEY_ID='你的AccessKey ID'
export ALIBABA_ACCESS_KEY_SECRET='你的AccessKey Secret'
export ALIBABA_APP_KEY='你的AppKey'
export ALIBABA_OSS_BUCKET='你的Bucket名称'
export ALIBABA_REGION='cn-shanghai'  # 可选，默认cn-shanghai
```

#### Windows (PowerShell)

```powershell
$env:ALIBABA_ACCESS_KEY_ID='你的AccessKey ID'
$env:ALIBABA_ACCESS_KEY_SECRET='你的AccessKey Secret'
$env:ALIBABA_APP_KEY='你的AppKey'
$env:ALIBABA_OSS_BUCKET='你的Bucket名称'
$env:ALIBABA_REGION='cn-shanghai'  # 可选，默认cn-shanghai
```

#### Windows (CMD)

```cmd
set ALIBABA_ACCESS_KEY_ID=你的AccessKey ID
set ALIBABA_ACCESS_KEY_SECRET=你的AccessKey Secret
set ALIBABA_APP_KEY=你的AppKey
set ALIBABA_OSS_BUCKET=你的Bucket名称
set ALIBABA_REGION=cn-shanghai
```

### 6. 配置Web界面（Gradio）

如果使用Web界面 `gradio_app.py`，在界面上直接填写配置即可，无需设置环境变量。

## 配置示例

完整的配置示例：

```bash
# AccessKey
ALIBABA_ACCESS_KEY_ID=LTAI5tABCDEFGH12345678
ALIBABA_ACCESS_KEY_SECRET=abcdefghijklmnopqrstuvwxyz123456

# 语音识别AppKey
ALIBABA_APP_KEY=1234567890abcdef

# OSS存储桶
ALIBABA_OSS_BUCKET=my-video-subtitle
ALIBABA_REGION=cn-shanghai
```

## 费用说明

使用阿里云语音识别服务会产生费用：

1. **语音识别费用**：
   - 每月前2小时免费
   - 超出部分按时长计费（约￥0.025/分钟）

2. **OSS存储费用**：
   - 标准存储：￥0.12/GB/月
   - 由于音频文件处理后会自动删除，存储费用极低

3. **OSS流量费用**：
   - 上传流量免费
   - 下载流量：￥0.5/GB

详细价格请参考：
- [语音识别定价](https://www.aliyun.com/price/product?spm=5176.19720258.J_3207526240.3.e9392c4aCQKbHg#/nls/detail)
- [OSS定价](https://www.aliyun.com/price/product?spm=5176.7933691.J_8058803260.2.5e5b2a66XPzL5y#/oss/detail)

## 常见问题

### Q1: 提示 "AccessKey ID 不存在"

检查AccessKey ID是否正确，注意不要有多余的空格。

### Q2: 提示 "权限不足"

确保AccessKey对应的账号有语音识别和OSS的访问权限。

### Q3: 提示 "Bucket不存在"

检查Bucket名称是否正确，以及Bucket所在地域是否匹配。

### Q4: 识别任务超时

- 检查网络连接是否正常
- 音频文件过大可能需要更长时间
- 可以在代码中增加`max_retries`的值

### Q5: 识别结果为空

- 检查视频是否包含音频
- 音频是否包含清晰的语音内容
- 尝试增大音频音量

## 技术支持

- 阿里云官方文档：https://help.aliyun.com/
- 语音识别文档：https://help.aliyun.com/product/30413.html
- 工单支持：https://selfservice.console.aliyun.com/ticket/createIndex

## 安全建议

1. **不要**将AccessKey硬编码在代码中
2. **不要**将包含AccessKey的配置文件提交到Git仓库
3. 建议使用RAM子账号，只授予必要的权限
4. 定期轮换AccessKey
5. 启用MFA（多因素认证）保护主账号
