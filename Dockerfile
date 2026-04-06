FROM python:3.10-slim

# อัปเดตและติดตั้ง Google Chrome สำหรับให้บอทใช้งาน
RUN apt-get update && apt-get install -y wget gnupg unzip && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && apt-get install -y google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ตั้งค่าพื้นที่ทำงาน
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ก๊อปปี้ไฟล์ทั้งหมดของเราเข้าไปในเซิร์ฟเวอร์
COPY . .

# สั่งรัน Web Server
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]
