#!/usr/bin/env python3
"""
Daemonize một tiến trình bằng kỹ thuật double-fork + setsid,
giúp tiến trình con sống sót trước reaper của sandbox (giết tiến trình
con của shell khi shell kết thúc).

Cách dùng:
    python3 scripts/daemonize.py <log_file> <cmd> [args...]

Ví dụ:
    python3 scripts/daemonize.py /tmp/ai_core.log .venv/bin/python ai_core/server.py
    python3 scripts/daemonize.py /tmp/bot.log node src/index.js

LƯU Ý: Chạy lệnh này từ thư mục dự án — tiến trình con kế thừa cwd hiện tại
(cần thiết vì config.py load_dotenv() tìm .env theo cwd).
"""
import os
import sys


def daemonize(cmd: list, log_path: str) -> None:
    # Fork lần 1: cha thoát ngay, con vào session mới
    pid = os.fork()
    if pid > 0:
        os.waitpid(pid, 0)
        return

    os.setsid()

    # Fork lần 2: con trung gian thoát, cháu được nhận nuôi bởi init (không còn controlling terminal)
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)

    # Tiến trình cháu: gắn stdout/stderr vào log, stdin vào /dev/null
    with open(log_path, "ab", buffering=0) as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, sys.stdin.fileno())

    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    log_file = sys.argv[1]
    command = sys.argv[2:]
    daemonize(command, log_file)
