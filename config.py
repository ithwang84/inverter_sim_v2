"""
설정 파일
레지스터 매핑 및 시스템 설정
"""
from typing import Dict, Any

# 레지스터 타입 정의
REGISTER_TYPE_COIL = 0
REGISTER_TYPE_DISCRETE_INPUT = 1
REGISTER_TYPE_HOLDING_REGISTER = 2
REGISTER_TYPE_INPUT_REGISTER = 3

# 기본 레지스터 매핑 설정
# Sungrow 인버터 Modbus RTU 프로토콜 기반
DEFAULT_REGISTER_MAPPING: Dict[str, Dict[str, Any]] = {
    # ========== 제어 레지스터 (Holding Register - Read/Write) ==========
    # Modbus Function Code: 0x03 (Read), 0x06 (Write Single), 0x10 (Write Multiple)
    
    "start_stop": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5006,
        "description": "인버터 시작/정지 (0xCF: Start, 0xCE: Stop)",
        "default": 0xCE,
        "scale": 1,
        "values": {"start": 0xCF, "stop": 0xCE}
    },
    "power_limitation_switch": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5007,
        "description": "제어 모드 스위치 (0xAA: P제어 모드, 0x55: MPPT 모드)",
        "default": 0x55,
        "scale": 1,
        "values": {"p_control": 0xAA, "mppt": 0x55},
        "note": "0xAA = P제어 모드 활성화, 0x55 = MPPT 모드 (전력 제한 비활성화)"
    },
    "power_limitation_setting": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5008,
        "description": "P 제어 출력 비율 설정 (0-1000, 스케일 0.10%)",
        "default": 1000,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (%)
        "range": [0, 1000],
        "note": "power_limitation_switch가 0xAA일 때만 유효"
    },
    "active_power_regulation_setpoint": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5077,  # 5077-5078 (U32, 2개 레지스터)
        "description": "유효 전력 조절 설정값 (W) - Except SG5.5RS-JP",
        "default": 0,
        "scale": 1,  # W
        "data_type": "U32",
        "register_count": 2
    },
    "reactive_power_regulation_setpoint": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5079,  # 5079-5080 (S32, 2개 레지스터)
        "description": "무효 전력 조절 설정값 (Var) - Except SG5.5RS-JP",
        "default": 0,
        "scale": 1,  # Var
        "data_type": "S32",
        "register_count": 2
    },
    "power_factor_setpoint": {
        "type": REGISTER_TYPE_HOLDING_REGISTER,
        "address": 5125,
        "description": "역률 설정값 (스케일 0.001) - Except SG5.5RS-JP",
        "default": 1000,
        "scale": 0.001,  # 실제 값 = 레지스터 값 * 0.001
        "data_type": "S16",
        "range": [-1000, 1000]
    },
    
    # ========== 모니터링 레지스터 (Input Register - Read Only) ==========
    # Modbus Function Code: 0x04 (Read Input Registers)
    
    # 기본 정보
    "nominal_active_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5001,
        "description": "정격 유효 전력 (kW)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (kW)
        "data_type": "U16"
    },
    "daily_yields_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5003,
        "description": "일일 발전량 (kWh)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (kWh)
        "data_type": "U16"
    },
    "total_yields_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5004,  # 5004-5005 (U32, 2개 레지스터)
        "description": "총 발전량 (kWh)",
        "default": 0,
        "scale": 1,  # kWh
        "data_type": "U32",
        "register_count": 2
    },
    
    # 운전 정보
    "total_running_time": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5006,  # 5006-5007 (U32, 2개 레지스터)
        "description": "총 가동 시간 (h)",
        "default": 0,
        "scale": 1,  # h
        "data_type": "U32",
        "register_count": 2
    },
    "internal_temperature": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5008,
        "description": "내부 온도 (°C)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (°C)
        "data_type": "S16"
    },
    "total_apparent_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5009,  # 5009-5010 (U32, 2개 레지스터)
        "description": "총 피상 전력 (VA)",
        "default": 0,
        "scale": 1,  # VA
        "data_type": "U32",
        "register_count": 2
    },
    
    # MPPT 정보 (DC 측)
    "mppt1_voltage": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5011,
        "description": "MPPT 1 전압 (V)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (V)
        "data_type": "U16"
    },
    "mppt1_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5012,
        "description": "MPPT 1 전류 (A)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (A)
        "data_type": "U16"
    },
    "mppt2_voltage": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5013,
        "description": "MPPT 2 전압 (V)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "mppt2_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5014,
        "description": "MPPT 2 전류 (A)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "mppt3_voltage": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5015,
        "description": "MPPT 3 전압 (V)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "mppt3_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5016,
        "description": "MPPT 3 전류 (A)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "total_dc_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5017,  # 5017-5018 (U32, 2개 레지스터)
        "description": "총 DC 전력 (W)",
        "default": 0,
        "scale": 1,  # W
        "data_type": "U32",
        "register_count": 2
    },
    
    # AC 출력 정보
    "ac_line_voltage_ab": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5019,
        "description": "A-B 선간 전압 또는 A상 전압 (V) - Output type에 따라 다름",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (V)
        "data_type": "U16"
    },
    "ac_line_voltage_bc": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5020,
        "description": "B-C 선간 전압 또는 B상 전압 (V)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "ac_line_voltage_ca": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5021,
        "description": "C-A 선간 전압 또는 C상 전압 (V)",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "phase_a_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5022,
        "description": "A상 전류 (A) - Except SG5.5RS-JP",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (A)
        "data_type": "U16"
    },
    "phase_b_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5023,
        "description": "B상 전류 (A) - Except SG5.5RS-JP",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    "phase_c_current": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5024,
        "description": "C상 전류 (A) - Except SG5.5RS-JP",
        "default": 0,
        "scale": 0.1,
        "data_type": "U16"
    },
    
    # 전력 정보
    "total_active_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5031,  # 5031-5032 (S32, 2개 레지스터)
        "description": "총 유효 전력 (W)",
        "default": 0,
        "scale": 1,  # W
        "data_type": "S32",
        "register_count": 2
    },
    "total_reactive_power": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5033,  # 5033-5034 (S32, 2개 레지스터)
        "description": "총 무효 전력 (Var)",
        "default": 0,
        "scale": 1,  # Var
        "data_type": "S32",
        "register_count": 2
    },
    "power_factor": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5035,
        "description": "역률 (스케일 0.001, >0: leading, <0: lagging)",
        "default": 0,
        "scale": 0.001,  # 실제 값 = 레지스터 값 * 0.001
        "data_type": "S16"
    },
    "grid_frequency": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5036,
        "description": "계통 주파수 (Hz)",
        "default": 0,
        "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (Hz)
        "data_type": "U16"
    },
    
    # 상태 정보
    "work_state_1": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5038,
        "description": "운전 상태 1 (See Appendix WorkingState 1)",
        "default": 0,
        "scale": 1,
        "data_type": "U16"
    },
    "work_state_2": {
        "type": REGISTER_TYPE_INPUT_REGISTER,
        "address": 5081,  # 5081-5082 (U32, 2개 레지스터) - Except SG5.5RS-JP
        "description": "운전 상태 2 (See Appendix WorkingState 2)",
        "default": 0,
        "scale": 1,
        "data_type": "U32",
        "register_count": 2
    },
    
    # ========== 대형 인버터용 레지스터 (15000번대 주소) ==========
    # 현재 시뮬레이터는 250kVA 인버터 사용 (5000번대 주소 사용)
    # 대형 인버터(SG1250UD, SG2500UD, SG3000UD 등)용 레지스터는 주석 처리
    # 필요시 주석 해제하여 사용 가능
    
    # "total_active_power_high": {
    #     "type": REGISTER_TYPE_INPUT_REGISTER,
    #     "address": 15100,  # 15100-15101 (U32, 2개 레지스터)
    #     "description": "총 유효 전력 (W) - 대형 인버터",
    #     "default": 0,
    #     "scale": 1,  # W
    #     "data_type": "U32",
    #     "register_count": 2
    # },
    # "total_reactive_power_high": {
    #     "type": REGISTER_TYPE_INPUT_REGISTER,
    #     "address": 15102,  # 15102-15103 (S32, 2개 레지스터)
    #     "description": "총 무효 전력 (Var) - 대형 인버터",
    #     "default": 0,
    #     "scale": 1,  # Var
    #     "data_type": "S32",
    #     "register_count": 2
    # },
    # "power_factor_high": {
    #     "type": REGISTER_TYPE_INPUT_REGISTER,
    #     "address": 15106,
    #     "description": "역률 (스케일 0.001) - 대형 인버터",
    #     "default": 0,
    #     "scale": 0.001,
    #     "data_type": "S16"
    # },
    # "grid_frequency_high": {
    #     "type": REGISTER_TYPE_INPUT_REGISTER,
    #     "address": 15107,
    #     "description": "계통 주파수 (Hz) - 대형 인버터",
    #     "default": 0,
    #     "scale": 0.1,  # 실제 값 = 레지스터 값 * 0.1 (Hz)
    #     "data_type": "U16"
    # },
}

# 시스템 설정
SYSTEM_CONFIG = {
    "plant_id": "PLANT_01",
    "total_capacity_mva": 1.0,
    "inverter_capacity_kva": 250.0,
    "num_inverters": 4,
    "modbus": {
        "slave_id": 1,  # 첫 번째 인버터의 슬레이브 ID (나머지는 2, 3, 4...)
        "port": "COM1",  # RS-485 시리얼 포트 (Windows: COM1, Linux: /dev/ttyUSB0)
        "baudrate": 9600,
        "parity": "N",
        "stopbits": 1,
        "bytesize": 8
    }
}


def load_register_config_from_file(filepath: str) -> Dict[str, Dict[str, Any]]:
    """파일에서 레지스터 설정 로드"""
    import json
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_REGISTER_MAPPING
    except json.JSONDecodeError:
        print(f"설정 파일 파싱 오류: {filepath}")
        return DEFAULT_REGISTER_MAPPING


def save_register_config_to_file(filepath: str, config: Dict[str, Dict[str, Any]]):
    """레지스터 설정을 파일에 저장"""
    import json
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

