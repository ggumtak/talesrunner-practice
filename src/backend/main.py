"""
FastAPI 메인 서버
WebSocket을 통해 GOAL 감지 이벤트를 프론트엔드로 전송
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from goal_detector import get_detector, DetectionResult
from screen_capture import cleanup as cleanup_screen_capture


# ========================================
# 데이터 모델 정의
# ========================================

class MapProgress(BaseModel):
    """맵 진행 상태"""
    map_id: str
    map_name: str
    category: str  # "training" | "fairytale" | "custom"
    current_count: int = 0
    target_count: int = 5
    total_time_seconds: int = 0


class AppState(BaseModel):
    """앱 전체 상태"""
    maps: dict[str, MapProgress] = {}
    auto_detect_enabled: bool = True
    session_start_time: str = ""
    total_session_seconds: int = 0


# ========================================
# 전역 상태 관리
# ========================================

# 초기 맵 데이터
INITIAL_MAPS = {
    # 트레이닝 맵
    "training_hurdle_normal": MapProgress(map_id="training_hurdle_normal", map_name="허들 노멀", category="training"),
    "training_block_easy": MapProgress(map_id="training_block_easy", map_name="블럭 이지", category="training"),
    "training_block_hard": MapProgress(map_id="training_block_hard", map_name="블럭 하드", category="training"),
    "training_updown": MapProgress(map_id="training_updown", map_name="업다운", category="training"),
    "training_block_hell": MapProgress(map_id="training_block_hell", map_name="블럭헬", category="training"),
    "training_block_mix1": MapProgress(map_id="training_block_mix1", map_name="블럭믹스1", category="training"),
    "training_block_mix2": MapProgress(map_id="training_block_mix2", map_name="블럭믹스2", category="training"),
    # 동화 맵
    "fairytale_sun_moon": MapProgress(map_id="fairytale_sun_moon", map_name="해와 달", category="fairytale"),
    "fairytale_heungbu1": MapProgress(map_id="fairytale_heungbu1", map_name="흥부와 놀부1", category="fairytale"),
    "fairytale_heungbu2": MapProgress(map_id="fairytale_heungbu2", map_name="흥부와 놀부2", category="fairytale"),
    "fairytale_momotaro": MapProgress(map_id="fairytale_momotaro", map_name="복숭아동자", category="fairytale"),
    "fairytale_pinocchio": MapProgress(map_id="fairytale_pinocchio", map_name="피노키오", category="fairytale"),
}

# 앱 상태
app_state = AppState(
    maps=INITIAL_MAPS.copy(),
    session_start_time=datetime.now().isoformat()
)

# WebSocket 연결 관리
connected_clients: Set[WebSocket] = set()

# GOAL 감지 태스크 핸들
detection_task: asyncio.Task = None


# ========================================
# WebSocket 브로드캐스트
# ========================================

async def broadcast_message(message: dict) -> None:
    """모든 연결된 클라이언트에게 메시지 전송"""
    if not connected_clients:
        return
    
    message_json = json.dumps(message, ensure_ascii=False)
    disconnected = set()
    
    for client in connected_clients:
        try:
            await client.send_text(message_json)
        except Exception:
            disconnected.add(client)
    
    # 연결 끊긴 클라이언트 제거
    connected_clients.difference_update(disconnected)


async def broadcast_state_update() -> None:
    """현재 앱 상태를 모든 클라이언트에게 브로드캐스트"""
    await broadcast_message({
        "type": "state_update",
        "data": app_state.model_dump()
    })


async def broadcast_goal_detected(map_id: str = None) -> None:
    """GOAL 감지 이벤트 브로드캐스트"""
    await broadcast_message({
        "type": "goal_detected",
        "data": {
            "map_id": map_id,
            "timestamp": datetime.now().isoformat()
        }
    })


# ========================================
# GOAL 감지 백그라운드 태스크
# ========================================

async def goal_detection_loop() -> None:
    """0.5초마다 화면을 캡처하여 GOAL 감지"""
    # 템플릿 경로 설정
    template_path = Path(__file__).parent / "assets" / "goal_template.png"
    detector = get_detector(str(template_path) if template_path.exists() else None)
    
    while True:
        try:
            # 자동 감지가 활성화된 경우에만 실행
            if app_state.auto_detect_enabled:
                # 동기 함수를 비동기로 실행
                result = await asyncio.get_event_loop().run_in_executor(
                    None, detector.check_for_goal
                )
                
                if result and result.detected:
                    print(f"[GOAL DETECTED] Confidence: {result.confidence:.2f}")
                    await broadcast_goal_detected()
            
            await asyncio.sleep(0.5)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[ERROR] Detection loop error: {e}")
            await asyncio.sleep(1.0)


# ========================================
# 앱 라이프사이클
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스 관리"""
    global detection_task
    
    # 시작 시: GOAL 감지 루프 시작
    detection_task = asyncio.create_task(goal_detection_loop())
    print("[INFO] GOAL detection loop started")
    
    yield
    
    # 종료 시: 정리
    if detection_task:
        detection_task.cancel()
        try:
            await detection_task
        except asyncio.CancelledError:
            pass
    
    cleanup_screen_capture()
    print("[INFO] Cleanup completed")


# ========================================
# FastAPI 앱 설정
# ========================================

app = FastAPI(
    title="TalesRunner Practice Tracker",
    description="테일즈런너 연습 트래커 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (로컬 개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (Frontend)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ========================================
# REST API 엔드포인트
# ========================================

@app.get("/")
async def root():
    """프론트엔드 페이지 반환"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "TalesRunner Practice Tracker API"}


@app.get("/api/state")
async def get_state():
    """현재 앱 상태 조회"""
    return app_state.model_dump()


@app.post("/api/maps/{map_id}/increment")
async def increment_count(map_id: str):
    """맵 완주 카운트 +1"""
    if map_id not in app_state.maps:
        return {"error": "Map not found"}, 404
    
    current_map = app_state.maps[map_id]
    updated_map = MapProgress(
        **{
            **current_map.model_dump(),
            "current_count": current_map.current_count + 1
        }
    )
    app_state.maps[map_id] = updated_map
    
    await broadcast_state_update()
    return {"success": True, "new_count": updated_map.current_count}


@app.post("/api/maps/{map_id}/reset")
async def reset_count(map_id: str):
    """맵 완주 카운트 리셋"""
    if map_id not in app_state.maps:
        return {"error": "Map not found"}, 404
    
    current_map = app_state.maps[map_id]
    updated_map = MapProgress(
        **{
            **current_map.model_dump(),
            "current_count": 0,
            "total_time_seconds": 0
        }
    )
    app_state.maps[map_id] = updated_map
    
    await broadcast_state_update()
    return {"success": True}


@app.post("/api/auto-detect/toggle")
async def toggle_auto_detect():
    """자동 GOAL 감지 토글"""
    app_state.auto_detect_enabled = not app_state.auto_detect_enabled
    await broadcast_state_update()
    return {"auto_detect_enabled": app_state.auto_detect_enabled}


@app.post("/api/maps/add")
async def add_custom_map(map_name: str, category: str = "custom"):
    """커스텀 맵 추가"""
    map_id = f"custom_{map_name.replace(' ', '_').lower()}"
    
    if map_id in app_state.maps:
        return {"error": "Map already exists"}, 400
    
    new_map = MapProgress(
        map_id=map_id,
        map_name=map_name,
        category=category
    )
    app_state.maps[map_id] = new_map
    
    await broadcast_state_update()
    return {"success": True, "map_id": map_id}


# ========================================
# WebSocket 엔드포인트
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결 처리"""
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"[WS] Client connected. Total: {len(connected_clients)}")
    
    try:
        # 연결 시 현재 상태 전송
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "data": app_state.model_dump()
        }, ensure_ascii=False))
        
        # 클라이언트 메시지 수신 대기
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입별 처리
            if message.get("type") == "increment":
                map_id = message.get("map_id")
                if map_id and map_id in app_state.maps:
                    await increment_count(map_id)
                    
            elif message.get("type") == "reset":
                map_id = message.get("map_id")
                if map_id and map_id in app_state.maps:
                    await reset_count(map_id)
                    
            elif message.get("type") == "toggle_auto_detect":
                await toggle_auto_detect()
                
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected. Total: {len(connected_clients)}")
    except Exception as e:
        print(f"[WS ERROR] {e}")
        connected_clients.discard(websocket)


# ========================================
# 엔트리포인트
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
