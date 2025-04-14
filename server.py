import socket
import threading
import subprocess
import re
import queue
import json
import time
import argparse

clients = []
clients_lock = threading.Lock()

def decode_joystick_input(input_str):
    axes = {}
    buttons = {}

    axes_match = re.search(r"Axes:\s+(.*?)(Buttons:|$)", input_str)
    if axes_match:
        axes_part = axes_match.group(1)
        axes_matches = re.findall(r"(\d+):\s*(-?\d+)", axes_part)
        axes = {int(index): int(value) for index, value in axes_matches}

    buttons_match = re.search(r"Buttons:\s+(.*)", input_str)
    if buttons_match:
        buttons_part = buttons_match.group(1)
        buttons_matches = re.findall(r"(\d+):(on|off)", buttons_part)
        buttons = {int(index): (value == "on") for index, value in buttons_matches}

    return axes, buttons

def read_joystick_output(process, q):
    for line in iter(process.stdout.readline, ''):
        if line:
            q.queue.clear()
            q.put(line.strip())

def broadcast_to_clients(message: dict):
    data = json.dumps(message).encode()
    disconnected = []
    with clients_lock:
        for conn in clients:
            try:
                conn.sendall(data)
            except:
                disconnected.append(conn)
        for conn in disconnected:
            clients.remove(conn)
            print("❌ Removed disconnected client.")

def handle_client(conn, addr):
    print(f"🔗 Client connected: {addr}")
    with clients_lock:
        clients.append(conn)
    try:
        while True:
            time.sleep(1)
    except:
        pass
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"🔌 Client {addr} disconnected.")

def run_server(host, port):
    process = subprocess.Popen(
        ["jstest", "/dev/input/js0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    line_queue = queue.Queue()
    reader_thread = threading.Thread(target=read_joystick_output, args=(process, line_queue))
    reader_thread.daemon = True
    reader_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(5)
        print(f"🎮 Joystick server running on {host}:{port}, waiting for clients...")

        # Client accepter thread
        def accept_clients():
            while True:
                conn, addr = s.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()

        threading.Thread(target=accept_clients, daemon=True).start()

        # Main broadcasting loop
        try:
            while True:
                time.sleep(0.1)
                if not line_queue.empty():
                    line = line_queue.get()
                    axes, buttons = decode_joystick_input(line)
                    if axes or buttons:
                        print("Sending")
                        broadcast_to_clients({"axes": axes, "buttons": buttons})
        except KeyboardInterrupt:
            print("🛑 Server shutting down...")
        finally:
            process.terminate()
            with clients_lock:
                for conn in clients:
                    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joystick server for broadcasting control signals.")
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='Host IP address to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=9999, help='Port number to bind (default: 9999)')
    args = parser.parse_args()

    run_server(host=args.ip, port=args.port)
