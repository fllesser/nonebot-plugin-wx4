from pydantic import BaseModel  
from nonebot import get_plugin_config, logger

class Config(BaseModel):  
    # 在这里定义你的配置项  
    DBNAME: str = "wxbot.db"
    API_KEY: str = ""
    SECRET_KEY: str = ""
    MAX_MESSAGES: int = 5 
    
    
wx_config: Config = get_plugin_config(Config)
