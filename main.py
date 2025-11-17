"""
태양광 인버터 시뮬레이터 메인 프로그램
"""
import time
from power_plant import PowerPlant
from modbus_rtu_manager import ModbusRTUManager
from config import SYSTEM_CONFIG
from solar_pv_generator import ControlMode


def main():
    """메인 함수"""
    print("=" * 60)
    print("태양광 인버터 시뮬레이터 v2.0")
    print("=" * 60)
    
    # 발전소 생성
    plant = PowerPlant(
        plant_id=SYSTEM_CONFIG["plant_id"],
        total_capacity_mva=SYSTEM_CONFIG["total_capacity_mva"]
    )
    
    # Modbus RTU 서버 관리자 생성
    modbus_manager = ModbusRTUManager(
        power_plant=plant,
        port=SYSTEM_CONFIG["modbus"].get("port", "COM1"),
        baudrate=SYSTEM_CONFIG["modbus"]["baudrate"],
        parity=SYSTEM_CONFIG["modbus"]["parity"],
        stopbits=SYSTEM_CONFIG["modbus"]["stopbits"],
        bytesize=SYSTEM_CONFIG["modbus"]["bytesize"],
        base_slave_id=SYSTEM_CONFIG["modbus"]["slave_id"]
    )
    
    # 시뮬레이션 시작
    print("\n발전소 초기화 완료")
    print(f"- 총 용량: {SYSTEM_CONFIG['total_capacity_mva']} MVA")
    print(f"- 인버터 수: {SYSTEM_CONFIG['num_inverters']}대")
    print(f"- 인버터 용량: {SYSTEM_CONFIG['inverter_capacity_kva']} kVA")
    
    # 발전소 ON
    plant.turn_on_all()
    plant.set_irradiance_all(1000.0)  # 일사량 1000 W/m²
    plant.set_temperature_all(25.0)  # 온도 25°C
    
    # Modbus RTU 서버 시작
    try:
        modbus_manager.start_all()
    except Exception as e:
        print(f"Modbus RTU 서버 시작 오류: {e}")
        print("시리얼 포트가 없거나 사용 중일 수 있습니다.")
        print("시뮬레이션은 계속 진행되지만 Modbus 통신은 사용할 수 없습니다.")
    
    print("\n시뮬레이션 시작... (Ctrl+C로 종료)")
    print("-" * 60)
    
    try:
        while True:
            # 발전소 상태 업데이트
            plant.update()
            
            # Modbus 레지스터 업데이트
            modbus_manager.update_all_registers()
            
            # 상태 출력 (5초마다)
            if int(time.time()) % 5 == 0:
                total_power = plant.get_total_power()
                print(f"\n[시간: {time.strftime('%H:%M:%S')}]")
                print(f"전체 발전량: {total_power['total_active_power_kw']:.2f} kW")
                print(f"이용률: {total_power['utilization_percent']:.2f}%")
                
                # 각 인버터 상태
                for i, inverter in enumerate(plant.inverters):
                    inv_monitoring = inverter.get_monitoring()
                    print(f"  인버터 {i+1}: {inv_monitoring.active_power:.2f} kW "
                          f"(효율: {inv_monitoring.efficiency:.1f}%)")
            
            time.sleep(0.1)  # 100ms 간격 업데이트
            
    except KeyboardInterrupt:
        print("\n\n시뮬레이션 종료")
        modbus_manager.stop_all()
        plant.turn_off_all()


if __name__ == "__main__":
    main()

