#!/bin/bash
set -e

# Dọn lock file cũ nếu container restart để tránh Xvfb bị kẹt
rm -f /tmp/.X99-lock

# Khởi động Xvfb ở background, giả lập màn hình 1920x1080x24bit
# -> Chrome "headful" nhìn thấy DISPLAY này và chạy như có GUI thật,
#    khác hẳn --headless nên né được nhiều check headless-detection.
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -nolisten unix &
XVFB_PID=$!

# Chờ Xvfb sẵn sàng
for i in $(seq 1 10); do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Bật x11vnc để soi trực tiếp Chrome đang render gì khi debug bypass fail
# (VNC_ENABLED=1 mới bật, mặc định tắt vì tốn tài nguyên + lộ màn hình nếu map port ra ngoài)
VNC_PID=""
NOVNC_PID=""
if [ "${VNC_ENABLED:-0}" = "1" ]; then
    VNC_ARGS="-display :99 -forever -shared -rfbport 5900 -noxdamage"
    if [ -n "${VNC_PASSWORD:-}" ]; then
        VNC_ARGS="$VNC_ARGS -passwd $VNC_PASSWORD"
    else
        echo "[entrypoint] CANH BAO: VNC bat khong mat khau (VNC_PASSWORD trong), chi map port 5900 ra localhost/VPN tin cay." >&2
        VNC_ARGS="$VNC_ARGS -nopw"
    fi
    x11vnc $VNC_ARGS >/tmp/x11vnc.log 2>&1 &
    VNC_PID=$!

    # noVNC: bọc VNC (5900) qua WebSocket + serve web UI, xem trực tiếp bằng browser
    # http://localhost:${NOVNC_PORT:-6080}/vnc.html thay vì cần VNC client riêng
    websockify --web=/usr/share/novnc "${NOVNC_PORT:-6080}" localhost:5900 >/tmp/novnc.log 2>&1 &
    NOVNC_PID=$!
fi

# Dọn dẹp khi container dừng
cleanup() {
    kill "$XVFB_PID" 2>/dev/null || true
    [ -n "$VNC_PID" ] && kill "$VNC_PID" 2>/dev/null || true
    [ -n "$NOVNC_PID" ] && kill "$NOVNC_PID" 2>/dev/null || true
}
trap cleanup EXIT TERM INT

exec "$@"
