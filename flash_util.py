import os
import subprocess
import threading
import time
import curses
import sys
import shutil

# Verifica se la cartella klipper/scripts esiste
if not os.path.exists("/home/pi/klipper/scripts"):
    print("Error: The directory '/home/pi/klipper/scripts' was not found. Ensure Klipper is installed correctly.")
    sys.exit(1)

sys.path.append("/home/pi/klipper/scripts")  # Aggiunge il percorso di flash_usb.py
import flash_usb as u

def list_serial_devices():
    try:
        result = subprocess.run(["ls", "/dev/serial/by-id/"], capture_output=True, text=True)
        serial_devices = result.stdout.strip().split("\n") if result.stdout else []
        
        dfu_result = subprocess.run(["dfu-util", "--list"], capture_output=True, text=True)
        dfu_devices = []
        if "Found DFU" in dfu_result.stdout:
            dfu_devices = [line.strip() for line in dfu_result.stdout.split("\n") if "Found DFU" in line]

        if not serial_devices and not dfu_devices:
            return ["No devices found. Ensure the board is connected."]
        
        if dfu_devices:
            return serial_devices + [f"Device in DFU mode: {dfu_devices[0]}"]
        
        return serial_devices
    except Exception as e:
        return [f"Error: {e}"]

def enter_dfu_mode(device, stdscr, num_devices):
    stdscr.clear()
    stdscr.addstr(0, 0, f"Entering DFU mode for {device}...", curses.color_pair(1))
    stdscr.refresh()
    try:
        u.enter_bootloader(device)
        time.sleep(2)  # Attendi che il dispositivo entri in DFU
        stdscr.addstr(2, 0, "Device is now in DFU mode.", curses.color_pair(2))
    except Exception as e:
        stdscr.addstr(2, 0, f"Failed to enter DFU mode: {e}", curses.color_pair(1))
    stdscr.refresh()
    time.sleep(2)

def compile_firmware():
    subprocess.run(["make", "menuconfig"], cwd="/home/pi/klipper")
    subprocess.run(["make"], cwd="/home/pi/klipper")
    return "/home/pi/klipper/out/klipper.bin"

def firmware_selection_menu(stdscr):
    stdscr.clear()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    stdscr.addstr(0, 0, "Select Firmware Option:", curses.color_pair(1))
    options = []
    
    if os.path.exists("/home/pi/klipper/out/klipper.bin"):
        options.append("Use existing klipper.bin")
    options.append("Compile new firmware")
    options.append("Use custom firmware.config (Drag and drop supported)")
    options.append("Exit")
    
    selected_idx = 0
    while True:
        for i, option in enumerate(options):
            mode = curses.A_REVERSE if i == selected_idx else curses.A_NORMAL
            stdscr.addstr(2 + i, 2, option, mode)
        key = stdscr.getch()
        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(options) - 1:
            selected_idx += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if options[selected_idx] == "Use custom firmware.config (Drag and drop supported)":
                stdscr.clear()
                stdscr.addstr(0, 0, "Enter the path to firmware.config (Drag and drop the file here): ")
                curses.echo()
                firmware_config_path = stdscr.getstr(1, 0, 100).decode("utf-8").strip()
                curses.noecho()
                if not os.path.exists(firmware_config_path):
                    stdscr.addstr(2, 0, "Error: File not found. Press any key to return.")
                    stdscr.getch()
                    return None
                config_dest = "/home/pi/klipper/.config"
                if os.path.exists(config_dest):
                    os.remove(config_dest)
                with open(firmware_config_path, "r") as src, open(config_dest, "w") as dst:
                    dst.write(src.read())
                stdscr.addstr(2, 0, "Firmware configuration copied successfully. Press any key to continue.")
                stdscr.getch()
                return "Use custom firmware.config"
            return options[selected_idx]

def curses_menu(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    
    stdscr.clear()
    
    devices = list_serial_devices()
    selected_idx = 0
    
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "DFU-Util Firmware Flasher", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(2, 0, "Select Serial Device:", curses.color_pair(2))
        
        for i, device in enumerate(devices):
            mode = curses.A_REVERSE if i == selected_idx else curses.A_NORMAL
            stdscr.addstr(3 + i, 2, device, mode)
        
        stdscr.addstr(5 + len(devices), 0, "Press ENTER to select device, Q to quit", curses.color_pair(1))
        
        key = stdscr.getch()
        
        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(devices) - 1:
            selected_idx += 1
        elif key == ord('q'):
            return
        elif key == 10 or key == 13:
            selected_device = devices[selected_idx]
            firmware_option = firmware_selection_menu(stdscr)
            if firmware_option == "Exit":
                return
            firmware_path = "/home/pi/klipper/out/klipper.bin" if firmware_option == "Use existing klipper.bin" else compile_firmware()
            enter_dfu_mode(selected_device, stdscr, len(devices))

def main():
    curses.wrapper(curses_menu)

if __name__ == "__main__":
    main()
