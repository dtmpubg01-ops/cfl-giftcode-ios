import flet as ft
import httpx
import json
import os
import threading
import time
from datetime import datetime

API_BASE = "https://vgrapi-sea.vnggames.com"
SYNC_API = "https://giftcode.dtmsub8386.click"
GAME_CODE = "A49"
CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codes.txt")
SYNCED_CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synced_codes.txt")
RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")

def border_all(width, color):
    return ft.Border(
        left=ft.BorderSide(width, color),
        top=ft.BorderSide(width, color),
        right=ft.BorderSide(width, color),
        bottom=ft.BorderSide(width, color),
    )

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "x-client-region": "VN",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/136.0.0.0",
    "Origin": "https://giftcode.vnggames.com",
    "Referer": "https://giftcode.vnggames.com/",
}

ERR = {
    1: "Thành công", 2102: "Nhận quà thất bại", 2105: "Nhân vật offline/không tồn tại",
    2106: "Code không tồn tại", 2107: "Code hết hạn", 2108: "Code đã sử dụng",
    2109: "Đã nhận loại mã này", 2110: "Trùng loại mã", 2113: "Không tìm thấy nhân vật",
    2114: "Tài khoản bị khóa", 2115: "Sai định dạng", 2117: "Hết lượt",
    2119: "Code không hợp lệ", 2121: "Vượt quá lượt nhập", 2126: "Không áp dụng cho server",
    2127: "Đã nhận chuỗi sự kiện", 2129: "Hết lượt nhập trong ngày",
}

C = {
    "bg": "#0a0a0a", "surface": "#141414",
    "card": "rgba(18,18,18,0.82)",
    "border": "rgba(255,255,255,0.1)",
    "border_s": "rgba(255,255,255,0.18)",
    "text": "#f5f5f5", "muted": "#a3a3a3",
    "accent": "#ff7675", "success": "#22c55e", "error": "#ef4444",
    "surf_elem": "rgba(255,255,255,0.04)",
}

def tr(c, m=""):
    return ERR.get(c, m or f"Lỗi {c}")

def load_codes_local():
    if not os.path.exists(CODES_FILE):
        return []
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        codes = [line.strip().strip('\ufeff').upper() for line in f if line.strip()]
    seen = set()
    return [c for c in codes if not (c in seen or seen.add(c))]

def fetch_codes_from_api(role_id):
    url = f"{SYNC_API}/api.php?action=get_codes&role_id={role_id}&game_code={GAME_CODE}"
    try:
        with httpx.Client() as client:
            r = client.get(url, timeout=15)
            data = r.json()
            if data.get("status") == "success":
                queue = data.get("queue", [])
                cleaned = [c.strip().strip('\ufeff').upper() for c in queue if c.strip()]
                return {"total": data.get("total", 0), "redeemed": data.get("redeemed", 0), "queue": cleaned}
        return None
    except:
        return None

def save_result_to_api(role_id, code, status, err_msg=None):
    url = f"{SYNC_API}/api.php?action=save_result"
    try:
        payload = {
            "game_code": GAME_CODE, "server_id": "101",
            "role_id": role_id, "code": code,
            "status": status, "err_msg": err_msg,
        }
        with httpx.Client() as client:
            client.post(url, json=payload, timeout=10)
    except:
        pass

def sync_codes_from_api(role_id):
    result = fetch_codes_from_api(role_id)
    existing = load_synced_codes()
    if result and result["queue"]:
        merged = list(dict.fromkeys(existing + result["queue"]))
        with open(SYNCED_CODES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(merged))
        return merged
    return existing if existing else None

def load_synced_codes():
    if not os.path.exists(SYNCED_CODES_FILE):
        return []
    with open(SYNCED_CODES_FILE, "r", encoding="utf-8") as f:
        return [line.strip().upper() for line in f if line.strip()]

def save_result_local(role_id, code, status, err_msg=None):
    data = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []
    data.append({
        "time": datetime.now().isoformat(),
        "game_code": GAME_CODE, "role_id": role_id,
        "code": code, "status": status, "err_msg": err_msg,
    })
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_codes_local(codes):
    existing = load_synced_codes()
    all_codes = list(dict.fromkeys(existing + [c.upper() for c in codes]))
    with open(SYNCED_CODES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_codes))

def add_codes_to_api(codes):
    url = f"{SYNC_API}/api.php?action=add_codes"
    try:
        payload = {"game_code": GAME_CODE, "codes": codes}
        with httpx.Client() as client:
            r = client.post(url, json=payload, timeout=10)
            data = r.json()
            return data.get("added_count", 0)
    except:
        return 0

def redeem_multi(role_id, codes, server_id):
    url = f"{API_BASE}/coordinator/api/v1/code/redeem-multiple"
    payload = {"serverId": server_id, "gameCode": GAME_CODE, "roleId": str(role_id), "roleName": str(role_id), "codes": codes}
    with httpx.Client() as client:
        r = client.post(url, json=payload, headers=HEADERS, timeout=15)
        return r.json(), r.elapsed.total_seconds()

def redeem_single(role_id, code, server_id):
    url = f"{API_BASE}/coordinator/api/v1/code/redeem"
    payload = {"serverId": server_id, "gameCode": GAME_CODE, "roleId": str(role_id), "roleName": str(role_id), "code": code}
    with httpx.Client() as client:
        r = client.post(url, json=payload, headers=HEADERS, timeout=15)
        return r.json(), r.elapsed.total_seconds()


def input_field(label, hint="", value="", multiline=False, min_lines=1, max_lines=1, visible=True):
    return ft.TextField(
        label=label, hint_text=hint, value=value,
        multiline=multiline, min_lines=min_lines, max_lines=max_lines,
        border_radius=12, bgcolor=C["surf_elem"], border_color=C["border"],
        focused_border_color=C["border_s"],
        text_style=ft.TextStyle(color=C["text"]),
        label_style=ft.TextStyle(color=C["muted"], size=14),
        visible=visible,
    )


class CFLApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.is_running = False
        self.should_stop = False
        self.mode_idx = 0
        self.src_idx = 0
        page.title = "CFL Auto Giftcode"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = C["bg"]
        page.padding = 20
        page.scroll = ft.ScrollMode.AUTO
        page.on_resized = self.on_resized
        self.ui()

    def mode_group(self, labels, active, on_change):
        segments = [ft.Segment(value=str(i), label=label) for i, label in enumerate(labels)]
        return ft.Container(
            content=ft.SegmentedButton(
                segments=segments,
                selected=[str(active)],
                on_change=lambda e: on_change(int(e.control.selected[0])),
                show_selected_icon=False,
            ),
            bgcolor=C["surf_elem"],
            border=border_all(1, C["border"]),
            border_radius=12,
        )

    def ui(self):
        self.logs = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        self.pb = ft.ProgressBar(value=0, bar_height=10, color=C["accent"], bgcolor=C["surf_elem"])
        self.s_done = ft.Text("0/0", size=22, weight=ft.FontWeight.BOLD)
        self.s_ok = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=C["success"])
        self.s_fail = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=C["error"])

        self.role = input_field("ID Nhân Vật", "Ví dụ: 1919565206")
        self.role_m = input_field("Danh sách ID (mỗi ID 1 dòng)", "1919565206\n1919565207", multiline=True, min_lines=4, max_lines=8, visible=False)
        self.custom = input_field("Danh sách Code riêng (mỗi code 1 dòng)", "CODEFREE01\nCODEFREE02", multiline=True, min_lines=4, max_lines=8, visible=False)
        self.mode_grp = self.mode_group(["Cá Nhân (1 ID)", "Nông Dân (Nhiều ID)"], 0, self.on_mode)
        self.src_grp = self.mode_group(["Code hệ thống", "Code riêng"], 0, self.on_src)

        self.src_hint = ft.Container(
            content=ft.Text("Lấy code từ hệ thóng", size=12, color=C["muted"]),
            bgcolor=C["surf_elem"], border=border_all(1, C["border"]), border_radius=10, padding=10,
        )

        self.start_btn = ft.Button(
            "Bắt đầu Nhập Code",
            on_click=self.start,
            style=ft.ButtonStyle(
                color={"": C["bg"]},
                bgcolor={"": C["text"]},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
        self.stop_btn = ft.Button(
            "Dừng lại",
            on_click=self.stop,
            style=ft.ButtonStyle(
                color={"": C["text"]},
                bgcolor={"": C["error"]},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
        self.stop_btn.visible = False

        self.dash = ft.Column(spacing=16, controls=[
            self.pb,
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[
                self.stat_box(self.s_done, "Tiến trình"),
                self.stat_box(self.s_ok, "Thành công"),
                self.stat_box(self.s_fail, "Thất bại"),
            ]),
            ft.Container(content=self.logs, bgcolor=C["surf_elem"],
                border=border_all(1, C["border"]), border_radius=12, padding=12, height=280),
        ])

        self.card_col = ft.Column(spacing=16, controls=[
            ft.Text("Cảm ơn bạn đã sử dụng tool!", size=13, color=C["muted"]),
            self.mode_grp,
            self.role,
            self.role_m,
            self.src_grp,
            self.src_hint,
            self.custom,
            ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[self.start_btn, self.stop_btn]),
        ])

        self.left = ft.Container(content=self.card_col,
            bgcolor=C["card"], border=border_all(1, C["border"]), border_radius=16, padding=24, expand=1)
        self.right = ft.Container(content=self.donate_content(),
            bgcolor=C["card"], border=border_all(1, C["border"]), border_radius=16, padding=24, expand=1)

        self.cards_row = ft.Row(spacing=16, controls=[self.left, self.right])
        self.main_col = ft.Column(spacing=16, controls=[
            self.header(),
            self.cards_row,
        ])
        self.page.add(self.main_col)
        self.page.update()

    def on_resized(self, e):
        w = self.page.width
        if w < 680 and isinstance(self.cards_row, ft.Row):
            self.left.expand = 1
            self.right.expand = None
            idx = self.main_col.controls.index(self.cards_row)
            self.main_col.controls.remove(self.cards_row)
            self.cards_row = ft.Column(spacing=16, controls=[self.left, self.right])
            self.main_col.controls.insert(idx, self.cards_row)
        elif w >= 680 and isinstance(self.cards_row, ft.Column):
            self.left.expand = 1
            self.right.expand = 1
            idx = self.main_col.controls.index(self.cards_row)
            self.main_col.controls.remove(self.cards_row)
            self.cards_row = ft.Row(spacing=16, controls=[self.left, self.right])
            self.main_col.controls.insert(idx, self.cards_row)
        self.page.update()

    def rebuild_mode_grp(self):
        sb = self.mode_grp.content
        sb.selected = [str(self.mode_idx)]
        self.page.update()

    def rebuild_src_grp(self):
        sb = self.src_grp.content
        sb.selected = [str(self.src_idx)]
        self.page.update()

    def header(self):
        return ft.Container(content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
            ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                ft.Image(src="logo-dtmcfl.svg", width=54, height=54, fit=ft.BoxFit.CONTAIN),
                ft.Column(spacing=2, controls=[
                    ft.Text("Crossfire: Legends", size=24, weight=ft.FontWeight.BOLD),
                ]),
            ]),
            ft.Text("Nhập giftcode tự động • Tạo bởi DTM", size=14, color=C["muted"]),
        ]), margin=ft.Margin(left=0, top=0, right=0, bottom=8))

    def stat_box(self, val, label):
        return ft.Container(content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
            controls=[val, ft.Text(label, size=11, color=C["muted"])]),
            bgcolor=C["surf_elem"], border=border_all(1, C["border"]), border_radius=12, padding=12, expand=True)

    def donate_content(self):
        return ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16, controls=[
            ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                ft.Text("☕", size=28), ft.Text("Ủng hộ tác giả 1 cốc Coffee", size=20, weight=ft.FontWeight.BOLD)]),
            ft.Text("Nếu tool hữu ích với bạn, hãy mời mình 1 cốc cà phê nhé! Mọi đóng góp đều là động lực để mình phát triển thêm.",
                size=14, color=C["muted"], text_align=ft.TextAlign.CENTER),
            ft.Container(content=ft.Image(
                src="https://img.vietqr.io/image/VCB-1026047424-compact2.png?accountName=DINH%20DUC%20DUONG&addInfo=Ung%20ho%20CFL%20Giftcode",
                width=240, height=240, fit=ft.BoxFit.CONTAIN),
                bgcolor=C["surface"], border_radius=16, padding=12),
            ft.Container(content=ft.Column(spacing=8, controls=[
                self.br("Ngân hàng", "Vietcombank (VCB)"),
                self.br("Số tài khoản", "1026047424", copyable=True),
                self.br("Chủ tài khoản", "DINH DUC DUONG"),
            ]), bgcolor=C["surf_elem"], border=border_all(1, C["border"]), border_radius=12, padding=20),
            ft.Text("Quét mã QR bằng app ngân hàng bất kỳ để chuyển khoản", size=12, color=C["muted"]),
        ])

    def br(self, label, value, copyable=False):
        val = ft.Text(value, size=14, weight=ft.FontWeight.BOLD)
        if copyable:
            btn = ft.TextButton("Sao chép", on_click=lambda e: self.cp(value, btn),
                style=ft.ButtonStyle(color=C["muted"]))
            val = ft.Row(controls=[ft.Text(value, size=14, weight=ft.FontWeight.BOLD), btn])
        return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[ft.Text(label, size=13, color=C["muted"]), val])

    def cp(self, text, btn):
        self.page.clipboard = text
        btn.text = "Đã sao chép"
        self.page.update()

    def on_mode(self, idx):
        self.mode_idx = idx
        self.role.visible = (idx == 0)
        self.role_m.visible = (idx == 1)
        self.rebuild_mode_grp()

    def on_src(self, idx):
        self.src_idx = idx
        self.custom.visible = (idx == 1)
        self.src_hint.visible = (idx == 0)
        self.rebuild_src_grp()

    def alog(self, msg, code="", ok=False, err=False):
        color = C["error"] if err else (C["success"] if ok else C["text"])
        parts = [ft.Text(f"[{datetime.now().strftime('%H:%M:%S')}] ", size=12, color=C["muted"])]
        if code:
            parts.append(ft.Text(code, size=13, weight=ft.FontWeight.BOLD, color=C["accent"]))
        parts.append(ft.Text(msg, size=13, color=color))
        self.logs.controls.append(ft.Row(controls=parts, spacing=4))
        self.page.update()

    def stats(self, done, total, ok, fail):
        self.s_done.value = f"{done}/{total}"
        self.s_ok.value = str(ok)
        self.s_fail.value = str(fail)
        self.pb.value = done / total if total > 0 else 0
        self.page.update()

    def start(self, e):
        sid = "101"
        raw = self.role.value.strip() if self.mode_idx == 0 else self.role_m.value.strip()
        rids = [r.strip() for r in raw.split("\n") if r.strip()] if raw else []
        if not rids:
            self.alog("Vui lòng nhập ít nhất 1 Role ID!", err=True)
            return
        ccodes = []
        if self.src_idx == 1:
            rc = self.custom.value.strip()
            ccodes = [c.strip().upper() for c in rc.split("\n") if c.strip()] if rc else []
        delay = 1.5
        self.is_running = True
        self.should_stop = False
        self.start_btn.visible = False
        self.stop_btn.visible = True
        if self.dash not in self.main_col.controls:
            self.main_col.controls.append(self.dash)
        self.dash.visible = True
        self.logs.controls.clear()
        self.pb.value = 0
        self.s_done.value = "0/0"
        self.s_ok.value = "0"
        self.s_fail.value = "0"
        self.page.update()
        self.alog(f"🎮 CFL • Server: {sid} • {len(rids)} tài khoản")
        threading.Thread(target=self.run, args=(rids, sid, ccodes, delay), daemon=True).start()

    def run(self, rids, sid, ccodes, delay):
        if self.src_idx == 0:
            self.alog("📡 Đang đồng bộ code từ hệ thống...")
            rid0 = rids[0]
            codes = sync_codes_from_api(rid0)
            if codes:
                self.alog(f"✅ Đã lưu {len(codes)} code vào synced_codes.txt")
            else:
                self.alog("📂 Đọc từ synced_codes.txt có sẵn...")
                codes = load_synced_codes()
                if not codes:
                    self.alog("Không có code nào!", err=True)
                    self.finish()
                    return
        else:
            codes = ccodes
        if not codes:
            self.alog("Không có code nào!", err=True)
            self.finish()
            return
        total = len(codes)
        ok = 0
        fail = 0
        use_single = False
        for rid in rids:
            if self.should_stop:
                break
            self.alog(f"══════ ID: {rid} ══════")
            ok = 0
            fail = 0
            done = 0
            use_single = False
            for i in range(0, total, 5):
                if self.should_stop:
                    break
                batch = codes[i:i + 5]
                bn = i // 5 + 1
                if not use_single:
                    self.alog(f"Batch #{bn} — {len(batch)} codes (multi)")
                    try:
                        data, elapsed = redeem_multi(rid, batch, sid)
                        if "error" in data:
                            ec = data["error"].get("code", "?")
                            msg = data["error"].get("message", "")
                            self.alog(f"Multi reject! {tr(ec, msg)}", err=True)
                            self.alog("Chuyển sang single mode...")
                            use_single = True
                        else:
                            results = data.get("data", {}).get("codes", [])
                            if results:
                                for item in results:
                                    code = item.get("code", "?")
                                    ec = item.get("errorCode", 0)
                                    desc = item.get("description", "")
                                    if ec == 1:
                                        ok += 1
                                        self.alog(f"✓ {code}", ok=True)
                                        if self.src_idx == 1:
                                            save_codes_local([code])
                                            add_codes_to_api([code])
                                    else:
                                        fail += 1
                                        self.alog(f"✗ {code} — {tr(ec, desc)}", err=True)
                                    st = "success" if ec == 1 else "perm_fail"
                                    save_result_local(rid, code, st, desc)
                                    done += 1
                            else:
                                done += len(batch)
                                fail += len(batch)
                    except Exception as ex:
                        self.alog(f"Lỗi: {ex}", err=True)
                        self.alog("Chuyển sang single mode...")
                        use_single = True
                if use_single:
                    for code in codes[i:]:
                        if self.should_stop:
                            break
                        self.alog(f"Single: {code}")
                        try:
                            sd, se = redeem_single(rid, code, sid)
                            sec = sd.get("errorCode", sd.get("error", {}).get("code", 0))
                            smsg = sd.get("message", sd.get("error", {}).get("message", ""))
                            if sec == 1:
                                ok += 1
                                self.alog(f"✓ {code}", ok=True)
                                if self.src_idx == 1:
                                    save_codes_local([code])
                                    add_codes_to_api([code])
                            else:
                                fail += 1
                                self.alog(f"✗ {code} — {tr(sec, smsg)}", err=True)
                            st = "success" if sec == 1 else "perm_fail"
                            save_result_local(rid, code, st, smsg)
                        except Exception as ex:
                            fail += 1
                            self.alog(f"✗ {code} — {ex}", err=True)
                        done += 1
                        self.stats(done, total, ok, fail)
                        time.sleep(delay)
                    break
                self.stats(done, total, ok, fail)
                if i + 5 < total:
                    time.sleep(delay)
            self.alog(f"✨ Hoàn tất ID {rid} (✓{ok} ✗{fail})")
        if ok > 0:
            self.alog("💾 Đã lưu kết quả vào máy")
        self.alog(f"🎉 Hoàn tất! ✓{ok} ✗{fail} / {total} codes", ok=True)
        self.finish()

    def finish(self):
        self.is_running = False
        self.start_btn.visible = True
        self.stop_btn.visible = False
        self.page.update()

    def stop(self, e):
        self.should_stop = True
        self.alog("⚠️ Đang dừng...", err=True)
        self.stop_btn.visible = False
        self.page.update()


def main(page: ft.Page):
    CFLApp(page)

if __name__ == "__main__":
    ft.run(main=main)
