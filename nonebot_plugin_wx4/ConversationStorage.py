import sqlite3  
import json  
import hashlib  
import httpx  
from nonebot import logger
from .config import wx_config

class ConversationStorage:  
    API_Key = wx_config.API_KEY  
    Secret_Key = wx_config.SECRET_KEY  
    max_messages = wx_config.MAX_MESSAGES  # 设置最大对话次数  
  
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
  
    async def send_message(self, user_id, group_id, content):
        async def get_access_token():  
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.API_Key}&client_secret={self.Secret_Key}"  
            async with httpx.AsyncClient() as client:  
                response = await client.post(url)  
                return response.json().get("access_token")  
  
        conversation = self.read_conversation(user_id, group_id) or {"messages": []}  
        new_message = {"role": "user", "content": content}  
        message_list = conversation["messages"]
        message_list.append(new_message)  
        access_token = await get_access_token()  
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={access_token}"  
        headers = {'Content-Type': 'application/json'}  
        async with httpx.AsyncClient() as client:  
            response = await client.post(url, headers=headers, json=conversation, timeout=60.0)  
        
        result_str = response.json().get("result")
        new_message = {"role": "assistant", "content": result_str}
        message_list.append(new_message)
        if len(message_list) >= self.max_messages * 2:  
            self.clear(user_id, group_id)
            new_message = {"role": "assistant", "content": "超出对话长度，已清空对话记录"}
            message_list.append(new_message)
        self.write_conversation(user_id, group_id, conversation)  
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
