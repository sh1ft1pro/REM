import sys
import time
import serial
import serial.tools.list_ports
from tkinter import messagebox

ports = list(serial.tools.list_ports.comports())
number_of_ports = len(ports)
print(number_of_ports)
counter = 0

for p in ports:
    if "Arduino" in p.description:
        with open("pult_sender_sys_output.txt", "w", encoding="utf-8") as file:
            file.write(f"Привет!\nArduino Found!\nConnecting...\n{p.device}")
        break
    counter += 1

if (counter == number_of_ports):
   messagebox.showinfo('Ошибка', 'Плата Arduino не найдена!')
   sys.exit()

# настройка порта
ser_port = p.device

SerialObj = serial.Serial(ser_port)
SerialObj.baudrate = 9600
SerialObj.bytesize = 8
SerialObj.parity = 'N'
SerialObj.stopbits = 1

flag_work = True

while flag_work:
    x_read = SerialObj.readline().decode('utf-8').strip()
    y_read = SerialObj.readline().decode('utf-8').strip()
    left = SerialObj.readline().decode('utf-8').strip()
    right = SerialObj.readline().decode('utf-8').strip()

    with open("pult_sender_sys_output.txt", "w", encoding="utf-8") as file:
        file.write(x_read + "\n")
        file.write(y_read + "\n")
        file.write(left + "\n")
        file.write(right + "\n")

SerialObj.close()