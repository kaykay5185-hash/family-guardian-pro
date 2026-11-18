# Family Guardian Pro

Family Guardian Pro is a self-hostable family location sharing sample: Android (Kotlin), Flask/SQLite API, and a browser dashboard. It does not use Firebase. Sharing starts only after the device owner pairs the app, grants Android location permission, and taps **Start location sharing**. A persistent foreground notification stays visible and has a Stop action.

## Deliverables and build status

The complete source is in `android/` and `server/`. The Android project uses Gradle Kotlin DSL and Android Studio. **No APK is included in this package:** the environment used to prepare it had no Java/JDK, Android SDK, Gradle, or Python executable, so an APK build could not be run or verified. Do not install an APK from this package; build it in Android Studio using the steps below.

For a Windows parent PC, see `pc/README.md` and start the local dashboard with `pc/Start-FamilyGuardianPC.bat`. The PC dashboard runs in the default web browser and needs Python 3.10+; it is not a compiled `.exe` installer.

## Publishing

GitHub Pages can provide a free `https://<owner>.github.io/<repository>/` address for static HTML, CSS, and JavaScript. It cannot run this project's Flask/Python server, so publishing this source repository to Pages will not make the live dashboard work. To host the complete app, deploy the Flask server to a Python-capable host with HTTPS and configure its environment variables. Never commit passwords, session secrets, the SQLite location database, logs, or the local virtual environment.

## Android build

Install Android Studio with JDK 17 and Android SDK Platform 35. Open `android/`, allow Gradle to sync and download the declared public dependencies, then choose **Build > Build Bundle(s) / APK(s) > Build APK(s)**. The debug APK will be under `android/app/build/outputs/apk/debug/`. The project uses Android Gradle Plugin 8.7.3 and Kotlin 2.0.21.

## Server setup

Requires Python 3.10+ and pip. From `server/`, create a virtual environment, install `requirements.txt`, set secrets in the environment, and run `python app.py` for local development. For a public deployment use a reverse proxy with HTTPS and a production WSGI server, for example `gunicorn --bind 127.0.0.1:5000 app:app`.

Required environment variables:

- `PARENT_USERNAME`: dashboard login name.
- `PARENT_PASSWORD_HASH`: Werkzeug password hash (never store a plain text password). Generate one with `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash(input('Password: ')))"`.
- `SESSION_SECRET`: long random value used to sign dashboard sessions.
- `DATABASE_PATH`: optional SQLite file path; default is `family_guardian.sqlite3` in the server working directory.

Example PowerShell setup (set your own values in a private terminal):

```powershell
cd server
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PARENT_USERNAME = 'family-admin'
$env:PARENT_PASSWORD_HASH = '<generated Werkzeug hash>'
$env:SESSION_SECRET = '<random secret from a password manager>'
python app.py
```

Visit `http://127.0.0.1:5000`, sign in, and select **Pair a device**. On the Android device, enter the server URL and scan the QR code or type its short-lived code. The code expires after ten minutes and can be used once. For actual remote use, configure HTTPS and use that HTTPS URL in the app. The app intentionally permits cleartext only to support local/private-network development; never expose an HTTP server to the public internet. Deploy TLS, restrict inbound access, protect backups, and set an explicit secret key before production.

## API overview

- `POST /api/pairing-codes` — dashboard session; issues a one-use code.
- `POST /api/devices/register` — redeems a code and returns a one-time device token.
- `POST /api/locations` — device bearer token; validated coordinates, accuracy, battery.
- `GET /api/dashboard` — dashboard session; devices, latest points, zones, and geofence alerts.
- `GET /api/devices/{id}/history?limit=100` — dashboard session; recent location history.
- `POST /api/zones`, `DELETE /api/zones/{id}` — dashboard session; safe zones and arrival/departure events.

Device tokens are random, shown only once at registration, and stored server-side as SHA-256 hashes. Dashboard passwords are checked against a Werkzeug hash. Pairing codes are stored hashed. The SQLite database stores precise location history; secure and regularly back it up, and establish a retention/deletion policy appropriate to your family before deployment. Public production deployments should add rate limiting, CSRF protection for form/session mutations, secure cookie settings, and monitoring at the reverse proxy.

## Current limitations

Safe-zone arrival/departure alerts are created when a received GPS update crosses a zone boundary and displayed in the dashboard. Android location updates are requested about once per minute while the visible foreground service runs; Android device power settings may affect cadence. OpenStreetMap map tiles and Leaflet/QR libraries are loaded from their public CDNs, so the dashboard needs internet access for the map and QR image. This starter is not a substitute for emergency services or a reviewed child-safety product.
