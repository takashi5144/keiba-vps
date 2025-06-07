#!/bin/bash
apt update && apt install -y python3 python3-venv nginx git curl

mkdir -p /opt/keiba-ai
cd /opt/keiba-ai

python3 -m venv venv
source venv/bin/activate

git clone https://github.com/ai-keiba/keiba-vercel.git .
pip install -r requirements.txt

cat <<EOF > /etc/systemd/system/keiba.service
[Unit]
Description=Keiba AI App (FastAPI)
After=network.target

[Service]
User=root
WorkingDirectory=/opt/keiba-ai
ExecStart=/opt/keiba-ai/venv/bin/gunicorn api.index:app -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable keiba
systemctl start keiba

cat <<EOF > /etc/nginx/sites-available/keiba
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/keiba /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "✅ 完了：ブラウザで http://163.44.97.186 にアクセスしてください"

