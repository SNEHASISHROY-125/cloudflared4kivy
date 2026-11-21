<div align="left">
  <img
    src="https://devicons.io/devicons/icons/cloudflare-icon.svg"
    alt="Cloudflare"
    width="96"
  />
</div>


<!-- <div align="center"> -->

## Android service support

This package is designed to run **inside an Android foreground service** created by python-for-android/Buildozer. Starting the tunnel in the service keeps the tunnel active independently of the application's foreground UI.

Declare the service in `buildozer.spec`:

```ini
[app]
requirements = python3,kivy,cloudflared
android.permissions = android.permission.INTERNET,android.permission.FOREGROUND_SERVICE,android.permission.FOREGROUND_SERVICE_DATA_SYNC,android.permission.WAKE_LOCK

services = CloudflaredTunnel:service/service.py:foreground:sticky:foregroundServiceType=dataSync
```

The service module can then control the tunnel in the background:

```python
from cloudflared.android.helper.cloudflared import (
    start_cloudflared,
    stop_cloudflared,
)

# Create a managed tunnel.
start_cloudflared(token="<your-managed-tunnel-token>")

# Or expose a local server with a quick tunnel.
start_cloudflared(
    url="http://127.0.0.1:8769",
    emails=["person1@example.com", "person2@example.com"],  # or emails=[] not mandatory
)

# Stop the active tunnel.
stop_cloudflared()
```

> Treat tunnel tokens as secrets. Do not commit them to source control or log them publicly.

## What it does

- Creates a **Cloudflare managed tunnel** using a tunnel token.
- Creates a temporary **quick tunnel** for a local HTTP service.
- Runs `cloudflared` in a background thread with streamed stdout and stderr.
- Retrieves the generated `trycloudflare.com` URL after a quick tunnel starts.
- Stops and cleans up the active tunnel process.

## Installation

Add the package to your Buildozer requirements:

```ini
requirements = python3,kivy,cloudflared
```

## Usage

```python
from cloudflared.android.helper.cloudflared import (
    cloudflared,
    start_cloudflared,
    stop_cloudflared,
)
```

### Managed tunnel

Use a token issued for a named tunnel in a Cloudflare Zero Trust account:

```python
start_cloudflared(token="<your-managed-tunnel-token>")
```

The default local target is `http://localhost:5000` unless the optional `url` argument is supplied.

### Quick tunnel

Point the tunnel at a local HTTP server:

```python
start_cloudflared(
    url="http://127.0.0.1:8769",
    emails=["person1@example.com", "person2@example.com"],  # or emails=[] not mandatory
)
```

The `emails` argument is passed as Cloudflare `--allowed-mail` options. Omit it or pass an empty list when access restrictions are not required.

### Get the generated quick-tunnel URL

The public URL is populated asynchronously after `cloudflared` starts:

```python
from cloudflared.android.helper.cloudflared import cloudflared
url = cloudflared.get("temp_url", "N/A") if cloudflared is not None else "N/A"
print(url)
```

Retry briefly if the value is still `N/A` while the tunnel is starting.

### Stop the tunnel

```python
stop_cloudflared()
```

Only one tunnel can run at a time. Calling `start_cloudflared()` while a tunnel is active returns without starting another process.

## Android service example

```python
# service/service.py
from time import sleep

from cloudflared.android.helper.cloudflared import (
    cloudflared,
    start_cloudflared,
    stop_cloudflared,
)


def start_managed_tunnel(*args):
    start_cloudflared(token="<your-managed-tunnel-token>")


def start_quick_tunnel(*args):
    start_cloudflared(
        url="http://127.0.0.1:8769",
        emails=["person1@example.com", "person2@example.com"], # or emails=[] not mandatory
    )


def get_quick_tunnel_url(*args):
    from cloudflared.android.helper.cloudflared import cloudflared
    if cloudflared is None:
        return "N/A"
    return cloudflared.get("temp_url", "N/A")


start_managed_tunnel()

try:
    while True:
        sleep(...)
finally:
    stop_cloudflared()
```

## API

| Item                                                                              | Description                                                                                             |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `start_cloudflared(token=None, url="http://localhost:5000", env={}, emails=[])` | Start a managed tunnel when `token` is provided; otherwise start a quick tunnel.                      |
| `stop_cloudflared()`                                                            | Stop and clean up the active tunnel.                                                                    |
| `cloudflared`                                                                   | Runtime state dictionary containing `proc`, `stop_event`, `threads`, and optionally `temp_url`. |

## Compatibility

- **Android:** resolves `libcloudflared.so` from the application native-library directory. The package includes an ARM64 binary with 16 KB page-size compatibility.
- **Linux:** resolves the bundled AMD64 test binary at `cloudflared/android/libs/amd64/cloudflared-linux86`.
- The tunnel must be able to access the local target URL from the Android device or emulator.

## Troubleshooting

- **The public URL remains `N/A`:** wait for tunnel startup, verify Internet and DNS access, and confirm the local target is listening.
- **The tunnel does not start:** check Android logcat for the printed command and Cloudflare process errors.
- **Only one tunnel is allowed:** call `stop_cloudflared()` before starting another tunnel.
- **The Android service stops:** declare it as `foreground:sticky` and ensure the required foreground-service permissions are present.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
