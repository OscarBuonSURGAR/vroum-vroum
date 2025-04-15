import socket
import json
import subprocess
import argparse
import atexit
import signal
import sys
import os
import pwd

def set_fan_speed(gpu_id=0, fan_speed=80):
    command = [
        'nvidia-settings',
        '-a', f'[gpu:{gpu_id}]/GPUFanControlState=1',
        '-a', f'[fan:{gpu_id}]/GPUTargetFanSpeed={fan_speed}'
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL)

def reset_fan_control(gpu_id=0):
    command = ['nvidia-settings', '-a', f'[gpu:{gpu_id}]/GPUFanControlState=0']
    subprocess.run(command, stdout=subprocess.DEVNULL)
    print("♻️ Fan control reset to automatic")

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

# Get the main (non-root) user's info
main_user = os.getenv("SUDO_USER") or os.getenv("USER")
user_info = pwd.getpwnam(main_user)
user_env = os.environ.copy()
user_env["HOME"] = user_info.pw_dir
user_env["LOGNAME"] = main_user
user_env["USER"] = main_user
user_env["XDG_RUNTIME_DIR"] = f"/run/user/{user_info.pw_uid}"
# This is the most crucial one for gsettings:
user_env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{user_info.pw_uid}/bus"

def run_as_main_user(command):
    def demote():
        os.setgid(user_info.pw_gid)
        os.setuid(user_info.pw_uid)

    subprocess.run(command, preexec_fn=demote, text=True, env=user_env)

def run_fan_client(server_ip, server_port, canal, gpu_id=0):
    def cleanup(*args):
        reset_fan_control(gpu_id)
        sys.exit(0)

    # Register cleanup on normal exit and signals
    atexit.register(reset_fan_control, gpu_id)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_ip, server_port))
            print(f"💻 Connected to joystick server at {server_ip}:{server_port}")
            buffer = ""
            while True:
                data = s.recv(1024)
                if not data:
                    break
                buffer += data.decode()

                message = json.loads(buffer)
                buffer = ""  # Reset buffer after full JSON
                axes = message.get("axes", {})
                buttons = message.get("buttons", {})
                
                if f"{canal}" in axes:
                    val = -axes[f"{canal}"]
                    fan_speed = map_range(val, -33000, 33000, 0, 100)
                    print(f"🌀 Setting fan speed: {int(fan_speed)}%")
                    set_fan_speed(gpu_id=gpu_id, fan_speed=int(fan_speed))

                if "32" in buttons:
                    val = "prefer-dark" if buttons["32"] else "prefer-light"

                    print(f"🌀 Setting light mode: {val}")

                    run_as_main_user([
                        "gsettings", "set", "org.gnome.desktop.interface", "color-scheme", val
                    ])
    except Exception as e:
        print(f"⚠️ Client error: {e}")
        reset_fan_control(gpu_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fan control client.")
    parser.add_argument('--ip', type=str, default='localhost', help='Server IP address (default: localhost)')
    parser.add_argument('--port', type=int, default=9999, help='Server port (default: 9999)')
    parser.add_argument('--canal', type=int, default=0, help='Canal (default: 0)')
    parser.add_argument('--gpu', type=int, default=0, help='GPU ID (default: 0)')
    args = parser.parse_args()

    run_fan_client(server_ip=args.ip, server_port=args.port, canal=args.canal, gpu_id=args.gpu)
