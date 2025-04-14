# Vroum Vroum

## Server

Install these packages:
```bash
sudo apt install joystick evtest jstest-gtk
```

Run the program:
```bash
python3 server.py
```

### Client

You need a device with NVIDIA GPU and `nvidia-settings` installed.

Run the program:
```bash
sudo python3 client.py --ip 10.22.19.86
```
