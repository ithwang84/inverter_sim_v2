"""
Modbus RTU/RS-485 통신 기초 구조
레지스터 매핑은 설정 파일로 관리
"""
from typing import Dict, List, Optional, Any
from enum import IntEnum
import json


class ModbusFunctionCode(IntEnum):
    """Modbus 기능 코드"""
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10


class RegisterType(IntEnum):
    """레지스터 타입"""
    COIL = 0  # 출력 코일 (Read/Write)
    DISCRETE_INPUT = 1  # 입력 디스크리트 (Read Only)
    HOLDING_REGISTER = 2  # 홀딩 레지스터 (Read/Write)
    INPUT_REGISTER = 3  # 입력 레지스터 (Read Only)


class ModbusRTUServer:
    """Modbus RTU 서버 (슬레이브)"""
    
    def __init__(self, slave_id: int, register_config: Optional[Dict] = None):
        """
        Args:
            slave_id: 슬레이브 ID (1-247)
            register_config: 레지스터 설정 딕셔너리
        """
        if not 1 <= slave_id <= 247:
            raise ValueError("슬레이브 ID는 1-247 사이여야 합니다.")
            
        self.slave_id = slave_id
        self.register_config = register_config or {}
        
        # 레지스터 저장소
        self.coils: Dict[int, bool] = {}  # 주소 -> 값
        self.discrete_inputs: Dict[int, bool] = {}
        self.holding_registers: Dict[int, int] = {}  # 주소 -> 값 (16bit)
        self.input_registers: Dict[int, int] = {}
        
        # 레지스터 매핑 (설정에서 로드)
        self.register_mapping: Dict[str, Dict] = {}
        
        # 데이터 소스 콜백 함수들
        self.data_source_callbacks: Dict[str, callable] = {}
        
        self._initialize_registers()
        
    def _initialize_registers(self):
        """레지스터 초기화 (설정 파일 기반)"""
        if not self.register_config:
            return
            
        # 레지스터 매핑 로드
        self.register_mapping = self.register_config.get("register_mapping", {})
        
        # 각 레지스터 타입별로 초기화
        for reg_name, reg_info in self.register_mapping.items():
            reg_type = RegisterType(reg_info.get("type", RegisterType.HOLDING_REGISTER))
            address = reg_info.get("address", 0)
            default_value = reg_info.get("default", 0)
            
            if reg_type == RegisterType.COIL:
                self.coils[address] = bool(default_value)
            elif reg_type == RegisterType.DISCRETE_INPUT:
                self.discrete_inputs[address] = bool(default_value)
            elif reg_type == RegisterType.HOLDING_REGISTER:
                self.holding_registers[address] = int(default_value)
            elif reg_type == RegisterType.INPUT_REGISTER:
                self.input_registers[address] = int(default_value)
                
    def load_register_config(self, config: Dict):
        """레지스터 설정 로드"""
        self.register_config = config
        self._initialize_registers()
        
    def register_data_source(self, register_name: str, callback: callable):
        """
        레지스터에 데이터 소스 콜백 등록
        
        Args:
            register_name: 레지스터 이름 (설정 파일의 키)
            callback: 데이터를 반환하는 콜백 함수
        """
        self.data_source_callbacks[register_name] = callback
        
    def _get_register_value(self, register_name: str) -> Any:
        """레지스터 값 가져오기 (콜백 또는 저장된 값)"""
        if register_name in self.data_source_callbacks:
            return self.data_source_callbacks[register_name]()
        elif register_name in self.register_mapping:
            reg_info = self.register_mapping[register_name]
            reg_type = RegisterType(reg_info.get("type", RegisterType.HOLDING_REGISTER))
            address = reg_info.get("address", 0)
            
            if reg_type == RegisterType.COIL:
                return self.coils.get(address, False)
            elif reg_type == RegisterType.DISCRETE_INPUT:
                return self.discrete_inputs.get(address, False)
            elif reg_type == RegisterType.HOLDING_REGISTER:
                return self.holding_registers.get(address, 0)
            elif reg_type == RegisterType.INPUT_REGISTER:
                return self.input_registers.get(address, 0)
        return None
        
    def _set_register_value(self, register_name: str, value: Any):
        """레지스터 값 설정"""
        if register_name not in self.register_mapping:
            return False
            
        reg_info = self.register_mapping[register_name]
        reg_type = RegisterType(reg_info.get("type", RegisterType.HOLDING_REGISTER))
        address = reg_info.get("address", 0)
        
        if reg_type == RegisterType.COIL:
            self.coils[address] = bool(value)
            return True
        elif reg_type == RegisterType.HOLDING_REGISTER:
            self.holding_registers[address] = int(value)
            return True
        else:
            # 읽기 전용 레지스터
            return False
            
    def read_coils(self, start_address: int, quantity: int) -> List[bool]:
        """코일 읽기"""
        result = []
        for i in range(quantity):
            addr = start_address + i
            result.append(self.coils.get(addr, False))
        return result
        
    def read_discrete_inputs(self, start_address: int, quantity: int) -> List[bool]:
        """디스크리트 입력 읽기"""
        result = []
        for i in range(quantity):
            addr = start_address + i
            result.append(self.discrete_inputs.get(addr, False))
        return result
        
    def read_holding_registers(self, start_address: int, quantity: int) -> List[int]:
        """홀딩 레지스터 읽기"""
        result = []
        for i in range(quantity):
            addr = start_address + i
            result.append(self.holding_registers.get(addr, 0))
        return result
        
    def read_input_registers(self, start_address: int, quantity: int) -> List[int]:
        """입력 레지스터 읽기"""
        result = []
        for i in range(quantity):
            addr = start_address + i
            result.append(self.input_registers.get(addr, 0))
        return result
        
    def write_single_coil(self, address: int, value: bool) -> bool:
        """단일 코일 쓰기"""
        self.coils[address] = value
        return True
        
    def write_single_register(self, address: int, value: int) -> bool:
        """단일 레지스터 쓰기"""
        if not 0 <= value <= 65535:
            return False
        self.holding_registers[address] = value
        return True
        
    def write_multiple_coils(self, start_address: int, values: List[bool]) -> bool:
        """다중 코일 쓰기"""
        for i, value in enumerate(values):
            self.coils[start_address + i] = value
        return True
        
    def write_multiple_registers(self, start_address: int, values: List[int]) -> bool:
        """다중 레지스터 쓰기"""
        for i, value in enumerate(values):
            if not 0 <= value <= 65535:
                return False
            self.holding_registers[start_address + i] = value
        return True
        
    def update_registers_from_data_source(self):
        """데이터 소스에서 레지스터 값 업데이트"""
        for reg_name, callback in self.data_source_callbacks.items():
            if reg_name not in self.register_mapping:
                continue
                
            value = callback()
            reg_info = self.register_mapping[reg_name]
            reg_type = RegisterType(reg_info.get("type", RegisterType.INPUT_REGISTER))
            address = reg_info.get("address", 0)
            
            # 읽기 전용 레지스터만 업데이트 (입력 레지스터, 디스크리트 입력)
            if reg_type == RegisterType.INPUT_REGISTER:
                self.input_registers[address] = int(value)
            elif reg_type == RegisterType.DISCRETE_INPUT:
                self.discrete_inputs[address] = bool(value)
                
    def get_register_status(self) -> Dict:
        """레지스터 상태 정보 반환"""
        return {
            "slave_id": self.slave_id,
            "coils": dict(self.coils),
            "discrete_inputs": dict(self.discrete_inputs),
            "holding_registers": dict(self.holding_registers),
            "input_registers": dict(self.input_registers),
            "register_mapping": self.register_mapping
        }


class ModbusRTUClient:
    """Modbus RTU 클라이언트 (마스터) - 향후 구현용"""
    
    def __init__(self, port: str = "COM1", baudrate: int = 9600, timeout: float = 1.0):
        """
        Args:
            port: 시리얼 포트 (예: "COM1", "/dev/ttyUSB0")
            baudrate: 통신 속도
            timeout: 타임아웃 (초)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_connected = False
        
    def connect(self):
        """연결 (향후 구현)"""
        # 실제 구현 시 pymodbus 또는 pyserial 사용
        self.is_connected = True
        
    def disconnect(self):
        """연결 해제"""
        self.is_connected = False
        
    def read_holding_registers(self, slave_id: int, start_address: int, quantity: int) -> List[int]:
        """홀딩 레지스터 읽기 (향후 구현)"""
        # 실제 구현 필요
        return []
        
    def write_single_register(self, slave_id: int, address: int, value: int) -> bool:
        """단일 레지스터 쓰기 (향후 구현)"""
        # 실제 구현 필요
        return False

