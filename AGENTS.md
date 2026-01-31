# AGENTS.md

## Mục tiêu
Xây hệ thống “GPT + điều khiển chuột/bàn phím” trên Windows theo mức **100% tự động**, nhưng **bắt buộc hỏi xác nhận** ở các bước nguy hiểm. Ưu tiên **dễ làm**, ổn định vừa đủ.

## Chọn stack (dễ làm)
- **Python + pyautogui** (ưu tiên)
- OCR/Computer Vision: **pytesseract + opencv**
- (Tuỳ chọn) kiểm soát cửa sổ: **pygetwindow** hoặc **pywinauto**

Lý do: cài đơn giản, nhiều ví dụ, đủ cho MVP.

## Kiến trúc
1) **GPT nhận lệnh tự do** (text)
2) **Chuẩn hoá về Action Schema** (JSON có kiểm soát)
3) **Guardrails** (allowlist app, chặn hành động nguy hiểm, hỏi xác nhận)
4) **Executor** thực thi bằng pyautogui (click/type/hotkey/open)
5) **Vision** (tìm nút theo ảnh/text) khi cần

## Action Schema (ví dụ)
```json
{
  "action": "click|type|hotkey|open_app|sleep|locate_text|locate_image|scroll",
  "args": { "x": 0, "y": 0, "text": "", "keys": ["CTRL","L"], "app": "chrome" }
}
```

## Guardrails (bắt buộc)
- **Allowlist app**: chỉ cho phép thao tác trong danh sách ứng dụng (vd: chrome, notepad)
- **Verify active window** trước khi click/type/hotkey
- **Nguy hiểm → hỏi xác nhận**:
  - mở PowerShell/Command Prompt, Registry Editor
  - thao tác trên file hệ thống, xoá file, cài phần mềm
  - dán/nhập mật khẩu, gửi thông tin nhạy cảm
- **Kill switch**: bật `pyautogui.FAILSAFE = True` để kéo chuột lên góc trái trên màn hình để dừng

## Kế hoạch build (MVP)
1) **CLI**: nhận câu lệnh tự nhiên
2) **Parser**: GPT → Action Schema
3) **Executor**: map action -> pyautogui
4) **Guardrails**: allowlist + confirm
5) **OCR**: locate_text (pytesseract) để click theo text khi cần

## Lệnh cài (gợi ý)
- Python 3.10+
- `pip install pyautogui pytesseract opencv-python pygetwindow`
- Cài Tesseract OCR (Windows installer) và add PATH

## Hành vi chuẩn của hệ thống
- Mặc định **tự động**, không hỏi xác nhận
- Chỉ hỏi xác nhận nếu **trùng quy tắc nguy hiểm**
- Nếu không chắc target app, **dừng và yêu cầu chọn app**

## Checklist kiểm thử
- Mở Chrome, Ctrl+L, gõ URL, Enter
- Click tọa độ x,y
- Locate button theo text (OCR) rồi click
- Thử hành động nguy hiểm → bắt buộc hỏi xác nhận
- Kiểm tra kill switch góc trái trên

## Gợi ý nâng cấp
- Lưu lịch sử actions + rollback nhẹ
- Thêm “dry-run” mô phỏng trước khi chạy
- Tự hiệu chỉnh độ trễ (sleep) giữa các thao tác

---
Nếu cần scaffold code mẫu, tạo thêm thư mục `src/` với các module:
- `src/agent.py` (parse lệnh)
- `src/guardrails.py`
- `src/executor.py`
- `src/vision.py`
- `src/main.py`
