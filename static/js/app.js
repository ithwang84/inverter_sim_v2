// 전역 변수
let updateInterval = null;
let chartInterval = null;
const UPDATE_INTERVAL_MS = 1000; // 1초마다 업데이트
const CHART_UPDATE_INTERVAL_MS = 2000; // 2초마다 그래프 업데이트

// Chart.js 인스턴스
let powerChart = null;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    initializeEventListeners();
    startAutoUpdate();
    startChartUpdate();
    startModbusUpdate();
    loadInitialData();
});

// 차트 초기화
function initializeChart() {
    const ctx = document.getElementById('powerChart').getContext('2d');
    powerChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '발전량 (kW)',
                data: [],
                borderColor: 'rgb(102, 126, 234)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '시간'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: '발전량 (kW)'
                    },
                    beginAtZero: true
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// 이벤트 리스너 초기화
function initializeEventListeners() {
    // 전체 제어
    document.getElementById('btn-all-on').addEventListener('click', () => controlAllInverters('on'));
    document.getElementById('btn-all-off').addEventListener('click', () => controlAllInverters('off'));
    document.getElementById('btn-set-mode-all').addEventListener('click', setControlModeAll);
    document.getElementById('btn-set-p-control-all').addEventListener('click', setPControlAll);
    document.getElementById('btn-set-irradiance').addEventListener('click', setIrradiance);
    document.getElementById('btn-set-temperature').addEventListener('click', setTemperature);
}

// 초기 데이터 로드
async function loadInitialData() {
    await updateStatus();
}

// 자동 업데이트 시작
function startAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    updateInterval = setInterval(updateStatus, UPDATE_INTERVAL_MS);
}

// 차트 자동 업데이트 시작
function startChartUpdate() {
    if (chartInterval) {
        clearInterval(chartInterval);
    }
    chartInterval = setInterval(() => {
        updateChart();
        updateHourlyData(); // 시간별 데이터도 함께 업데이트
    }, CHART_UPDATE_INTERVAL_MS);
    updateChart(); // 즉시 한 번 실행
    updateHourlyData(); // 시간별 데이터도 즉시 실행
}

// 상태 업데이트
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('상태 업데이트 오류:', error);
    }
}

// UI 업데이트
function updateUI(data) {
    // 발전소 정보
    document.getElementById('plant-id').textContent = `발전소: ${data.plant_id}`;
    document.getElementById('update-time').textContent = `업데이트: ${new Date().toLocaleTimeString()}`;
    
    // 전체 요약
    const totalPower = data.total_power;
    document.getElementById('total-power').textContent = totalPower.total_active_power_kw.toFixed(2);
    document.getElementById('utilization').textContent = totalPower.utilization_percent.toFixed(2);
    document.getElementById('reactive-power').textContent = totalPower.total_reactive_power_kvar.toFixed(2);
    document.getElementById('rated-capacity').textContent = data.total_capacity_mva.toFixed(2);
    
    // 인버터 카드 업데이트
    updateInverterCards(data.inverters, data.pv_generators);
}

// 인버터 카드 업데이트
function updateInverterCards(inverters, pvGenerators) {
    const grid = document.getElementById('inverters-grid');
    
    // 기존 카드 제거
    grid.innerHTML = '';
    
    inverters.forEach((inverter, index) => {
        const pvGen = pvGenerators[index];
        const card = createInverterCard(inverter, pvGen, index);
        grid.appendChild(card);
    });
}

// 인버터 카드 생성
function createInverterCard(inverter, pvGen, index) {
    const card = document.createElement('div');
    card.className = `inverter-card ${inverter.is_on ? 'on' : 'off'}`;
    
    const monitoring = inverter.monitoring;
    const pvMonitoring = pvGen.monitoring;
    
    card.innerHTML = `
        <div class="inverter-header">
            <div class="inverter-title">${inverter.id}</div>
            <span class="status-badge ${inverter.is_on ? 'on' : 'off'}">
                ${inverter.is_on ? 'ON' : 'OFF'}
            </span>
        </div>
        
        <div class="monitoring-grid">
            <div class="monitoring-item">
                <div class="monitoring-label">PV 발전량</div>
                <div class="monitoring-value">${pvMonitoring.power_generation.toFixed(2)} kW</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">PV 전압</div>
                <div class="monitoring-value">${pvMonitoring.voltage.toFixed(1)} V</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">PV 전류</div>
                <div class="monitoring-value">${pvMonitoring.current.toFixed(2)} A</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">출력 전력</div>
                <div class="monitoring-value">${monitoring.active_power.toFixed(2)} kW</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">출력 전압</div>
                <div class="monitoring-value">${monitoring.output_voltage.toFixed(1)} V</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">출력 전류</div>
                <div class="monitoring-value">${monitoring.output_current.toFixed(2)} A</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">역률</div>
                <div class="monitoring-value">${monitoring.power_factor.toFixed(3)}</div>
            </div>
            <div class="monitoring-item">
                <div class="monitoring-label">효율</div>
                <div class="monitoring-value">${monitoring.efficiency.toFixed(1)}%</div>
            </div>
        </div>
        
        <div class="inverter-controls">
            <div class="inverter-control-row">
                <label>전원:</label>
                <button class="btn btn-success btn-sm" onclick="controlInverter(${index}, 'on')">ON</button>
                <button class="btn btn-danger btn-sm" onclick="controlInverter(${index}, 'off')">OFF</button>
            </div>
            <div class="inverter-control-row">
                <label>제어 모드:</label>
                <select id="control-mode-${index}" class="select-control">
                    <option value="MPPT" ${pvGen.control_mode === 'MPPT' ? 'selected' : ''}>MPPT</option>
                    <option value="P_CONTROL" ${pvGen.control_mode === 'P_CONTROL' ? 'selected' : ''}>P 제어</option>
                </select>
                <button class="btn btn-primary btn-sm" onclick="setControlMode(${index})">적용</button>
            </div>
            <div class="inverter-control-row">
                <label>P 제어 (%):</label>
                <input type="number" id="p-control-${index}" class="input-control" 
                       min="0" max="100" value="${pvGen.p_control_percent}" step="1">
                <button class="btn btn-primary btn-sm" onclick="setPControl(${index})">적용</button>
            </div>
        </div>
    `;
    
    return card;
}

// 인버터 제어
async function controlInverter(index, action) {
    try {
        const endpoint = action === 'on' ? 'on' : 'off';
        const response = await fetch(`/api/inverter/${index}/${endpoint}`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('제어 오류: ' + error.message, 'error');
    }
}

// 전체 인버터 제어
async function controlAllInverters(action) {
    try {
        const endpoint = action === 'on' ? 'all/on' : 'all/off';
        const response = await fetch(`/api/inverter/${endpoint}`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('제어 오류: ' + error.message, 'error');
    }
}

// 제어 모드 설정 (개별)
async function setControlMode(index) {
    try {
        const mode = document.getElementById(`control-mode-${index}`).value;
        const response = await fetch(`/api/inverter/${index}/control-mode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode: mode })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('제어 모드 설정 오류: ' + error.message, 'error');
    }
}

// 제어 모드 설정 (전체)
async function setControlModeAll() {
    try {
        const mode = document.getElementById('control-mode-all').value;
        const response = await fetch('/api/inverter/all/control-mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode: mode })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('제어 모드 설정 오류: ' + error.message, 'error');
    }
}

// P 제어 설정 (개별)
async function setPControl(index) {
    try {
        const percent = parseFloat(document.getElementById(`p-control-${index}`).value);
        const response = await fetch(`/api/inverter/${index}/p-control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ percent: percent })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('P 제어 설정 오류: ' + error.message, 'error');
    }
}

// P 제어 설정 (전체)
async function setPControlAll() {
    try {
        const percent = parseFloat(document.getElementById('p-control-all').value);
        const response = await fetch('/api/inverter/all/p-control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ percent: percent })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('P 제어 설정 오류: ' + error.message, 'error');
    }
}

// 일사량 설정
async function setIrradiance() {
    try {
        const irradiance = parseFloat(document.getElementById('irradiance').value);
        const response = await fetch('/api/environment/irradiance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ irradiance: irradiance })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('일사량 설정 오류: ' + error.message, 'error');
    }
}

// 온도 설정
async function setTemperature() {
    try {
        const temperature = parseFloat(document.getElementById('temperature').value);
        const response = await fetch('/api/environment/temperature', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ temperature: temperature })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('온도 설정 오류: ' + error.message, 'error');
    }
}

// 차트 업데이트
async function updateChart() {
    try {
        const response = await fetch('/api/timeseries');
        const result = await response.json();
        
        if (result.data && result.data.length > 0) {
            const labels = result.data.map(item => {
                const date = new Date(item.timestamp * 1000);
                return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            });
            const data = result.data.map(item => item.power_kw);
            
            powerChart.data.labels = labels;
            powerChart.data.datasets[0].data = data;
            powerChart.update('none'); // 애니메이션 없이 업데이트
        }
    } catch (error) {
        console.error('차트 업데이트 오류:', error);
    }
}

// 시간별 누적 발전량 업데이트
async function updateHourlyData() {
    try {
        const response = await fetch('/api/hourly');
        const result = await response.json();
        
        const hourlyList = document.getElementById('hourly-list');
        hourlyList.innerHTML = '';
        
        if (result.hourly_data && result.hourly_data.length > 0) {
            // 최근 24시간만 표시 (또는 모든 데이터)
            const recentData = result.hourly_data.slice(-24);
            
            recentData.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'hourly-item';
                itemDiv.innerHTML = `
                    <div class="hourly-item-label">${item.hour}</div>
                    <div class="hourly-item-value">${item.accumulated_kwh.toFixed(2)}</div>
                    <div class="hourly-item-unit">kWh</div>
                `;
                hourlyList.appendChild(itemDiv);
            });
        } else {
            hourlyList.innerHTML = '<div style="text-align: center; color: #666; padding: 20px;">데이터가 없습니다.</div>';
        }
    } catch (error) {
        console.error('시간별 데이터 업데이트 오류:', error);
    }
}

// Modbus 통신 상태 업데이트
async function updateModbusStatus() {
    try {
        const response = await fetch('/api/modbus/status');
        const data = await response.json();
        
        const statusIndicator = document.getElementById('modbus-status');
        const portElement = document.getElementById('modbus-port');
        const baudrateElement = document.getElementById('modbus-baudrate');
        const slavesElement = document.getElementById('modbus-slaves');
        
        if (data.available) {
            const status = data.status;
            portElement.textContent = status.port || '-';
            baudrateElement.textContent = status.baudrate || '-';
            slavesElement.textContent = status.num_slaves || 0;
            
            // 포트 연결 상태 확인
            if (!data.actually_connected) {
                if (!data.port_available) {
                    statusIndicator.textContent = '포트 없음';
                    statusIndicator.className = 'status-indicator error';
                    statusIndicator.title = data.port_error || '시리얼 포트가 연결되어 있지 않습니다.';
                    showModbusAlert(`포트 연결 실패: ${data.port_error || '시리얼 포트를 찾을 수 없습니다.'}`);
                } else if (!data.server_running) {
                    statusIndicator.textContent = '서버 중지';
                    statusIndicator.className = 'status-indicator stopped';
                    statusIndicator.title = 'Modbus 서버가 실행되지 않았습니다.';
                    showModbusAlert('Modbus RTU 서버가 실행되지 않았습니다.');
                } else {
                    statusIndicator.textContent = '연결 안됨';
                    statusIndicator.className = 'status-indicator error';
                    statusIndicator.title = data.warning || 'RTU와 통신할 수 없습니다.';
                    showModbusAlert(data.warning || 'RTU와 통신할 수 없습니다.');
                }
            } else if (status.is_running && data.port_available) {
                statusIndicator.textContent = '실행 중';
                statusIndicator.className = 'status-indicator running';
                hideModbusAlert();
            } else {
                statusIndicator.textContent = '중지됨';
                statusIndicator.className = 'status-indicator stopped';
                hideModbusAlert();
            }
            
            // 슬레이브별 통계 업데이트
            updateSlaveStats(status.communication_stats || {});
        } else {
            // Modbus Manager 초기화 실패
            portElement.textContent = '-';
            baudrateElement.textContent = '-';
            slavesElement.textContent = '0';
            statusIndicator.textContent = '초기화 실패';
            statusIndicator.className = 'status-indicator error';
            statusIndicator.title = data.error_detail || data.message;
            
            // 알람 표시
            showModbusAlert(data.error_detail || data.message || 'Modbus RTU Manager 초기화 실패');
        }
    } catch (error) {
        console.error('Modbus 상태 업데이트 오류:', error);
        showModbusAlert('Modbus 상태 조회 중 오류가 발생했습니다.');
    }
}

// Modbus 알람 표시
let modbusAlertElement = null;
function showModbusAlert(message) {
    // 기존 알람이 있으면 제거
    if (modbusAlertElement) {
        modbusAlertElement.remove();
    }
    
    // 알람 요소 생성
    modbusAlertElement = document.createElement('div');
    modbusAlertElement.className = 'modbus-alert';
    modbusAlertElement.innerHTML = `
        <div class="alert-icon">⚠️</div>
        <div class="alert-message">${message}</div>
        <button class="alert-close" onclick="hideModbusAlert()">×</button>
    `;
    
    // Modbus 섹션에 추가
    const modbusSection = document.querySelector('.modbus-section');
    if (modbusSection) {
        modbusSection.insertBefore(modbusAlertElement, modbusSection.firstChild);
    }
}

// Modbus 알람 숨기기
function hideModbusAlert() {
    if (modbusAlertElement) {
        modbusAlertElement.remove();
        modbusAlertElement = null;
    }
}

// 슬레이브별 통계 업데이트
function updateSlaveStats(stats) {
    const grid = document.getElementById('modbus-slaves-grid');
    grid.innerHTML = '';
    
    for (const [slaveId, stat] of Object.entries(stats)) {
        const card = document.createElement('div');
        card.className = 'slave-stat-card';
        card.innerHTML = `
            <div class="slave-stat-title">슬레이브 ID ${slaveId}</div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">총 요청:</span>
                <span class="slave-stat-value">${stat.total_requests || 0}</span>
            </div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">총 응답:</span>
                <span class="slave-stat-value">${stat.total_responses || 0}</span>
            </div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">읽기 요청:</span>
                <span class="slave-stat-value">${stat.read_requests || 0}</span>
            </div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">쓰기 요청:</span>
                <span class="slave-stat-value">${stat.write_requests || 0}</span>
            </div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">오류:</span>
                <span class="slave-stat-value">${stat.error_count || 0}</span>
            </div>
            <div class="slave-stat-item">
                <span class="slave-stat-label">마지막 요청:</span>
                <span class="slave-stat-value">${stat.last_request_time ? new Date(stat.last_request_time).toLocaleTimeString() : '-'}</span>
            </div>
        `;
        grid.appendChild(card);
    }
}

// Modbus 통신 로그 업데이트
async function updateModbusLog() {
    try {
        const response = await fetch('/api/modbus/log?limit=20');
        const data = await response.json();
        
        const logContainer = document.getElementById('modbus-log');
        logContainer.innerHTML = '';
        
        if (data.logs && data.logs.length > 0) {
            data.logs.reverse().forEach(log => {
                const entry = document.createElement('div');
                entry.className = `log-entry ${log.event_type}`;
                
                const functionName = log.function_name || `Function ${log.function_code}`;
                const time = new Date(log.timestamp).toLocaleTimeString();
                
                let detail = '';
                if (log.address !== null && log.address !== undefined) {
                    detail += `주소: ${log.address}`;
                }
                if (log.quantity) {
                    detail += `, 수량: ${log.quantity}`;
                }
                if (log.values && log.values.length > 0) {
                    detail += `, 값: [${log.values.join(', ')}]`;
                }
                if (log.error) {
                    detail += `, 오류: ${log.error}`;
                }
                
                entry.innerHTML = `
                    <div class="log-time">${time}</div>
                    <div class="log-content">
                        [${log.event_type.toUpperCase()}] 슬레이브 ${log.slave_id} - ${functionName}
                        ${log.success ? '✓' : '✗'}
                    </div>
                    ${detail ? `<div class="log-detail">${detail}</div>` : ''}
                `;
                logContainer.appendChild(entry);
            });
        } else {
            logContainer.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px;">통신 로그가 없습니다.</div>';
        }
    } catch (error) {
        console.error('Modbus 로그 업데이트 오류:', error);
    }
}

// Modbus 자동 업데이트 시작
function startModbusUpdate() {
    updateModbusStatus();
    updateModbusLog();
    
    // 2초마다 업데이트
    setInterval(() => {
        updateModbusStatus();
        updateModbusLog();
    }, 2000);
}

// 로그 지우기
document.addEventListener('DOMContentLoaded', function() {
    const btnClearLog = document.getElementById('btn-clear-log');
    if (btnClearLog) {
        btnClearLog.addEventListener('click', () => {
            const logContainer = document.getElementById('modbus-log');
            logContainer.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px;">로그가 지워졌습니다.</div>';
        });
    }
});

// 메시지 표시 (간단한 알림)
function showMessage(message, type) {
    // 간단한 alert로 구현 (나중에 더 나은 UI로 개선 가능)
    console.log(`[${type.toUpperCase()}] ${message}`);
    // 실제로는 토스트 메시지나 모달을 사용하는 것이 좋습니다
}

