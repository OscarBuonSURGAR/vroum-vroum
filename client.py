import socket
import json
import subprocess
import argparse

def set_fan_speed(gpu_id=0, fan_speed=80):
    command = [
        'nvidia-settings',
        '-a', f'[gpu:{gpu_id}]/GPUFanControlState=1',
        '-a', f'[fan:{gpu_id}]/GPUTargetFanSpeed={fan_speed}'
    ]
    subprocess.run(command)

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def run_fan_client(server_ip, server_port, canal):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_ip, server_port))
            print(f"💻 Connected to joystick server at {server_ip}:{server_port}")
            buffer = ""
            while True:
                print("Get")
                data = s.recv(1024)
                if not data:
                    break
                buffer += data.decode()

                message = json.loads(buffer)
                buffer = ""  # Reset buffer after full JSON
                axes = message.get("axes", {})
                if f"{canal}" in axes:
                    val = -axes[f"{canal}"]
                    fan_speed = map_range(val, -33000, 33000, 0, 100)
                    print(f"🌀 Setting fan speed: {int(fan_speed)}%")
                    set_fan_speed(fan_speed=int(fan_speed))
    except KeyboardInterrupt:
        print("👋 Client shutting down...")
        set_fan_speed(fan_speed=30)
    except Exception as e:
        print(f"⚠️ Client error: {e}")
        set_fan_speed(fan_speed=30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fan control client.")
    parser.add_argument('--ip', type=str, default='localhost', help='Server IP address (default: localhost)')
    parser.add_argument('--port', type=int, default=9999, help='Server port (default: 9999)')
    parser.add_argument('--canal', type=int, default=0, help='Canal (default: 0)')
    args = parser.parse_args()

    run_fan_client(server_ip=args.ip, server_port=args.port, canal=args.canal)
