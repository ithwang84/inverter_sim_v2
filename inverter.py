"""
인버터 모듈
250kVA 인버터 구현
"""
from dataclasses import dataclass
from typing import Optional
from solar_pv_generator import SolarPVGenerator, ControlMode


@dataclass
class InverterMonitoring:
    """인버터 모니터링 데이터"""
    id: str
    input_voltage: float  # 입력 전압 (DC, V)
    input_current: float  # 입력 전류 (DC, A)
    input_power: float  # 입력 전력 (DC, kW)
    output_voltage: float  # 출력 전압 (AC, V)
    output_current: float  # 출력 전류 (AC, A)
    active_power: float  # 유효전력 P (AC, kW)
    reactive_power: float  # 무효전력 Q (AC, kVar)
    power_factor: float  # 역률
    efficiency: float  # 효율 (%)
    frequency: float  # 주파수 (Hz)


class Inverter:
    """인버터 클래스 (250kVA)"""
    
    def __init__(self, inverter_id: str, rated_capacity_kva: float = 250.0):
        """
        Args:
            inverter_id: 인버터 ID
            rated_capacity_kva: 정격 용량 (kVA)
        """
        self.inverter_id = inverter_id
        self.rated_capacity_kva = rated_capacity_kva
        self.rated_capacity_kw = rated_capacity_kva * 0.9  # 일반적인 역률 0.9 가정
        
        # 상태
        self.is_on = False
        self.pv_generator: Optional[SolarPVGenerator] = None
        
        # 시뮬레이션 파라미터
        self._efficiency = 0.97  # 인버터 효율 (97%)
        self._output_voltage = 380.0  # 출력 전압 (AC, V) - 3상 기준
        self._frequency = 60.0  # 주파수 (Hz)
        
        # 모니터링 데이터
        self._input_voltage = 0.0
        self._input_current = 0.0
        self._input_power = 0.0
        self._output_current = 0.0
        self._active_power = 0.0
        self._reactive_power = 0.0
        
    def connect_pv_generator(self, pv_generator: SolarPVGenerator):
        """태양광 발전기 연결"""
        self.pv_generator = pv_generator
        print(f"[{self.inverter_id}] 태양광 발전기 연결: {pv_generator.generator_id}")
        
    def turn_on(self):
        """인버터 ON"""
        self.is_on = True
        if self.pv_generator:
            self.pv_generator.turn_on()
        print(f"[{self.inverter_id}] 인버터 ON")
        
    def turn_off(self):
        """인버터 OFF"""
        self.is_on = False
        if self.pv_generator:
            self.pv_generator.turn_off()
        self._reset_outputs()
        print(f"[{self.inverter_id}] 인버터 OFF")
        
    def _reset_outputs(self):
        """출력 초기화"""
        self._input_voltage = 0.0
        self._input_current = 0.0
        self._input_power = 0.0
        self._output_current = 0.0
        self._active_power = 0.0
        self._reactive_power = 0.0
        
    def set_control_mode(self, mode: ControlMode):
        """제어 모드 설정 (PV 발전기에 전달)"""
        if self.pv_generator:
            self.pv_generator.set_control_mode(mode)
            
    def set_p_control_percent(self, percent: float):
        """P 제어 출력 비율 설정 (PV 발전기에 전달)"""
        if self.pv_generator:
            self.pv_generator.set_p_control_percent(percent)
            
    def update(self):
        """인버터 상태 업데이트 (주기적으로 호출)"""
        if not self.is_on:
            self._reset_outputs()
            return
            
        if not self.pv_generator:
            self._reset_outputs()
            return
            
        # PV 발전기 상태 업데이트
        self.pv_generator.update()
        pv_monitoring = self.pv_generator.get_monitoring()
        
        # 입력 (DC) - PV 발전기에서 받음
        self._input_voltage = pv_monitoring.voltage
        self._input_current = pv_monitoring.current
        self._input_power = pv_monitoring.active_power
        
        # 출력 (AC) - 인버터 변환
        # 효율 고려
        output_power_dc = self._input_power * self._efficiency
        
        # 정격 용량 제한
        max_output_power = min(output_power_dc, self.rated_capacity_kw)
        self._active_power = max_output_power
        self._reactive_power = 0.0  # 간단화: 무효전력 0
        
        # 출력 전류 계산 (3상 기준)
        if self._output_voltage > 0:
            # P = sqrt(3) * V * I * cos(phi)
            # cos(phi) = 1 (역률 1.0 가정)
            self._output_current = (self._active_power * 1000.0) / (1.732 * self._output_voltage)
        else:
            self._output_current = 0.0
            
    def get_monitoring(self) -> InverterMonitoring:
        """모니터링 데이터 반환"""
        # 역률 계산
        apparent_power = (self._active_power ** 2 + self._reactive_power ** 2) ** 0.5
        if apparent_power > 0:
            power_factor = self._active_power / apparent_power
        else:
            power_factor = 0.0
            
        # 효율 계산
        if self._input_power > 0:
            efficiency = (self._active_power / self._input_power) * 100.0
        else:
            efficiency = 0.0
            
        return InverterMonitoring(
            id=self.inverter_id,
            input_voltage=self._input_voltage,
            input_current=self._input_current,
            input_power=self._input_power,
            output_voltage=self._output_voltage,
            output_current=self._output_current,
            active_power=self._active_power,
            reactive_power=self._reactive_power,
            power_factor=power_factor,
            efficiency=efficiency,
            frequency=self._frequency
        )
        
    def get_status(self) -> dict:
        """현재 상태 정보 반환"""
        monitoring = self.get_monitoring()
        return {
            "id": self.inverter_id,
            "is_on": self.is_on,
            "rated_capacity_kva": self.rated_capacity_kva,
            "pv_generator_id": self.pv_generator.generator_id if self.pv_generator else None,
            "monitoring": {
                "input_voltage": monitoring.input_voltage,
                "input_current": monitoring.input_current,
                "input_power": monitoring.input_power,
                "output_voltage": monitoring.output_voltage,
                "output_current": monitoring.output_current,
                "active_power": monitoring.active_power,
                "reactive_power": monitoring.reactive_power,
                "power_factor": monitoring.power_factor,
                "efficiency": monitoring.efficiency,
                "frequency": monitoring.frequency
            }
        }

