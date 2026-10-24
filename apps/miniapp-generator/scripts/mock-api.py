#!/usr/bin/env python3
"""视觉核查专用 mock API（仅本地预览用，不属于产品代码）。

按后端 UnifiedResponse 契约返回 {code:0, message:"ok", data:...}，
供微信开发者工具模拟器渲染真实数据形态，与竞品截图做布局对比。
数据全部为显式标注「视觉核查用」的假数据，不落库、不代表真实机构。

用法: python3 mock_api.py [port]   默认 9000
"""
import base64
import json
import struct
import sys
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000

DOCTOR_ID = "5f0a3c2e-1b4d-4e8f-9a6c-7d2e5b8a1c3f"  # 36 位 UUID（scene 编码用）


def png_solid(w, h, rgba):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgba) * w for _ in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def png_qr_like(size=29, scale=8):
    """确定性黑白图案，形似二维码（仅占位，非可扫真码）。"""
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    def finder(x, y):
        for dy in range(7):
            for dx in range(7):
                edge = dx in (0, 6) or dy in (0, 6)
                core = 2 <= dx <= 4 and 2 <= dy <= 4
                yield x + dx, y + dy, edge or core

    cells = {(x, y) for x, y, on in [0] * 0 for x in []}  # placeholder
    cells = set()
    for fx, fy in [(0, 0), (size - 7, 0), (0, size - 7)]:
        cells.update(finder(fx, fy))
    for y in range(size):
        for x in range(size):
            if (x, y) not in cells and (x * 7 + y * 13 + x * y) % 3 == 0:
                cells.add((x, y))
    px_w = size * scale
    rows = []
    for py in range(px_w):
        row = bytearray([0])
        cy = py // scale
        for px in range(px_w):
            row.append(0 if (px // scale, cy) in cells else 255)
        rows.append(bytes(row))
    raw = b"".join(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", px_w, px_w, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


QR_PNG = png_qr_like()
GREEN_PNG = png_solid(320, 200, (0xE5, 0xF3, 0xEE, 0xFF))

DOCTOR = {
    "id": DOCTOR_ID,
    "name": "核查医生",
    "title": "资深中医师",
    "departmentName": "中医科",
    "specialty": "妇科、备孕指导、内分泌调理、脾胃（尤其小儿脾胃）、失眠",
    "introduction": "从业中医临床三十余年，医学功底系统扎实。师承多位民间名老中医，博采众长，"
    "熟练运用特色古法疗法，辨证调治各类急慢性鼻炎、过敏性鼻炎等鼻部疾患，"
    "坚持中医药守正创新，临床疗效确切，广受患者信赖。此为视觉核查用介绍文案。",
    "avatar": "",
}

STORE = {
    "id": "mock-store-1",
    "name": "重庆颐草堂中医馆（视觉核查用）",
    "phone": "023-68888888",
    "address": "重庆市市辖区巴南区巴县大道57号附27号（视觉核查用地址）",
    "description": "重庆颐草堂中医诊所始建于2018年，是一家纯正的中医医疗机构；秉持「聚百草，传好方，"
    "承古法」的经营理念，汇聚名医大家，成立「汇诊制」，致力解决疑难杂症。此为视觉核查用介绍。",
    "latitude": 29.382084,
    "longitude": 106.521194,
}


def ok(data):
    return {"code": 0, "message": "ok", "data": data}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200, content_type="application/json"):
        body = json.dumps(payload, ensure_ascii=False).encode() if content_type == "application/json" else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        qs = self.path.split("?")[1] if "?" in self.path else ""
        q = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
        if path == "/api/v1/doctors/recommended":
            return self._send(ok([DOCTOR]))
        if path.startswith("/api/v1/doctors/") and path.endswith("/schedules"):
            return self._send(ok({"items": [], "total": 0}))
        if path.startswith("/api/v1/doctors/"):
            return self._send(ok(DOCTOR))
        if path == "/api/v1/content/banners/active":
            position = q.get("position", "home")
            banner = {
                "id": "banner-" + position,
                "title": "【预约提醒】请提前线上预约，不支持临时线下加号",
                "imageUrl": "/static/cover.png" if position == "org" else "",
                "linkType": 1,
                "linkUrl": "",
                "position": position,
                "sortOrder": 1,
                "status": 1,
                "createdAt": "2026-10-01T09:00:00",
            }
            return self._send(ok([banner]))
        if path == "/api/v1/doctor-reviews":
            items = [
                {"id": f"r{i}", "patientName": f"患者{i}", "rating": 5, "content": f"第{i}条视觉核查评价：医生态度很好。", "createdAt": "2026-10-1%dT10:00:00" % i}
                for i in range(1, 4)
            ]
            return self._send(ok({"items": items, "total": 3}))
        if path == "/api/v1/marketing/poster-qrcode":
            return self._send(ok({"image": base64.b64encode(QR_PNG).decode()}))
        if path.startswith("/api/v1/stores/"):
            return self._send(ok(STORE))
        if path.startswith("/static/"):
            return self._send(GREEN_PNG, content_type="image/png")
        return self._send({"code": 404, "message": "not found (mock)", "data": None}, status=404)

    def log_message(self, fmt, *args):
        sys.stderr.write("[mock] " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"[mock] serving on http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
