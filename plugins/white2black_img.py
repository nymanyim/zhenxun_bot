from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, MessageEvent, GroupMessageEvent
from nonebot import on_command
from utils.utils import get_message_imgs, get_local_proxy, get_message_text, is_Chinese
from utils.message_builder import image
import aiohttp
import aiofiles
from configs.path_config import IMAGE_PATH
from utils.image_utils import CreateImg
from utils.user_agent import get_user_agent
from services.log import logger

# ZH_CN2EN 中文　»　英语
# ZH_CN2JA 中文　»　日语
# ZH_CN2KR 中文　»　韩语
# ZH_CN2FR 中文　»　法语
# ZH_CN2RU 中文　»　俄语
# ZH_CN2SP 中文　»　西语
# EN2ZH_CN 英语　»　中文
# JA2ZH_CN 日语　»　中文
# KR2ZH_CN 韩语　»　中文
# FR2ZH_CN 法语　»　中文
# RU2ZH_CN 俄语　»　中文
# SP2ZH_CN 西语　»　中文

__plugin_name__ = "黑白草图"

__plugin_usage__ = "用法： \n\t黑白图 [文字] [图片]\n示例：黑白草图 没有人不喜欢萝莉 [图片]"

w2b_img = on_command("黑白草图", aliases={"黑白图"}, priority=5, block=True)


@w2b_img.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    # try:
    img = get_message_imgs(event.json())
    msg = get_message_text(event.json())
    if not img or not msg:
        await w2b_img.finish(f"格式错误：\n" + __plugin_usage__)
    img = img[0]
    async with aiohttp.ClientSession(headers=get_user_agent()) as session:
        async with session.get(img, proxy=get_local_proxy()) as response:
            async with aiofiles.open(
                IMAGE_PATH + f"temp/{event.user_id}_w2b.png", "wb"
            ) as f:
                await f.write(await response.read())
    msg = await get_translate(msg)
    w2b = CreateImg(0, 0, background=IMAGE_PATH + f"temp/{event.user_id}_w2b.png")
    w2b.convert("L")
    msg_sp = msg.split("<|>")
    w, h = w2b.size
    add_h, font_size = init_h_font_size(h)
    bg = CreateImg(w, h + add_h, color="black", font_size=font_size)
    bg.paste(w2b)
    chinese_msg = formalization_msg(msg)
    if not bg.check_font_size(chinese_msg):
        if len(msg_sp) == 1:
            centered_text(bg, chinese_msg, add_h)
        else:
            centered_text(bg, chinese_msg + "<|>" + msg_sp[1], add_h)
    elif not bg.check_font_size(msg_sp[0]):
        centered_text(bg, msg, add_h)
    else:
        ratio = (bg.getsize(msg_sp[0])[0] + 20) / bg.w
        add_h = add_h * ratio
        bg.resize(ratio)
        centered_text(bg, msg, add_h)
    await w2b_img.send(image(b64=bg.pic2bs4()))
    logger.info(
        f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        f" 制作黑白草图 {msg}"
    )


def centered_text(img: CreateImg, text: str, add_h: int):
    top_h = img.h - add_h + (img.h / 100)
    bottom_h = img.h - (img.h / 100)
    text_sp = text.split("<|>")
    w, h = img.getsize(text_sp[0])
    if len(text_sp) == 1:
        w = (img.w - w) / 2
        h = top_h + (bottom_h - top_h - h) / 2
        img.text((w, h), text_sp[0], (255, 255, 255))
    else:
        br_h = top_h + (bottom_h - top_h) / 2
        w = (img.w - w) / 2
        h = top_h + (br_h - top_h - h) / 2
        img.text((w, h), text_sp[0], (255, 255, 255))
        w, h = img.getsize(text_sp[1])
        w = (img.w - w) / 2
        h = br_h + (bottom_h - br_h - h) / 2
        img.text((w, h), text_sp[1], (255, 255, 255))


async def get_translate(msg: str) -> str:
    url = f"http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule&smartresult=ugc&sessionFrom=null"
    data = {
        "type": "ZH_CN2JA",
        "i": msg,
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "ue": "UTF-8",
        "action": "FY_BY_CLICKBUTTON",
        "typoResult": "true",
    }
    async with aiohttp.ClientSession(headers=get_user_agent()) as session:
        try:
            async with session.post(url, data=data, proxy=get_local_proxy()) as res:
                data = await res.json()
                if data["errorCode"] == 0:
                    translate = data["translateResult"][0][0]["tgt"]
                    msg += "<|>" + translate
        except Exception as e:
            logger.warning(f"黑白草图翻译出错 e:{e}")
    return msg


def formalization_msg(msg: str) -> str:
    rst = ""
    for i in range(len(msg)):
        if is_Chinese(msg[i]):
            rst += msg[i] + " "
        else:
            rst += msg[i]
        if i + 1 < len(msg) and is_Chinese(msg[i + 1]) and msg[i].isalpha():
            rst += " "
    return rst


def init_h_font_size(h):
    #       高度      字体
    if h < 400:
        return init_h_font_size(400)
    elif 400 < h < 800:
        return init_h_font_size(800)
    return h * 0.2, h * 0.05
