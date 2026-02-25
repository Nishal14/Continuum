"""Kill process on port 8000"""
import subprocess
import sys

# Find process using port 8000
result = subprocess.run(
    ['netstat', '-ano'],
    capture_output=True,
    text=True
)

for line in result.stdout.split('\n'):
    if ':8000' in line and 'LISTENING' in line:
        parts = line.split()
        pid = parts[-1]
        print(f"Found process {pid} on port 8000")

        # Try to kill it
        kill_result = subprocess.run(
            ['taskkill', '/PID', pid, '/F'],
            capture_output=True,
            text=True
        )
        print(kill_result.stdout)
        print(kill_result.stderr)

        if kill_result.returncode == 0:
            print("Successfully killed process")
            sys.exit(0)
        else:
            # Try Python's psutil if available
            try:
                import psutil
                p = psutil.Process(int(pid))
                p.terminate()
                p.wait(timeout=5)
                print(f"Killed process {pid} using psutil")
                sys.exit(0)
            except ImportError:
                print("psutil not available")
            except Exception as e:
                print(f"Error with psutil: {e}")

print("Could not kill process. Please close it manually.")
