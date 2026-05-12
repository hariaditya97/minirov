import sys, json, time
from fc import FlightController

LOOP_MS = 20

def parse_input_and_handle(fc):
    line = sys.stdin.readline()
    if not line:
        return
    line = line.strip()
    if line.startswith('{'):
        try:
            cmd = json.loads(line)
            fc.handle_command(cmd)
        except Exception:
            print('{"event": "ERROR", "msg": "invalid JSON"}')
    else:
        fc.handle_command(line)
        
def main():
    fc = FlightController()
    last_time = time.ticks_ms()
    loop_start = time.ticks_ms()
    while True:
        loop_start = time.ticks_ms()

        now = time.ticks_ms()
        dt = time.ticks_diff(now, last_time) / 1000.0
        last_time = now

        parse_input_and_handle(fc)  # read and handle first
        fc.update(dt)               # then update with latest command

        elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
        remaining = LOOP_MS - elapsed
        if remaining > 0:
            time.sleep_ms(remaining)


main()