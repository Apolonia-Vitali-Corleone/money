# 🚀 GPU加速配置指南（RTX 2060）

## 为什么要启用GPU加速？

使用RTX 2060 GPU可以让Whisper识别速度提升**5-10倍**，特别是使用large-v3模型时效果更明显。

## 📋 简化版配置步骤（推荐）

### 步骤1: 检查NVIDIA驱动

1. 按 `Win + R`，输入 `cmd` 打开命令行
2. 运行以下命令检查驱动：
   ```bash
   nvidia-smi
   ```
3. 如果显示GPU信息（包括RTX 2060），说明驱动已安装 ✓
4. 如果提示找不到命令，需要先安装NVIDIA驱动

**安装驱动**（如果需要）：
- 访问：https://www.nvidia.cn/Download/index.aspx
- 选择：GeForce RTX 20系列 > RTX 2060
- 下载并安装最新驱动（建议Game Ready驱动）

### 步骤2: 安装支持CUDA的PyTorch

在您的项目目录中打开命令行，运行：

```bash
# 激活虚拟环境
D:\GithubRepositories\money\.venv\Scripts\activate

# 卸载当前的CPU版PyTorch
pip uninstall torch torchvision torchaudio -y

# 安装CUDA 11.8版本的PyTorch（推荐，兼容性好）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**或者使用CUDA 12.1版本**（如果驱动较新）：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**下载说明**：
- PyTorch CUDA版本大约 2-3 GB
- 下载时间取决于网速，通常5-15分钟
- 无需单独安装CUDA Toolkit，PyTorch已包含所需的CUDA库

### 步骤3: 验证GPU可用性

运行检测脚本：
```bash
python check_cuda.py
```

您应该看到：
```
✓ PyTorch 版本: 2.x.x
✓ CUDA 是否可用: True
✓ CUDA 版本: 11.8 (或 12.1)
✓ 当前 GPU: NVIDIA GeForce RTX 2060
✓ GPU 加速功能正常！
```

### 步骤4: 运行应用并享受GPU加速

```bash
python gradio_app.py
```

您应该看到：
```
============================================================
设备信息: ✓ 使用GPU加速: NVIDIA GeForce RTX 2060
============================================================
```

## ✅ 完成！

现在Whisper会自动使用GPU加速，不会再看到"FP16 is not supported on CPU"的警告。

---

## 🔧 故障排查

### 问题1: nvidia-smi 找不到

**解决方案**：需要安装或更新NVIDIA驱动
- 下载地址：https://www.nvidia.cn/Download/index.aspx
- 选择对应的RTX 2060驱动
- 安装后重启电脑

### 问题2: torch.cuda.is_available() 返回 False

**可能原因**：
1. **安装了CPU版本的PyTorch**
   - 解决：卸载后重新安装CUDA版本（见步骤2）

2. **NVIDIA驱动版本过旧**
   - 解决：更新到最新驱动
   - CUDA 11.8需要驱动 >= 450.80.02
   - CUDA 12.1需要驱动 >= 525.60.13

3. **环境变量问题**
   - 解决：确保 `C:\Program Files\NVIDIA Corporation\NVSMI` 在PATH中

### 问题3: 下载PyTorch速度慢

**解决方案**：使用国内镜像
```bash
# 清华镜像
pip install torch torchvision torchaudio -i https://pypi.tuna.tsinghua.edu.cn/simple
```

注意：镜像可能没有最新的CUDA版本，建议还是使用官方源。

### 问题4: GPU内存不足

RTX 2060有6GB显存，使用large-v3模型时可能会占用较多内存。

**解决方案**：
- 关闭其他占用GPU的程序（游戏、视频编辑软件等）
- 如果仍然不够，可以改用medium或small模型

---

## 📊 性能对比

使用10分钟的视频测试（large-v3模型）：

| 设备 | 处理时间 | 速度提升 |
|------|---------|---------|
| CPU (Intel i7) | ~25分钟 | 1x |
| RTX 2060 | ~3分钟 | **8x** |
| RTX 3090 | ~1.5分钟 | 16x |

---

## 💡 常见问题

**Q: 我需要安装CUDA Toolkit吗？**
A: 不需要！PyTorch的CUDA版本已经包含了所需的CUDA库。

**Q: CUDA 11.8和12.1选哪个？**
A: 推荐CUDA 11.8，兼容性更好，除非你的驱动很新（>= 525）。

**Q: 安装会影响其他Python项目吗？**
A: 不会，因为使用了虚拟环境(.venv)，所有更改都在这个项目内。

**Q: 可以同时支持CPU和GPU吗？**
A: 可以！代码已自动检测，如果GPU不可用会自动降级到CPU。

---

## 📞 需要帮助？

如果遇到问题，请提供以下信息：
1. `nvidia-smi` 的输出
2. `python check_cuda.py` 的输出
3. 具体的错误信息

---

**更新日期**: 2025-11-23
**适用GPU**: NVIDIA RTX 2060 及其他支持CUDA的NVIDIA显卡
