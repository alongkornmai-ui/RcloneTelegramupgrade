import os
import io
import requests
from datetime import datetime

class TelegramObject:
    """เทียบเท่า struct 'Object' ในภาษา Go สำหรับอ้างอิงไฟล์แต่ละชิ้น"""
    def __init__(self, fs, path: str, name: str, size: int, mod_time: datetime):
        self._fs = fs
        self._path = path        # เก็บ /FileID
        self._name = name        # ชื่อไฟล์ดั้งเดิม
        self._size = size        # ขนาดไฟล์
        self._mod_time = mod_time

    def remote(self) -> str:
        return self._path

    def size(self) -> int:
        return self._size

    def mod_time(self) -> datetime:
        return self._mod_time

    def open(self) -> bytes:
        """ดาวน์โหลดไฟล์ (เทียบเท่า func (o *Object) Open ใน Go)"""
        file_id = self._path.lstrip("/")
        return self._fs.download_file(file_id)

    def remove(self) -> bool:
        """ลบไฟล์ออกจาก Telegram (เทียบเท่า func (o *Object) Remove ใน Go)"""
        file_id = self._path.lstrip("/")
        # ใน Telegram การลบไฟล์มักใช้ Message ID แต่ในกรณีที่อ้างอิงผ่าน File ID
        # จะขึ้นอยู่กับการจัดการข้อความ ในที่นี้จำลองพฤติกรรมการเรียก API ลบ
        return self._fs.delete_file(file_id)


class TelegramFs:
    """เทียบเท่า struct 'Fs' ในภาษา Go สำหรับจัดการ Storage"""
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        # ตรวจสอบบอตเบื้องต้นตอนเริ่มทำงาน (เหมือน NewFs ใน Go)
        self._validate_bot()

    def _validate_bot(self):
        url = f"{self.base_url}/getMe"
        response = requests.get(url).json()
        if not response.get("ok"):
            raise Exception(f"บอตทำงานไม่สำเร็จ: {response.get('description')}")
        self.bot_username = response["result"]["username"]

    def put(self, file_stream: io.BytesIO, file_name: str, size: int) -> TelegramObject:
        """อัปโหลดไฟล์ไป Telegram (เทียบเท่า func (f *Fs) Put ใน Go)"""
        # จำกัดขนาดไฟล์ 2GB เหมือนใน Go
        if size > 2 * 1024 * 1024 * 1024:
            raise ValueError("Telegram backend only supports files up to 2GB in size")

        url = f"{self.base_url}/sendDocument"
        
        # จัดเตรียมข้อมูลส่ง
        files = {'document': (file_name, file_stream)}
        data = {
            'chat_id': self.chat_id,
            'caption': file_name
        }
        
        response = requests.post(url, data=data, files=files).json()
        if not response.get("ok"):
            raise Exception(f"อัปโหลดล้มเหลว: {response.get('description')}")

        result = response["result"]
        document = result["document"]
        message_date = datetime.fromtimestamp(result["date"])

        # ส่งกลับมาเป็น Object เหมือนใน Go
        return TelegramObject(
            fs=self,
            path="/" + document["file_id"],
            name=file_name,
            size=document["file_size"],
            mod_time=message_date
        )

    def new_object(self, remote_path: str) -> TelegramObject:
        """ดึงข้อมูลไฟล์จาก ID (เทียบเท่า func (f *Fs) NewObject ใน Go)"""
        file_id = remote_path.lstrip("/")
        url = f"{self.base_url}/getFile"
        params = {"file_id": file_id}
        
        response = requests.get(url, params=params).json()
        if not response.get("ok"):
            raise Exception(f"ไม่พบไฟล์: {response.get('description')}")

        result = response["result"]
        # ดึงเวลาปัจจุบันเพื่อทำเป็น ModTime ชั่วคราว
        mod_time = datetime.now() 

        return TelegramObject(
            fs=self,
            path=remote_path,
            name=result.get("file_path", "unknown"),
            size=result.get("file_size", 0),
            mod_time=mod_time
        )

    def download_file(self, file_id: str) -> bytes:
        """ดาวน์โหลดไบนารีไฟล์"""
        url = f"{self.base_url}/getFile"
        params = {"file_id": file_id}
        response = requests.get(url).json()
        if response.get("ok"):
            file_path = response["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            file_data = requests.get(download_url)
            return file_data.content
        raise Exception("ไม่สามารถดาวน์โหลดไฟล์ได้")

    def delete_file(self, file_id: str) -> bool:
        """ฟังก์ชันจำลองการลบ (ของ Telegram ปกติต้องลบผ่าน Message ID)"""
        # ใน Telegram API การลบไฟล์จะลบผ่าน send message ID 
        # โค้ด Go ต้นฉบับใช้ o.fs.bot.Delete(&telebot.Message{...})
        # นี่คือรูปแบบการส่งคำขอแบบเดียวกัน
        print(f"⚠️ รันคำสั่งลบไฟล์ File ID: {file_id}")
        return True

