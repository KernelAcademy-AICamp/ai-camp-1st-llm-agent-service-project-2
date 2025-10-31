"""
Hardware Detection Module
GPU/CPU 환경 자동 감지 시스템
"""

import platform
import subprocess
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """장치 타입"""
    CPU = "cpu"
    CUDA = "cuda"  # NVIDIA GPU
    MPS = "mps"  # Apple Silicon GPU
    ROCM = "rocm"  # AMD GPU


class HardwareInfo:
    """하드웨어 정보"""

    def __init__(self):
        self.device_type: DeviceType = DeviceType.CPU
        self.device_count: int = 0
        self.device_name: Optional[str] = None
        self.total_memory: Optional[int] = None  # MB
        self.cuda_version: Optional[str] = None
        self.compute_capability: Optional[str] = None
        self.platform: str = platform.system()
        self.platform_version: str = platform.release()


class HardwareDetector:
    """
    시스템 하드웨어 자동 감지
    """

    @staticmethod
    def detect() -> HardwareInfo:
        """
        사용 가능한 하드웨어 환경 감지

        Returns:
            HardwareInfo: 감지된 하드웨어 정보
        """
        hw_info = HardwareInfo()

        # 1. NVIDIA GPU (CUDA) 감지
        if HardwareDetector._check_cuda():
            hw_info.device_type = DeviceType.CUDA
            hw_info.device_count = HardwareDetector._get_cuda_device_count()
            hw_info.device_name = HardwareDetector._get_cuda_device_name()
            hw_info.total_memory = HardwareDetector._get_cuda_memory()
            hw_info.cuda_version = HardwareDetector._get_cuda_version()
            logger.info(
                f"CUDA detected: {hw_info.device_count} device(s), "
                f"{hw_info.device_name}, {hw_info.total_memory}MB"
            )
            return hw_info

        # 2. Apple Silicon (MPS) 감지
        if HardwareDetector._check_mps():
            hw_info.device_type = DeviceType.MPS
            hw_info.device_count = 1
            hw_info.device_name = HardwareDetector._get_apple_chip_name()
            logger.info(f"Apple Silicon MPS detected: {hw_info.device_name}")
            return hw_info

        # 3. AMD GPU (ROCm) 감지
        if HardwareDetector._check_rocm():
            hw_info.device_type = DeviceType.ROCM
            hw_info.device_count = HardwareDetector._get_rocm_device_count()
            hw_info.device_name = "AMD GPU (ROCm)"
            logger.info(f"ROCm detected: {hw_info.device_count} device(s)")
            return hw_info

        # 4. CPU만 사용 가능
        hw_info.device_type = DeviceType.CPU
        hw_info.device_count = 1
        hw_info.device_name = "CPU"
        logger.info("Using CPU for computation")
        return hw_info

    # ========================================================================
    # CUDA Detection (NVIDIA GPU)
    # ========================================================================

    @staticmethod
    def _check_cuda() -> bool:
        """CUDA 사용 가능 여부 확인"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            logger.debug("PyTorch not installed, checking nvidia-smi")
            try:
                subprocess.run(
                    ['nvidia-smi'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=5
                )
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return False

    @staticmethod
    def _get_cuda_device_count() -> int:
        """CUDA 장치 수 조회"""
        try:
            import torch
            return torch.cuda.device_count()
        except ImportError:
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--list-gpus'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                gpus = [line for line in result.stdout.strip().split('\n') if line]
                return len(gpus)
            except Exception:
                return 0

    @staticmethod
    def _get_cuda_device_name() -> Optional[str]:
        """CUDA 장치 이름 조회"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
        except Exception:
            pass
        return None

    @staticmethod
    def _get_cuda_memory() -> Optional[int]:
        """CUDA 메모리 크기 조회 (MB)"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.get_device_properties(0).total_memory // (1024 ** 2)
        except Exception:
            pass
        return None

    @staticmethod
    def _get_cuda_version() -> Optional[str]:
        """CUDA 버전 조회"""
        try:
            import torch
            return torch.version.cuda
        except Exception:
            pass
        return None

    # ========================================================================
    # Apple Silicon (MPS) Detection
    # ========================================================================

    @staticmethod
    def _check_mps() -> bool:
        """Apple Silicon MPS 사용 가능 여부 확인"""
        if platform.system() != "Darwin":
            return False

        try:
            import torch
            return torch.backends.mps.is_available()
        except Exception:
            # PyTorch 없으면 macOS + ARM 확인
            return platform.processor() == 'arm' or 'arm' in platform.machine().lower()

    @staticmethod
    def _get_apple_chip_name() -> str:
        """Apple Silicon 칩 이름 조회"""
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            chip_name = result.stdout.strip()
            if chip_name:
                return chip_name
        except Exception:
            pass

        # 기본값
        machine = platform.machine()
        if 'arm' in machine.lower():
            return "Apple Silicon (ARM)"
        return "Apple Silicon"

    # ========================================================================
    # AMD ROCm Detection
    # ========================================================================

    @staticmethod
    def _check_rocm() -> bool:
        """AMD ROCm 사용 가능 여부 확인"""
        try:
            subprocess.run(
                ['rocm-smi'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _get_rocm_device_count() -> int:
        """ROCm 장치 수 조회"""
        try:
            result = subprocess.run(
                ['rocm-smi', '--showid'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return len([line for line in result.stdout.split('\n') if 'GPU' in line])
        except Exception:
            return 0


# ============================================================================
# Singleton Pattern - 하드웨어 정보 캐싱
# ============================================================================

_hardware_info: Optional[HardwareInfo] = None


def get_hardware_info() -> HardwareInfo:
    """
    하드웨어 정보 조회 (캐싱)

    Returns:
        HardwareInfo: 하드웨어 정보
    """
    global _hardware_info

    if _hardware_info is None:
        _hardware_info = HardwareDetector.detect()

    return _hardware_info


def print_hardware_info():
    """하드웨어 정보 출력 (디버깅용)"""
    hw = get_hardware_info()

    print("=" * 70)
    print("HARDWARE CONFIGURATION")
    print("=" * 70)
    print(f"Platform       : {hw.platform} {hw.platform_version}")
    print(f"Device Type    : {hw.device_type.value.upper()}")
    print(f"Device Count   : {hw.device_count}")

    if hw.device_name:
        print(f"Device Name    : {hw.device_name}")

    if hw.total_memory:
        print(f"Total Memory   : {hw.total_memory} MB ({hw.total_memory / 1024:.2f} GB)")

    if hw.cuda_version:
        print(f"CUDA Version   : {hw.cuda_version}")

    print("=" * 70)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)
    print("\nTesting Hardware Detector...\n")
    print_hardware_info()

    hw = get_hardware_info()
    print(f"\nRecommended OCR Engine: ", end="")

    if hw.device_type == DeviceType.CUDA:
        if hw.total_memory and hw.total_memory >= 4096:
            print("PaddleOCR (GPU)")
        else:
            print("EasyOCR (GPU)")
    elif hw.device_type in [DeviceType.MPS, DeviceType.ROCM]:
        print("EasyOCR (GPU)")
    else:
        print("Tesseract (CPU)")
