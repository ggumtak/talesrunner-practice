"""
화면 캡처 모듈
mss 라이브러리를 사용하여 게임 화면을 캡처하는 유틸리티
"""

import mss
import numpy as np
from PIL import Image
from typing import Optional

# 싱글톤 패턴으로 mss 인스턴스 관리
_sct: Optional[mss.mss] = None


def get_screen_capture_instance() -> mss.mss:
    """mss 인스턴스를 반환 (싱글톤)"""
    global _sct
    if _sct is None:
        _sct = mss.mss()
    return _sct


def capture_primary_monitor() -> np.ndarray:
    """
    주 모니터 전체를 캡처하여 numpy 배열로 반환
    
    Returns:
        np.ndarray: BGR 형식의 이미지 배열 (OpenCV 호환)
    """
    sct = get_screen_capture_instance()
    # monitor[1]은 주 모니터
    monitor = sct.monitors[1]
    screenshot = sct.grab(monitor)
    
    # BGRA -> BGR 변환 (OpenCV 호환)
    img = np.array(screenshot)
    return img[:, :, :3]


def capture_region(left: int, top: int, width: int, height: int) -> np.ndarray:
    """
    특정 영역만 캡처
    
    Args:
        left: 캡처 시작 x 좌표
        top: 캡처 시작 y 좌표
        width: 캡처 너비
        height: 캡처 높이
    
    Returns:
        np.ndarray: BGR 형식의 이미지 배열
    """
    sct = get_screen_capture_instance()
    monitor = {
        "left": left,
        "top": top,
        "width": width,
        "height": height
    }
    screenshot = sct.grab(monitor)
    img = np.array(screenshot)
    return img[:, :, :3]


def save_screenshot(image: np.ndarray, filepath: str) -> None:
    """
    캡처된 이미지를 파일로 저장
    
    Args:
        image: numpy 배열 형태의 이미지
        filepath: 저장할 파일 경로
    """
    # BGR -> RGB 변환 후 저장
    pil_image = Image.fromarray(image[:, :, ::-1])
    pil_image.save(filepath)


def cleanup() -> None:
    """mss 인스턴스 정리"""
    global _sct
    if _sct is not None:
        _sct.close()
        _sct = None
