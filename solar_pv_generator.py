"""
태양광 발전기 모듈
On/OFF, MPPT 제어/P 제어, 모니터링 기능 제공
"""
import time
import random
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class ControlMode(Enum):
    """제어 모드"""
    MPPT = "MPPT"  # 최대 전력점 추적
    P_CONTROL = "P_CONTROL"  # 출력 제어 (%)


@dataclass
class PVMonitoring:
    """태양광 발전기 모니터링 데이터"""
    id: str
    power_generation: float  # 발전량 (kW)
    voltage: float  # 전압 (V)
    current: float  # 전류 (A)
    active_power: float  # 유효전력 P (kW)
    reactive_power: float  # 무효전력 Q (kVar)
    power_factor: float  # 역률


class SolarPVGenerator:
    """태양광 발전기 클래스"""
    
    def __init__(self, generator_id: str, rated_capacity_kw: float = 1000.0):
        """
        Args:
            generator_id: 발전기 ID
            rated_capacity_kw: 정격 용량 (kW)
        """
        self.generator_id = generator_id
        self.rated_capacity_kw = rated_capacity_kw
        
        # 상태
        self.is_on = False
        self.control_mode = ControlMode.MPPT
        self.p_control_percent = 100.0  # P 제어 시 출력 비율 (%)
        
        # 시뮬레이션 파라미터
        self._base_irradiance = 1000.0  # 기준 일사량 (W/m²)
        self._irradiance = 1000.0  # 현재 일사량 (W/m²) - 진동 포함
        self._base_temperature = 25.0  # 기준 온도 (°C)
        self._temperature = 25.0  # 현재 온도 (°C) - 진동 포함
        
        # 모니터링 데이터
        self._voltage = 0.0
        self._current = 0.0
        self._active_power = 0.0
        self._reactive_power = 0.0
        
    def turn_on(self):
        """발전기 ON"""
        self.is_on = True
        print(f"[{self.generator_id}] 발전기 ON")
        
    def turn_off(self):
        """발전기 OFF"""
        self.is_on = False
        self._voltage = 0.0
        self._current = 0.0
        self._active_power = 0.0
        self._reactive_power = 0.0
        print(f"[{self.generator_id}] 발전기 OFF")
        
    def set_control_mode(self, mode: ControlMode):
        """제어 모드 설정"""
        self.control_mode = mode
        print(f"[{self.generator_id}] 제어 모드: {mode.value}")
        
    def set_p_control_percent(self, percent: float):
        """
        P 제어 출력 비율 설정
        
        Args:
            percent: 출력 비율 (0.0 ~ 100.0)
        """
        if not 0.0 <= percent <= 100.0:
            raise ValueError("출력 비율은 0.0 ~ 100.0 사이여야 합니다.")
        self.p_control_percent = percent
        print(f"[{self.generator_id}] P 제어 출력 비율: {percent}%")
        
    def set_irradiance(self, irradiance: float):
        """일사량 설정 (시뮬레이션용) - 기준값 설정"""
        self._base_irradiance = max(0.0, irradiance)
        self._irradiance = self._base_irradiance
        
    def set_temperature(self, temperature: float):
        """온도 설정 (시뮬레이션용) - 기준값 설정"""
        self._base_temperature = temperature
        self._temperature = self._base_temperature
        
    def _apply_variation(self):
        """일사량과 온도에 진동 적용 (+-1%)"""
        # 일사량 진동: +-1%
        irradiance_variation = random.uniform(-0.01, 0.01)
        self._irradiance = max(0.0, self._base_irradiance * (1.0 + irradiance_variation))
        
        # 온도 진동: +-1%
        temperature_variation = random.uniform(-0.01, 0.01)
        self._temperature = self._base_temperature * (1.0 + temperature_variation)
        
    def _calculate_mppt_power(self) -> float:
        """MPPT 모드에서 최대 전력 계산"""
        # 간단한 MPPT 시뮬레이션
        # 실제로는 더 복잡한 알고리즘이 필요하지만, 시뮬레이션을 위해 단순화
        base_power = (self._irradiance / 1000.0) * self.rated_capacity_kw
        # 온도 보정 (온도가 높을수록 출력 감소)
        temp_coefficient = 1.0 - (self._temperature - 25.0) * 0.004
        mppt_power = base_power * max(0.0, temp_coefficient)
        return min(mppt_power, self.rated_capacity_kw)
        
    def _calculate_p_control_power(self) -> float:
        """P 제어 모드에서 출력 계산"""
        mppt_power = self._calculate_mppt_power()
        return mppt_power * (self.p_control_percent / 100.0)
        
    def update(self):
        """발전기 상태 업데이트 (주기적으로 호출)"""
        if not self.is_on:
            self._voltage = 0.0
            self._current = 0.0
            self._active_power = 0.0
            self._reactive_power = 0.0
            return
            
        # 일사량과 온도에 진동 적용
        self._apply_variation()
            
        # 제어 모드에 따른 출력 계산
        if self.control_mode == ControlMode.MPPT:
            target_power = self._calculate_mppt_power()
        else:  # P_CONTROL
            target_power = self._calculate_p_control_power()
            
        # 전압, 전류 계산 (간단한 시뮬레이션)
        # 일반적인 태양광 시스템: DC 전압 600~1000V 범위
        self._voltage = 800.0 + (self._irradiance / 1000.0 - 1.0) * 100.0
        if self._voltage > 0:
            self._current = (target_power * 1000.0) / self._voltage  # A
        else:
            self._current = 0.0
            
        self._active_power = target_power  # kW
        self._reactive_power = 0.0  # 태양광은 일반적으로 유효전력만 (간단화)
        
    def get_monitoring(self) -> PVMonitoring:
        """모니터링 데이터 반환"""
        # 역률 계산 (P / sqrt(P^2 + Q^2))
        if self._active_power == 0 and self._reactive_power == 0:
            power_factor = 0.0
        else:
            apparent_power = (self._active_power ** 2 + self._reactive_power ** 2) ** 0.5
            if apparent_power > 0:
                power_factor = self._active_power / apparent_power
            else:
                power_factor = 0.0
                
        return PVMonitoring(
            id=self.generator_id,
            power_generation=self._active_power,  # 발전량 = 유효전력
            voltage=self._voltage,
            current=self._current,
            active_power=self._active_power,
            reactive_power=self._reactive_power,
            power_factor=power_factor
        )
        
    def get_status(self) -> dict:
        """현재 상태 정보 반환"""
        monitoring = self.get_monitoring()
        return {
            "id": self.generator_id,
            "is_on": self.is_on,
            "control_mode": self.control_mode.value,
            "p_control_percent": self.p_control_percent,
            "rated_capacity_kw": self.rated_capacity_kw,
            "monitoring": {
                "power_generation": monitoring.power_generation,
                "voltage": monitoring.voltage,
                "current": monitoring.current,
                "active_power": monitoring.active_power,
                "reactive_power": monitoring.reactive_power,
                "power_factor": monitoring.power_factor
            }
        }

