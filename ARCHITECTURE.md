# Architecture and packaging plan

The project currently has four runtime parts:

1. `Environment/EnvironmentCreator.py` owns the simulated objects and exposes
   a FastAPI HTTP API on port 8000. `monitor.html` polls that API and renders a
   Leaflet map.
2. `serverSocket.py` is the common TCP bus. Agents connect to the DDS port in
   `config.ini` (7106 by default); it forwards addressed and broadcast frames.
3. `AgentLibrary/` and `Library/` implement agent decisions, the DDS client,
   local TinyDB history, and per-agent HTTP services.
4. `GroundStation/CommandCLI.py` starts the ground-station DDS endpoint and
   provides the scenario and manoeuvre menu.

`run_simulation.py` supervises these components from one terminal. The bus is
started in headless mode, the environment is started with Uvicorn, and the
Ground Station keeps the interactive menu. It also stops child processes when
the menu exits or the user presses Ctrl+C.

The current web map is an adapter, not the simulation core. It depends on a
browser and OpenStreetMap tiles. A browser-free desktop build needs a separate
UI adapter (for example Qt) or a bundled webview. The simulation and bus can
be packaged without changing their protocol.

The practical packaging route is an OS-specific PyInstaller build of
`run_simulation.py`. Windows, Linux, and macOS need separate builds because a
single executable cannot contain native dependencies for all three platforms.
The output will still need permission to bind local TCP ports. PyInstaller
does not remove that operating-system requirement.

The Ubuntu source and packaging commands are in `README.md`. The launcher
also has a frozen-executable component mode, so PyInstaller child processes
reuse the same executable instead of looking for loose `.py` files.

Before packaging for distribution, the next refactor should move import-time
side effects out of `GroundStation/CommandCLI.py`, replace wildcard imports,
centralize paths and configuration, and add protocol tests for partial reads,
disconnects, duplicate agent IDs, and broadcast delivery.
