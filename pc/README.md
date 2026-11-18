# Family Guardian Pro for Windows PC

This is a one-click Windows launcher for the parent dashboard. It runs the Flask dashboard locally and opens it in your default browser. You do not need to install the Android app on the parent PC.

## Start it

1. Install Python 3.10 or later from [python.org](https://www.python.org/downloads/windows/) and enable the Python launcher (`py`).
2. Double-click `Start-FamilyGuardianPC.bat`.
3. On first run, allow it to create a private virtual environment and install the Python packages. Internet access is needed for this first setup.
4. Choose a dashboard username and a password with at least 12 characters. Sign in when the browser opens.

The launcher stores the SQLite database in `server/family_guardian.sqlite3`. The password is held briefly in memory to produce a one-way hash; only the username, hash, and a fresh session-signing secret are passed to the local server process. No password is written to disk. Closing the console stops the local server. Run the launcher again to start a new session and sign in again.

The PC launcher listens on the local network so a phone on the same Wi-Fi can open the address printed at startup (for example, `http://192.168.1.20:5000`). Keep the PC and phone on the same trusted Wi-Fi. If Windows Firewall blocks access, allow Python on private networks or add an inbound rule for TCP port 5000. Do not expose this HTTP server to the public internet. For access outside your home network, deploy the backend on an HTTPS-enabled server as described in the main README. This PC launcher is not a compiled `.exe` installer.
