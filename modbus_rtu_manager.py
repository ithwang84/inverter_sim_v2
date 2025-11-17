"""
Modbus RTU 서버 관리자
여러 인버터의 Modbus RTU 서버를 통합 관리
RS-485 멀티드롭 버스에서 여러 슬레이브를 하나의 포트로 처리
"""
from typing import List, Dict, Optional
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
from power_plant import PowerPlant
from inverter import Inverter
from config import SYSTEM_CONFIG, DEFAULT_REGISTER_MAPPING, REGISTER_TYPE_HOLDING_REGISTER, REGISTER_TYPE_INPUT_REGISTER
import asyncio
import threading
import time


class ModbusRTUManager:
    """Modbus RTU 서버 통합 관리 클래스
    하나의 RS-485 버스에 여러 슬레이브(인버터)를 등록하여 처리
    """
    
    def __init__(
        self,
        power_plant: PowerPlant,
        port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        base_slave_id: int = 1
    ):
        """
        Args:
            power_plant: 발전소 인스턴스
            port: RS-485 시리얼 포트
            baudrate: 통신 속도
            parity: 패리티
            stopbits: 스톱 비트
            bytesize: 데이터 비트
            base_slave_id: 첫 번째 인버터의 슬레이브 ID (기본값: 1)
        """
        self.power_plant = power_plant
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.base_slave_id = base_slave_id
        
        # 각 인버터별 슬레이브 컨텍스트
        self.slave_contexts: Dict[int, ModbusSlaveContext] = {}
        
        # 각 인버터별 데이터 블록 참조 (레지스터 업데이트용)
        self.input_blocks: Dict[int, ModbusSequentialDataBlock] = {}
        self.holding_blocks: Dict[int, ModbusSequentialDataBlock] = {}
        
        # 데이터 소스 콜백 함수들 (슬레이브 ID별)
        self.data_source_callbacks: Dict[int, Dict[str, callable]] = {}
        
        # 서버 인스턴스
        self.server = None
        self.server_thread = None
        self.is_running = False
        
        # 통신 이벤트 로그
        self.communication_log: List[Dict] = []  # 최근 통신 이벤트
        self.max_log_entries = 100  # 최대 로그 개수
        
        # 통신 통계
        self.communication_stats: Dict[int, Dict] = {}  # 슬레이브 ID별 통계
        
        # 초기화
        self._initialize_slaves()
        
    def _initialize_slaves(self):
        """각 인버터별 슬레이브 컨텍스트 초기화"""
        # 최대 레지스터 주소 찾기
        max_holding_addr = 0
        max_input_addr = 0
        
        for reg_name, reg_info in DEFAULT_REGISTER_MAPPING.items():
            reg_type = reg_info.get("type", REGISTER_TYPE_HOLDING_REGISTER)
            address = reg_info.get("address", 0)
            register_count = reg_info.get("register_count", 1)
            max_addr = address + register_count - 1
            
            if reg_type == REGISTER_TYPE_HOLDING_REGISTER:
                max_holding_addr = max(max_holding_addr, max_addr)
            elif reg_type == REGISTER_TYPE_INPUT_REGISTER:
                max_input_addr = max(max_input_addr, max_addr)
        
        holding_size = max_holding_addr + 1 if max_holding_addr > 0 else 10000
        input_size = max_input_addr + 1 if max_input_addr > 0 else 10000
        
        # 각 인버터별로 슬레이브 컨텍스트 생성
        for i, inverter in enumerate(self.power_plant.inverters):
            slave_id = self.base_slave_id + i
            
            # 데이터 블록 생성
            holding_block = ModbusSequentialDataBlock(0, [0] * holding_size)
            input_block = ModbusSequentialDataBlock(0, [0] * input_size)
            
            # 기본값으로 초기화
            for reg_name, reg_info in DEFAULT_REGISTER_MAPPING.items():
                reg_type = reg_info.get("type", REGISTER_TYPE_HOLDING_REGISTER)
                address = reg_info.get("address", 0)
                default_value = reg_info.get("default", 0)
                
                if reg_type == REGISTER_TYPE_HOLDING_REGISTER:
                    holding_block.setValues(address, [default_value])
                elif reg_type == REGISTER_TYPE_INPUT_REGISTER:
                    input_block.setValues(address, [default_value])
            
            # 슬레이브 컨텍스트 생성
            slave_context = ModbusSlaveContext(
                di=None,
                co=None,
                hr=holding_block,
                ir=input_block
            )
            
            self.slave_contexts[slave_id] = slave_context
            self.input_blocks[slave_id] = input_block
            self.holding_blocks[slave_id] = holding_block
            self.data_source_callbacks[slave_id] = {}
            
            # 레지스터에 데이터 소스 연결
            self._connect_data_sources(slave_id, inverter, i, input_block, holding_block)
            
        # 서버 컨텍스트 생성 (여러 슬레이브 등록)
        self.server_context = ModbusServerContext(
            slaves=self.slave_contexts,
            single=False
        )
        
        # 통신 통계 초기화
        for slave_id in self.slave_contexts.keys():
            self.communication_stats[slave_id] = {
                "total_requests": 0,
                "total_responses": 0,
                "read_requests": 0,
                "write_requests": 0,
                "last_request_time": None,
                "last_response_time": None,
                "error_count": 0
            }
        
        print(f"[Modbus RTU Manager] {len(self.slave_contexts)}개 슬레이브 초기화 완료")
        
    def _connect_data_sources(
        self, 
        slave_id: int, 
        inverter: Inverter, 
        index: int,
        input_block: ModbusSequentialDataBlock,
        holding_block: ModbusSequentialDataBlock
    ):
        """인버터 데이터를 레지스터에 연결"""
        pv_gen = self.power_plant.pv_generators[index]
        
        # 총 발전량 (total_yields_power) - 5004-5005 (U32)
        def get_total_yields_power():
            """총 발전량 (kWh) - 누적값 시뮬레이션"""
            # 실제로는 시간에 따라 누적되어야 하지만, 간단히 현재 전력으로 시뮬레이션
            monitoring = inverter.get_monitoring()
            # kWh 단위 (U32, 스케일 1)
            # 간단 시뮬레이션: 현재 전력으로 가정
            return int(monitoring.active_power)  # kWh
        
        # 정격 유효 전력 (nominal_active_power) - 5001
        def get_nominal_active_power():
            """정격 유효 전력 (kW) * 10"""
            return int(inverter.rated_capacity_kw * 10)
        
        # 일일 발전량 (daily_yields_power) - 5003
        def get_daily_yields_power():
            """일일 발전량 (kWh) * 10"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.active_power * 10)  # 간단 시뮬레이션
        
        # MPPT 1 전압 (mppt1_voltage) - 5011
        def get_mppt1_voltage():
            """MPPT 1 전압 (V) * 10"""
            pv_monitoring = pv_gen.get_monitoring()
            return int(pv_monitoring.voltage * 10)
        
        # MPPT 1 전류 (mppt1_current) - 5012
        def get_mppt1_current():
            """MPPT 1 전류 (A) * 10"""
            pv_monitoring = pv_gen.get_monitoring()
            return int(pv_monitoring.current * 10)
        
        # 총 DC 전력 (total_dc_power) - 5017-5018 (U32)
        def get_total_dc_power():
            """총 DC 전력 (W)"""
            pv_monitoring = pv_gen.get_monitoring()
            return int(pv_monitoring.active_power * 1000)  # kW -> W
        
        # AC 선간 전압 (ac_line_voltage_ab) - 5019
        def get_ac_line_voltage_ab():
            """A-B 선간 전압 (V) * 10"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.output_voltage * 10)
        
        # A상 전류 (phase_a_current) - 5022
        def get_phase_a_current():
            """A상 전류 (A) * 10"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.output_current * 10)
        
        # 총 유효 전력 (total_active_power) - 5031-5032 (S32)
        def get_total_active_power():
            """총 유효 전력 (W)"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.active_power * 1000)  # kW -> W
        
        # 총 무효 전력 (total_reactive_power) - 5033-5034 (S32)
        def get_total_reactive_power():
            """총 무효 전력 (Var)"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.reactive_power * 1000)  # kVar -> Var
        
        # 역률 (power_factor) - 5035
        def get_power_factor():
            """역률 * 1000"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.power_factor * 1000)
        
        # 계통 주파수 (grid_frequency) - 5036
        def get_grid_frequency():
            """계통 주파수 (Hz) * 10"""
            monitoring = inverter.get_monitoring()
            return int(monitoring.frequency * 10)
        
        # 운전 상태 1 (work_state_1) - 5038
        def get_work_state_1():
            """운전 상태 1"""
            # 0x0: Run, 0x8000: Stop
            return 0x0 if inverter.is_on else 0x8000
        
        # 레지스터 연결 (콜백 저장)
        self.data_source_callbacks[slave_id]["total_yields_power"] = get_total_yields_power
        self.data_source_callbacks[slave_id]["nominal_active_power"] = get_nominal_active_power
        self.data_source_callbacks[slave_id]["daily_yields_power"] = get_daily_yields_power
        self.data_source_callbacks[slave_id]["mppt1_voltage"] = get_mppt1_voltage
        self.data_source_callbacks[slave_id]["mppt1_current"] = get_mppt1_current
        self.data_source_callbacks[slave_id]["total_dc_power"] = get_total_dc_power
        self.data_source_callbacks[slave_id]["ac_line_voltage_ab"] = get_ac_line_voltage_ab
        self.data_source_callbacks[slave_id]["phase_a_current"] = get_phase_a_current
        self.data_source_callbacks[slave_id]["total_active_power"] = get_total_active_power
        self.data_source_callbacks[slave_id]["total_reactive_power"] = get_total_reactive_power
        self.data_source_callbacks[slave_id]["power_factor"] = get_power_factor
        self.data_source_callbacks[slave_id]["grid_frequency"] = get_grid_frequency
        self.data_source_callbacks[slave_id]["work_state_1"] = get_work_state_1
        
    def start_all(self):
        """Modbus RTU 서버 시작 (모든 슬레이브 포함)"""
        if self.is_running:
            print(f"[Modbus RTU Manager] 서버가 이미 실행 중입니다.")
            return
            
        try:
            print(f"\n[Modbus RTU Manager] Modbus RTU 서버 시작 중...")
            print(f"  포트: {self.port}")
            print(f"  통신 속도: {self.baudrate}")
            print(f"  슬레이브 ID: {list(self.slave_contexts.keys())}")
            
            # 서버 시작 (비동기)
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            # 서버 시작 대기
            time.sleep(1)
            self.is_running = True
            print(f"[Modbus RTU Manager] Modbus RTU 서버 시작 완료\n")
            
        except Exception as e:
            print(f"[Modbus RTU Manager] 서버 시작 오류: {e}")
            self.is_running = False
            
    def _log_communication(self, event_type: str, slave_id: int, function_code: int, 
                          address: int = None, quantity: int = None, values: List = None, 
                          success: bool = True, error: str = None):
        """통신 이벤트 로깅"""
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,  # "request", "response", "error"
            "slave_id": slave_id,
            "function_code": function_code,
            "function_name": self._get_function_name(function_code),
            "address": address,
            "quantity": quantity,
            "values": values,
            "success": success,
            "error": error
        }
        
        self.communication_log.append(log_entry)
        
        # 최대 로그 개수 제한
        if len(self.communication_log) > self.max_log_entries:
            self.communication_log.pop(0)
        
        # 통계 업데이트
        if slave_id in self.communication_stats:
            stats = self.communication_stats[slave_id]
            if event_type == "request":
                stats["total_requests"] += 1
                stats["last_request_time"] = log_entry["timestamp"]
                if function_code in [0x03, 0x04]:
                    stats["read_requests"] += 1
                elif function_code in [0x06, 0x10]:
                    stats["write_requests"] += 1
            elif event_type == "response":
                stats["total_responses"] += 1
                stats["last_response_time"] = log_entry["timestamp"]
            elif event_type == "error":
                stats["error_count"] += 1
                
    def _get_function_name(self, function_code: int) -> str:
        """Function Code를 이름으로 변환"""
        func_names = {
            0x01: "Read Coils",
            0x02: "Read Discrete Inputs",
            0x03: "Read Holding Registers",
            0x04: "Read Input Registers",
            0x05: "Write Single Coil",
            0x06: "Write Single Register",
            0x0F: "Write Multiple Coils",
            0x10: "Write Multiple Registers"
        }
        return func_names.get(function_code, f"Unknown (0x{function_code:02X})")
    
    def _run_server(self):
        """서버 실행 (별도 스레드)"""
        try:
            # asyncio 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 커스텀 핸들러로 통신 이벤트 추적
            # pymodbus의 로깅을 활성화하여 통신 추적
            import logging
            logging.basicConfig()
            log = logging.getLogger()
            log.setLevel(logging.DEBUG)
            
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
                    # request_tracer를 사용하여 통신 추적
                )
            )
            loop.run_forever()
        except Exception as e:
            print(f"[Modbus RTU Manager] 서버 실행 오류: {e}")
            self.is_running = False
            self._log_communication("error", 0, 0, error=str(e), success=False)
        
    def stop_all(self):
        """Modbus RTU 서버 중지"""
        if not self.is_running:
            return
            
        self.is_running = False
        print(f"[Modbus RTU Manager] Modbus RTU 서버 중지\n")
        
    def update_all_registers(self):
        """모든 인버터의 레지스터 업데이트"""
        for slave_id, callbacks in self.data_source_callbacks.items():
            if slave_id not in self.input_blocks:
                continue
                
            input_block = self.input_blocks[slave_id]
            
            for reg_name, callback in callbacks.items():
                if reg_name not in DEFAULT_REGISTER_MAPPING:
                    continue
                    
                try:
                    value = callback()
                    reg_info = DEFAULT_REGISTER_MAPPING[reg_name]
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
                        low_word = register_value & 0xFFFF
                        high_word = (register_value >> 16) & 0xFFFF
                        values = [low_word, high_word]
                    else:
                        if register_value < 0:
                            register_value = register_value & 0xFFFF
                        elif register_value > 65535:
                            register_value = 65535
                        values = [register_value]
                    
                    # 레지스터 업데이트
                    if reg_type == REGISTER_TYPE_INPUT_REGISTER:
                        input_block.setValues(address, values)
                        
                except Exception as e:
                    print(f"[슬레이브 {slave_id}] 레지스터 {reg_name} 업데이트 오류: {e}")
            
    def get_status(self) -> Dict:
        """전체 상태 정보 반환"""
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "is_running": self.is_running,
            "num_slaves": len(self.slave_contexts),
            "slave_ids": list(self.slave_contexts.keys()),
            "communication_stats": self.communication_stats
        }
    
    def get_communication_log(self, limit: int = 50) -> List[Dict]:
        """통신 로그 반환"""
        return self.communication_log[-limit:] if limit > 0 else self.communication_log
    
    def simulate_communication(self, slave_id: int, function_code: int, address: int, quantity: int = 1):
        """통신 시뮬레이션 (테스트용)"""
        if slave_id not in self.slave_contexts:
            self._log_communication("error", slave_id, function_code, address, quantity, 
                                  success=False, error=f"슬레이브 ID {slave_id} 없음")
            return
            
        # 요청 로깅
        self._log_communication("request", slave_id, function_code, address, quantity)
        
        # 응답 시뮬레이션
        try:
            slave_context = self.slave_contexts[slave_id]
            if function_code == 0x04:  # Read Input Registers
                values = []
                for i in range(quantity):
                    val = slave_context.getValues(3, address + i, 1)[0]  # 3 = Input Registers
                    values.append(val)
                self._log_communication("response", slave_id, function_code, address, quantity, values)
            elif function_code == 0x03:  # Read Holding Registers
                values = []
                for i in range(quantity):
                    val = slave_context.getValues(2, address + i, 1)[0]  # 2 = Holding Registers
                    values.append(val)
                self._log_communication("response", slave_id, function_code, address, quantity, values)
        except Exception as e:
            self._log_communication("error", slave_id, function_code, address, quantity, 
                                  success=False, error=str(e))

