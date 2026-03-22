from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os
import json  # 新增：用于数据持久化

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
    ["科技", "Science", "9.7", "9.7"],  # 修复拼写错误：Sciece → Science
    ["导航", "Pilot", "10.5", "10.5"],
    ["引擎", "Engine", "7.5", "9"],
    ["维修", "Repair", "0.6", "0.7"],
]

# 训练计算器核心常量（和原HTML逻辑1:1复刻）
FATIGUE = {"大笑": 1, "微笑": 0.5, "流汗": 0.33}
FATIGUE_ORDER = ["大笑", "微笑", "流汗"]
MEDICINE = {
    "normal": {"一级药": {"main": 0.02, "sub": 0.01}, "二级药": {"main": 0.04, "sub": 0.02}, 
               "三级药": {"main": 0.08, "sub": 0.03}, "四级药": {"main": 0.16, "sub": 0.05}},
    "endurance": {"一级耐力药": {"main": 0.08, "sub": 0.01}, "二级耐力药": {"main": 0.12, "sub": 0.01}, 
                  "三级耐力药": {"main": 0.16, "sub": 0.02}},
    "order": {
        "base": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"],
        "priorFour": ["一级药", "二级药", "四级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药"],
        "saveFive": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"]
    }
}
TRAIN = {
    "normal": {"绿色训练": {"main": 0.02, "sub": 0.01}, "蓝色训练": {"main": 0.08, "sub": 0.01}, 
               "金色训练": {"main": 0.12, "sub": 0.02}},
    "endurance": {"耐力绿训": {"main": 0.02, "sub": 0}, "耐力蓝训": {"main": 0.08, "sub": 0.02}, 
                  "耐力金训": {"main": 0.16, "sub": 0.03}},
    "order": ["绿色训练", "蓝色训练", "金色训练", "耐力绿训", "耐力蓝训", "耐力金训"]
}

# 属性列表（生命/攻击/维修等）
ATTR_LIST = [
    {"name": "生命", "key": "life"}, {"name": "攻击", "key": "atk"}, {"name": "维修", "key": "repair"},
    {"name": "能力", "key": "ability"}, {"name": "武器", "key": "weapon"}, {"name": "引擎", "key": "engine"},
    {"name": "科技", "key": "tech"}, {"name": "导航", "key": "nav"}, {"name": "耐力", "key": "endurance"}
]
ATTR_NAME_MAP = {item["name"]: item["key"] for item in ATTR_LIST}  # 名字转key
ATTR_KEY_MAP = {item["key"]: item["name"] for item in ATTR_LIST}  # key转名字

# ===================== 数据持久化配置 =====================
# 用户数据存储路径
USER_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data.json")

# 加载用户数据（启动时）
def load_user_data():
    """加载持久化的用户数据"""
    if os.path.exists(USER_DATA_PATH):
        try:
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户数据失败：{e}")
            return {}
    return {}

# 保存用户数据（修改时）
def save_user_data(data):
    """保存用户数据到JSON文件"""
    try:
        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存用户数据失败：{e}")

# 初始化用户数据（持久化）
USER_DATA = load_user_data()

# ===================== 核心计算函数 =====================
def calc_rate(max_limit, total_train, attr_value, fatigue_val, factor):
    """计算加点成功率"""
    numerator = (max_limit - total_train) * (max_limit - attr_value) * fatigue_val * factor * 100
    denominator = max_limit * max_limit
    return numerator / denominator

def can_add(max_limit, total_train, main_attr_value, fatigue_val, main_factor, sub_factor):
    """判断是否可以加点"""
    main_rate = calc_rate(max_limit, total_train, main_attr_value, fatigue_val, main_factor)
    sub_rate = calc_rate(max_limit, total_train, 0, fatigue_val, sub_factor)
    return main_rate >= 1 and sub_rate < 1

def generate_plan(user_id, plan_type, strategy="base"):
    """
    生成加点方案
    :param user_id: 用户ID（隔离数据）
    :param plan_type: 方案类型（medicine=吃药/ train=纯训练）
    :param strategy: 吃药策略（base=基础/ priorFour=优先四药/ saveFive=最省五药）
    :return: 加点方案文本
    """
    user = USER_DATA.get(user_id, {})
    max_limit = user.get("train_limit", 110)  # 默认训练上限110
    current_attr = user.get("current_attr", {item["key"]: 0 for item in ATTR_LIST})  # 当前属性
    target_attr = user.get("target_attr", {item["key"]: 0 for item in ATTR_LIST})    # 目标属性

    attr_values = current_attr.copy()
    total_train = sum(attr_values.values())  # 已用训练点数
    start_total = total_train
    five_level_count = 0  # 五级药使用次数
    five_attr_count = {item["key"]: 0 for item in ATTR_LIST}  # 各属性五级药次数
    result = []  # 加点记录
    last_record = None  # 上一条加点记录（用于合并连续加点）
    current_focus_attr = None  # 最省五药策略的聚焦属性

    while True:
        # 终止条件：所有属性达标 或 训练点数用完
        all_finish = all(attr_values[item["key"]] >= target_attr[item["key"]] for item in ATTR_LIST)
        if all_finish or total_train >= max_limit:
            break
        
        success = False

        # 优先四药策略逻辑
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
                    # 遍历属性尝试加点
                    for attr in attr_list:
                        attr_key = attr["key"]
                        if success or attr_values[attr_key] >= target_attr[attr_key]:
                            continue
                        # 获取药品系数
                        if attr["name"] == "耐力":
                            main_factor = MEDICINE["endurance"].get(item, {}).get("main")
                            sub_factor = MEDICINE["endurance"].get(item, {}).get("sub")
                        else:
                            main_factor = MEDICINE["normal"].get(item, {}).get("main")
                            sub_factor = MEDICINE["normal"].get(item, {}).get("sub")
                        if not main_factor:
                            continue
                        # 判断是否可加点
                        if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                            old_val = attr_values[attr_key]
                            attr_values[attr_key] += 1
                            total_train += 1
                            # 合并连续加点记录
                            if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                last_record["end"] = attr_values[attr_key]
                                result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                            else:
                                result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                            success = True
        # 基础/最省五药/纯训练策略
        else:
            for f in FATIGUE_ORDER:
                if success:
                    break
                f_val = FATIGUE[f]
                # 选择药/训练类型列表
                item_list = MEDICINE["order"][strategy] if plan_type == "medicine" else TRAIN["order"]
                for item in item_list:
                    if success:
                        break
                    # 优先非维修属性
                    attr_list = [a for a in ATTR_LIST if a["name"] != "维修"]
                    if all(attr_values[a["key"]] >= target_attr[a["key"]] for a in attr_list):
                        attr_list = ATTR_LIST
                    # 最省五药策略：聚焦单个未达标属性
                    if plan_type == "medicine" and strategy == "saveFive":
                        if not current_focus_attr or attr_values[current_focus_attr["key"]] >= target_attr[current_focus_attr["key"]]:
                            current_focus_attr = next((a for a in attr_list if attr_values[a["key"]] < target_attr[a["key"]]), None)
                        if current_focus_attr:
                            attr_list = [current_focus_attr]
                    # 遍历属性尝试加点
                    for attr in attr_list:
                        attr_key = attr["key"]
                        if success or attr_values[attr_key] >= target_attr[attr_key]:
                            continue
                        # 获取系数（药/训练）
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
                        # 判断是否可加点
                        if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                            old_val = attr_values[attr_key]
                            attr_values[attr_key] += 1
                            total_train += 1
                            # 合并连续加点记录
                            if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                last_record["end"] = attr_values[attr_key]
                                result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                            else:
                                result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                            success = True
        # 脸黑保底：使用五级药
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
            # 合并五级药记录
            if last_record and last_record.get("is_five") and last_record["attr_key"] == attr_key:
                last_record["end"] = attr_values[attr_key]
                result[-1] = f"[脸黑] - 五级药 - {target_attr_item['name']} {last_record['start']}→{last_record['end']}"
            else:
                result.append(f"[脸黑] - 五级药 - {target_attr_item['name']} {old_val}→{attr_values[attr_key]}")
                last_record = {"is_five": True, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
    
    # 生成最终方案文本（优化排版）
    result_text = "📋 加点方案详情\n" + "-"*30 + "\n" + "\n".join(result)
    # 方案总结
    summary = f"\n" + "-"*30 + f"\n✅ 总训练点数：{total_train - start_total}\n✅ 五级药总量：{five_level_count}\n"
    for key, count in five_attr_count.items():
        if count > 0:
            summary += f"  • {ATTR_KEY_MAP[key]}：{count}个\n"
    summary += "✅ 最终属性：\n  "
    attr_summary = []
    for item in ATTR_LIST:
        attr_summary.append(f"{item['name']}{attr_values[item['key']]}")
    summary += " | ".join(attr_summary)
    
    return result_text + summary

def calc_attr_plan(attr_name, base, equip1, equip2, target):
    """
    属性规划计算（根据基础/装备值，计算需要的训练点数）
    :param attr_name: 属性名（生命/攻击等）
    :param base: 基础值
    :param equip1: 装备1加成
    :param equip2: 装备2加成
    :param target: 目标值
    :return: 计算结果文本
    """
    attr_info = next((a for a in ATTR_LIST if a["name"] == attr_name), None)
    if not attr_info:
        return "❌ 属性名错误！请输入：生命/攻击/维修/能力/武器/引擎/科技/导航/耐力"
    
    attr_type = attr_info["key"]
    eq_sum = equip1 + equip2  # 装备总加成
    train_val = 0

    # 不同属性的计算规则
    if attr_type == "life":
        calc_target = target - 0.5
    elif attr_type == "endurance":
        calc_target = target
    else:
        calc_target = target - 0.05
    
    # 核心计算公式（修复除零错误）
    if attr_type in ["life", "atk", "repair", "weapon", "engine", "tech", "nav"]:
        if base != 0:
            train_val = ((calc_target - eq_sum) / base - 1) / 0.01
        else:
            return f"❌ {attr_name}基础值不能为0！"
    elif attr_type == "ability":
        if base != 0:
            train_val = (calc_target / (base * (1 + 0.01 * eq_sum)) - 1) / 0.01
        else:
            return f"❌ {attr_name}基础值不能为0！"
    elif attr_type == "endurance":
        train_val = calc_target - eq_sum
    
    # 确保训练值非负并取整
    train_val = max(0, train_val)
    train_val = round(train_val)
    
    return f"📊 {attr_name} 属性规划结果\n------------------------\n基础值：{base}\n装备总和：{eq_sum}\n目标值：{target}\n✅ 需要训练值：{train_val}"

# ===================== 插件主类（修复sender_id + 跨平台字体 + 数据持久化） =====================
@register("starcitizen_plugin", "超时空星舰工具", "超时空星舰训练计算器", "2.0.0")
class StarCitizenPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰工具插件加载成功！")
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))  # 插件目录
        self.font = self._get_system_font()  # 修复：跨平台字体加载

    def _get_system_font(self):
        """跨平台字体加载（Windows/Linux/macOS）"""
        # 各系统字体路径
        font_paths = []
        if os.name == "nt":  # Windows
            font_paths.extend([
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc")
            ])
        else:  # Linux/macOS
            font_paths.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux通用
                "/System/Library/Fonts/PingFang.ttc",               # macOS苹方
                "/Library/Fonts/Arial Unicode.ttf"                  # macOS通用
            ])
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, 20)
                except Exception as e:
                    logger.warning(f"加载字体{path}失败：{e}")
                    continue
        return ImageFont.load_default(size=20)  # 兜底

    def _create_equip_image(self):
        """生成装备属性表格图片"""
        try:
            cell_w, cell_h = 180, 40  # 单元格宽高
            rows, cols = len(EQUIP_TABLE), len(EQUIP_TABLE[0])
            img_w, img_h = cell_w * cols, cell_h * rows
            img = Image.new('RGB', (img_w, img_h), (255, 255, 255))  # 白色背景
            draw = ImageDraw.Draw(img)
            
            # 绘制表格边框
            for i in range(rows + 1):
                draw.line([(0, i*cell_h), (img_w, i*cell_h)], fill=(0,0,0), width=2)
            for j in range(cols + 1):
                draw.line([(j*cell_w, 0), (j*cell_w, img_h)], fill=(0,0,0), width=2)
            
            # 绘制表格文字
            for i in range(rows):
                for j in range(cols):
                    text = EQUIP_TABLE[i][j]
                    bbox = draw.textbbox((0,0), text, font=self.font)
                    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
                    # 文字居中
                    x = j*cell_w + (cell_w - w) // 2
                    y = i*cell_h + (cell_h - h) // 2
                    draw.text((x, y), text, fill=(0,0,0), font=self.font)
            
            # 保存图片到插件目录
            img_path = os.path.join(self.plugin_dir, "equip_attr.png")
            if os.path.exists(img_path):
                os.remove(img_path)
            img.save(img_path, "PNG")
            return img_path
        except Exception as e:
            logger.error(f"生成装备图片失败：{e}")
            return None

    # ===================== 指令函数（核心修复：sender_id + 完整指令） =====================
    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        """核心指令：显示功能菜单"""
        # 修复：使用sender_id替代user_id
        logger.info(f"收到 /超时空星舰菜单 指令（用户ID：{event.sender_id}）")
        menu_content = """📋 超时空星舰 完整工具菜单
------------------------
🔧 基础功能
/超时空星舰菜单   - 显示此菜单
/装备属性        - 查看橙装/金装属性表（图片）

📊 训练计算器（需按顺序设置）
1. /训练上限 [数值] - 设置训练上限（例：/训练上限 110）
2. /当前属性 [属性名+数值] - 设置当前属性（例：/当前属性 生命0 攻击50 耐力20）
3. /目标属性 [属性名+数值] - 设置目标属性（例：/目标属性 生命100 攻击80 耐力50）
4. /生成吃药方案 [策略] - 生成吃药加点方案（策略：基础/最省五药/优先四药）
5. /生成训练方案 - 生成纯训练加点方案
6. /重置训练数据 - 重置你的所有训练配置数据

📈 属性规划器（单独使用）
/属性规划 [属性名] 基础[数值] 装备1[数值] 装备2[数值] 目标[数值]
例：/属性规划 生命 基础10 装备15 装备23 目标100
"""
        # 返回tuple格式（框架强制要求）
        return (menu_content, )

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        """指令：发送装备属性表格（图片+文字兜底）"""
        # 修复：使用sender_id替代user_id
        logger.info(f"收到 /装备属性 指令（用户ID：{event.sender_id}）")
        # 尝试生成图片
        img_path = self._create_equip_image()
        if img_path and os.path.exists(img_path):
            # 返回图片（tuple包裹字典）
            return ({"image": img_path}, )
        else:
            # 图片生成失败，返回文字版
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
│ 科技     │ Science         │ 9.7    │ 9.7    │
│ 导航     │ Pilot           │ 10.5   │ 10.5   │
│ 引擎     │ Engine          │ 7.5    │ 9      │
│ 维修     │ Repair          │ 0.6    │ 0.7    │
└──────────┴─────────────────┴────────┴────────┘"""
            return (fallback, )

    @filter.command("训练上限")
    async def 训练上限(self, event: AstrMessageEvent):
        """指令：设置训练上限"""
        user_id = event.sender_id  # 修复：使用sender_id
        args = event.content.strip().split()[1:]
        if not args or not args[0].isdigit():
            return ("❌ 格式错误！示例：/训练上限 110", )
        limit = int(args[0])
        # 更新用户数据
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        USER_DATA[user_id]["train_limit"] = limit
        save_user_data(USER_DATA)  # 持久化保存
        return (f"✅ 训练上限已设置为：{limit}", )

    @filter.command("当前属性")
    async def 当前属性(self, event: AstrMessageEvent):
        """指令：设置当前属性（例：/当前属性 生命0 攻击50 耐力20）"""
        user_id = event.sender_id  # 修复：使用sender_id
        args = event.content.strip().split()[1:]
        if not args:
            return ("❌ 格式错误！示例：/当前属性 生命0 攻击50 耐力20", )
        
        # 初始化用户数据
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        
        # 解析属性参数
        error_msg = []
        for arg in args:
            # 提取属性名和数值（支持“生命0”“攻击50”格式）
            attr_name = ""
            num_str = ""
            for c in arg:
                if c.isdigit() or c == ".":
                    num_str += c
                else:
                    attr_name += c
            if not attr_name or not num_str:
                error_msg.append(f"无效参数：{arg}")
                continue
            if attr_name not in ATTR_NAME_MAP:
                error_msg.append(f"未知属性：{attr_name}")
                continue
            try:
                val = float(num_str)
                attr_key = ATTR_NAME_MAP[attr_name]
                USER_DATA[user_id]["current_attr"][attr_key] = val
            except:
                error_msg.append(f"数值错误：{arg}")
        
        # 保存数据
        save_user_data(USER_DATA)
        
        if error_msg:
            return (f"⚠️ 部分参数解析失败：\n{chr(10).join(error_msg)}\n已设置的属性仍会生效", )
        else:
            # 返回当前属性汇总
            current_attr = USER_DATA[user_id]["current_attr"]
            attr_text = []
            for item in ATTR_LIST:
                attr_text.append(f"{item['name']}：{current_attr[item['key']]}")
            return (f"✅ 当前属性已设置：\n{chr(10).join(attr_text)}", )

    @filter.command("目标属性")
    async def 目标属性(self, event: AstrMessageEvent):
        """指令：设置目标属性（例：/目标属性 生命100 攻击80 耐力50）"""
        user_id = event.sender_id  # 修复：使用sender_id
        args = event.content.strip().split()[1:]
        if not args:
            return ("❌ 格式错误！示例：/目标属性 生命100 攻击80 耐力50", )
        
        # 初始化用户数据
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "train_limit": 110,
                "current_attr": {item["key"]: 0 for item in ATTR_LIST},
                "target_attr": {item["key"]: 0 for item in ATTR_LIST}
            }
        
        # 解析属性参数
        error_msg = []
        for arg in args:
            attr_name = ""
            num_str = ""
            for c in arg:
                if c.isdigit() or c == ".":
                    num_str += c
                else:
                    attr_name += c
            if not attr_name or not num_str:
                error_msg.append(f"无效参数：{arg}")
                continue
            if attr_name not in ATTR_NAME_MAP:
                error_msg.append(f"未知属性：{attr_name}")
                continue
            try:
                val = float(num_str)
                attr_key = ATTR_NAME_MAP[attr_name]
                USER_DATA[user_id]["target_attr"][attr_key] = val
            except:
                error_msg.append(f"数值错误：{arg}")
        
        # 保存数据
        save_user_data(USER_DATA)
        
        if error_msg:
            return (f"⚠️ 部分参数解析失败：\n{chr(10).join(error_msg)}\n已设置的属性仍会生效", )
        else:
            target_attr = USER_DATA[user_id]["target_attr"]
            attr_text = []
            for item in ATTR_LIST:
                attr_text.append(f"{item['name']}：{target_attr[item['key']]}")
            return (f"✅ 目标属性已设置：\n{chr(10).join(attr_text)}", )

    @filter.command("生成吃药方案")
    async def 生成吃药方案(self, event: AstrMessageEvent):
        """指令：生成吃药加点方案（策略：基础/最省五药/优先四药）"""
        user_id = event.sender_id  # 修复：使用sender_id
        args = event.content.strip().split()[1:]
        strategy = args[0] if args else "base"
        if strategy not in ["base", "最省五药", "优先四药"]:
            return ("❌ 策略错误！仅支持：基础/最省五药/优先四药", )
        
        if user_id not in USER_DATA:
            return ("❌ 你还未设置属性！请先执行：/当前属性 /目标属性", )
        
        # 生成方案
        try:
            plan = generate_plan(user_id, "medicine", strategy)
            return (plan, )
        except Exception as e:
            logger.error(f"生成吃药方案失败：{e}")
            return (f"❌ 生成方案失败：{str(e)}", )

    @filter.command("生成训练方案")
    async def 生成训练方案(self, event: AstrMessageEvent):
        """指令：生成纯训练加点方案"""
        user_id = event.sender_id  # 修复：使用sender_id
        if user_id not in USER_DATA:
            return ("❌ 你还未设置属性！请先执行：/当前属性 /目标属性", )
        
        try:
            plan = generate_plan(user_id, "train")
            return (plan, )
        except Exception as e:
            logger.error(f"生成训练方案失败：{e}")
            return (f"❌ 生成方案失败：{str(e)}", )

    @filter.command("属性规划")
    async def 属性规划(self, event: AstrMessageEvent):
        """指令：属性规划计算（例：/属性规划 生命 基础10 装备15 装备23 目标100）"""
        args = event.content.strip().split()[1:]
        if len(args) < 5:
            return ("❌ 格式错误！示例：/属性规划 生命 基础10 装备15 装备23 目标100", )
        
        # 解析参数
        attr_name = args[0]
        try:
            base = float(args[1].replace("基础", ""))
            equip1 = float(args[2].replace("装备1", ""))
            equip2 = float(args[3].replace("装备2", ""))
            target = float(args[4].replace("目标", ""))
        except:
            return ("❌ 数值解析失败！请确保基础/装备1/装备2/目标后是数字", )
        
        # 计算结果
        result = calc_attr_plan(attr_name, base, equip1, equip2, target)
        return (result, )

    @filter.command("重置训练数据")
    async def 重置训练数据(self, event: AstrMessageEvent):
        """指令：重置当前用户的所有训练配置数据"""
        user_id = event.sender_id  # 修复：使用sender_id
        if user_id in USER_DATA:
            del USER_DATA[user_id]
            save_user_data(USER_DATA)  # 持久化删除
            return ("✅ 已重置你的所有训练配置数据（训练上限/当前属性/目标属性）", )
        else:
            return ("❌ 你暂无训练配置数据可重置", )
