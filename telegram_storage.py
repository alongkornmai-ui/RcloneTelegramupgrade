import os
import sys
import requests
from datetime import datetime

class TelegramStorage:
    def __init__(self, token: str, chat_id: str):
        """
        แปลงโครงสร้างมาจาก NewFs ในภาษา Go
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._verify_connection()

    def _verify_connection(self):
        """ตรวจสอบว่า Token ของ Bot ใช้งานได้จริงไหม"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10).json()
            if not response.get("ok"):
                print(f"❌ Error: Token ไม่ถูกต้อง ({response.get('description')})")
                sys.exit(1)
            print(f"🤖 เชื่อมต่อบอตสำเร็จ: @{response['result']['username']}")
        except Exception as e:
            print(f"❌ ไม่สามารถเชื่อมต่ออินเทอร์เน็ตเพื่อคุยกับ Telegram ได้: {e}")
            sys.exit(1)

    def upload_file(self, file_path: str) -> str:
        """
        เทียบเท่าฟังก์ชัน Put() ในภาษา Go (รองรับไฟล์สูงสุด 2GB)
        """
        if not os.path.exists(file_path):
            print(f"❌ ไม่พบไฟล์: {file_path}")
            return None

        file_size = os.path.getsize(file_path)
        # เช็กขีดจำกัด 2GB ของ Telegram
        if file_size > 2 * 1024 * 1024 * 1024:
            print("❌ Telegram รองรับขนาดไฟล์สูงสุดไม่เกิน 2GB เท่านั้น")
            return None

        file_name = os.path.basename(file_path)
        print(f"🚀 กำลังอัปโหลด: {file_name} ({file_size / (1024*1024):.2f} MB)...")

        url = f"{self.base_url}/sendDocument"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'document': (file_name, f)}
                data = {
                    'chat_id': self.chat_id,
                    'caption': file_name
                }
                # ตั้ง timeout ยาวหน่อยสำหรับไฟล์ขนาดใหญ่
                response = requests.post(url, data=data, files=files, timeout=300).json()

            if response.get("ok"):
                file_id = response["result"]["document"]["file_id"]
                message_id = response["result"]["message_id"]
                print(f"✅ อัปโหลดสำเร็จ!")
                print(f"🔑 File ID (สำหรับดาวน์โหลด): {file_id}")
                print(f"💬 Message ID (สำหรับลบ): {message_id}")
                return file_id
            else:
                print(f"❌ อัปโหลดล้มเหลว: {response.get('description')}")
                return None
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะอัปโหลด: {e}")
            return None

    def download_file(self, file_id: str, save_path: str):
        """
        เทียบเท่าฟังก์ชัน Open() และ Download ในภาษา Go
        """
        print("🔍 กำลังค้นหาที่อยู่ไฟล์...")
        url = f"{self.base_url}/getFile"
        params = {"file_id": file_id}
        
        try:
            response = requests.get(url, params=params, timeout=15).json()
            if not response.get("ok"):
                print(f"❌ ไม่พบไฟล์: {response.get('description')}")
                return False

            file_path = response["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            print("📥 กำลังดาวน์โหลดไฟล์...")
            with requests.get(download_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"✅ ดาวน์โหลดเสร็จสิ้น! บันทึกไว้ที่: {save_path}")
            return True
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะดาวน์โหลด: {e}")
            return False

    def delete_file(self, message_id: int) -> bool:
        """
        เทียบเท่าฟังก์ชัน Remove() ในภาษา Go
        (ลบข้อความที่มีไฟล์นั้นทิ้ง เพื่อเป็นการลบไฟล์ออกจาก Storage ของกลุ่ม)
        """
        url = f"{self.base_url}/deleteMessage"
        data = {
            'chat_id': self.chat_id,
            'message_id': message_id
        }
        try:
            response = requests.post(url, data=data, timeout=10).json()
            if response.get("ok"):
                print("✅ ลบไฟล์ออกจาก Telegram สำเร็จแล้ว")
                return True
            else:
                print(f"❌ ลบไฟล์ไม่สำเร็จ: {response.get('description')}")
                return False
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะลบ: {e}")
            return False
          
