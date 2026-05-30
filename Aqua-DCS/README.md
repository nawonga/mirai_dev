## 운영 (systemd)

이 프로젝트는 Raspberry Pi에서 **SSH 연결과 무관하게** 항상 실행되도록 systemd system service로 운영할 수 있습니다.

### 서비스 상태/로그

```bash
sudo systemctl status aqua-dcs-web.service aqua-dcs-collector.service
sudo journalctl -u aqua-dcs-web.service -n 200 --no-pager
sudo journalctl -u aqua-dcs-collector.service -n 200 --no-pager
```

### 시작/중지/재시작

```bash
sudo systemctl start aqua-dcs-web.service aqua-dcs-collector.service
sudo systemctl stop aqua-dcs-web.service aqua-dcs-collector.service
sudo systemctl restart aqua-dcs-web.service aqua-dcs-collector.service
```

### 부팅 자동 시작(enable)

```bash
sudo systemctl enable --now aqua-dcs-web.service aqua-dcs-collector.service
```

### 접속

- Pi 로컬: http://127.0.0.1:8000
- 같은 LAN의 다른 기기: http://<PI_IP>:8000 (예: http://192.168.0.201:8000)

