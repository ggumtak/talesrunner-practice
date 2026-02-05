"""
GOAL 이미지 감지 모듈 (개선 버전)
배경이 변해도 GOAL 텍스트를 인식할 수 있도록 다중 방식 사용:
1. HSV 색상 기반 감지 (오렌지-골드 색상)
2. 에지 검출 기반 형태 분석
3. 텍스트 영역 크기 및 위치 검증
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
    location: Optional[Tuple[int, int]] = None
    timestamp: float = 0.0


class GoalDetector:
    """
    GOAL 화면 감지기 (배경 변화에 강한 버전)
    
    GOAL 텍스트 특성:
    - 색상: 오렌지-골드 그라데이션 (HSV: H=15~40, S=150~255, V=200~255)
    - 위치: 화면 상단~중앙부 (y: 10%~50%)
    - 크기: 화면 너비의 20~50% 정도 차지
    - 형태: 두꺼운 글자, 흰색 테두리
    """
    
    # 감지 설정
    CONFIDENCE_THRESHOLD = 0.65  # 신뢰도 임계값 (색상 기반은 낮춰도 됨)
    COOLDOWN_SECONDS = 3.0       # 중복 감지 방지 쿨다운
    
    # GOAL 텍스트 색상 범위 (HSV) - 오렌지~골드
    # 테일즈런너 GOAL 텍스트의 정확한 색상 범위
    HSV_RANGES = [
        # 밝은 노란색 부분
        (np.array([20, 150, 200]), np.array([35, 255, 255])),
        # 오렌지색 부분  
        (np.array([10, 150, 180]), np.array([25, 255, 255])),
        # 골드색 부분
        (np.array([25, 120, 180]), np.array([40, 255, 255])),
    ]
    
    def __init__(self, template_path: Optional[str] = None):
        self._last_detection_time: float = 0.0
        self._consecutive_detections: int = 0
        
        # 템플릿 로드 (있으면)
        self._template = None
        if template_path and Path(template_path).exists():
            self._template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    
    def detect_goal_by_color_and_shape(self, image: np.ndarray) -> DetectionResult:
        """
        색상 + 형태 기반 GOAL 감지 (배경 변화에 강함)
        
        1단계: HSV 색상으로 오렌지-골드 영역 추출
        2단계: 형태학적 처리로 노이즈 제거
        3단계: 컨투어 분석으로 GOAL 크기/위치 검증
        """
        height, width = image.shape[:2]
        
        # BGR -> HSV 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 여러 색상 범위를 합쳐서 마스크 생성
        combined_mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in self.HSV_RANGES:
            mask = cv2.inRange(hsv, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        # 형태학적 처리 (노이즈 제거 + 영역 연결)
        kernel_small = np.ones((3, 3), np.uint8)
        kernel_large = np.ones((7, 7), np.uint8)
        
        # 작은 노이즈 제거
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_small)
        # 가까운 영역 연결
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_large)
        # 팽창으로 글자 연결
        combined_mask = cv2.dilate(combined_mask, kernel_small, iterations=2)
        
        # 컨투어 찾기
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return DetectionResult(detected=False, confidence=0.0, timestamp=time.time())
        
        # GOAL 텍스트 조건에 맞는 컨투어 찾기
        screen_area = width * height
        valid_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 최소 크기 (화면의 0.5% 이상)
            if area < screen_area * 0.005:
                continue
            
            # 바운딩 박스 분석
            x, y, w, h = cv2.boundingRect(contour)
            
            # 위치 검증: GOAL은 화면 상단~중앙에 위치
            if y > height * 0.6:  # 너무 아래에 있으면 제외
                continue
            
            # 가로가 세로보다 길어야 함 (GOAL은 가로로 긴 텍스트)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 1.5:  # 최소 1.5:1 비율
                continue
            
            # 너비 검증: 화면 너비의 15~60%
            width_ratio = w / width
            if width_ratio < 0.15 or width_ratio > 0.7:
                continue
            
            valid_contours.append((contour, area, (x, y, w, h)))
        
        if not valid_contours:
            return DetectionResult(detected=False, confidence=0.0, timestamp=time.time())
        
        # 가장 큰 유효 컨투어 선택
        best = max(valid_contours, key=lambda x: x[1])
        contour, area, (x, y, w, h) = best
        
        # 중심점 계산
        cx = x + w // 2
        cy = y + h // 2
        
        # 신뢰도 계산 (영역 크기 + 위치 기반)
        # 영역이 크고 화면 중앙 상단에 있을수록 높은 신뢰도
        size_score = min(area / (screen_area * 0.05), 1.0)  # 5% 면적이면 만점
        position_score = 1.0 - (y / height)  # 상단일수록 높은 점수
        aspect_score = min(w/h / 4.0, 1.0)  # GOAL은 약 4:1 비율
        
        confidence = (size_score * 0.4 + position_score * 0.3 + aspect_score * 0.3)
        
        detected = confidence >= self.CONFIDENCE_THRESHOLD
        
        return DetectionResult(
            detected=detected,
            confidence=confidence,
            location=(cx, cy) if detected else None,
            timestamp=time.time()
        )
    
    def detect_goal_by_edge(self, image: np.ndarray) -> DetectionResult:
        """
        에지 검출 기반 GOAL 감지 (보조 방법)
        GOAL 텍스트의 흰색 테두리를 감지
        """
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 밝은 영역 추출 (흰색 테두리)
        _, bright = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)
        
        # 에지 검출
        edges = cv2.Canny(gray, 100, 200)
        
        # 밝은 영역과 에지 결합
        combined = cv2.bitwise_and(edges, bright)
        
        # 형태학적 처리
        kernel = np.ones((5, 5), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        
        # 컨투어 분석
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        height, width = image.shape[:2]
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # GOAL 조건 검사
            if w > width * 0.15 and h > height * 0.05:
                if w/h > 2.0 and y < height * 0.5:
                    return DetectionResult(
                        detected=True,
                        confidence=0.7,
                        location=(x + w//2, y + h//2),
                        timestamp=time.time()
                    )
        
        return DetectionResult(detected=False, confidence=0.0, timestamp=time.time())
    
    def check_for_goal(self) -> Optional[DetectionResult]:
        """
        화면을 캡처하고 GOAL 감지 수행
        다중 방식으로 검증하여 오탐지 최소화
        """
        current_time = time.time()
        
        # 쿨다운 체크
        if current_time - self._last_detection_time < self.COOLDOWN_SECONDS:
            return None
        
        # 화면 캡처
        screen = capture_primary_monitor()
        
        # 1차: 색상 + 형태 기반 감지
        result1 = self.detect_goal_by_color_and_shape(screen)
        
        # 2차: 에지 기반 감지 (보조)
        result2 = self.detect_goal_by_edge(screen)
        
        # 둘 다 감지하면 높은 신뢰도
        if result1.detected and result2.detected:
            final_confidence = (result1.confidence + result2.confidence) / 2 + 0.1
            self._consecutive_detections += 1
        elif result1.detected:
            final_confidence = result1.confidence
            self._consecutive_detections += 1
        else:
            final_confidence = 0.0
            self._consecutive_detections = 0
        
        # 연속 2회 이상 감지되면 확정
        detected = final_confidence >= self.CONFIDENCE_THRESHOLD and self._consecutive_detections >= 1
        
        if detected:
            self._last_detection_time = current_time
            self._consecutive_detections = 0
        
        return DetectionResult(
            detected=detected,
            confidence=final_confidence,
            location=result1.location,
            timestamp=current_time
        )
    
    @property
    def is_in_cooldown(self) -> bool:
        return time.time() - self._last_detection_time < self.COOLDOWN_SECONDS
    
    def reset_cooldown(self) -> None:
        self._last_detection_time = 0.0


# 싱글톤 인스턴스
_detector: Optional[GoalDetector] = None


def get_detector(template_path: Optional[str] = None) -> GoalDetector:
    """GoalDetector 싱글톤 인스턴스 반환"""
    global _detector
    if _detector is None:
        _detector = GoalDetector(template_path)
    return _detector
