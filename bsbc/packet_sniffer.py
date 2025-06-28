from scapy.all import sniff, TCP, IP
import datetime
import json
import os

TARGET_IP = "192.168.0.200"
TARGET_PORT = 22000

# JSON 파일 경로
JSON_FILE = "captured_packets_all.json"

# 기존 파일이 있으면 로드, 없으면 새로 생성
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        packets = json.load(f)
else:
    packets = []

print(f"패킷 캡처 시작: {TARGET_IP}:{TARGET_PORT}")
print(f"저장 파일: {JSON_FILE}")
print("SEND(켜는 신호) 패킷만 캡처")
print("Ctrl+C로 종료")

def save_packets():
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(packets, f, ensure_ascii=False, indent=2)

def is_turn_on_packet(raw):
    # 10~23번 바이트 중 하나라도 0이 아니면 켜는 신호로 간주
    if len(raw) >= 24:
        for i in range(10, 24):
            if raw[i] != 0:
                return True
    return False

def packet_callback(pkt):
    if IP in pkt and TCP in pkt:
        raw = bytes(pkt[TCP].payload)
        if len(raw) == 0:
            return
        now = datetime.datetime.now().strftime("%H:%M:%S")
        direction = None
        if pkt[IP].dst == TARGET_IP and pkt[TCP].dport == TARGET_PORT:
            direction = "recv"
        elif pkt[IP].src == TARGET_IP and pkt[TCP].sport == TARGET_PORT:
            direction = "send"
        # SEND + 켜는 신호만 저장
        if direction == "send" and is_turn_on_packet(raw):
            packet_data = {
                "timestamp": now,
                "hex_data": raw.hex(),
                "length": len(raw),
                "direction": direction
            }
            packets.append(packet_data)
            save_packets()  # 실시간으로 파일에 저장
            print(f"[{now}] {direction.upper()} 켜는 패킷: {raw.hex()}")

try:
    sniff(filter=f"tcp and (host {TARGET_IP} and port {TARGET_PORT})", prn=packet_callback, store=0)
except PermissionError:
    print("[!] 관리자 권한 필요")
except KeyboardInterrupt:
    print(f"\n종료 - 총 {len(packets)}개 패킷 저장됨") 