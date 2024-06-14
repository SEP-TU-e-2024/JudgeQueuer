#!/bin/bash

set -e

# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | bash
az login

# Install Python and dependencies
echo "-- Installing Python and dependencies"
apt-get update
apt-get install -y software-properties-common wget
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.12 python3.12-venv
wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py
python3.12 get-pip.py

python3.12 -m pip install -r requirements.txt


# Copy judge queuer to final program location
cp -r ./ /usr/local/bin/judge_queuer/

ENTRYPOINT=judgequeuer.py
chmod +x /usr/local/bin/judge_queuer/$ENTRYPOINT


# Define service
echo "-- Creating service"
SERVICE_FILE=/etc/systemd/system/benchlab-judge-queuer.service

echo "[Unit]
Description=BenchLab Judge Queuer Service
After=network.target

[Service]
ExecStart=/usr/local/bin/judge_queuer/$ENTRYPOINT
WorkingDirectory=/usr/local/bin/judge_queuer
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target" | tee $SERVICE_FILE


# Load, enable and start service
echo "-- Starting service"
systemctl daemon-reload
systemctl enable benchlab-judge-queuer.service
systemctl start benchlab-judge-queuer.service


# Wait for 3 seconds to see if service stable
echo "-- Checking service health"
sleep 3

RESTART_COUNT=$(systemctl show -p NRestarts benchlab-judge-queuer.service | cut -d'=' -f2)
if [[ "$RESTART_COUNT" -gt 0 ]]; then
    echo "-- Service has restarted $RESTART_COUNT times. Health check failed."
    exit 1
fi

SERVICE_STATUS=$(systemctl is-active benchlab-judge-queuer.service)
if [[ "$SERVICE_STATUS" != "active" ]]; then
    echo "-- Service is not running properly. Status: $SERVICE_STATUS"
    exit 1
fi

echo "-- Health check passed"

echo "-- All done"
