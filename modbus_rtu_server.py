"""
Modbus RTU 서버 구현
표준 Modbus RTU 프로토콜을 사용한 RS-485 통신
각 인버터는 독립적인 슬레이브로 동작
"""
from pymodbus.server import StartSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
try:
    from pymodbus.framer import FramerRTU as ModbusRtuFramer
except ImportError:
    try:
        from pymodbus.framer.rtu import FramerRTU as ModbusRtuFramer
    except ImportError:
        # 구버전 호환성
        try:
            from pymodbus.transaction import ModbusRtuFramer
        except ImportError:
            # 문자열로 사용
            ModbusRtuFramer = "rtu"
from typing import Dict, Optional, Callable
import asyncio
import threading
import time
from config import DEFAULT_REGISTER_MAPPING, REGISTER_TYPE_HOLDING_REGISTER, REGISTER_TYPE_INPUT_REGISTER


class InverterModbusServer:
    """인버터별 Modbus RTU 서버 (슬레이브)"""
    
    def __init__(
        self,
        slave_id: int,
        port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        register_config: Optional[Dict] = None
    ):
        """
        Args:
            slave_id: 슬레이브 ID (1-247)
            port: 시리얼 포트 (예: "COM1", "/dev/ttyUSB0")
            baudrate: 통신 속도 (9600, 19200, 38400 등)
            parity: 패리티 (N: None, E: Even, O: Odd)
            stopbits: 스톱 비트 (1, 2)
            bytesize: 데이터 비트 (7, 8)
            register_config: 레지스터 설정
        """
        if not 1 <= slave_id <= 247:
            raise ValueError("슬레이브 ID는 1-247 사이여야 합니다.")
            
        self.slave_id = slave_id
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        
        self.register_config = register_config or {}
        self.register_mapping = self.register_config.get("register_mapping", DEFAULT_REGISTER_MAPPING)
        
        # 데이터 소스 콜백 함수들
        self.data_source_callbacks: Dict[str, Callable] = {}
        
        # Modbus 데이터 블록 초기화
        self._initialize_datastore()
        
        # 서버 인스턴스
        self.server = None
        self.server_thread = None
        self.is_running = False
        
    def _initialize_datastore(self):
        """Modbus 데이터 저장소 초기화"""
        # Holding Registers (제어 레지스터) - 주소 0부터 시작
        # Input Registers (모니터링 레지스터) - 주소 0부터 시작
        
        # 최대 레지스터 주소 찾기
        max_holding_addr = 0
        max_input_addr = 0
        
        for reg_name, reg_info in self.register_mapping.items():
            reg_type = reg_info.get("type", REGISTER_TYPE_HOLDING_REGISTER)
            address = reg_info.get("address", 0)
            register_count = reg_info.get("register_count", 1)
            max_addr = address + register_count - 1
            
            if reg_type == REGISTER_TYPE_HOLDING_REGISTER:
                max_holding_addr = max(max_holding_addr, max_addr)
            elif reg_type == REGISTER_TYPE_INPUT_REGISTER:
                max_input_addr = max(max_input_addr, max_addr)
        
        # 데이터 블록 생성 (0으로 초기화)
        # pymodbus는 주소를 0부터 시작하므로, 실제 주소와 매핑 필요
        holding_size = max_holding_addr + 1 if max_holding_addr > 0 else 1000
        input_size = max_input_addr + 1 if max_input_addr > 0 else 1000
        
        self.holding_block = ModbusSequentialDataBlock(0, [0] * holding_size)
        self.input_block = ModbusSequentialDataBlock(0, [0] * input_size)
        
        # 기본값으로 초기화
        for reg_name, reg_info in self.register_mapping.items():
            reg_type = reg_info.get("type", REGISTER_TYPE_HOLDING_REGISTER)
            address = reg_info.get("address", 0)
            default_value = reg_info.get("default", 0)
            
            if reg_type == REGISTER_TYPE_HOLDING_REGISTER:
                self.holding_block.setValues(address, [default_value])
            elif reg_type == REGISTER_TYPE_INPUT_REGISTER:
                self.input_block.setValues(address, [default_value])
        
        # 슬레이브 컨텍스트 생성
        self.slave_context = ModbusSlaveContext(
            di=None,  # Discrete Inputs
            co=None,  # Coils
            hr=self.holding_block,  # Holding Registers
            ir=self.input_block     # Input Registers
        )
        
        # 서버 컨텍스트 생성
        self.server_context = ModbusServerContext(
            slaves={self.slave_id: self.slave_context},
            single=False
        )
        
    def register_data_source(self, register_name: str, callback: Callable):
        """
        레지스터에 데이터 소스 콜백 등록
        
        Args:
            register_name: 레지스터 이름 (config.py의 키)
            callback: 데이터를 반환하는 콜백 함수
        """
        self.data_source_callbacks[register_name] = callback
        
    def update_registers(self):
        """데이터 소스에서 레지스터 값 업데이트"""
        for reg_name, callback in self.data_source_callbacks.items():
            if reg_name not in self.register_mapping:
                continue
                
            try:
                value = callback()
                reg_info = self.register_mapping[reg_name]
                reg_type = reg_info.get("type", REGISTER_TYPE_INPUT_REGISTER)
                address = reg_info.get("address", 0)
                register_count = reg_info.get("register_count", 1)
                scale = reg_info.get("scale", 1)
                
                # 실제 값을 레지스터 값으로 변환
                if scale != 1:
                    register_value = int(value / scale)
                else:
                    register_value = int(value)
                
                # U32/S32 타입은 2개 레지스터 사용
                if register_count == 2:
                    # 하위 16비트, 상위 16비트로 분리
                    low_word = register_value & 0xFFFF
                    high_word = (register_value >> 16) & 0xFFFF
                    values = [low_word, high_word]
                else:
                    # 값 범위 체크 (U16: 0-65535, S16: -32768~32767)
                    if register_value < 0:
                        register_value = register_value & 0xFFFF  # 16비트 부호 처리
                    elif register_value > 65535:
                        register_value = 65535
                    values = [register_value]
                
                # 레지스터 업데이트
                if reg_type == REGISTER_TYPE_INPUT_REGISTER:
                    self.input_block.setValues(address, values)
                elif reg_type == REGISTER_TYPE_HOLDING_REGISTER:
                    self.holding_block.setValues(address, values)
                    
            except Exception as e:
                print(f"[슬레이브 {self.slave_id}] 레지스터 {reg_name} 업데이트 오류: {e}")
                
    def write_holding_register(self, address: int, value: int):
        """홀딩 레지스터 쓰기 (제어 명령)"""
        if 0 <= address < len(self.holding_block.values):
            self.holding_block.setValues(address, [value])
            return True
        return False
        
    def read_input_register(self, address: int) -> int:
        """입력 레지스터 읽기"""
        if 0 <= address < len(self.input_block.values):
            values = self.input_block.getValues(address, 1)
            return values[0] if values else 0
        return 0
        
    def start(self):
        """Modbus RTU 서버 시작"""
        if self.is_running:
            print(f"[슬레이브 {self.slave_id}] 서버가 이미 실행 중입니다.")
            return
            
        try:
            # 패리티 변환
            parity_map = {"N": "N", "E": "E", "O": "O"}
            parity_char = parity_map.get(self.parity.upper(), "N")
            
            print(f"[슬레이브 {self.slave_id}] Modbus RTU 서버 시작 중...")
            print(f"  포트: {self.port}")
            print(f"  통신 속도: {self.baudrate}")
            print(f"  슬레이브 ID: {self.slave_id}")
            
            # 서버 시작 (비동기)
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            # 서버 시작 대기
            time.sleep(1)
            self.is_running = True
            print(f"[슬레이브 {self.slave_id}] Modbus RTU 서버 시작 완료")
            
        except Exception as e:
            print(f"[슬레이브 {self.slave_id}] 서버 시작 오류: {e}")
            self.is_running = False
            
    def _run_server(self):
        """서버 실행 (별도 스레드)"""
        try:
            # asyncio 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 서버 시작
            loop.run_until_complete(
                StartSerialServer(
                    context=self.server_context,
                    framer=ModbusRtuFramer,
                    port=self.port,
                    baudrate=self.baudrate,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    bytesize=self.bytesize,
                )
            )
            loop.run_forever()
        except Exception as e:
            print(f"[슬레이브 {self.slave_id}] 서버 실행 오류: {e}")
            self.is_running = False
            
    def stop(self):
        """Modbus RTU 서버 중지"""
        if not self.is_running:
            return
            
        self.is_running = False
        print(f"[슬레이브 {self.slave_id}] Modbus RTU 서버 중지")
        
    def get_register_status(self) -> Dict:
        """레지스터 상태 정보 반환"""
        return {
            "slave_id": self.slave_id,
            "port": self.port,
            "is_running": self.is_running,
            "holding_registers_count": len(self.holding_block.values),
            "input_registers_count": len(self.input_block.values)
        }

