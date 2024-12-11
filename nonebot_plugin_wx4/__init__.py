from nonebot import on_command, logger, require, get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message, PrivateMessageEvent, GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from .ConversationStorage import WxClient
from nonebot.plugin import PluginMetadata
from .config import Config, wx_config
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic
import re

__plugin_meta__ = PluginMetadata(
    name="文心一言4适配",
    description="文心一言4适配的连续对话",
    usage="《文心 内容》向文心提出问题，《失忆术》忘掉以往对话",

    type="application",

    homepage="https://github.com/Pasumao/nonebot-plugin-wx4",

    config=Config,

    supported_adapters={"~onebot.v11",},
)

wx = on_command("%", block = True, priority = 1)
# clear_wx = on_command("***", block = True, priority = 1)
  
# wx_client = ConversationStorage(wx_config.DBNAME)
wx_client = WxClient(wx_config.wx_api_key, wx_config.wx_secret_key)

@get_driver().on_startup
async def _():
    await wx_client.init_access_token()
    logger.info(f"wx4 init, access_token: {wx_client.access_token}")


@wx.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    user_id, group_id = get_id(event)
    content = args.extract_plain_text().strip()
    if reply := event.reply:
        reply = reply.message.extract_plain_text().strip()
        if content:
            match = re.match(r"(\d*)(\D*)", content)
            delete_len = int(match.group(1)) if match.group(1) else 0
            premise = match.group(2)
            content = premise + " " + reply[delete_len:]
        else:
            content = reply
        content = content.strip()
    if content == "":
        await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '38')
        return
    await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '282')
    ai_reply = await wx_client.send_message(content)
    if "```" in ai_reply:
        msg = [
            MessageSegment.reply(event.message_id),
            MessageSegment.image(await md_to_pic(md=ai_reply))
        ]
    else:
        msg = [
            MessageSegment.node_custom(user_id = user_id, nickname = 'you', content = content),
            MessageSegment.node_custom(user_id = bot.self_id, nickname = 'wx4', content = ai_reply)
        ]
    await wx.send(msg)
    # msg_list = await wx_client.send_multi_message(user_id, group_id, content)
    # nickname = (await bot.get_login_info())['nickname']
    # username = (await bot.get_group_member_info(group_id=group_id, user_id=user_id))['nickname']
    # nodes = []
    # msg_list.reverse()
    # for msg in msg_list:
    #     if msg['role'] == 'assistant':
    #         uid, name = bot.self_id, nickname
    #     else:
    #         uid, name = user_id, username
    #     if content := msg.get('content'):
    #         if "```" in content:
    #             content = MessageSegment.image(await md_to_pic(md=content))
    #         nodes.append(MessageSegment.node_custom(user_id=uid, nickname=name, content=content))
    # await wx.finish(nodes)

# @clear_wx.handle()
# async def _(event: MessageEvent):
#     user_id, group_id = get_id(event)
#     wx_client.clear(user_id, group_id)
#     await clear_wx.finish("clear finished")

def get_id(event: MessageEvent) -> (int, int):
    return event.user_id, event.group_id if isinstance(event, GroupMessageEvent) else None