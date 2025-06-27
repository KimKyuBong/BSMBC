from scapy.all import sniff, TCP, IP
import datetime

TARGET_IP = "192.168.0.200"
TARGET_PORT = 22000

print(f"패킷 캡처 시작: {TARGET_IP}:{TARGET_PORT}로 나가는 패킷을 모니터링합니다.")
print("Ctrl+C로 종료하세요.")


def packet_callback(pkt):
    if IP in pkt and TCP in pkt:
        if pkt[IP].dst == TARGET_IP and pkt[TCP].dport == TARGET_PORT:
            raw = bytes(pkt[TCP].payload)
            if len(raw) == 0:
                return  # 데이터 없는 패킷은 무시
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("\n" + "="*60)
            print(f"[{now}] 패킷 캡처: {pkt[IP].dst}:{pkt[TCP].dport}")
            print(f"HEX: {raw.hex()}")
            print(f"LEN: {len(raw)} bytes")
            print("="*60)

try:
    sniff(filter=f"tcp and dst host {TARGET_IP} and dst port {TARGET_PORT}", prn=packet_callback, store=0)
except PermissionError:
    print("[!] 관리자 권한으로 실행해야 합니다.")
except KeyboardInterrupt:
    print("\n[!] 캡처를 종료합니다.") 