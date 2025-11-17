"""
태양광 인버터 시뮬레이터 웹 서버
Flask 기반 모니터링 및 제어 인터페이스
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
from power_plant import PowerPlant
from solar_pv_generator import ControlMode
from config import SYSTEM_CONFIG
from modbus_rtu_manager import ModbusRTUManager

app = Flask(__name__)
CORS(app)

# 전역 발전소 인스턴스
plant = PowerPlant(
    plant_id=SYSTEM_CONFIG["plant_id"],
    total_capacity_mva=SYSTEM_CONFIG["total_capacity_mva"]
)

# Modbus RTU Manager (선택적 - 시리얼 포트가 없을 수 있음)
modbus_manager = None
modbus_error_message = None
try:
    modbus_manager = ModbusRTUManager(
        power_plant=plant,
        port=SYSTEM_CONFIG["modbus"].get("port", "COM1"),
        baudrate=SYSTEM_CONFIG["modbus"]["baudrate"],
        parity=SYSTEM_CONFIG["modbus"]["parity"],
        stopbits=SYSTEM_CONFIG["modbus"]["stopbits"],
        bytesize=SYSTEM_CONFIG["modbus"]["bytesize"],
        base_slave_id=SYSTEM_CONFIG["modbus"]["slave_id"]
    )
    # Modbus 서버는 인버터 ON 시 자동으로 시작됨
except Exception as e:
    modbus_error_message = str(e)
    print(f"Modbus RTU Manager 초기화 오류: {e}")
    print("Modbus 통신 기능은 사용할 수 없습니다.")
    print("→ 시리얼 포트(RS-485)가 연결되어 있지 않거나 사용 중일 수 있습니다.")

# 시뮬레이션 업데이트 스레드
update_thread = None
update_running = False

# 시계열 데이터 저장
time_series_data = []  # [(timestamp, power_kw), ...]
hourly_accumulated = defaultdict(float)  # {hour: accumulated_power}
MAX_DATA_POINTS = 3600  # 최대 1시간치 데이터 (1초 간격)


def update_loop():
    """발전소 상태 업데이트 루프"""
    global update_running, time_series_data, hourly_accumulated
    last_second = None
    
    while update_running:
        plant.update()
        
        # Modbus 레지스터 업데이트
        if modbus_manager:
            modbus_manager.update_all_registers()
        
        # 1초마다 시계열 데이터 저장
        current_time = datetime.now()
        current_second = current_time.replace(microsecond=0)
        
        if last_second != current_second:
            total_power = plant.get_total_power()
            power_kw = total_power['total_active_power_kw']
            
            # 시계열 데이터 추가
            timestamp = current_second.timestamp()
            time_series_data.append((timestamp, power_kw))
            
            # 최대 데이터 포인트 수 제한
            if len(time_series_data) > MAX_DATA_POINTS:
                time_series_data.pop(0)
            
            # 시간별 누적 발전량 계산
            hour_key = current_second.replace(minute=0, second=0)
            # 1초당 발전량을 누적 (kW * 1초 = kWh/3600)
            hourly_accumulated[hour_key] += power_kw / 3600.0  # kWh
            
            last_second = current_second
        
        time.sleep(0.1)  # 100ms 간격


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """전체 발전소 상태 조회"""
    plant.update()
    status = plant.get_all_status()
    return jsonify(status)


@app.route('/api/timeseries', methods=['GET'])
def get_timeseries():
    """시계열 발전량 데이터 조회"""
    global time_series_data
    # 최근 데이터만 반환 (최대 1시간치)
    recent_data = time_series_data[-MAX_DATA_POINTS:] if len(time_series_data) > MAX_DATA_POINTS else time_series_data
    
    return jsonify({
        "data": [
            {"timestamp": ts, "power_kw": power}
            for ts, power in recent_data
        ]
    })


@app.route('/api/hourly', methods=['GET'])
def get_hourly():
    """시간별 누적 발전량 조회"""
    global hourly_accumulated
    
    # 시간별 데이터를 정렬하여 반환
    hourly_list = []
    for hour_key in sorted(hourly_accumulated.keys()):
        hour_str = hour_key.strftime("%Y-%m-%d %H:%M")
        hour_range = f"{hour_key.hour:02d}시~{hour_key.hour+1:02d}시"
        hourly_list.append({
            "hour": hour_range,
            "datetime": hour_str,
            "accumulated_kwh": round(hourly_accumulated[hour_key], 3)
        })
    
    return jsonify({
        "hourly_data": hourly_list
    })


@app.route('/api/inverter/<int:inverter_index>/on', methods=['POST'])
def turn_on_inverter(inverter_index):
    """인버터 ON"""
    try:
        plant.turn_on_inverter(inverter_index)
        return jsonify({"success": True, "message": f"인버터 {inverter_index + 1} ON"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/<int:inverter_index>/off', methods=['POST'])
def turn_off_inverter(inverter_index):
    """인버터 OFF"""
    try:
        plant.turn_off_inverter(inverter_index)
        return jsonify({"success": True, "message": f"인버터 {inverter_index + 1} OFF"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/all/on', methods=['POST'])
def turn_on_all():
    """모든 인버터 ON"""
    try:
        plant.turn_on_all()
        
        # Modbus RTU 서버 자동 시작 (인버터 ON 시)
        if modbus_manager and not modbus_manager.is_running:
            try:
                modbus_manager.start_all()
                print("Modbus RTU 서버 자동 시작 완료")
            except Exception as e:
                print(f"Modbus RTU 서버 시작 오류: {e}")
        
        return jsonify({"success": True, "message": "모든 인버터 ON"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/all/off', methods=['POST'])
def turn_off_all():
    """모든 인버터 OFF"""
    try:
        plant.turn_off_all()
        
        # 모든 인버터가 OFF이면 Modbus 서버도 중지 (선택적)
        # 실제 인버터는 OFF되어도 통신은 유지할 수 있으므로 주석 처리
        # if modbus_manager and modbus_manager.is_running:
        #     modbus_manager.stop_all()
        #     print("모든 인버터 OFF - Modbus RTU 서버 중지")
        
        return jsonify({"success": True, "message": "모든 인버터 OFF"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/<int:inverter_index>/control-mode', methods=['POST'])
def set_control_mode(inverter_index):
    """인버터 제어 모드 설정"""
    try:
        data = request.get_json()
        mode_str = data.get('mode', 'MPPT')
        
        if mode_str == 'MPPT':
            mode = ControlMode.MPPT
        elif mode_str == 'P_CONTROL':
            mode = ControlMode.P_CONTROL
        else:
            return jsonify({"success": False, "message": "잘못된 제어 모드"}), 400
            
        plant.set_control_mode_inverter(inverter_index, mode)
        return jsonify({"success": True, "message": f"인버터 {inverter_index + 1} 제어 모드: {mode_str}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/all/control-mode', methods=['POST'])
def set_control_mode_all():
    """모든 인버터 제어 모드 설정"""
    try:
        data = request.get_json()
        mode_str = data.get('mode', 'MPPT')
        
        if mode_str == 'MPPT':
            mode = ControlMode.MPPT
        elif mode_str == 'P_CONTROL':
            mode = ControlMode.P_CONTROL
        else:
            return jsonify({"success": False, "message": "잘못된 제어 모드"}), 400
            
        plant.set_control_mode_all(mode)
        return jsonify({"success": True, "message": f"모든 인버터 제어 모드: {mode_str}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/<int:inverter_index>/p-control', methods=['POST'])
def set_p_control_percent(inverter_index):
    """인버터 P 제어 출력 비율 설정"""
    try:
        data = request.get_json()
        percent = float(data.get('percent', 100.0))
        
        if not 0.0 <= percent <= 100.0:
            return jsonify({"success": False, "message": "출력 비율은 0.0 ~ 100.0 사이여야 합니다"}), 400
            
        plant.set_p_control_percent_inverter(inverter_index, percent)
        return jsonify({"success": True, "message": f"인버터 {inverter_index + 1} P 제어: {percent}%"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/inverter/all/p-control', methods=['POST'])
def set_p_control_percent_all():
    """모든 인버터 P 제어 출력 비율 설정"""
    try:
        data = request.get_json()
        percent = float(data.get('percent', 100.0))
        
        if not 0.0 <= percent <= 100.0:
            return jsonify({"success": False, "message": "출력 비율은 0.0 ~ 100.0 사이여야 합니다"}), 400
            
        plant.set_p_control_percent_all(percent)
        return jsonify({"success": True, "message": f"모든 인버터 P 제어: {percent}%"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/environment/irradiance', methods=['POST'])
def set_irradiance():
    """일사량 설정"""
    try:
        data = request.get_json()
        irradiance = float(data.get('irradiance', 1000.0))
        plant.set_irradiance_all(irradiance)
        return jsonify({"success": True, "message": f"일사량: {irradiance} W/m²"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/environment/temperature', methods=['POST'])
def set_temperature():
    """온도 설정"""
    try:
        data = request.get_json()
        temperature = float(data.get('temperature', 25.0))
        plant.set_temperature_all(temperature)
        return jsonify({"success": True, "message": f"온도: {temperature}°C"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/modbus/status', methods=['GET'])
def get_modbus_status():
    """Modbus RTU 통신 상태 조회"""
    if modbus_manager is None:
        return jsonify({
            "available": False,
            "error": True,
            "message": "Modbus RTU Manager가 초기화되지 않았습니다.",
            "error_detail": modbus_error_message or "시리얼 포트(RS-485)가 연결되어 있지 않거나 사용 중입니다.",
            "recommendation": "RS-485 어댑터를 연결하거나 config.py에서 포트 설정을 확인하세요."
        })
    
    status = modbus_manager.get_status()
    
    # 시리얼 포트 연결 상태 확인
    port_available = False
    port_error = None
    port_test_result = None
    
    try:
        import serial.tools.list_ports
        import serial
        
        # 1단계: 시스템에 사용 가능한 포트 목록 확인
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        target_port = status["port"]
        
        if target_port not in available_ports:
            port_available = False
            port_error = f"포트 {target_port}가 시스템에 존재하지 않습니다."
            port_test_result = {
                "step": "port_check",
                "status": "failed",
                "message": f"사용 가능한 포트: {', '.join(available_ports) if available_ports else '없음'}"
            }
        else:
            # 2단계: 포트를 실제로 열어서 테스트 (짧은 시간만)
            try:
                test_serial = serial.Serial(
                    port=target_port,
                    baudrate=status["baudrate"],
                    parity=status["parity"],
                    stopbits=status["stopbits"],
                    bytesize=status["bytesize"],
                    timeout=0.1  # 매우 짧은 타임아웃
                )
                test_serial.close()
                port_available = True
                port_test_result = {
                    "step": "port_open_test",
                    "status": "success",
                    "message": "포트 열기 테스트 성공"
                }
            except serial.SerialException as e:
                port_available = False
                port_error = f"포트 {target_port}를 열 수 없습니다: {str(e)}"
                port_test_result = {
                    "step": "port_open_test",
                    "status": "failed",
                    "message": str(e)
                }
            except Exception as e:
                port_available = False
                port_error = f"포트 테스트 중 오류: {str(e)}"
                port_test_result = {
                    "step": "port_test",
                    "status": "error",
                    "message": str(e)
                }
                
    except ImportError:
        port_available = False
        port_error = "pyserial 라이브러리가 설치되지 않았습니다."
        port_test_result = {
            "step": "library_check",
            "status": "failed",
            "message": "pyserial 설치 필요"
        }
    except Exception as e:
        port_available = False
        port_error = f"포트 확인 중 오류: {str(e)}"
        port_test_result = {
            "step": "unknown",
            "status": "error",
            "message": str(e)
        }
    
    # 3단계: Modbus 서버 실행 상태 확인
    server_running = status.get("is_running", False)
    
    # 최종 연결 상태: 포트 사용 가능 + 서버 실행 중
    actually_connected = port_available and server_running
    
    return jsonify({
        "available": True,
        "error": not port_available,
        "status": status,
        "port_available": port_available,
        "server_running": server_running,
        "actually_connected": actually_connected,
        "port_error": port_error,
        "port_test_result": port_test_result,
        "warning": None if actually_connected else (
            "포트가 연결되어 있지 않습니다." if not port_available 
            else "Modbus 서버가 실행되지 않았습니다." if not server_running
            else "RTU와 통신할 수 없습니다."
        )
    })


@app.route('/api/modbus/log', methods=['GET'])
def get_modbus_log():
    """Modbus RTU 통신 로그 조회"""
    if modbus_manager is None:
        return jsonify({"logs": []})
    
    limit = request.args.get('limit', 50, type=int)
    logs = modbus_manager.get_communication_log(limit=limit)
    return jsonify({"logs": logs})


@app.route('/api/modbus/simulate', methods=['POST'])
def simulate_modbus_communication():
    """Modbus 통신 시뮬레이션 (테스트용)"""
    if modbus_manager is None:
        return jsonify({"success": False, "message": "Modbus RTU Manager가 없습니다."}), 400
    
    try:
        data = request.get_json()
        slave_id = int(data.get('slave_id', 1))
        function_code = int(data.get('function_code', 0x04))
        address = int(data.get('address', 5004))
        quantity = int(data.get('quantity', 1))
        
        modbus_manager.simulate_communication(slave_id, function_code, address, quantity)
        return jsonify({"success": True, "message": "통신 시뮬레이션 완료"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


def start_simulation():
    """시뮬레이션 시작"""
    global update_thread, update_running
    
    if not update_running:
        plant.turn_on_all()
        plant.set_irradiance_all(1000.0)
        plant.set_temperature_all(25.0)
        
        # Modbus RTU 서버 자동 시작 (인버터 ON 시)
        if modbus_manager:
            try:
                modbus_manager.start_all()
                print("Modbus RTU 서버 자동 시작 완료")
            except Exception as e:
                print(f"Modbus RTU 서버 시작 오류: {e}")
                print("시뮬레이션은 계속 진행되지만 Modbus 통신은 사용할 수 없습니다.")
        
        update_running = True
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        print("시뮬레이션 시작")


if __name__ == '__main__':
    start_simulation()
    print("웹 서버 시작: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

