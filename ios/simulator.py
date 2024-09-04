import subprocess
import re

def run_command(command):
    """Execute a shell command and return the output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def list_devices():
    """List all devices and return them sorted with booted devices first."""
    output = run_command("xcrun simctl list devices")
    devices = []
    current_ios = None
    for line in output.split('\n'):
        if line.startswith('--'):
            current_ios = line.strip('- ')
        elif '(' in line and ')' in line:
            name = line.split('(')[0].strip()
            uuid = re.search(r'\((.*?)\)', line).group(1)
            status = 'Booted' if 'Booted' in line else 'Shutdown'
            devices.append((name, uuid, status, current_ios))

    # Sort devices: Booted first, then by iOS version and name
    return sorted(devices, key=lambda x: (x[2] != 'Booted', x[3], x[0]))

def print_devices(devices):
    """Print the list of devices with numbering."""
    print("Available devices:")
    for i, (name, uuid, status, ios) in enumerate(devices, 1):
        print(f"{i}. {name} ({ios}) - {status}")
    print("0. Shutdown all devices")

def main():
    devices = list_devices()
    print_devices(devices)

    choice = input("Enter the number of the device to boot/open (or 0 to shutdown all): ")

    if choice == '0':
        # Shutdown all devices
        run_command("xcrun simctl shutdown all")
        print("All devices have been shut down.")
    elif choice.isdigit() and 1 <= int(choice) <= len(devices):
        selected_device = devices[int(choice) - 1]
        name, uuid, status, _ = selected_device

        if status == 'Booted':
            # Open Simulator for already booted device
            run_command(f"open -a Simulator")
            print(f"Opening Simulator for {name}")
        else:
            # Boot and open the selected device
            run_command(f"open -a Simulator --args -CurrentDeviceUDID {uuid}")
            print(f"Booting and opening Simulator for {name}")
    else:
        print("Invalid choice. Please try again.")

    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()

