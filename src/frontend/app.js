/**
 * 테일즈런너 연습 트래커 - 메인 앱 로직
 * 순환 연습 시스템 + 삭제 기능 + 탭별 타이머
 */

// ========================================
// 상태 관리
// ========================================

const AppState = {
    maps: {},
    autoDetectEnabled: true,
    sessionStartTime: null,
    currentTab: 'training',

    // 순환 연습: 현재 포커스된 맵
    focusedMapId: null,

    // 탭별 타이머 (초 단위)
    tabTimers: {
        training: 0,
        fairytale: 0,
        custom: 0
    },

    ws: null,
    timerInterval: null,
    tabTimerInterval: null
};

// ========================================
// WebSocket 연결
// ========================================

function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname || 'localhost'}:8000/ws`;

    try {
        AppState.ws = new WebSocket(wsUrl);
    } catch (e) {
        console.log('[WS] Connection failed, running in offline mode');
        return;
    }

    AppState.ws.onopen = () => {
        console.log('[WS] Connected');
        document.body.classList.add('ws-connected');
        showToast('서버 연결됨', 'success');
    };

    AppState.ws.onclose = () => {
        console.log('[WS] Disconnected');
        document.body.classList.remove('ws-connected');
        setTimeout(connectWebSocket, 3000);
    };

    AppState.ws.onerror = () => { };

    AppState.ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        } catch (e) { }
    };
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'state_update':
            // 서버 상태와 로컬 상태 병합
            if (message.data && message.data.maps) {
                Object.keys(message.data.maps).forEach(mapId => {
                    if (!AppState.maps[mapId]) {
                        AppState.maps[mapId] = message.data.maps[mapId];
                    }
                });
            }
            renderMaps();
            updateStats();
            break;

        case 'goal_detected':
            handleGoalDetected();
            break;
    }
}

// ========================================
// 오프라인 모드 초기화
// ========================================

function initOfflineMode() {
    // 기본 맵 데이터 (카운트 0으로 시작)
    const defaultMaps = {
        // 트레이닝 맵 (7개)
        "training_hurdle_normal": { map_id: "training_hurdle_normal", map_name: "허들 노멀", category: "training", current_count: 0, target_count: 5 },
        "training_block_easy": { map_id: "training_block_easy", map_name: "블럭 이지", category: "training", current_count: 0, target_count: 5 },
        "training_block_hard": { map_id: "training_block_hard", map_name: "블럭 하드", category: "training", current_count: 0, target_count: 5 },
        "training_updown": { map_id: "training_updown", map_name: "업다운", category: "training", current_count: 0, target_count: 5 },
        "training_block_hell": { map_id: "training_block_hell", map_name: "블럭헬", category: "training", current_count: 0, target_count: 5 },
        "training_block_mix1": { map_id: "training_block_mix1", map_name: "블럭믹스1", category: "training", current_count: 0, target_count: 5 },
        "training_block_mix2": { map_id: "training_block_mix2", map_name: "블럭믹스2", category: "training", current_count: 0, target_count: 5 },
        // 동화 맵 (5개)
        "fairytale_sun_moon": { map_id: "fairytale_sun_moon", map_name: "해와 달", category: "fairytale", current_count: 0, target_count: 5 },
        "fairytale_heungbu1": { map_id: "fairytale_heungbu1", map_name: "흥부와 놀부1", category: "fairytale", current_count: 0, target_count: 5 },
        "fairytale_heungbu2": { map_id: "fairytale_heungbu2", map_name: "흥부와 놀부2", category: "fairytale", current_count: 0, target_count: 5 },
        "fairytale_momotaro": { map_id: "fairytale_momotaro", map_name: "복숭아동자", category: "fairytale", current_count: 0, target_count: 5 },
        "fairytale_pinocchio": { map_id: "fairytale_pinocchio", map_name: "피노키오", category: "fairytale", current_count: 0, target_count: 5 },
    };

    AppState.maps = defaultMaps;

    // LocalStorage에서 저장된 상태 복원
    loadFromLocalStorage();

    // 첫 번째 미완료 맵에 포커스
    setInitialFocus();

    renderMaps();
    updateStats();
    updateFocusIndicator();
}

// ========================================
// LocalStorage 저장/복원
// ========================================

function saveToLocalStorage() {
    const data = {
        maps: AppState.maps,
        focusedMapId: AppState.focusedMapId,
        tabTimers: AppState.tabTimers
    };
    localStorage.setItem('tr_tracker_state', JSON.stringify(data));
}

function loadFromLocalStorage() {
    try {
        const saved = localStorage.getItem('tr_tracker_state');
        if (saved) {
            const data = JSON.parse(saved);

            // 저장된 맵 상태 복원
            if (data.maps) {
                Object.keys(data.maps).forEach(mapId => {
                    if (AppState.maps[mapId]) {
                        AppState.maps[mapId].current_count = data.maps[mapId].current_count || 0;
                    } else {
                        // 커스텀 맵 복원
                        AppState.maps[mapId] = data.maps[mapId];
                    }
                });
            }

            AppState.focusedMapId = data.focusedMapId;
            AppState.tabTimers = data.tabTimers || { training: 0, fairytale: 0, custom: 0 };
        }
    } catch (e) {
        console.log('LocalStorage load failed');
    }
}

// ========================================
// 순환 연습 시스템
// ========================================

function setInitialFocus() {
    const maps = getFilteredMaps();
    const incomplete = maps.find(m => m.current_count < m.target_count);

    if (incomplete) {
        AppState.focusedMapId = incomplete.map_id;
    } else if (maps.length > 0) {
        AppState.focusedMapId = maps[0].map_id;
    }
}

function moveToNextMap() {
    const maps = getFilteredMaps();
    if (maps.length === 0) return;

    const currentIndex = maps.findIndex(m => m.map_id === AppState.focusedMapId);

    // 다음 미완료 맵 찾기 (순환)
    for (let i = 1; i <= maps.length; i++) {
        const nextIndex = (currentIndex + i) % maps.length;
        const nextMap = maps[nextIndex];

        if (nextMap.current_count < nextMap.target_count) {
            AppState.focusedMapId = nextMap.map_id;
            updateFocusIndicator();
            renderMaps();
            saveToLocalStorage();
            showToast(`다음 맵: ${nextMap.map_name}`, 'info');
            return;
        }
    }

    // 현재 탭 모든 맵 완료
    showToast('🎉 이 카테고리 모든 맵 완료!', 'success');
}

function focusMap(mapId) {
    AppState.focusedMapId = mapId;
    updateFocusIndicator();
    renderMaps();
    saveToLocalStorage();
}

function updateFocusIndicator() {
    const nameEl = document.getElementById('focusMapName');
    const indicatorEl = document.getElementById('focusIndicator');

    if (AppState.focusedMapId && AppState.maps[AppState.focusedMapId]) {
        const map = AppState.maps[AppState.focusedMapId];
        nameEl.textContent = map.map_name;
        indicatorEl.classList.add('active');
    } else {
        nameEl.textContent = '-';
        indicatorEl.classList.remove('active');
    }
}

// ========================================
// GOAL 감지 처리
// ========================================

function handleGoalDetected() {
    if (!AppState.focusedMapId) {
        showToast('포커스된 맵이 없습니다', 'warning');
        return;
    }

    const map = AppState.maps[AppState.focusedMapId];
    if (!map) return;

    // 카운트 증가
    incrementMapCount(AppState.focusedMapId);

    showToast(`✓ ${map.map_name} 완주!`, 'success');

    // 다음 맵으로 이동
    setTimeout(moveToNextMap, 500);
}

// ========================================
// 맵 렌더링
// ========================================

function getFilteredMaps() {
    return Object.values(AppState.maps).filter(map => map.category === AppState.currentTab);
}

function renderMaps() {
    const grid = document.getElementById('mapGrid');
    if (!grid) return;

    const filteredMaps = getFilteredMaps();

    if (filteredMaps.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-folder-open"></i>
                <span>+ 버튼으로 연습 항목을 추가하세요</span>
            </div>
        `;
        return;
    }

    grid.innerHTML = filteredMaps.map(map => createMapCard(map)).join('');
    attachCardEventListeners();
}

function createMapCard(map) {
    const progress = (map.current_count / map.target_count) * 100;
    const isCompleted = map.current_count >= map.target_count;
    const isFocused = map.map_id === AppState.focusedMapId;
    const categoryClass = map.category === 'fairytale' ? 'fairytale' : '';

    const categoryLabel = {
        'training': '트레이닝',
        'fairytale': '동화',
        'custom': '커스텀'
    }[map.category] || '';

    return `
        <div class="map-card ${categoryClass} ${isFocused ? 'focused' : ''}" 
             data-map-id="${map.map_id}" 
             ${isCompleted ? 'style="border-color: var(--color-success);"' : ''}>
            
            ${isFocused ? '<div class="focus-badge"><i class="fa-solid fa-crosshairs"></i> 현재 연습 중</div>' : ''}
            
            <div class="card-header">
                <span class="map-title">${map.map_name}</span>
                <span class="map-badge ${isCompleted ? 'completed' : ''}">${isCompleted ? 'COMPLETED' : categoryLabel}</span>
            </div>
            
            <div class="progress-container">
                <div class="progress-header">
                    <span>진행도</span>
                    <span>${map.current_count} / ${map.target_count}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${Math.min(progress, 100)}%; ${isCompleted ? 'background: var(--color-success);' : ''}"></div>
                </div>
            </div>

            <div class="card-actions">
                <button class="btn btn-focus" data-action="focus" title="이 맵 연습하기">
                    <i class="fa-solid fa-crosshairs"></i>
                </button>
                <button class="btn btn-primary" data-action="increment" ${isCompleted ? 'disabled style="opacity: 0.5;"' : ''}>
                    <i class="fa-solid ${isCompleted ? 'fa-trophy' : 'fa-check'}"></i> ${isCompleted ? '완료' : '+1'}
                </button>
                <button class="btn btn-secondary" data-action="reset" title="리셋">
                    <i class="fa-solid fa-rotate-left"></i>
                </button>
                <button class="btn btn-delete" data-action="delete" title="삭제">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </div>
    `;
}

function attachCardEventListeners() {
    // 포커스
    document.querySelectorAll('[data-action="focus"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            focusMap(btn.closest('.map-card').dataset.mapId);
        });
    });

    // 완주 +1
    document.querySelectorAll('[data-action="increment"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            incrementMapCount(btn.closest('.map-card').dataset.mapId);
        });
    });

    // 리셋
    document.querySelectorAll('[data-action="reset"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            resetMapCount(btn.closest('.map-card').dataset.mapId);
        });
    });

    // 삭제
    document.querySelectorAll('[data-action="delete"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteMap(btn.closest('.map-card').dataset.mapId);
        });
    });

    // 카드 클릭 = 포커스
    document.querySelectorAll('.map-card').forEach(card => {
        card.addEventListener('click', () => focusMap(card.dataset.mapId));
    });
}

// ========================================
// 맵 조작 함수들
// ========================================

function incrementMapCount(mapId) {
    const map = AppState.maps[mapId];
    if (!map) return;

    AppState.maps[mapId] = { ...map, current_count: map.current_count + 1 };

    saveToLocalStorage();
    renderMaps();
    updateStats();

    // 시각적 피드백
    const card = document.querySelector(`[data-map-id="${mapId}"]`);
    if (card) {
        card.classList.add('pulse');
        setTimeout(() => card.classList.remove('pulse'), 500);
    }
}

function resetMapCount(mapId) {
    if (!confirm('이 맵의 진행도를 초기화할까요?')) return;

    const map = AppState.maps[mapId];
    if (!map) return;

    AppState.maps[mapId] = { ...map, current_count: 0 };

    saveToLocalStorage();
    renderMaps();
    updateStats();
    showToast('초기화됨', 'info');
}

function deleteMap(mapId) {
    const map = AppState.maps[mapId];
    if (!map) return;

    if (!confirm(`"${map.map_name}"을(를) 삭제할까요?`)) return;

    // 맵 삭제
    delete AppState.maps[mapId];

    // 포커스가 삭제된 맵이었으면 재설정
    if (AppState.focusedMapId === mapId) {
        setInitialFocus();
        updateFocusIndicator();
    }

    saveToLocalStorage();
    renderMaps();
    updateStats();
    showToast(`"${map.map_name}" 삭제됨`, 'info');
}

// ========================================
// 맵 추가
// ========================================

function setupAddMapModal() {
    const addBtn = document.getElementById('addMapBtn');
    const modal = document.getElementById('addMapModal');
    const input = document.getElementById('newMapName');
    const categorySelect = document.getElementById('newMapCategory');
    const cancelBtn = document.getElementById('cancelAddMap');
    const confirmBtn = document.getElementById('confirmAddMap');

    addBtn.addEventListener('click', () => {
        modal.classList.add('show');
        input.value = '';
        categorySelect.value = AppState.currentTab; // 현재 탭 기본 선택
        input.focus();
    });

    cancelBtn.addEventListener('click', () => modal.classList.remove('show'));
    confirmBtn.addEventListener('click', addCustomMap);
    input.addEventListener('keypress', (e) => { if (e.key === 'Enter') addCustomMap(); });
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
}

function addCustomMap() {
    const input = document.getElementById('newMapName');
    const categorySelect = document.getElementById('newMapCategory');
    const name = input.value.trim();
    const category = categorySelect.value;

    if (!name) {
        showToast('이름을 입력하세요', 'warning');
        return;
    }

    const mapId = `${category}_custom_${Date.now()}`;

    AppState.maps[mapId] = {
        map_id: mapId,
        map_name: name,
        category: category,
        current_count: 0,
        target_count: 5
    };

    saveToLocalStorage();

    // 해당 탭으로 이동
    if (AppState.currentTab !== category) {
        AppState.currentTab = category;
        document.querySelectorAll('.tab-btn').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === category);
        });
    }

    renderMaps();
    updateStats();

    document.getElementById('addMapModal').classList.remove('show');
    showToast(`"${name}" 추가됨`, 'success');
}

// ========================================
// 탭 전환
// ========================================

function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            AppState.currentTab = tab.dataset.tab;

            setInitialFocus();
            updateFocusIndicator();
            renderMaps();
        });
    });
}

// ========================================
// 통계 업데이트
// ========================================

function updateStats() {
    const maps = Object.values(AppState.maps);
    const totalGoal = maps.reduce((sum, m) => sum + m.target_count, 0);
    const totalCompleted = maps.reduce((sum, m) => sum + Math.min(m.current_count, m.target_count), 0);

    const statsEl = document.getElementById('completionStats');
    if (statsEl) {
        statsEl.textContent = `${totalCompleted} / ${totalGoal}`;
    }
}

// ========================================
// 타이머
// ========================================

function startSessionTimer() {
    AppState.sessionStartTime = new Date();

    // 세션 타이머
    AppState.timerInterval = setInterval(() => {
        const elapsed = Math.floor((new Date() - AppState.sessionStartTime) / 1000);

        const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');

        document.getElementById('sessionTimer').textContent = `${h}:${m}:${s}`;
    }, 1000);

    // 탭별 타이머 (현재 탭만 증가)
    AppState.tabTimerInterval = setInterval(() => {
        AppState.tabTimers[AppState.currentTab]++;
        updateTabTimers();

        // 10초마다 저장
        if (AppState.tabTimers[AppState.currentTab] % 10 === 0) {
            saveToLocalStorage();
        }
    }, 1000);
}

function updateTabTimers() {
    ['training', 'fairytale', 'custom'].forEach(tab => {
        const seconds = AppState.tabTimers[tab] || 0;
        const m = String(Math.floor(seconds / 60)).padStart(2, '0');
        const s = String(seconds % 60).padStart(2, '0');

        const el = document.getElementById(`${tab}Timer`);
        if (el) {
            el.innerHTML = `<i class="fa-solid fa-stopwatch"></i> ${m}:${s}`;
        }
    });
}

// ========================================
// 토스트 알림
// ========================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ========================================
// 토글 설정
// ========================================

function setupAutoDetectToggle() {
    document.getElementById('autoDetectToggle').addEventListener('click', () => {
        AppState.autoDetectEnabled = !AppState.autoDetectEnabled;
        document.getElementById('autoDetectToggle').classList.toggle('active', AppState.autoDetectEnabled);
        showToast(AppState.autoDetectEnabled ? 'GOAL 자동 감지 ON' : 'GOAL 자동 감지 OFF', 'info');
    });
}

// ========================================
// 초기화
// ========================================

function initApp() {
    initOfflineMode();
    connectWebSocket();
    setupTabs();
    setupAddMapModal();
    setupAutoDetectToggle();
    startSessionTimer();
    updateTabTimers();
    updateFocusIndicator();
}

document.addEventListener('DOMContentLoaded', initApp);
