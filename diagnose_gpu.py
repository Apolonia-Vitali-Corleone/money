#!/usr/bin/env python3
"""
GPU显存诊断工具
帮助诊断CUDA内存问题并提供优化建议
"""
import sys

print("=" * 70)
print("GPU 显存诊断工具")
print("=" * 70)

# 检查PyTorch
try:
    import torch
    print(f"\n✓ PyTorch 版本: {torch.__version__}")
    print(f"✓ CUDA 是否可用: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"✓ CUDA 版本: {torch.version.cuda}")
        print(f"✓ GPU 数量: {torch.cuda.device_count()}")
        print(f"✓ 当前 GPU: {torch.cuda.get_device_name(0)}")

        # 显存信息
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        allocated = torch.cuda.memory_allocated(0) / 1024**3
        reserved = torch.cuda.memory_reserved(0) / 1024**3
        free = total_memory - reserved

        print(f"\n{'显存统计':=^70}")
        print(f"总显存:        {total_memory:.2f} GB")
        print(f"已分配:        {allocated:.2f} GB ({allocated/total_memory*100:.1f}%)")
        print(f"已保留:        {reserved:.2f} GB ({reserved/total_memory*100:.1f}%)")
        print(f"可用:          {free:.2f} GB ({free/total_memory*100:.1f}%)")

        # 清理并重新检测
        torch.cuda.empty_cache()
        import gc
        gc.collect()

        allocated_after = torch.cuda.memory_allocated(0) / 1024**3
        reserved_after = torch.cuda.memory_reserved(0) / 1024**3
        free_after = total_memory - reserved_after

        print(f"\n{'清理缓存后':=^70}")
        print(f"已分配:        {allocated_after:.2f} GB ({allocated_after/total_memory*100:.1f}%)")
        print(f"已保留:        {reserved_after:.2f} GB ({reserved_after/total_memory*100:.1f}%)")
        print(f"可用:          {free_after:.2f} GB ({free_after/total_memory*100:.1f}%)")

        # 建议
        print(f"\n{'优化建议':=^70}")
        if total_memory < 8:
            print("⚠ 显存容量较小 (< 8GB)，建议：")
            print("  1. 使用 base 或 small 模型，避免使用 large-v3")
            print("  2. 启用显存优化参数（已在代码中实现）")
            print("  3. 处理前关闭其他占用GPU的程序")

        if reserved > total_memory * 0.7:
            print("⚠ 显存使用率较高，建议：")
            print("  1. 重启Python程序释放显存")
            print("  2. 使用 torch.cuda.empty_cache() 清理缓存")
            print("  3. 考虑使用CPU模式处理")

        if free_after > 2:
            print("✓ 显存充足，可以使用GPU模式")
        elif free_after > 1:
            print("⚠ 显存紧张，建议使用 base 或 small 模型")
        else:
            print("❌ 显存严重不足，建议使用 CPU 模式")

        # Whisper 模型显存需求
        print(f"\n{'Whisper 模型显存需求参考':=^70}")
        print("tiny:          ~1 GB")
        print("base:          ~1.5 GB")
        print("small:         ~2.5 GB")
        print("medium:        ~5 GB")
        print("large/large-v3: ~7-10 GB (包括处理开销)")

        print(f"\n{'推荐配置':=^70}")
        if total_memory >= 10:
            print("✓ 可使用 large-v3 模型（最佳准确度）")
        elif total_memory >= 8:
            print("✓ 可使用 medium 模型（较好准确度）")
        elif total_memory >= 6:
            print("✓ 可使用 small 或 base 模型（建议使用优化参数）")
        else:
            print("⚠ 建议使用 CPU 模式或升级显卡")

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
    print("\n" + "=" * 70)
    print("GPU 加速测试")
    print("=" * 70)
    try:
        # 创建一个测试张量并移到GPU
        print("执行矩阵运算测试...")
        test_tensor = torch.randn(1000, 1000).cuda()
        result = test_tensor @ test_tensor
        torch.cuda.synchronize()
        print("✓ GPU 加速功能正常！")

        # 清理测试张量
        del test_tensor, result
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"❌ GPU 测试失败: {e}")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
