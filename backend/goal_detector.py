"""
GOAL 이미지 감지 모듈
OpenCV 템플릿 매칭을 사용하여 테일즈런너 GOAL 화면을 감지
"""

import cv2
import numpy as np
import time
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass

from screen_capture import capture_primary_monitor


@dataclass
class DetectionResult:
    """감지 결과를 담는 데이터 클래스"""
    detected: bool
    confidence: float
    location: Optional[Tuple[int, int]] = None  # (x, y) 좌표
    timestamp: float = 0.0


class GoalDetector:
    """GOAL 화면 감지기"""
    
    # 감지 설정
    CONFIDENCE_THRESHOLD = 0.75  # 신뢰도 임계값
    COOLDOWN_SECONDS = 3.0       # 중복 감지 방지 쿨다운
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Args:
            template_path: GOAL 템플릿 이미지 경로 (없으면 색상 기반 감지 사용)
        """
        self._template: Optional[np.ndarray] = None
        self._last_detection_time: float = 0.0
        self._is_running: bool = False
        
        # 템플릿 로드 시도
        if template_path and Path(template_path).exists():
            self._template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if self._template is not None:
                # 여러 크기에서 매칭할 수 있도록 그레이스케일로 변환
                self._template_gray = cv2.cvtColor(self._template, cv2.COLOR_BGR2GRAY)
    
    def detect_goal_by_color(self, image: np.ndarray) -> DetectionResult:
        """
        GOAL 텍스트의 특징적인 오렌지-골드 색상으로 감지
        템플릿이 없을 때 폴백으로 사용
        
        GOAL 텍스트 색상 범위 (HSV):
        - Hue: 15-35 (오렌지-골드)
        - Saturation: 150-255 (채도 높음)
        - Value: 200-255 (밝음)
        """
        # BGR -> HSV 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # GOAL 텍스트의 오렌지-골드 색상 범위
        lower_orange = np.array([15, 150, 200])
        upper_orange = np.array([35, 255, 255])
        
        # 마스크 생성
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        
        # 노이즈 제거
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 컨투어 찾기
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 일정 크기 이상의 영역이 있으면 GOAL로 판단
        # GOAL 텍스트는 화면에서 상당히 큰 영역을 차지함
        large_contours = [c for c in contours if cv2.contourArea(c) > 5000]
        
        if large_contours:
            # 가장 큰 컨투어의 중심점 계산
            largest = max(large_contours, key=cv2.contourArea)
            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # 신뢰도는 영역 크기에 비례
                area = cv2.contourArea(largest)
                confidence = min(area / 50000, 1.0)  # 정규화
                
                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    location=(cx, cy),
                    timestamp=time.time()
                )
        
        return DetectionResult(detected=False, confidence=0.0, timestamp=time.time())
    
    def detect_goal_by_template(self, image: np.ndarray) -> DetectionResult:
        """
        템플릿 매칭으로 GOAL 감지
        """
        if self._template is None:
            return self.detect_goal_by_color(image)
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 다중 스케일 템플릿 매칭
        best_match = 0.0
        best_location = None
        
        for scale in [0.5, 0.75, 1.0, 1.25, 1.5]:
            # 템플릿 크기 조정
            width = int(self._template_gray.shape[1] * scale)
            height = int(self._template_gray.shape[0] * scale)
            
            if width < 10 or height < 10:
                continue
                
            resized_template = cv2.resize(self._template_gray, (width, height))
            
            # 이미지가 템플릿보다 작으면 스킵
            if gray.shape[0] < height or gray.shape[1] < width:
                continue
            
            # 템플릿 매칭
            result = cv2.matchTemplate(gray, resized_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_match:
                best_match = max_val
                best_location = (max_loc[0] + width // 2, max_loc[1] + height // 2)
        
        detected = best_match >= self.CONFIDENCE_THRESHOLD
        
        return DetectionResult(
            detected=detected,
            confidence=best_match,
            location=best_location if detected else None,
            timestamp=time.time()
        )
    
    def check_for_goal(self) -> Optional[DetectionResult]:
        """
        화면을 캡처하고 GOAL 감지 수행
        쿨다운 중이면 None 반환
        
        Returns:
            DetectionResult if detection attempted, None if in cooldown
        """
        current_time = time.time()
        
        # 쿨다운 체크
        if current_time - self._last_detection_time < self.COOLDOWN_SECONDS:
            return None
        
        # 화면 캡처
        screen = capture_primary_monitor()
        
        # 감지 수행 (템플릿 있으면 템플릿 매칭, 없으면 색상 기반)
        if self._template is not None:
            result = self.detect_goal_by_template(screen)
        else:
            result = self.detect_goal_by_color(screen)
        
        # 감지 성공 시 쿨다운 시작
        if result.detected:
            self._last_detection_time = current_time
        
        return result
    
    @property
    def is_in_cooldown(self) -> bool:
        """현재 쿨다운 중인지 확인"""
        return time.time() - self._last_detection_time < self.COOLDOWN_SECONDS
    
    def reset_cooldown(self) -> None:
        """쿨다운 리셋"""
        self._last_detection_time = 0.0


# 모듈 레벨 인스턴스 (싱글톤)
_detector: Optional[GoalDetector] = None


def get_detector(template_path: Optional[str] = None) -> GoalDetector:
    """GoalDetector 싱글톤 인스턴스 반환"""
    global _detector
    if _detector is None:
        _detector = GoalDetector(template_path)
    return _detector
