import sqlite3  
import json  
import hashlib  
import httpx  
from nonebot import logger
from .config import wx_config

class ConversationStorage:  
    API_Key = wx_config.wx_api_key
    Secret_Key = wx_config.wx_secret_key 
    max_messages = wx_config.MAX_MESSAGES  # 设置最大对话次数  
    access_token = ""
    single_url = ""
  
    def __init__(self, db_name):  
        self.db_name = db_name  
        self.conn = sqlite3.connect(db_name)  
        self.conn.row_factory = sqlite3.Row  
        self.cursor = self.conn.cursor()  
        self.table_name = 'conversation_store'  
        self.setup_db()  
  
    def setup_db(self):  
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} (hash TEXT PRIMARY KEY, data TEXT)")  
        self.conn.commit()  
  
    def generate_hash(self, user_id, group_id):  
        combined = f"{user_id}:{group_id}"  
        return hashlib.sha256(combined.encode()).hexdigest()  
  
    def read_conversation(self, user_id, group_id):  
        hash_value = self.generate_hash(user_id, group_id)  
        with self.conn:  
            self.cursor.execute(f"SELECT data FROM {self.table_name} WHERE hash=?", (hash_value,))  
            row = self.cursor.fetchone()  
            if row:  
                conversation = json.loads(row[0])  
                return conversation  
            else:  
                return None  
                
    async def init_access_token(self):  
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.API_Key}&client_secret={self.Secret_Key}"  
        async with httpx.AsyncClient() as client:  
            response = await client.post(url)  
            self.access_token = response.json().get("access_token")
            self.single_url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/eb-instant?access_token={self.access_token}"
    
    async def send_single_message(self, content):
        conversation = {"messages": [{"role": "user", "content": content}]}
        headers = {'Content-Type': 'application/json'}  
        async with httpx.AsyncClient() as client:  
            response = await client.post(self.single_url, headers=headers, json=conversation, timeout=60.0)  
        if res := response.json().get("result"):
            return res
        return "请求失败"
         
          
    async def send_multi_message(self, user_id, group_id, content):
        conversation = self.read_conversation(user_id, group_id) or {"messages": []}  
        new_message = {"role": "user", "content": content}  
        message_list = conversation["messages"]
        message_list.append(new_message)  
        # access_token = await get_access_token()  
        # logger.info(f'conversation: {conversation}')
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={self.access_token}"  
        headers = {'Content-Type': 'application/json'}  
        async with httpx.AsyncClient() as client:  
            response = await client.post(url, headers=headers, json=conversation, timeout=60.0)  
        
        if res := response.json().get("result"):
            new_message = {"role": "assistant", "content": res}
            message_list.append(new_message)
        elif res := response.json().get('error_msg'):
            new_message = {"role": "assistant", "content": res}
            message_list.append(new_message)
        self.write_conversation(user_id, group_id, conversation)
        if len(message_list) >= self.max_messages * 2:  
            self.clear(user_id, group_id)
            new_message = {"role": "assistant", "content": "超出对话长度，已清空对话记录"}
            message_list.append(new_message)
        return message_list
  
    def write_conversation(self, user_id, group_id, conversation):  
        hash_value = self.generate_hash(user_id, group_id)  
        json_data = json.dumps(conversation)  
        with self.conn:  
            self.cursor.execute(f"INSERT OR REPLACE INTO {self.table_name} (hash, data) VALUES (?, ?)", (hash_value, json_data))  
  
    def clear(self, user_id, group_id):  
        hash_value = self.generate_hash(user_id, group_id)  
        with self.conn:  
            self.cursor.execute(f"DELETE FROM {self.table_name} WHERE hash=?", (hash_value,))

class WxClient:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = ""
        self.url = ""
    
    async def init_access_token(self):
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"  
        async with httpx.AsyncClient() as client:  
            response = await client.post(url)  
            self.access_token = response.json().get("access_token")
            self.url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={self.access_token}"
    
    async def send_message(self, content: str) -> str:
        conversation = {"messages": [{"role": "user", "content": content}]}
        headers = {'Content-Type': 'application/json'}  
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, headers=headers, json=conversation, timeout=60.0)
                response.raise_for_status()  # 检查HTTP请求是否成功
                data = response.json()
                return data.get("result", "返回为空")
            except httpx.RequestError as exc:
                return f"请求错误: {exc}"
            except httpx.HTTPStatusError as exc:
                return f"HTTP错误: {exc.response.status_code}"
