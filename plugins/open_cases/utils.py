from models.buff_price import BuffPrice
from services.db_context import db
from datetime import datetime, timedelta
from utils.user_agent import get_user_agent
from configs.path_config import IMAGE_PATH
import aiohttp
import aiofiles
from models.open_cases_user import OpenCasesUser
import os
from services.log import logger
from utils.utils import get_bot
from models.group_remind import GroupRemind
from utils.utils import get_cookie_text
from asyncio.exceptions import TimeoutError
import pypinyin
from nonebot.adapters.cqhttp.exception import ActionFailed
from configs.config import BUFF_PROXY

url = "https://buff.163.com/api/market/goods"
# proxies = 'http://49.75.59.242:3128'


async def util_get_buff_price(case_name: str = "狂牙大行动") -> str:
    cookie = {'session': get_cookie_text('buff')}
    failed_list = []
    case = ""
    for i in pypinyin.pinyin(case_name, style=pypinyin.NORMAL):
        case += ''.join(i)
    if case_name == "狂牙大行动":
        case_id = 1
    elif case_name == "突围大行动":
        case_id = 2
    elif case_name == "命悬一线":
        case_id = 3
    elif case_name == '裂空':
        case_id = 4
    elif case_name == '光谱':
        case_id = 5
    else:
        return "未查询到武器箱"
    case = case.upper()
    CASE_KNIFE = eval(case + "_CASE_KNIFE")
    CASE_RED = eval(case + "_CASE_RED")
    CASE_PINK = eval(case + "_CASE_PINK")
    CASE_PURPLE = eval(case + "_CASE_PURPLE")
    CASE_BLUE = eval(case + "_CASE_BLUE")
    async with aiohttp.ClientSession(cookies=cookie, headers=get_user_agent()) as session:
        for total_list in [CASE_KNIFE, CASE_RED, CASE_PINK, CASE_PURPLE, CASE_BLUE]:
            print("----------------------------------")
            for skin in total_list:
                print(skin)
                if skin in ["蝴蝶刀 | 无涂装", '求生匕首 | 无涂装', '流浪者匕首 | 无涂装', '系绳匕首 | 无涂装', '骷髅匕首 | 无涂装']:
                    skin = skin.split('|')[0].strip()
                async with db.transaction():
                    name_list = []
                    price_list = []
                    parameter = {
                        "game": "csgo",
                        "page_num": "1",
                        "search": skin
                    }
                    try:
                        async with session.get(url, proxy=BUFF_PROXY, params=parameter, timeout=20) as response:
                            if response.status == 200:
                                data = (await response.json())["data"]
                                total_page = data["total_page"]
                                data = data["items"]
                                flag = False
                                if skin.find('|') == -1:    # in ['蝴蝶刀', '求生匕首', '流浪者匕首', '系绳匕首', '骷髅匕首']:
                                    for i in range(1, total_page + 1):
                                        name_list = []
                                        price_list = []
                                        parameter = {
                                            "game": "csgo",
                                            "page_num": f"{i}",
                                            "search": skin
                                        }
                                        async with session.get(url, params=parameter, timeout=20) as res:
                                            data = (await response.json())["data"]["items"]
                                            for j in range(len(data)):
                                                if data[j]['name'] in [f'{skin}（★）']:
                                                    name = data[j]["name"]
                                                    price = data[j]["sell_reference_price"]
                                                    name_list.append(name.split('（')[0].strip() + ' | 无涂装')
                                                    price_list.append(price)
                                                    print(name_list[-1])
                                                    print(price_list[-1])
                                                    flag = True
                                                    break
                                        if flag:
                                            break
                                else:
                                    try:
                                        for _ in range(total_page):
                                            for i in range(len(data)):
                                                name = data[i]["name"]
                                                price = data[i]["sell_reference_price"]
                                                name_list.append(name)
                                                price_list.append(price)
                                    except Exception as e:
                                        failed_list.append(skin)
                                        print(f"{skin}更新失败")
                            else:
                                failed_list.append(skin)
                                print(f"{skin}更新失败")
                    except Exception:
                        failed_list.append(skin)
                        print(f"{skin}更新失败")
                        continue
                    for i in range(len(name_list)):
                        name = name_list[i].strip()
                        price = float(price_list[i])
                        if name.find("（★）") != -1:
                            name = name[: name.find("（")] + name[name.find("）") + 1:]
                        if name.find("消音") != -1 and name.find("（S") != -1:
                            name = name.split("（")[0][:-4] + "（" + name.split("（")[1]
                            name = name.split("|")[0].strip() + " | " + name.split("|")[1].strip()
                        elif name.find("消音") != -1:
                            name = name.split("|")[0][:-5].strip() + " | " + name.split("|")[1].strip()
                        if name.find(" 18 ") != -1 and name.find("（S") != -1:
                            name = name.split("（")[0][:-5] + "（" + name.split("（")[1]
                            name = name.split("|")[0].strip() + " | " + name.split("|")[1].strip()
                        elif name.find(" 18 ") != -1:
                            name = name.split("|")[0][:-6].strip() + " | " + name.split("|")[1].strip()
                        dbskin = await BuffPrice.ensure(name, True)
                        if (dbskin.update_date + timedelta(8)).date() == datetime.now().date():
                            continue
                        await dbskin.update(
                            case_id=case_id,
                            skin_price=price,
                            update_date=datetime.now(),
                        ).apply()
                        print(f"{name_list[i]}---------->成功更新")
    result = None
    if failed_list:
        result = ""
        for fail_skin in failed_list:
            result += fail_skin + "\n"
    return result[:-1] if result else "更新价格成功"


async def util_get_buff_img(case_name: str = "狂牙大行动") -> str:
    cookie = {'session': get_cookie_text('buff')}
    error_list = []
    case = ""
    for i in pypinyin.pinyin(case_name, style=pypinyin.NORMAL):
        case += ''.join(i)
    path = "cases/" + case + "/"
    if not os.path.exists(IMAGE_PATH + path):
        os.mkdir(IMAGE_PATH + path)
    case = case.upper()
    CASE_KNIFE = eval(case + "_CASE_KNIFE")
    CASE_RED = eval(case + "_CASE_RED")
    CASE_PINK = eval(case + "_CASE_PINK")
    CASE_PURPLE = eval(case + "_CASE_PURPLE")
    CASE_BLUE = eval(case + "_CASE_BLUE")
    async with aiohttp.ClientSession(cookies=cookie, headers=get_user_agent()) as session:
        for total_list in [CASE_KNIFE, CASE_RED, CASE_PINK, CASE_PURPLE, CASE_BLUE]:
            for skin in total_list:
                parameter = {
                    "game": "csgo",
                    "page_num": "1",
                    "search": skin
                }
                if skin in ["蝴蝶刀 | 无涂装", '求生匕首 | 无涂装', '流浪者匕首 | 无涂装', '系绳匕首 | 无涂装', '骷髅匕首 | 无涂装']:
                    skin = skin.split('|')[0].strip()
                print("开始更新----->", skin)
                print(skin)
                skin_name = ''
                # try:
                async with session.get(url, proxy=BUFF_PROXY, params=parameter, timeout=20) as response:
                    if response.status == 200:
                        data = (await response.json())["data"]
                        total_page = data["total_page"]
                        flag = False
                        if skin.find('|') == -1:  # in ['蝴蝶刀', '求生匕首', '流浪者匕首', '系绳匕首', '骷髅匕首']:
                            for i in range(1, total_page + 1):
                                async with session.get(url, params=parameter, timeout=20) as res:
                                    data = (await response.json())["data"]["items"]
                                    for j in range(len(data)):
                                        if data[j]['name'] in [f'{skin}（★）']:
                                            img_url = data[j]['goods_info']['icon_url']
                                            for k in pypinyin.pinyin(skin + '无涂装', style=pypinyin.NORMAL):
                                                skin_name += ''.join(k)
                                            async with aiofiles.open(IMAGE_PATH + path + skin_name + ".png", 'wb') as f:
                                                print("------->开始写入 ", skin)
                                                async with session.get(img_url, timeout=7) as res:
                                                    await f.write(await res.read())
                                            flag = True
                                            break
                                if flag:
                                    break
                        else:
                            img_url = (await response.json())["data"]['items'][0]['goods_info']['icon_url']
                            for i in pypinyin.pinyin(skin.replace('|', '-').strip(), style=pypinyin.NORMAL):
                                skin_name += ''.join(i)
                            async with aiofiles.open(IMAGE_PATH + path + skin_name + ".png", 'wb') as f:
                                print("------->开始写入 ", skin)
                                async with session.get(img_url, timeout=7) as res:
                                    await f.write(await res.read())
                    # async with session.get(url, params=parameter, timeout=7) as response:
                    #     if response.status == 200:
                    #         img_url = (await response.json())["data"]['items'][0]['goods_info']['icon_url']
                    #         skin_name = ''
                    #         for i in pypinyin.pinyin(skin.split("|")[1].strip(), style=pypinyin.NORMAL):
                    #             skin_name += ''.join(i)
                    #         async with aiofiles.open(IMAGE_PATH + path + skin_name + ".png", 'wb') as f:
                    #             print("------->开始写入 ", skin)
                    #             async with session.get(img_url, timeout=7) as res:
                    #                 await f.write(await res.read())
                # except Exception:
                #     print("图片更新失败 ---->", skin)
                #     error_list.append(skin)
    result = None
    if error_list:
        result = ""
        for errskin in error_list:
            result += errskin + "\n"
    return result[:-1] if result else "更新图片成功"


async def get_price(dname):
    cookie = {'session': get_cookie_text('buff')}
    name_list = []
    price_list = []
    parameter = {
        "game": "csgo",
        "page_num": "1",
        "search": dname
    }
    try:
        async with aiohttp.ClientSession(cookies=cookie, headers=get_user_agent()) as session:
            async with session.get(url, params=parameter, timeout=7) as response:
                if response.status == 200:
                    try:
                        data = (await response.json())["data"]
                        total_page = data["total_page"]
                        data = data["items"]
                        for _ in range(total_page):
                            for i in range(len(data)):
                                name = data[i]["name"]
                                price = data[i]["sell_reference_price"]
                                name_list.append(name)
                                price_list.append(price)
                    except Exception as e:
                        return "没有查询到...", 998
                else:
                    return "访问失败！", response.status
    except TimeoutError as e:
        return "访问超时! 请重试或稍后再试!", 997
    result = f"皮肤: {dname}({len(name_list)})\n"
    # result = "皮肤: " + dname + "\n"
    for i in range(len(name_list)):
        result += name_list[i] + ": " + price_list[i] + "\n"
    return result[:-1], 999


async def update_count_daily():
    try:
        users = await OpenCasesUser.get_user_all()
        if users:
            for user in users:
                await user.update(
                    today_open_total=0,
                    ).apply()
        bot = get_bot()
        gl = await bot.get_group_list(self_id=bot.self_id)
        gl = [g['group_id'] for g in gl]
        for g in gl:
            if await GroupRemind.get_status(g, 'kxcz'):
                try:
                    await bot.send_group_msg(group_id=g, message="今日开箱次数重置成功")
                except ActionFailed:
                    logger.warning(f'{g} 群被禁言，无法发送 开箱重置提醒')
        logger.info("今日开箱次数重置成功")
    except Exception as e:
        logger.error(f'开箱重置错误 e:{e}')



# 蝴蝶刀（★） | 噩梦之夜 (久经沙场)
if __name__ == '__main__':
    print(util_get_buff_img("xxxx/"))
