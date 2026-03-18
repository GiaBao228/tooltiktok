# TikDown - Premium TikTok Downloader

Dự án TikTok Downloader mạnh mẽ với giao diện Premium Glassmorphism, hỗ trợ tải video Full HD không logo.

## 🚀 Tính năng chính
- Tải video TikTok không watermark (Logo).
- Hỗ trợ tải chất lượng gốc (Full HD).
- Tải nhạc nền (MP3).
- Giao diện hiện đại, hiệu ứng tuyết rơi nhẹ nhàng.
- Tương thích hoàn toàn với Mobile & Desktop.

## 🛠 Cách chạy Local
1. Cài đặt thư viện: `pip install -r requirements.txt`
2. Chạy server: `python server.py`
3. Truy cập: `http://localhost:5000`

## 🌍 Cách Deploy Online (Render.com)
1. Đẩy code này lên một repository GitHub mới của bạn.
2. Truy cập [Render.com](https://render.com) và tạo một **Web Service** mới.
3. Kết nối với repository GitHub của bạn.
4. Render sẽ tự động nhận diện:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server:app`
5. Nhấn **Deploy** và đợi trong 1-2 phút là bạn có link online!

## 📜 Cấu trúc dự án
- `server.py`: Backend Flask xử lý API.
- `index.html`: Frontend Premium duy nhất.
- `requirements.txt`: Chứa dependencies (`flask`, `requests`, `gunicorn`).
- `Procfile`: Cấu hình cho Hosting v1.
- `.gitignore`: Loại bỏ các file rác khi đẩy lên Git.

---
© 2026 Designed & Developed by Nguyễn Đức Gia Bảo
