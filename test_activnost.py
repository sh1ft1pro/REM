from pypresence import Presence
import time

CLIENT_ID = "1574126133375537152" # Вставьте скопированный ID сюда

RPC = Presence(CLIENT_ID)
RPC.connect()

RPC.update(
    details="Запуск эмулятора",
    state="Ожидание команд",
    large_image="logo", # Ваш загруженный ключ
    large_text="Robot emulator MODIFICATED"
)

time.sleep(30) # Держим статус 30 секунд для проверки
RPC.close()
