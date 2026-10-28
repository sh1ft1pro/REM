import sys
import time
import serial
import serial.tools.list_ports
#from tkinter import messagebox

ports = list(serial.tools.list_ports.comports())
number_of_ports = len(ports)
#print(number_of_ports)
counter = 0

console_output_file_name = "buffer_console_output.txt"

print("programm started")
# Вместо старого цикла делаем так:

ports = list(serial.tools.list_ports.comports())
found_port = None

for p in ports:
    # Ищем именно ACM (это виртуальный COM-порт Arduino)
    if "ACM" in p.device:
        found_port = p.device
        print(f"Найдена плата: {found_port} ({p.description})")
        break

if found_port is None:
    print("Плата не найдена!")
    sys.exit()
    
# Теперь можно подключаться
SerialObj = serial.Serial(found_port, 9600, timeout=2)

SerialObj = serial.Serial(found_port)
SerialObj.baudrate = 9600
SerialObj.bytesize = 8
SerialObj.parity = 'N'
SerialObj.stopbits = 1

flag_work = True

print("3")

while flag_work:
    print("4")
    
    # Отправляем сигнал
    SerialObj.write(b"1\n") 
    print("Отправлено: 1")

    try:
        # Пытаемся прочитать ответ
        raw_signal = SerialObj.readline()
        
        # Если пришла пустая строка (таймаут 2 секунды), значит Ардуино ничего не ответило
        if raw_signal:
            signal_from_ARDUINO = raw_signal.decode('utf-8', errors='ignore').strip()
            print(f"Сигнал получен: {signal_from_ARDUINO}")
            
            # Записываем в файл только если реально что-то пришло
            with open("pult_sender_sys_output.txt", "w", encoding="utf-8") as file:
                file.write(signal_from_ARDUINO + "\n")
            print("Signal!")
        else:
            print("Ардуино не ответило (таймаут). Ждем дальше...")

    except Exception as e:
        # На случай, если шнур выдернут или порт сломался
        print(f"Ошибка при чтении с порта: {e}")
        break # Выходим из цикла, чтобы не спамить ошибками

    # Небольшая пауза, чтобы не грузить процессор на 100%
    time.sleep(0.1)

print("5")
SerialObj.close()