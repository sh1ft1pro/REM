import time
import serial
import serial.tools.list_ports

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    
    print("=== Поиск Arduino ===")
    for p in ports:
        print(f" - {p.device} ({p.description})")
        
    for p in ports:
        desc = p.description.lower()
        # Ищем Ардуино или популярные китайские чипы (CH340/CH341)
        if "arduino" in desc or "ch340" in desc or "ch341" in desc or "usb-serial" in desc:
            return p.device
    return None

def build_message(start_char, address, func_code, data):
    payload = f"{address}{func_code}{data}"
    total = sum(bytes.fromhex(payload))
    lrc = ((total ^ 0xFF) + 1) & 0xFF
    lrc_hex = f"{lrc:02X}"
    result = f"{start_char}{payload}{lrc_hex}\r\n"
    return result

def main():
    # 1. Ищем порт автоматически
    port = find_arduino_port()

    if not port:
        print("\n[ОШИБКА] Arduino не найдена! Проверь кабель.")
        # Если автоматика не справилась, можно спросить вручную:
        # port = input("Введи порт вручную (например, COM3): ")
        return

    print(f"\n[OK] Найдена Arduino на порту: {port}")

    try:
        print(f"Подключение к {port}...")
        ser = serial.Serial(port, 9600, timeout=2) 
        
        print("Ждем 2 секунды (перезагрузка Arduino)...")
        time.sleep(2) 
        ser.reset_input_buffer() 
        
        result = build_message(":", "01", "07", "0A")
        print(f"Отправка: {result.strip()}")
        
        ser.write(result.encode('ascii'))
        
        print("Ждем ответ...")
        response = ser.readline().decode('ascii', errors='ignore').strip()
        
        if response:
            print(f"=== УСПЕХ! Ответ: {response} ===")
        else:
            print("=== ТАЙМАУТ. ===")
            
        ser.close()
        
    except serial.SerialException:
        print(f"\n[ОШИБКА] Порт {port} занят. Закрой Монитор порта в Arduino IDE!")
    except Exception as e:
        print(f"\n[ОШИБКА] {e}")

if __name__ == "__main__":
    main()