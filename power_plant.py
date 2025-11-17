"""
태양광 발전소 통합 제어 모듈
1MVA 발전소, 4대 인버터 (각 250kVA) 통합 제어
"""
from typing import List, Dict
from solar_pv_generator import SolarPVGenerator, ControlMode
from inverter import Inverter


class PowerPlant:
    """태양광 발전소 통합 제어 클래스"""
    
    def __init__(self, plant_id: str = "PLANT_01", total_capacity_mva: float = 1.0):
        """
        Args:
            plant_id: 발전소 ID
            total_capacity_mva: 총 정격 용량 (MVA)
        """
        self.plant_id = plant_id
        self.total_capacity_mva = total_capacity_mva
        self.total_capacity_kw = total_capacity_mva * 1000.0 * 0.9  # 역률 0.9 가정
        
        # 인버터 설정
        self.inverter_capacity_kva = 250.0
        self.num_inverters = 4
        
        # 인버터 및 PV 발전기 리스트
        self.inverters: List[Inverter] = []
        self.pv_generators: List[SolarPVGenerator] = []
        
        # 초기화
        self._initialize_components()
        
    def _initialize_components(self):
        """컴포넌트 초기화"""
        # PV 발전기 생성 (각 인버터당 1개)
        # 총 1MVA를 4대로 나누면 각각 250kVA
        pv_capacity_per_unit = (self.total_capacity_kw / self.num_inverters)
        
        for i in range(self.num_inverters):
            # PV 발전기 생성
            pv_id = f"PV_{self.plant_id}_{i+1:02d}"
            pv_gen = SolarPVGenerator(
                generator_id=pv_id,
                rated_capacity_kw=pv_capacity_per_unit
            )
            self.pv_generators.append(pv_gen)
            
            # 인버터 생성
            inv_id = f"INV_{self.plant_id}_{i+1:02d}"
            inverter = Inverter(
                inverter_id=inv_id,
                rated_capacity_kva=self.inverter_capacity_kva
            )
            
            # PV 발전기 연결
            inverter.connect_pv_generator(pv_gen)
            self.inverters.append(inverter)
            
        print(f"[{self.plant_id}] 발전소 초기화 완료: {self.num_inverters}대 인버터")
        
    def turn_on_all(self):
        """모든 인버터 ON"""
        for inverter in self.inverters:
            inverter.turn_on()
        print(f"[{self.plant_id}] 모든 인버터 ON")
        
    def turn_off_all(self):
        """모든 인버터 OFF"""
        for inverter in self.inverters:
            inverter.turn_off()
        print(f"[{self.plant_id}] 모든 인버터 OFF")
        
    def turn_on_inverter(self, inverter_index: int):
        """특정 인버터 ON (0-based index)"""
        if 0 <= inverter_index < len(self.inverters):
            self.inverters[inverter_index].turn_on()
        else:
            raise ValueError(f"인버터 인덱스 범위 오류: {inverter_index}")
            
    def turn_off_inverter(self, inverter_index: int):
        """특정 인버터 OFF (0-based index)"""
        if 0 <= inverter_index < len(self.inverters):
            self.inverters[inverter_index].turn_off()
        else:
            raise ValueError(f"인버터 인덱스 범위 오류: {inverter_index}")
            
    def set_control_mode_all(self, mode: ControlMode):
        """모든 인버터 제어 모드 설정"""
        for inverter in self.inverters:
            inverter.set_control_mode(mode)
        print(f"[{self.plant_id}] 모든 인버터 제어 모드: {mode.value}")
        
    def set_control_mode_inverter(self, inverter_index: int, mode: ControlMode):
        """특정 인버터 제어 모드 설정"""
        if 0 <= inverter_index < len(self.inverters):
            self.inverters[inverter_index].set_control_mode(mode)
        else:
            raise ValueError(f"인버터 인덱스 범위 오류: {inverter_index}")
            
    def set_p_control_percent_all(self, percent: float):
        """모든 인버터 P 제어 출력 비율 설정"""
        for inverter in self.inverters:
            inverter.set_p_control_percent(percent)
        print(f"[{self.plant_id}] 모든 인버터 P 제어 출력 비율: {percent}%")
        
    def set_p_control_percent_inverter(self, inverter_index: int, percent: float):
        """특정 인버터 P 제어 출력 비율 설정"""
        if 0 <= inverter_index < len(self.inverters):
            self.inverters[inverter_index].set_p_control_percent(percent)
        else:
            raise ValueError(f"인버터 인덱스 범위 오류: {inverter_index}")
            
    def set_irradiance_all(self, irradiance: float):
        """모든 PV 발전기 일사량 설정"""
        for pv_gen in self.pv_generators:
            pv_gen.set_irradiance(irradiance)
            
    def set_temperature_all(self, temperature: float):
        """모든 PV 발전기 온도 설정"""
        for pv_gen in self.pv_generators:
            pv_gen.set_temperature(temperature)
            
    def update(self):
        """발전소 상태 업데이트 (주기적으로 호출)"""
        for inverter in self.inverters:
            inverter.update()
            
    def get_total_power(self) -> Dict[str, float]:
        """전체 발전량 집계"""
        total_active_power = 0.0
        total_reactive_power = 0.0
        total_input_power = 0.0
        
        for inverter in self.inverters:
            monitoring = inverter.get_monitoring()
            total_active_power += monitoring.active_power
            total_reactive_power += monitoring.reactive_power
            total_input_power += monitoring.input_power
            
        apparent_power = (total_active_power ** 2 + total_reactive_power ** 2) ** 0.5
        
        return {
            "total_active_power_kw": total_active_power,
            "total_reactive_power_kvar": total_reactive_power,
            "total_apparent_power_kva": apparent_power,
            "total_input_power_kw": total_input_power,
            "total_capacity_kw": self.total_capacity_kw,
            "utilization_percent": (total_active_power / self.total_capacity_kw * 100.0) if self.total_capacity_kw > 0 else 0.0
        }
        
    def get_all_status(self) -> Dict:
        """전체 발전소 상태 정보 반환"""
        inverter_statuses = []
        for inverter in self.inverters:
            inverter_statuses.append(inverter.get_status())
            
        pv_statuses = []
        for pv_gen in self.pv_generators:
            pv_statuses.append(pv_gen.get_status())
            
        total_power = self.get_total_power()
        
        return {
            "plant_id": self.plant_id,
            "total_capacity_mva": self.total_capacity_mva,
            "num_inverters": self.num_inverters,
            "inverter_capacity_kva": self.inverter_capacity_kva,
            "total_power": total_power,
            "inverters": inverter_statuses,
            "pv_generators": pv_statuses
        }

