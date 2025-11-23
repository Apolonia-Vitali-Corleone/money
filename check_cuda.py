#!/usr/bin/env python3
"""
检测CUDA和PyTorch GPU支持状态
"""
import sys

print("=" * 60)
print("CUDA 和 GPU 环境检测")
print("=" * 60)

# 检查PyTorch
try:
    import torch
    print(f"\n✓ PyTorch 版本: {torch.__version__}")
    print(f"✓ CUDA 是否可用: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"✓ CUDA 版本: {torch.version.cuda}")
        print(f"✓ GPU 数量: {torch.cuda.device_count()}")
        print(f"✓ 当前 GPU: {torch.cuda.get_device_name(0)}")
        print(f"✓ GPU 内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("\n⚠ CUDA 不可用 - PyTorch 将使用 CPU")
        print("\n可能的原因：")
        print("1. 安装的是CPU版本的PyTorch")
        print("2. NVIDIA驱动未安装或版本过旧")
        print("3. CUDA Toolkit未安装")

except ImportError:
    print("\n❌ PyTorch 未安装")
    sys.exit(1)

# 检查Whisper
try:
    import whisper
    print(f"\n✓ Whisper 已安装")
except ImportError:
    print("\n❌ Whisper 未安装")

# 测试GPU加速
if torch.cuda.is_available():
    print("\n" + "=" * 60)
    print("GPU 加速测试")
    print("=" * 60)
    try:
        # 创建一个测试张量并移到GPU
        test_tensor = torch.randn(1000, 1000).cuda()
        result = test_tensor @ test_tensor
        print("✓ GPU 加速功能正常！")
    except Exception as e:
        print(f"❌ GPU 测试失败: {e}")

print("\n" + "=" * 60)
