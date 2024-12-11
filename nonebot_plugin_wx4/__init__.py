from nonebot import on_command, logger, require
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message, PrivateMessageEvent, GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from .ConversationStorage import ConversationStorage
from nonebot.plugin import PluginMetadata
from .config import Config, wx_config
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

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
clear_wx = on_command("***", block = True, priority = 1)
  
wxbot = ConversationStorage(wx_config.DBNAME)
await wxbot.init_access_token()

@wx.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    user_id, group_id = get_id(event)
    content = args.extract_plain_text().strip()
    if reply := event.reply:
        content += " " + reply.message.extract_plain_text().strip()
    if content.strip() == "":
        return
    await bot.call_api("set_msg_emoji_like", message_id = event.message_id, emoji_id = '282')
    ai_reply = await wxbot.send_single_message(content)
    await wx.send(MessageSegment.image(await md_to_pic(md=ai_reply)), at_sender=True)
    # msg_list = await wxbot.send_multi_message(user_id, group_id, content)
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

@clear_wx.handle()
async def _(event: MessageEvent):
    user_id, group_id = get_id(event)
    wxbot.clear(user_id, group_id)
    await clear_wx.finish("clear finished")

def get_id(event: MessageEvent) -> (int, int):
    return event.user_id, event.group_id if isinstance(event, GroupMessageEvent) else None