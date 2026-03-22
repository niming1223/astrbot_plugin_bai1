from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os

# ===================== 全局配置 =====================
# 装备属性表格数据
EQUIP_TABLE = [
    ["装备属性", "英语", "橙装", "金装"],
    ["HP", "HP", "3.0", "3.0"],
    ["攻击", "Attack", "0.7", "0.7"],
    ["能力", "Ability", "15.7", "15.7"],
    ["火抗", "FireResistance", "63.7", "63.7"],
    ["耐力", "Stamina", "22", "26"],
    ["武器", "Weapon", "6.7", "6.7"],
    ["科技", "Sciece", "9.7", "9.7"],
    ["导航", "Pilot", "10.5", "10.5"],
    ["引擎", "Engine", "7.5", "9"],
    ["维修", "Repair", "0.6", "0.7"],
]

# 训练计算器核心常量（和HTML完全一致）
FATIGUE = {"大笑": 1, "微笑": 0.5, "流汗": 0.33}
FATIGUE_ORDER = ["大笑", "微笑", "流汗"]
MEDICINE = {
    "normal": {"一级药": {"main": 0.02, "sub": 0.01}, "二级药": {"main": 0.04, "sub": 0.02}, "三级药": {"main": 0.08, "sub": 0.03}, "四级药": {"main": 0.16, "sub": 0.05}},
    "endurance": {"一级耐力药": {"main": 0.08, "sub": 0.01}, "二级耐力药": {"main": 0.12, "sub": 0.01}, "三级耐力药": {"main": 0.16, "sub": 0.02}},
    "order": {
        "base": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"],
        "priorFour": ["一级药", "二级药", "四级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药"],
        "saveFive": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"]
    }
}
TRAIN = {
    "normal": {"绿色训练": {"main": 0.02, "sub": 0.01}, "蓝色训练": {"main": 0.08, "sub": 0.01}, "金色训练": {"main": 0.12, "sub": 0.02}},
    "endurance": {"耐力绿训": {"main": 0.02, "sub": 0}, "耐力蓝训": {"main": 0.08, "sub": 0.02}, "耐力金训": {"main": 0.16, "sub": 0.03}},
    "order": ["绿色训练", "蓝色训练", "金色训练", "耐力绿训", "耐力蓝训", "耐力金训"]
}
ATTR_LIST = [
    {"name": "生命", "key": "life"}, {"name": "攻击", "key": "atk"}, {"name": "维修", "key": "repair"},
    {"name": "能力", "key": "ability"}, {"name": "武器", "key": "weapon"}, {"name": "引擎", "key": "engine"},
    {"name": "科技", "key": "tech"}, {"name": "导航", "key": "nav"}, {"name": "耐力", "key": "endurance"}
]
ATTR_NAME_MAP = {item["name"]: item["key"] for item in ATTR_LIST}
ATTR_KEY_MAP = {item["key"]: item["name"] for item in ATTR_LIST}

# 用户数据存储（按用户ID隔离，多用户不冲突）
USER_DATA = {}

# ===================== 核心计算函数（和HTML逻辑1:1复刻） =====================
def calc_rate(max_limit, total_train, attr_value, fatigue_val, factor):
    numerator = (max_limit - total_train) * (max_limit - attr_value) * fatigue_val * factor * 100
    denominator = max_limit * max_limit
    return numerator / denominator

def can_add(max_limit, total_train, main_attr_value, fatigue_val, main_factor, sub_factor):
    main_rate = calc_rate(max_limit, total_train, main_attr_value, fatigue_val, main_factor)
    sub_rate = calc_rate(max_limit, total_train, 0, fatigue_val, sub_factor)
    return main_rate >= 1 and sub_rate < 1

def generate_plan(user_id, plan_type, strategy="base"):
    """生成加点方案，和HTML逻辑完全一致"""
    user = USER_DATA.get(user_id, {})
    max_limit = user.get("train_limit", 110)
    current_attr = user.get("current_attr", {item["key"]: 0 for item in ATTR_LIST})
    target_attr = user.get("target_attr", {item["key"]: 0 for item in ATTR_LIST})

    attr_values = current_attr.copy()
    total_train = sum(attr_values.values())
    start_total = total_train
    five_level_count = 0
    five_attr_count = {item["key"]: 0 for item in ATTR_LIST}
    result = []
    last_record = None
    current_focus_attr = None

    while True:
        # 检查是否全部完成
        all_finish = all(attr_values[item["key"]] >= target_attr[item["key"]] for item in ATTR_LIST)
        if all_finish or total_train >= max_limit:
            break
        
        success = False

        # 优先四药策略
        if plan_type == "medicine" and strategy == "priorFour":
            item_list = MEDICINE["order"][strategy]
            for item in item_list:
                if success:
                    break
                for f in FATIGUE_ORDER:
                    if success:
                        break
                    f_val = FATIGUE[f]
                    # 优先非维修属性
                    attr_list = [a for a in ATTR_LIST if a["name"] != "维修"]
                    if all(attr_values[a["key"]] >= target_attr[a["key"]] for a in attr_list):
                        attr_list = ATTR_LIST
                    for attr in attr_list:
                        attr_key = attr["key"]
                        if success or attr_values[attr_key] >= target_attr[attr_key]:
                            continue
                        # 获取系数
                        if attr["name"] == "耐力":
                            main_factor = MEDICINE["endurance"].get(item, {}).get("main")
                            sub_factor = MEDICINE["endurance"].get(item, {}).get("sub")
                        else:
                            main_factor = MEDICINE["normal"].get(item, {}).get("main")
                            sub_factor = MEDICINE["normal"].get(item, {}).get("sub")
                        if not main_factor:
                            continue
                        # 判断是否可加
                        if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                            old_val = attr_values[attr_key]
                            attr_values[attr_key] += 1
                            total_train += 1
                            # 合并连续记录
                            if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                last_record["end"] = attr_values[attr_key]
                                result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                            else:
                                result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                            success = True
        else:
            # 基础/最省五药策略/全训练
            for f in FATIGUE_ORDER:
                if success:
                    break
                f_val = FATIGUE[f]
                item_list = MEDICINE["order"][strategy] if plan_type == "medicine" else TRAIN["order"]
                for item in item_list:
                    if success:
                        break
                    # 优先非维修属性
                    attr_list = [a for a in ATTR_LIST if a["name"] != "维修"]
                    if all(attr_values[a["key"]] >= target_attr[a["key"]] for a in attr_list):
                        attr_list = ATTR_LIST
                    # 最省五药策略：单属性拉满
                    if plan_type == "medicine" and strategy == "saveFive":
                        if not current_focus_attr or attr_values[current_focus_attr["key"]] >= target_attr[current_focus_attr["key"]]:
                            current_focus_attr = next((a for a in attr_list if attr_values[a["key"]] < target_attr[a["key"]]), None)
                        if current_focus_attr:
                            attr_list = [current_focus_attr]
                    # 遍历属性
                    for attr in attr_list:
                        attr_key = attr["key"]
                        if success or attr_values[attr_key] >= target_attr[attr_key]:
                            continue
                        # 获取系数
                        if attr["name"] == "耐力":
                            data = MEDICINE if plan_type == "medicine" else TRAIN
                            main_factor = data["endurance"].get(item, {}).get("main")
                            sub_factor = data["endurance"].get(item, {}).get("sub")
                        else:
                            data = MEDICINE if plan_type == "medicine" else TRAIN
                            main_factor = data["normal"].get(item, {}).get("main")
                            sub_factor = data["normal"].get(item, {}).get("sub")
                        if not main_factor:
                            continue
                        # 判断是否可加
                        if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                            old_val = attr_values[attr_key]
                            attr_values[attr_key] += 1
                            total_train += 1
                            # 合并连续记录
                            if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                last_record["end"] = attr_values[attr_key]
                                result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                            else:
                                result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                            success = True
        
        # 脸黑保底：五级药
        if not success:
            target_attr_item = next((a for a in ATTR_LIST if a["name"] != "维修" and attr_values[a["key"]] < target_attr[a["key"]]), None)
            if not target_attr_item:
                target_attr_item = next((a for a in ATTR_LIST if attr_values[a["key"]] < target_attr[a["key"]]), None)
            if not target_attr_item:
                break
            attr_key = target_attr_item["key"]
            old_val = attr_values[attr_key]
            attr_values[attr_key] += 1
            total_train += 1
            five_level_count += 1
            five_attr_count[attr_key] += 1
            # 合并连续记录
            if last_record and last_record.get("is_five") and last_record["attr_key"] == attr_key:
                last_record["end"] = attr_values[attr_key]
                result[-1] = f"[脸黑] - 五级药 - {target_attr_item['name']} {last_record['start']}→{last_record['end']}"
            else:
                result.append(f"[脸黑] - 五级药 - {target_attr_item['name']} {old_val}→{attr_values[attr_key]}")
                last_record = {"is_five": True, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
    
    # 生成结果文本
    result_text = "📋 加点方案详情\n" + "\n".join(result)
    # 生成总结
    summary = f"\n✅ 总训练点数：{total_train - start_total}\n✅ 五级药总量：{five_level_count}\n"
    for key, count in five_attr_count.items():
        if count > 0:
            summary += f"{ATTR_KEY_MAP[key]}：{count}个\n"
    summary += "✅ 最终属性："
    for item in ATTR_LIST:
        summary += f"{item['name']}{attr_values[item['key']]} "
    return result_text + summary

def calc_attr_plan(attr_name, base, equip1, equip2, target):
    """属性规划计算，和HTML逻辑一致"""
    attr_info = next((a for a in ATTR_LIST if a["name"] == attr_name), None)
    if not attr_info:
        return "❌ 属性名错误，请输入正确的属性名（如：生命、攻击、维修等）"
    
    attr_type = attr_info["key"]
    eq_sum = equip1 + equip2
    train_val = 0

    # 扣减规则
    if attr_type == "life":
        calc_target = target - 0.5
    elif attr_type == "endurance":
        calc_target = target
    else:
        calc_target = target - 0.05
    
    # 计算公式
    if attr_type in ["life", "atk", "repair", "weapon", "engine", "tech", "nav"]:
        if base != 0:
            train_val = ((calc_target - eq_sum) / base - 1) / 0.01
    elif attr_type == "ability":
        if base != 0:
            train_val = (calc_target / (base * (1 + 0.01 * eq_sum)) - 1) / 0.01
    elif attr_type == "endurance":
        train_val = calc_target - eq_sum
    
    train_val = max(0, train_val)
    train_val = round(train_val)
    return f"📊 {attr_name} 属性规划结果\n------------------------\n基础值：{base}\n装备总和：{eq_sum}\n目标值：{target}\n✅ 需要训练值：{train_val}"

# ===================== 插件主类 =====================
@register("starcitizen_plugin", "YourName", "超时空星舰完整工具插件", "2.0.0")
class StarCitizenPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰完整工具插件加载成功！")
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.font = self._get_windows_font()

    def _get_windows_font(self):
        """获取Windows系统中文字体"""
        font_paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc")
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, 20)
                except:
                    continue
        return ImageFont.load_default(size=20)

    def _create_equip_image(self):
        """生成装备属性表格图片"""
        cell_w, cell_h = 180, 40
        rows, cols = len(EQUIP_TABLE), len(EQUIP_TABLE[0])
        img_w, img_h = cell_w * cols, cell_h * rows
        img = Image.new('RGB', (img_w, img_h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 绘制边框
        for i in range(rows + 1):
            draw.line([(0, i*cell_h), (img_w, i*cell_h)], fill=(0,0,0), width=2)
        for j in range(cols + 1):
            draw.line([(j*cell_w, 0), (j*cell_w, img_h)], fill=(0,0,0), width=2)
        
        # 绘制文字
        for i in range(rows):
            for j in range(cols):
                text = EQUIP_TABLE[i][j]
                bbox = draw.textbbox((0,0), text, font=self.font)
                w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                x = j*cell_w + (cell_w - w) // 2
                y = i*cell_h + (cell_h - h) // 2
                draw.text((x, y), text, fill=(0,0,0), font=self.font)
        
        img_path = os.path.join(self.plugin_dir, "equip_attr.png")
        if os.path.exists(img_path):
            os.remove(img_path)
        img.save(img_path, "PNG")
        return img_path

    # ===================== 指令函数（修复参数解析问题） =====================
    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        """显示功能菜单"""
        logger.info("收到 /超时空星舰菜单 指令！")
        menu_content = """📋 超时空星舰 完整工具菜单
------------------------
🔧 基础功能
/超时空星舰菜单   - 显示此菜单
/装备属性        - 查看橙装/金装属性表（图片）

📊 训练计算器（可输入数值）
1. /训练上限 [数值] - 设置训练上限（例：/训练上限 110）
2. /当前属性 [属性名+数值] - 设置当前属性（例：/当前属性 生命0 攻击0 维修0 能力0 武器0 引擎0 科技0 导航0 耐力0）
3. /目标属性 [属性名+数值] - 设置目标属性（例：/目标属性 生命50 攻击40 维修30 能力60 武器50 引擎40 科技40 导航40 耐力30）
4. /生成吃药方案 [策略] - 生成吃药方案（策略：基础/最省五药/优先四药，例：/生成吃药方案 基础）
5. /生成训练方案 - 生成全训练方案

📈 属性规划器
/属性规划 [属性名] 基础[数值] 装备1[数值] 装备2[数值] 目标[数值]
例：/属性规划 生命 基础10 装备15 装备23 目标100
"""
        await event.reply(menu_content)

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        """生成装备属性图片"""
        logger.info("收到 /装备属性 指令！")
        try:
            img_path = self._create_equip_image()
            await event.reply(image_path=img_path)
        except Exception as e:
            logger.error(f"装备属性图片生成失败：{e}")
            fallback = """📊 超时空星舰装备属性对比表
┌──────────┬─────────────────┬────────┬────────┐
│ 装备属性 │ 英语            │ 橙装   │ 金装   │
├──────────┼─────────────────┼────────┼────────┤
│ HP       │ HP              │ 3.0    │ 3.0    │
│ 攻击     │ Attack          │ 0.7    │ 0.7    │
│ 能力     │ Ability         │ 15.7   │ 15.7   │
│ 火抗     │ FireResistance  │ 63.7   │ 63.7   │
│ 耐力     │ Stamina         │ 22     │ 26     │
│ 武器     │ Weapon          │ 6.7    │ 6.7    │
│ 科技     │ Sciece          │ 9.7    │ 9.7    │
│ 导航     │ Pilot           │ 10.5   │ 10.5   │
│ 引擎     │ Engine          │ 7.5    │ 9      │
│ 维修     │ Repair          │ 0.6    │ 0.7    │
└──────────┴─────────────────┴────────┴────────┘"""
            await event.reply(fallback)

    @filter.command("训练上限")
    async def 训练上限(self, event: AstrMessageEvent):
        """设置训练上限"""
        user_id = event.sender_id
        message = event.message.strip()
        logger.info(f"收到 /训练上限 指令，用户：{user_id}，内容：{message}")
        
        # 解析数值
        try:
            # 拆分指令和参数（去掉指令前缀）
            params = message.replace("/训练上限", "").strip()
            if not params:
                await event.reply("❌ 格式错误！正确格式：/训练上限 [数值]，例：/训练上限 110")
                return
            limit = int(params)
            if limit <= 0:
                await event.reply("❌ 训练上限必须是大于0的数字！")
                return
        except:
            await event.reply("❌ 格式错误！正确格式：/训练上限 [数值]，例：/训练上限 110")
            return
        
        # 保存用户设置
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        USER_DATA[user_id]["train_limit"] = limit
        await event.reply(f"✅ 训练上限已设置为：{limit}")

    @filter.command("当前属性")
    async def 当前属性(self, event: AstrMessageEvent):
        """设置/查看当前属性"""
        user_id = event.sender_id
        message = event.message.strip()
        logger.info(f"收到 /当前属性 指令，用户：{user_id}")
        
        # 初始化用户数据
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        
        # 解析参数（去掉指令前缀）
        params = message.replace("/当前属性", "").strip()
        if not params:
            # 显示当前属性
            current = USER_DATA[user_id]["current_attr"]
            text = "📊 当前属性设置：\n"
            for item in ATTR_LIST:
                text += f"{item['name']}：{current[item['key']]}\n"
            await event.reply(text)
            return
        
        # 设置属性
        try:
            parts = params.split(" ")
            for part in parts:
                if not part:
                    continue
                # 拆分属性名和数值
                attr_name = ""
                value_str = ""
                for i, c in enumerate(part):
                    if c.isdigit() or c == "-":
                        attr_name = part[:i]
                        value_str = part[i:]
                        break
                if not attr_name or not value_str:
                    continue
                # 匹配属性
                attr_key = ATTR_NAME_MAP.get(attr_name)
                if not attr_key:
                    continue
                value = int(value_str)
                USER_DATA[user_id]["current_attr"][attr_key] = value
        except Exception as e:
            logger.error(f"解析当前属性失败：{e}")
            await event.reply("❌ 格式错误！正确格式：/当前属性 [属性名+数值]，例：/当前属性 生命0 攻击0 维修0")
            return
        
        # 返回结果
        current = USER_DATA[user_id]["current_attr"]
        text = "✅ 当前属性已更新：\n"
        for item in ATTR_LIST:
            text += f"{item['name']}：{current[item['key']]}\n"
        await event.reply(text)

    @filter.command("目标属性")
    async def 目标属性(self, event: AstrMessageEvent):
        """设置/查看目标属性"""
        user_id = event.sender_id
        message = event.message.strip()
        logger.info(f"收到 /目标属性 指令，用户：{user_id}")
        
        # 初始化用户数据
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        
        # 解析参数（去掉指令前缀）
        params = message.replace("/目标属性", "").strip()
        if not params:
            # 显示目标属性
            target = USER_DATA[user_id]["target_attr"]
            text = "📊 目标属性设置：\n"
            for item in ATTR_LIST:
                text += f"{item['name']}：{target[item['key']]}\n"
            await event.reply(text)
            return
        
        # 设置属性
        try:
            parts = params.split(" ")
            for part in parts:
                if not part:
                    continue
                # 拆分属性名和数值
                attr_name = ""
                value_str = ""
                for i, c in enumerate(part):
                    if c.isdigit() or c == "-":
                        attr_name = part[:i]
                        value_str = part[i:]
                        break
                if not attr_name or not value_str:
                    continue
                # 匹配属性
                attr_key = ATTR_NAME_MAP.get(attr_name)
                if not attr_key:
                    continue
                value = int(value_str)
                USER_DATA[user_id]["target_attr"][attr_key] = value
        except Exception as e:
            logger.error(f"解析目标属性失败：{e}")
            await event.reply("❌ 格式错误！正确格式：/目标属性 [属性名+数值]，例：/目标属性 生命50 攻击40 维修30")
            return
        
        # 返回结果
        target = USER_DATA[user_id]["target_attr"]
        text = "✅ 目标属性已更新：\n"
        for item in ATTR_LIST:
            text += f"{item['name']}：{target[item['key']]}\n"
        await event.reply(text)

    @filter.command("生成吃药方案")
    async def 生成吃药方案(self, event: AstrMessageEvent):
        """生成吃药加点方案"""
        user_id = event.sender_id
        message = event.message.strip()
        logger.info(f"收到 /生成吃药方案 指令，用户：{user_id}")
        
        # 检查用户数据
        if user_id not in USER_DATA:
            await event.reply("❌ 请先设置训练上限、当前属性和目标属性！发送 /超时空星舰菜单 查看使用说明")
            return
        
        # 解析策略（去掉指令前缀）
        params = message.replace("/生成吃药方案", "").strip()
        strategy = params if params else "基础"
        if strategy not in ["基础", "最省五药", "优先四药"]:
            await event.reply("❌ 策略错误！可选策略：基础/最省五药/优先四药，例：/生成吃药方案 基础")
            return
        # 转换策略名
        strategy_map = {"基础": "base", "最省五药": "saveFive", "优先四药": "priorFour"}
        strategy_key = strategy_map[strategy]
        
        # 生成方案
        try:
            result = generate_plan(user_id, "medicine", strategy_key)
            # 拆分长文本，避免消息过长
            if len(result) > 3000:
                lines = result.split("\n")
                mid = len(lines) // 2
                await event.reply("\n".join(lines[:mid]))
                await event.reply("\n".join(lines[mid:]))
            else:
                await event.reply(result)
        except Exception as e:
            logger.error(f"生成吃药方案失败：{e}")
            await event.reply(f"❌ 生成方案失败：{str(e)}")

    @filter.command("生成训练方案")
    async def 生成训练方案(self, event: AstrMessageEvent):
        """生成全训练加点方案"""
        user_id = event.sender_id
        logger.info(f"收到 /生成训练方案 指令，用户：{user_id}")
        
        # 检查用户数据
        if user_id not in USER_DATA:
            await event.reply("❌ 请先设置训练上限、当前属性和目标属性！发送 /超时空星舰菜单 查看使用说明")
            return
        
        # 生成方案
        try:
            result = generate_plan(user_id, "train")
            # 拆分长文本
            if len(result) > 3000:
                lines = result.split("\n")
                mid = len(lines) // 2
                await event.reply("\n".join(lines[:mid]))
                await event.reply("\n".join(lines[mid:]))
            else:
                await event.reply(result)
        except Exception as e:
            logger.error(f"生成训练方案失败：{e}")
            await event.reply(f"❌ 生成方案失败：{str(e)}")

    @filter.command("属性规划")
    async def 属性规划(self, event: AstrMessageEvent):
        """属性规划计算"""
        message = event.message.strip()
        logger.info(f"收到 /属性规划 指令，内容：{message}")
        
        # 解析参数（去掉指令前缀）
        params = message.replace("/属性规划", "").strip()
        parts = params.split(" ")
        parts = [p for p in parts if p]  # 过滤空字符串
        if len(parts) < 5:
            await event.reply("❌ 格式错误！正确格式：/属性规划 [属性名] 基础[数值] 装备1[数值] 装备2[数值] 目标[数值]\n例：/属性规划 生命 基础10 装备15 装备23 目标100")
            return
        
        try:
            attr_name = parts[0]
            base = int(parts[1].replace("基础", ""))
            equip1 = int(parts[2].replace("装备1", ""))
            equip2 = int(parts[3].replace("装备2", ""))
            target = float(parts[4].replace("目标", ""))
        except Exception as e:
            logger.error(f"解析属性规划参数失败：{e}")
            await event.reply("❌ 格式错误！请检查参数格式，例：/属性规划 生命 基础10 装备15 装备23 目标100")
            return
        
        # 计算结果
        result = calc_attr_plan(attr_name, base, equip1, equip2, target)
        await event.reply(result)
