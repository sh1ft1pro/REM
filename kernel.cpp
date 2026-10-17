#include <iostream>
#include <string>
#include <fstream>
#include <thread>
#include <chrono>
//#include "varibles.h"
//#include "functions.h"

/*
Ядро запускаем после браузера во избежании проблем с совместимостью.
*/

using namespace std;

/*
Система режимов терминала
main> - доступ к основному режиму (0)
core> - доступ к элементам ядра (1)
browser> - доступ к браузеру (2)
buffersys> - доступ к системе буфера (3)
sendersys> - доступ к системе отправки (4)
robot> - доступ к роботу (5)
pult> - доступ к пульту (6)
test> - тестовый режим системы (7)
*/  

// Системные переменные
bool system_is_working = true;
int work_mode = 7;

string input_console_data = "f";
string last_command = "";
// переменные



int main(){
    ofstream start_kernel_message("buffer_console_output.txt");

    start_kernel_message << "========================== REM (Robot Emulator MODIFIED) =========================" << endl;
    start_kernel_message << "============== REI (Robot emulator interface) version: v4.0.0 ====================" << endl;
    start_kernel_message << "============================== Core: v1.0.0-alpha.1 ==============================" << endl;
    start_kernel_message << "======================== Browser (Core-dependent): v1.0.0-alpha.1 ================" << endl;
    start_kernel_message << "========================= Buffer system: v1.0.0-alpha.1 ========================" << endl;
    start_kernel_message << "========================= Sender system: v1.0.0-alpha.1 ========================" << endl;
    start_kernel_message << "==================== Date of creation: September–Desember 2026 ====================" << endl;
    start_kernel_message << "===================== Contact information: daniel8.8@mail.ru =====================" << endl << endl << endl << endl;
    start_kernel_message.close();

    if (work_mode == 0){ // основной режим
            ofstream work_mode_0("work_mode.txt");
            work_mode_0 << "main";
            work_mode_0.close();
    }
    else if (work_mode == 1){ // ядро режим
        ofstream work_mode_1("work_mode.txt");
        work_mode_1 << "core";
        work_mode_1.close();
    }
    else if (work_mode == 2){ // браузер режим
        ofstream work_mode_2("work_mode.txt");
        work_mode_2 << "browser";
        work_mode_2.close();
    }
    else if (work_mode == 3){ // буфер режим
        ofstream work_mode_3("work_mode.txt");
        work_mode_3 << "buffersys";
        work_mode_3.close();
    }
    else if (work_mode == 4){ // отпрака режим
        ofstream work_mode_4("work_mode.txt");
        work_mode_4 << "sendersys";
        work_mode_4.close();
    }
    else if (work_mode == 5){ // робот режим
        ofstream work_mode_5("work_mode.txt");
        work_mode_5 << "robot";
        work_mode_5.close();
    }
    else if (work_mode == 6){ // пульт режим
        ofstream work_mode_6("work_mode.txt");
        work_mode_6 << "pult";
        work_mode_6.close();
    }
    else if (work_mode == 7){ // тест режим
        ofstream work_mode_7("work_mode.txt");
        work_mode_7 << "test";
        work_mode_7.close();
    }
    

    while(system_is_working == true){
        //cout << "Программа работает" << endl;
    string command;
    bool got_command = false;

    {
        ifstream input_file("buffer_console_input.txt");
        if (getline(input_file, command)) {
            got_command = true;
            //cout << "[DEBUG] прочитал: '" << command << "'" << endl;
        }
    }

    if (got_command) {
        ofstream clear_input("buffer_console_input.txt", ios::trunc);
        clear_input.close();
        //cout << "[DEBUG] файл очищен" << endl;

        if (command == "rem_sys"){
            //cout << "[DEBUG] команда rem_sys, пишу арт" << endl;
            ofstream rem_sys_command_output("buffer_console_output.txt");
            rem_sys_command_output << "       ______________________________________\n";
            rem_sys_command_output << "     /  ##################################  /\n";
            rem_sys_command_output << "    /   ##  ######    ######               /\n";
            rem_sys_command_output << "   /    ##  ##   ##   ##                   /\n";
            rem_sys_command_output << "  /     ##  ######    ######              /\n";
            rem_sys_command_output << " /      ##  ##  ##    ##                  /\n";
            rem_sys_command_output << "/       ##  ##   ##   ######              /\n";
            rem_sys_command_output << "\\       #################################/\n";
            rem_sys_command_output << " \\     / M O D I F I C A T E D          /\n";
            rem_sys_command_output << "  \\___/________________________________/\n";
            rem_sys_command_output.close();

            last_command = command;
            command = "";
        }
        else{
            ofstream CONMAND_NOT_FOUND_output("buffer_console_output.txt");
            CONMAND_NOT_FOUND_output << "Command not found: " << command << "\n";
            CONMAND_NOT_FOUND_output << "Check that the input is correct.\n";
            CONMAND_NOT_FOUND_output.close();

            last_command = command;
            command = "";
        }
    }

    this_thread::sleep_for(chrono::milliseconds(100));
}

    return 0;
}