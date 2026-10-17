.PHONY: all compile_kernel run_kernel compile_browser run_browser run_python_virtual_interface run_sender_system

all: run_sender_system

compile_kernel:
	g++ kernel.cpp -o kernel

run_kernel: compile_kernel
	./kernel

compile_browser: run_kernel
	g++ browser.cpp -o browser

run_browser: compile_browser
	./browser

run_python_virtual_interface: run_browser
	python3 python_virtual_inteface.py

run_sender_system: run_python_virtual_interface
	python3 sender_system.py