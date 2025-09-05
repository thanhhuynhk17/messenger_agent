from pyngrok import ngrok

# Port bạn muốn expose, ví dụ Flask app chạy ở 5000
PORT = 5000

# Mở tunnel
public_url = ngrok.connect(PORT)
print("Public URL:", public_url)

# Giữ script chạy để tunnel không bị đóng
print("Ngrok tunnel is running. Press Ctrl+C to stop.")
try:
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Tunnel stopped.")
    ngrok.kill()


