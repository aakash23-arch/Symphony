#!/usr/bin/env python3
"""Mock SIP/RTP Telecom Ingress Adapter Demonstration Script.

This script demonstrates how an enterprise PBX (e.g. FreeSWITCH, Asterisk,
or Kamailio SIP gateway) bridges real-time RTP audio packets into VoiceShield's
streaming WebSocket ingestion endpoint (/v1/sessions/{session_id}/audio).

Workflow:
1. Creates a new session with carrier metadata (caller_ref, SIP trunk source).
2. Initiates the WebSocket audio stream.
3. Sends the standard 16kHz PCM audio.header negotiation packet.
4. Streams 20ms or 1000ms chunked PCM audio packets simulating RTP payload delivery.
5. Displays live telemetry and risk evaluation.
"""

import argparse
import asyncio
import json
import struct
import sys
import httpx
import websockets

BACKEND_HTTP = "http://127.0.0.1:8000"
BACKEND_WS = "ws://127.0.0.1:8000"


async def run_telecom_ingress(
    caller_ref: str = "+91 22 6123 4567",
    duration_s: float = 5.0,
    sample_rate: int = 16000,
) -> None:
    print(f"\n[PBX-SIP-GATEWAY] Initiating SIP Trunk Call Ingress for: {caller_ref}")
    print(f"[PBX-SIP-GATEWAY] Target VoiceShield API: {BACKEND_HTTP}")

    # 1. Create Session over REST API
    async with httpx.AsyncClient(base_url=BACKEND_HTTP, timeout=10.0) as client:
        resp = await client.post(
            "/api/sessions",
            json={
                "source_type": "ws",
                "caller_ref": caller_ref,
            },
        )
        if resp.status_code not in (200, 201):
            print(f"[ERROR] Failed to create session: {resp.status_code} {resp.text}")
            return

        session_id = resp.json()["session_id"]
        print(f"[PBX-SIP-GATEWAY] Session established: {session_id}")

        # Post context
        await client.post(
            f"/api/sessions/{session_id}/context",
            json={
                "claimed_identity": "cfo.ananya_sharma",
                "call_source": "SIP_TRUNK_PSTN",
                "telecom_carrier": "AIRTEL_ENTERPRISE_SIP",
                "transaction_type": "WIRE_TRANSFER",
            },
        )

        # Start session
        await client.post(f"/api/sessions/{session_id}/start")
        print(f"[PBX-SIP-GATEWAY] Session started on backend pipeline")

    # 2. Connect Audio Ingress WebSocket
    ws_url = f"{BACKEND_WS}/v1/sessions/{session_id}/audio"
    print(f"[PBX-SIP-GATEWAY] Connecting RTP audio stream to {ws_url}...")

    async with websockets.connect(ws_url) as ws:
        # Send Audio Header
        header = {
            "type": "audio.header",
            "sample_rate": sample_rate,
            "channels": 1,
            "encoding": "pcm_s16le",
        }
        await ws.send(json.dumps(header))
        print("[PBX-SIP-GATEWAY] Handshake complete: 16kHz PCM S16LE negotiated")

        # Stream audio chunks (simulating 50ms RTP packets: 800 samples = 1600 bytes)
        chunk_samples = 800
        chunk_bytes_len = chunk_samples * 2
        total_chunks = int(duration_s * (sample_rate / chunk_samples))

        print(f"[PBX-SIP-GATEWAY] Streaming {total_chunks} RTP packets ({duration_s}s total)...")

        # Generate a mild synthetic test signal (440Hz sine wave)
        import math
        for chunk_idx in range(total_chunks):
            pcm_data = bytearray()
            for s in range(chunk_samples):
                t = (chunk_idx * chunk_samples + s) / sample_rate
                # 440 Hz + 880 Hz harmonics with gentle amplitude
                val = 0.3 * math.sin(2 * math.pi * 440 * t) + 0.15 * math.sin(2 * math.pi * 880 * t)
                int_val = max(-32768, min(32767, int(val * 32767)))
                pcm_data.extend(struct.pack("<h", int_val))

            await ws.send(bytes(pcm_data))
            await asyncio.sleep(0.05)  # 50ms packet interval

            if (chunk_idx + 1) % 20 == 0:
                print(f"[PBX-SIP-GATEWAY] Sent {chunk_idx + 1}/{total_chunks} packets")

        print("[PBX-SIP-GATEWAY] Ingress stream completed cleanly.")

    # 3. Fetch Final Assessment
    async with httpx.AsyncClient(base_url=BACKEND_HTTP, timeout=10.0) as client:
        await asyncio.sleep(1.0)
        risk_resp = await client.get(f"/api/sessions/{session_id}/risk")
        if risk_resp.status_code == 200:
            print("\n[PBX-SIP-GATEWAY] Final Forensic Assessment Result:")
            print(json.dumps(risk_resp.json(), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock PBX/SIP Ingress Adapter")
    parser.add_argument("--caller", default="+91 22 6123 4567", help="Caller phone number")
    parser.add_argument("--duration", type=float, default=3.0, help="Stream duration in seconds")
    args = parser.parse_args()

    asyncio.run(run_telecom_ingress(caller_ref=args.caller, duration_s=args.duration))
