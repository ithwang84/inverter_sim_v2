"""
태양광 인버터 시뮬레이터 테스트 스크립트
"""
from power_plant import PowerPlant
from solar_pv_generator import ControlMode
from modbus_rtu import ModbusRTUServer
from config import DEFAULT_REGISTER_MAPPING


def test_pv_generator():
    """PV 발전기 테스트"""
    print("\n=== PV 발전기 테스트 ===")
    
    from solar_pv_generator import SolarPVGenerator
    
    pv = SolarPVGenerator("PV_TEST_01", rated_capacity_kw=250.0)
    
    # OFF 상태
    print(f"초기 상태: {pv.get_status()}")
    
    # ON
    pv.turn_on()
    pv.set_irradiance(1000.0)
    pv.set_temperature(25.0)
    pv.update()
    
    monitoring = pv.get_monitoring()
    print(f"ON 상태 - 발전량: {monitoring.power_generation:.2f} kW")
    print(f"  전압: {monitoring.voltage:.2f} V")
    print(f"  전류: {monitoring.current:.2f} A")
    print(f"  역률: {monitoring.power_factor:.3f}")
    
    # MPPT 모드
    pv.set_control_mode(ControlMode.MPPT)
    pv.update()
    monitoring = pv.get_monitoring()
    print(f"MPPT 모드 - 발전량: {monitoring.power_generation:.2f} kW")
    
    # P 제어 모드
    pv.set_control_mode(ControlMode.P_CONTROL)
    pv.set_p_control_percent(50.0)
    pv.update()
    monitoring = pv.get_monitoring()
    print(f"P 제어 50% - 발전량: {monitoring.power_generation:.2f} kW")
    
    pv.turn_off()
    print("PV 발전기 테스트 완료\n")


def test_inverter():
    """인버터 테스트"""
    print("\n=== 인버터 테스트 ===")
    
    from inverter import Inverter
    from solar_pv_generator import SolarPVGenerator
    
    pv = SolarPVGenerator("PV_TEST_01", rated_capacity_kw=250.0)
    inverter = Inverter("INV_TEST_01", rated_capacity_kva=250.0)
    
    inverter.connect_pv_generator(pv)
    inverter.turn_on()
    
    pv.set_irradiance(1000.0)
    pv.set_temperature(25.0)
    
    inverter.update()
    
    monitoring = inverter.get_monitoring()
    print(f"입력 (DC): {monitoring.input_power:.2f} kW")
    print(f"출력 (AC): {monitoring.active_power:.2f} kW")
    print(f"효율: {monitoring.efficiency:.2f}%")
    print(f"출력 전압: {monitoring.output_voltage:.2f} V")
    print(f"출력 전류: {monitoring.output_current:.2f} A")
    
    inverter.turn_off()
    print("인버터 테스트 완료\n")


def test_power_plant():
    """발전소 통합 테스트"""
    print("\n=== 발전소 통합 테스트 ===")
    
    plant = PowerPlant("PLANT_TEST", total_capacity_mva=1.0)
    
    # 전체 ON
    plant.turn_on_all()
    plant.set_irradiance_all(1000.0)
    plant.set_temperature_all(25.0)
    
    plant.update()
    
    total_power = plant.get_total_power()
    print(f"전체 발전량: {total_power['total_active_power_kw']:.2f} kW")
    print(f"이용률: {total_power['utilization_percent']:.2f}%")
    
    # 제어 모드 변경
    print("\n제어 모드 변경 테스트:")
    plant.set_control_mode_all(ControlMode.P_CONTROL)
    plant.set_p_control_percent_all(75.0)
    plant.update()
    
    total_power = plant.get_total_power()
    print(f"P 제어 75% - 발전량: {total_power['total_active_power_kw']:.2f} kW")
    
    # 개별 인버터 제어
    print("\n개별 인버터 제어 테스트:")
    plant.set_p_control_percent_inverter(0, 50.0)
    plant.set_p_control_percent_inverter(1, 100.0)
    plant.update()
    
    for i, inverter in enumerate(plant.inverters):
        monitoring = inverter.get_monitoring()
        print(f"인버터 {i+1}: {monitoring.active_power:.2f} kW")
    
    plant.turn_off_all()
    print("발전소 테스트 완료\n")


def test_modbus_rtu():
    """Modbus RTU 테스트"""
    print("\n=== Modbus RTU 테스트 ===")
    
    server = ModbusRTUServer(
        slave_id=1,
        register_config={"register_mapping": DEFAULT_REGISTER_MAPPING}
    )
    
    # 레지스터 읽기/쓰기 테스트
    print("레지스터 읽기/쓰기 테스트:")
    
    # 홀딩 레지스터 쓰기
    server.write_single_register(0x0001, 1)  # On/Off
    server.write_single_register(0x0002, 0)  # MPPT 모드
    server.write_single_register(0x0003, 100)  # 100%
    
    # 홀딩 레지스터 읽기
    values = server.read_holding_registers(0x0001, 3)
    print(f"홀딩 레지스터 (0x0001-0x0003): {values}")
    
    # 입력 레지스터 쓰기 (시뮬레이션)
    server.input_registers[0x1002] = 2500  # 250.0 kW * 10
    server.input_registers[0x1003] = 8000  # 800.0 V * 10
    
    values = server.read_input_registers(0x1002, 2)
    print(f"입력 레지스터 (0x1002-0x1003): {values}")
    
    status = server.get_register_status()
    print(f"레지스터 상태: {len(status['holding_registers'])}개 홀딩 레지스터")
    print(f"  {len(status['input_registers'])}개 입력 레지스터")
    
    print("Modbus RTU 테스트 완료\n")


def main():
    """전체 테스트 실행"""
    print("=" * 60)
    print("태양광 인버터 시뮬레이터 테스트")
    print("=" * 60)
    
    test_pv_generator()
    test_inverter()
    test_power_plant()
    test_modbus_rtu()
    
    print("=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()

