FROM python:3.11-slim-bookworm

# ---- ENV cơ bản ----
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    CHROME_BIN=/usr/bin/google-chrome

# ---- Cài Xvfb + các lib cần cho Chrome chạy headful trong container ----
# (Chrome headful vẫn cần đầy đủ lib GUI dù không có màn hình thật -> Xvfb giả lập X server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    xauth \
    dbus \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxkbcommon0 \
    libu2f-udev \
    libvulkan1 \
    procps \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# ---- Cài Google Chrome (bản thật, KHÔNG dùng chromium — fingerprint Chrome thật ổn định hơn) ----
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# ---- User không phải root (Chrome + sandbox khuyến nghị không chạy root) ----
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser \
    && mkdir -p /app /home/appuser/.cache /home/appuser/.chrome-profile \
    && chown -R appuser:appuser /app /home/appuser

WORKDIR /app

# ---- Cài Python deps ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

# ---- Script khởi động Xvfb rồi mới chạy app ----
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---- noVNC: vào thẳng "/" là auto-connect + auto-scale full khung, khỏi gõ query param tay ----
COPY novnc-index.html /usr/share/novnc/index.html

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
