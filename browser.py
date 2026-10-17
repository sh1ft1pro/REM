import sys
import time

console_input_data = ""
console_output_data = ""
programm_is_working = True
work_mode = "start"

#name_files
programm_works_file_name = "programm_is_working_flag.txt"
work_mode_file_name = "work_mode.txt"
console_output_file_name = "buffer_console_output.txt"
console_input_file_name = "buffer_console_input.txt"

output_wait_counter = 0

def is_file_empty(filename):
        with open(filename, "r") as f:
            content = f.read()
            return not content  # True, если пусто
def clear_file(filename):
    with open(filename, "w") as f:
        pass

while True:
    # checking is programm working
    with open(programm_works_file_name, "r") as work_flag_file:
        programm_is_working = work_flag_file.readline().strip()
    if not programm_is_working or programm_is_working != "1":
        break

    # main_work
    with open(work_mode_file_name, "r") as work_mode_file:
        if is_file_empty(console_output_file_name) == True:
            work_mode = work_mode_file.readline().strip()
            if is_file_empty(console_output_file_name) == True:
                console_input_data = input(f"{work_mode}> ")
                while console_input_data == "":
                    console_input_data = input(f"{work_mode}> ")           
                with open(console_input_file_name, "w") as console_input_file:
                    console_input_file.write(console_input_data + "\n") # лучше добавить \n
                
                # --- ВОТ ТУТ МЫ ЖДЕМ ОТВЕТА ОТ ЯДРА ---
                while is_file_empty(console_output_file_name):
                    time.sleep(0.05)
                    output_wait_counter += 1
                    if (output_wait_counter >= 15):
                        print("[!] Error: the kernel is not responding.")
                        output_wait_counter = 0
                        break
                        
                # --------------------------------------
                
            # (тут твой else можно убрать, потому что мы уже дождались ответа и он 100% есть)
            with open(console_output_file_name, "r") as console_output_file:
                console_output_data = console_output_file.read()
            clear_file(console_output_file_name)
            print(console_output_data, flush=True) # flush=True заставляет печатать сразу
            
        else:
            with open(console_output_file_name, "r") as console_output_file:
                console_output_data = console_output_file.read()
            clear_file(console_output_file_name)
            print(console_output_data, flush=True)
            
    time.sleep(0.05)
sys.exit()