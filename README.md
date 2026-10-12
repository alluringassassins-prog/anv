# ANV multi-agent simulation

The project models agents, their decisions, a common-bus network, a simulated
environment, and a ground station. The source tree is designed to run on
Linux, macOS, or Windows with Python 3.10 or newer.

## Run on Ubuntu

```bash
sudo apt update
sudo apt install -y python3-venv
git clone https://github.com/alluringassassins-prog/anv.git
cd anv
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_simulation.py
```

The launcher starts the common bus and environment automatically, then opens
the Ground Station menu in the same terminal. Use the menu's Exit option or
Ctrl+C to stop all components. The services use ports 7106 and 8000 by
default; change `config.ini` or pass `--bus-port` and `--environment-port` to
the launcher when those ports are already in use.

## Optional map

`Environment/monitor.html` is the existing browser map adapter. It reads
`config.ini` and polls the environment API. The simulator itself does not
require the map to run. A native desktop map can be added as a separate UI
adapter without changing the simulation protocol.

## Build an executable

PyInstaller builds must be made on the target operating system. On Ubuntu:

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --clean --noconfirm --onedir --name anv run_simulation.py
./dist/anv/anv
```

Build a Windows `.exe` on Windows and a macOS application on macOS. The
executable still needs permission to bind local TCP ports; packaging cannot
remove that operating-system requirement.
