#include <iostream>
#include <fstream>
#include <string>
using namespace std;

int main() {
    string console_input_data;
    string console_output_data;
    string programm_is_working;
    string work_mode = "start";

    while (true) {
        ifstream flag_file("programm_is_working_flag.txt");
        if (!getline(flag_file, programm_is_working) || programm_is_working != "1") {
            break;
        }

        ifstream mode_file("work_mode.txt"); // определение режима работы / вывод приглашения
        getline(mode_file, work_mode);
        cout << work_mode << ">";

        getline(cin, console_input_data); // чтение ввода
        ofstream input_file("buffer_console_input.txt");
        input_file << console_input_data;
        input_file.close();
        //cout << console_input_data << endl;

        ifstream output_file("buffer_console_output.txt");   // открыли на чтение
        while (getline(output_file, console_output_data)) {  // прочитали
            cout << console_output_data << endl;
        }
        ofstream clear_output("buffer_console_output.txt", ios::trunc); // ← а output_file ВСЁ ЕЩЁ ОТКРЫТ
        clear_output.close();
    }
    return 0;
}