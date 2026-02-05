# 🏃 TalesRunner Practice Tracker

테일즈런너 혼자달리기 연습 트래커

## ✨ 기능

- **순환 연습 시스템**: GOAL 감지 시 자동으로 다음 맵으로 이동
- **맵 관리**: 추가/삭제/리셋
- **탭별 타이머**: 트레이닝/동화/기술연습 각각 시간 측정
- **상태 저장**: LocalStorage에 자동 저장

## 🚀 사용법

### 웹 버전 (수동 모드)
[https://tr-tracker.vercel.app](배포 후 URL)에서 바로 사용

### 로컬 + GOAL 자동 감지
```bash
cd backend
pip install -r requirements.txt
python main.py
```
http://localhost:8000 접속

## 📁 구조

```
├── frontend/       # 웹 UI
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── backend/        # GOAL 자동 감지 (로컬 전용)
    ├── main.py
    ├── screen_capture.py
    └── goal_detector.py
```

## 맵 목록

| 카테고리 | 맵 |
|----------|-----|
| 트레이닝 | 허들 노멀, 블럭 이지/하드/헬/믹스1/믹스2, 업다운 |
| 동화 | 해와 달, 흥부와 놀부1/2, 복숭아동자, 피노키오 |
