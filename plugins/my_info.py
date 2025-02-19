from nonebot import on_command
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent
from models.group_member_info import GroupInfoUser
from datetime import timedelta
from models.level_user import LevelUser

__plugin_name__ = "更新群组成员列表 [Hidden]"
__plugin_usage__ = "用法：\n" "更新群员的信息"


get_my_group_info = on_command("我的信息", permission=GROUP, priority=1, block=True)
my_level = on_command("我的权限", permission=GROUP, priority=5, block=True)


@get_my_group_info.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    result = await get_member_info(event.user_id, event.group_id)
    await get_my_group_info.finish(result)


async def get_member_info(user_qq: int, group_id: int) -> str:
    user = await GroupInfoUser.get_member_info(user_qq, group_id)
    if user is None:
        return "该群员不在列表中，请更新群成员信息"
    result = ""
    result += "昵称:" + user.user_name + "\n"
    result += "加群时间:" + str(user.user_join_time.date() + timedelta(hours=8))
    return result


@my_level.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    if (level := await LevelUser.get_user_level(event.user_id, event.group_id)) == -1:
        await my_level.finish("您目前没有任何权限了，硬要说的话就是0吧~", at_sender=True)
    await my_level.finish(f"您目前的权限等级：{level}", at_sender=True)
