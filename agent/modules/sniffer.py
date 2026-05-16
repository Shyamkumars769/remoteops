from collections import Counter
from time import time


def packet_summary(duration: float = 5.0) -> dict:
    """Opt-in packet summary example.

    This intentionally returns aggregate counts only. It avoids storing payloads or
    raw PCAP data, and it is not wired into the default task dispatcher.
    """
    try:
        from scapy.all import sniff
    except Exception as exc:
        return {"enabled": False, "error_message": f"scapy unavailable: {exc}"}

    protocols: Counter[str] = Counter()
    src_ips: Counter[str] = Counter()
    dst_ips: Counter[str] = Counter()
    ports: Counter[int] = Counter()

    def summarize(packet) -> None:
        if packet.haslayer("TCP"):
            protocols["TCP"] += 1
            ports.update([int(packet["TCP"].sport), int(packet["TCP"].dport)])
        elif packet.haslayer("UDP"):
            protocols["UDP"] += 1
            ports.update([int(packet["UDP"].sport), int(packet["UDP"].dport)])
        elif packet.haslayer("ICMP"):
            protocols["ICMP"] += 1

        if packet.haslayer("IP"):
            src_ips[packet["IP"].src] += 1
            dst_ips[packet["IP"].dst] += 1

    started = time()
    sniff(timeout=duration, prn=summarize, store=False)
    return {
        "duration": round(time() - started, 3),
        "protocols": dict(protocols),
        "top_sources": src_ips.most_common(10),
        "top_destinations": dst_ips.most_common(10),
        "top_ports": ports.most_common(10),
    }
