# 🏃 테일즈런너 연습 트래커

혼자달리기 맵 연습을 체계적으로 관리하는 트래커

## 🚀 사용 방법

### 방법 1: 웹만 사용 (수동 모드)
👉 https://talesrunner-practice.vercel.app/

- 인터넷만 있으면 어디서든 사용 가능
- 완주 버튼을 직접 클릭해서 카운트

---

### 방법 2: GOAL 자동 감지 (로컬 실행)

#### 준비물
1. **Python 설치** (없으면 아래 참고)
2. 이 폴더 전체

#### 실행 방법
1. `실행.bat` 더블클릭
2. 브라우저에서 http://localhost:8000 열기
3. 테일즈런너 실행 후 연습 시작
4. GOAL 화면이 뜨면 자동으로 카운트!

---

## 🐍 Python 설치 (처음 한 번만)

1. https://www.python.org/downloads/ 접속
2. **Download Python** 버튼 클릭
3. 설치 실행
4. ⚠️ **"Add Python to PATH" 반드시 체크!**
5. Install Now 클릭
6. 완료!

---

## ✨ 기능

- **순환 연습**: GOAL 감지 → 자동으로 다음 맵으로 이동
- **탭별 관리**: 트레이닝 / 동화 / 기술연습 분리
- **타이머**: 전체 시간 + 탭별 시간 측정
- **자동 저장**: 브라우저 닫아도 진행 상태 유지

---

## 📁 파일 구조

```
├── 실행.bat          ← 더블클릭해서 실행!
├── frontend/         ← 웹 화면
└── backend/          ← GOAL 감지 프로그램
    └── assets/
        └── goal_template.png  ← GOAL 인식용 이미지
```

---

## ❓ 문제 해결

**Q: 실행이 안 돼요**
→ Python이 설치되어 있나요? "Add Python to PATH" 체크했나요?

**Q: GOAL 감지가 안 돼요**
→ 테일즈런너가 화면에 보여야 합니다 (최소화 X)

**Q: 웹만 쓰고 싶어요**
→ https://talesrunner-practice.vercel.app/ 접속 (GOAL 자동 감지 불가)
