#include <iostream>
#include <string>
#include <fstream>
#include <thread>
#include <chrono>
//#include "varibles.h"
//#include "functions.h"

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
int work_mode = 0;

string input_console_data = "f";
string last_command = "";
// переменные


// ===============================================================
// МОДУЛЬ: enum + command_code()
// ===============================================================
enum CommandCode {
    CMD_UNKNOWN   = 0,
    CMD_REM_SYS   = 1,
    CMD_MODE_TEST = 2
};

int command_code(const string& cmd) {
    if (cmd == "rem_sys")   return CMD_REM_SYS;
    if (cmd == "mode_test") return CMD_MODE_TEST;
    return CMD_UNKNOWN;
}


// ===============================================================
// ОБРАБОТЧИКИ КОМАНД (вынесены из switch)
// ===============================================================

// rem_sys — рисует арт
void handle_rem_sys() {
    ofstream out("buffer_console_output.txt");
    out << "       ______________________________________\n";
    out << "     /  ##################################  /\n";
    out << "    /   ##  ######    ######               /\n";
    out << "   /    ##  ##   ##   ##                   /\n";
    out << "  /     ##  ######    ######              /\n";
    out << " /      ##  ##  ##    ##                  /\n";
    out << "/       ##  ##   ##   ######              /\n";
    out << "\\       #################################/\n";
    out << " \\     / M O D I F I C A T E D          /\n";
    out << "  \\___/________________________________/\n";
}

// mode_test — переключает режим на test
void handle_mode_test() {
    work_mode = 7;
    ofstream wm("work_mode.txt");
    wm << "test";
    wm.close();

    ofstream out("buffer_console_output.txt");
    out << "Mode was changed to TEST\n";
}

// неизвестная команда
void handle_unknown(const string& command) {
    ofstream out("buffer_console_output.txt");
    out << "Command not found: " << command << "\n";
    out << "Check that the input is correct.\n";
}


// ===============================================================
// main
// ===============================================================
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

    // --- switch по work_mode ---
    switch (work_mode) {
        case 0: { ofstream f("work_mode.txt"); f << "main";      break; }
        case 1: { ofstream f("work_mode.txt"); f << "core";      break; }
        case 2: { ofstream f("work_mode.txt"); f << "browser";   break; }
        case 3: { ofstream f("work_mode.txt"); f << "buffersys"; break; }
        case 4: { ofstream f("work_mode.txt"); f << "sendersys"; break; }
        case 5: { ofstream f("work_mode.txt"); f << "robot";     break; }
        case 6: { ofstream f("work_mode.txt"); f << "pult";      break; }
        case 7: { ofstream f("work_mode.txt"); f << "test";      break; }
    }

    while(system_is_working == true){
        string command;
        bool got_command = false;

        {
            ifstream input_file("buffer_console_input.txt");
            if (getline(input_file, command)) {
                got_command = true;
            }
        }

        if (got_command) {
            ofstream clear_input("buffer_console_input.txt", ios::trunc);
            clear_input.close();

            // --- switch по коду команды: 6 строк ---
            switch (command_code(command)) {
                case CMD_REM_SYS:   handle_rem_sys();        break;
                case CMD_MODE_TEST: handle_mode_test();      break;
                default:            handle_unknown(command); break;
            }

            last_command = command;
            command = "";
        }

        this_thread::sleep_for(chrono::milliseconds(100));
    }

    return 0;
}