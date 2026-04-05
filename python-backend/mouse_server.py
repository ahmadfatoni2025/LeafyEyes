import asyncio
import websockets
import json
import pyautogui

# Mematikan Pause PyAutoGUI otomatis (agar real-time)
pyautogui.PAUSE = 0
# Opsional: Jika kursor tersangkut di pinggir bisa dimatikan dengan False
pyautogui.FAILSAFE = True 

SCREEN_W, SCREEN_H = pyautogui.size()

class MouseController:
    def __init__(self):
        self.prev_x = SCREEN_W // 2
        self.prev_y = SCREEN_H // 2
        
    def smooth(self, target_x, target_y, factor=2.5):
        # Smoothing sederhana agar gerakan tidak patah-patah
        smooth_x = self.prev_x + (target_x - self.prev_x) / factor
        smooth_y = self.prev_y + (target_y - self.prev_y) / factor
        self.prev_x = smooth_x
        self.prev_y = smooth_y
        return int(smooth_x), int(smooth_y)

controller = MouseController()

async def control_mouse(websocket):
    print("\n🟢 [SUCCESS] Website Next.js telah terhubung ke Sistem Windows!")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get("action")
                
                if action == "move":
                    # Menerima rasio (0.0 - 1.0) dari web
                    norm_x = data.get("x", 0.5)
                    norm_y = data.get("y", 0.5)
                    
                    # Mapping ke ukuran layar monitor asli
                    target_x = int(norm_x * SCREEN_W)
                    target_y = int(norm_y * SCREEN_H)
                    
                    # Terapkan smoothing
                    final_x, final_y = controller.smooth(target_x, target_y)
                    
                    # Pindahkan kursor Windows asli
                    pyautogui.moveTo(final_x, final_y)
                    
                elif action == "click":
                    pyautogui.click()
                    print("--> Klik Kiri OS!")
                    
                elif action == "scroll":
                    # Scroll amount
                    pyautogui.scroll(-30) # Nilai negatif/positif bergantung arah
                    
            except Exception as loop_e:
                pass # Abaikan error parsing sesaat
                
    except websockets.exceptions.ConnectionClosed:
        print("🔴 [DISCONNECTED] Website Next.js terputus dari server.")

async def main():
    print("="*60)
    print("🚀 PYTHON MOUSE SERVER BERJALAN")
    print(f"🖥️  Resolusi Layar Terdeteksi: {SCREEN_W} x {SCREEN_H}")
    print("Mendengarkan koneksi WebSocket di port ws://localhost:8765...")
    print("Buka website Next.js Anda dan klik 'Mulai'!")
    print("="*60)
    async with websockets.serve(control_mouse, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer dimatikan.")
