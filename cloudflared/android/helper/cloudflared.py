'''
cloudflared on android @2026
``aarch64``
16kb page size complient

*** managed tunnels ***
*** quick tunnels ***

SEE RELEASES FOR INFO
'''

import subprocess ,os, threading , signal
import re, json
from platform import system

global binary_path

if system() == "Android":
    from jnius import autoclass
    PythonService = autoclass("org.kivy.android.PythonService")
    context = PythonService.mService.getApplicationContext()

    lib_dir = context.getApplicationInfo().nativeLibraryDir
    binary_path = os.path.join(lib_dir, "libcloudflared.so")
elif system() == "Linux":
    binary_path = 'cloudflared/android/libs/amd64/cloudflared-linux86'

# 
global cloudflared
cloudflared = None

def start_cloudflared(token=None , url="http://localhost:5000" , env={} , emails=[]):
    '''
    run http server in a thread
    returns a controller dict with keys: proc, stop_event, threads
    '''
    global binary_path
    global cloudflared
    # no duplicates
    if cloudflared:
        print("already running one...")
        return

    cloudflared = {"proc": None, "stop_event": threading.Event(), "threads": []}

    def run(worker_id , server_bin_path, token, url, env, emails, ctrl):
        try:
            print("cloudflared starting...")
            # 
            cmd = [
                server_bin_path,
                'tunnel',
            ]
            if token is not None:
                cmd.append('run')
                cmd.append('--token')
                cmd.append(token)

            if token is None:
                cmd.append('--url')
                cmd.append(url)

            if token is None and emails is not []:
                for mail in emails:
                    cmd.append('--allowed-mail')
                    cmd.append(mail)

            # debug
            print("final cmd ", cmd)

            # env = os.environ.copy()
            if system() == 'Android': env["GODEBUG"] = "netdns=cgo+1"

            p = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )
            ctrl["proc"] = p

            # XXX JAVA WorkManager catches pid via stdout watcher
            print(f"__WM__|STARTED|{worker_id}|{p.pid}", flush=True)

            # temp url
            def extract_temp_url(line):
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line.decode().rstrip())
                if match: public_url = match.group(0) ; print("Extracted URL:", public_url) ; cloudflared["temp_url"] = public_url

            def stream_output(stream, prefix, stop_event):
                while not stop_event.is_set():
                    line = stream.readline()
                    if not line:
                        break
                    print(f"{prefix}: {line.decode().rstrip()}")
                    # 
                    if cloudflared.get("temp_url") is None:
                        extract_temp_url(line)
                try:
                    stream.close()
                except Exception:
                    pass

            t1 = threading.Thread(target=stream_output, args=(p.stdout, "GO OUT", cloudflared["stop_event"]), daemon=True)
            t2 = threading.Thread(target=stream_output, args=(p.stderr, "GO ERR", cloudflared["stop_event"]), daemon=True)
            t1.start(); t2.start() ;
            ctrl["threads"].extend([t1, t2 ])

            # wait until process ends or stop_event set
            while p.poll() is None and not ctrl["stop_event"].is_set():
                ctrl["stop_event"].wait(0.1)
                # debug
                # print("start cloudflared poll...")

            if ctrl["stop_event"].is_set() and p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    p.wait(timeout=2)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass
        except subprocess.CalledProcessError:
            print("http server failed to start")

    threading.Thread(target=run, args=("cloudflared-daemon", binary_path, token, url ,env, emails, cloudflared), daemon=True).start()
    return cloudflared

def stop_cloudflared(*args):
    """Gracefully stop the http server started by start_http_server."""
    global cloudflared
    if not cloudflared:
        return
    cloudflared["stop_event"].set()
    p = cloudflared.get("proc")
    if p and p.poll() is None:
        try:
            # debug
            print("trying to kill ", _pid := p.pid)
            # p.terminate()
            os.kill(p.pid , signal.SIGTERM)
            print("killed ", _pid)
        except Exception as e:
            print("something went wrong when killing ", _pid , e)
    # join threads briefly
    for t in cloudflared.get("threads", []):
        t.join(timeout=1)
    cloudflared = None
    # ensure process dead
    if p:
        try:
            p.wait(timeout=1)
        except Exception:
            try:
                p.kill()
            except Exception as e:
                print("e")


