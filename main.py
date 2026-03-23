from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import re
import math

# ===================== 核心配置（优化后的样式） =====================
# 菜单图片尺寸（更紧凑）
MENU_IMG_WIDTH = 800
MENU_IMG_HEIGHT = 750

# 优化后的配色（柔和蓝紫渐变，更有科技感）
COLORS = {
    "bg_start": (15, 25, 65),     # 背景起始色（深幽蓝）
    "bg_end": (55, 45, 120),       # 背景结束色（浅紫蓝）
    "title": (255, 255, 255),      # 标题文字（纯白）
    "subtitle": (255, 220, 100),   # 子标题（暖金）
    "content": (240, 245, 255),    # 内容文字（浅蓝白）
    "highlight": (120, 210, 255),  # 高亮文字（天青蓝）
    "line": (80, 120, 200),        # 分割线（浅蓝）
    "panel_bg": (0, 0, 0, 60),     # 板块背景（半透黑）
    "shadow": (0, 0, 0, 80)        # 文字阴影（半透黑）
}

# 优化后的字体大小（层级更清晰）
FONT_SIZES = {
    "title": 36,      # 主标题
    "subtitle": 22,   # 板块标题
    "content": 17,    # 普通内容
    "small": 15       # 小字体内容
}

# 间距配置（优化留白）
SPACING = {
    "title_margin": 30,
    "panel_padding": 20,
    "line_margin": 15,
    "item_margin": 12,
    "panel_margin": 25
}

# ===================== 训练/吃药计算器核心配置 =====================
FATIGUE = {"大笑": 1, "微笑": 0.5, "流汗": 0.33}
FATIGUE_ORDER = ["大笑", "微笑", "流汗"]

MEDICINE = {
    "normal": {
        "一级药": {"main": 0.02, "sub": 0.01},
        "二级药": {"main": 0.04, "sub": 0.02},
        "三级药": {"main": 0.08, "sub": 0.03},
        "四级药": {"main": 0.16, "sub": 0.05}
    },
    "endurance": {
        "一级耐力药": {"main": 0.08, "sub": 0.01},
        "二级耐力药": {"main": 0.12, "sub": 0.01},
        "三级耐力药": {"main": 0.16, "sub": 0.02}
    },
    "order": {
        "base": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"],
        "priorFour": ["一级药", "二级药", "四级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药"],
        "saveFive": ["一级药", "二级药", "三级药", "一级耐力药", "二级耐力药", "三级耐力药", "四级药"]
    }
}

TRAIN = {
    "normal": {
        "绿色训练": {"main": 0.02, "sub": 0.01},
        "蓝色训练": {"main": 0.08, "sub": 0.01},
        "金色训练": {"main": 0.12, "sub": 0.02}
    },
    "endurance": {
        "耐力绿训": {"main": 0.02, "sub": 0},
        "耐力蓝训": {"main": 0.08, "sub": 0.02},
        "耐力金训": {"main": 0.16, "sub": 0.03}
    },
    "order": ["绿色训练", "蓝色训练", "金色训练", "耐力绿训", "耐力蓝训", "耐力金训"]
}

ATTRS = [
    {"name": "生命", "key": "life"}, {"name": "攻击", "key": "atk"},
    {"name": "维修", "key": "repair"}, {"name": "能力", "key": "ability"},
    {"name": "武器", "key": "weapon"}, {"name": "引擎", "key": "engine"},
    {"name": "科技", "key": "tech"}, {"name": "导航", "key": "nav"},
    {"name": "耐力", "key": "endurance"}
]

STRATEGY_MAP = {"base": "基础方案", "priorFour": "优先四级药方案", "saveFive": "最省五级药方案"}
TABLE_DATA = [
    ["装备属性", "英语", "橙装", "金装"],
    ["HP", "HP", "3.0", "3.0"], ["攻击", "Attack", "0.7", "0.7"],
    ["能力", "Ability", "15.7", "15.7"], ["火抗", "FireResistance", "63.7", "63.7"],
    ["耐力", "Stamina", "22", "26"], ["武器", "Weapon", "6.7", "6.7"],
    ["科技", "Sciece", "9.7", "9.7"], ["导航", "Pilot", "10.5", "10.5"],
    ["引擎", "Engine", "7.5", "9"], ["维修", "Repair", "0.6", "0.7"]
]
FOOTER_TEXT = "天啟舰队欢迎你，群号951239404"

# ===================== 核心工具函数（优化视觉） =====================
def draw_gradient_background(draw, width, height, start_color, end_color):
    """绘制更柔和的蓝紫渐变背景"""
    for y in range(height):
        ratio = y / height
        # 蓝紫渐变混合（更自然）
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_rounded_rect(draw, xy, radius, fill):
    """绘制圆角矩形（美化板块背景）"""
    x1, y1, x2, y2 = xy
    # 绘制圆角
    draw.pieslice([x1, y1, x1+2*radius, y1+2*radius], 180, 270, fill=fill)
    draw.pieslice([x2-2*radius, y1, x2, y1+2*radius], 270, 0, fill=fill)
    draw.pieslice([x1, y2-2*radius, x1+2*radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2-2*radius, y2-2*radius, x2, y2], 0, 90, fill=fill)
    # 绘制矩形主体
    draw.rectangle([x1+radius, y1, x2-radius, y2], fill=fill)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill)

def get_font(size):
    """获取系统字体（优先微软雅黑，更美观）"""
    font_paths = [
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc"),
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    return ImageFont.load_default(size=size)

def draw_text_with_shadow(draw, pos, text, font, fill, shadow_fill=COLORS["shadow"], offset=2):
    """绘制带阴影的文字（提升可读性和美观度）"""
    x, y = pos
    # 先画阴影
    draw.text((x+offset, y+offset), text, font=font, fill=shadow_fill)
    # 再画主文字
    draw.text((x, y), text, font=font, fill=fill)

# ===================== 核心计算函数 =====================
def calc_rate(max_limit: int, total_train: int, attr_value: int, fatigue_val: float, factor: float) -> float:
    numerator = (max_limit - total_train) * (max_limit - attr_value) * fatigue_val * factor * 100
    denominator = max_limit * max_limit
    return numerator / denominator

def can_add(max_limit: int, total_train: int, main_attr_value: int, fatigue_val: float, main_factor: float, sub_factor: float) -> bool:
    main_rate = calc_rate(max_limit, total_train, main_attr_value, fatigue_val, main_factor)
    sub_rate = calc_rate(max_limit, total_train, 0, fatigue_val, sub_factor)
    return main_rate >= 1 and sub_rate < 1

# ===================== 插件主类（优化菜单生成） =====================
@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

    def get_event_params(self, event: AstrMessageEvent) -> str:
        if hasattr(event, "args") and event.args:
            params_str = " ".join(event.args)
            logger.info(f"✅ 从event.args获取到参数: {params_str}")
            params_str = params_str.strip().replace("）", "").replace("(", "").replace("，", " ")
            return params_str
        
        msg = ""
        attr_list = ["message_str", "get_message_str", "content", "raw_message", "message"]
        for attr in attr_list:
            if hasattr(event, attr):
                try:
                    if callable(getattr(event, attr)):
                        msg = getattr(event, attr)()
                    else:
                        msg = getattr(event, attr)
                    if msg:
                        logger.info(f"✅ 从event.{attr}获取到消息: {msg}")
                        break
                except:
                    continue
        
        if msg:
            for cmd in ["/生成吃药方案", "生成吃药方案", "/生成训练方案", "生成训练方案"]:
                if msg.startswith(cmd):
                    msg = msg[len(cmd):].strip()
            msg = msg.replace("）", "").replace("(", "").replace("，", " ")
        
        logger.info(f"📝 最终解析到的参数字符串: {msg}")
        return msg

    # ===================== 生成优化后的精美菜单图片 =====================
    def generate_menu_image(self):
        """生成更美观的菜单图片：圆角板块+渐变+阴影+精致排版"""
        # 创建图片和绘图对象
        img = Image.new('RGB', (MENU_IMG_WIDTH, MENU_IMG_HEIGHT), color=COLORS["bg_start"])
        draw = ImageDraw.Draw(img)
        
        # 绘制柔和渐变背景
        draw_gradient_background(draw, MENU_IMG_WIDTH, MENU_IMG_HEIGHT, 
                               COLORS["bg_start"], COLORS["bg_end"])
        
        # 加载字体
        font_title = get_font(FONT_SIZES["title"])
        font_subtitle = get_font(FONT_SIZES["subtitle"])
        font_content = get_font(FONT_SIZES["content"])
        font_small = get_font(FONT_SIZES["small"])
        
        # 初始化位置（优化留白）
        y = SPACING["title_margin"]
        
        # 1. 主标题（居中+阴影+更大字号）
        title_text = "🚀 超时空星舰 功能菜单"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (MENU_IMG_WIDTH - title_width) // 2
        draw_text_with_shadow(draw, (title_x, y), title_text, font_title, COLORS["title"])
        y += 50
        
        # 绘制精致分割线（两端短横线装饰）
        line_y = y + 5
        draw.line([(100, line_y), (700, line_y)], fill=COLORS["line"], width=2)
        draw.line([(80, line_y), (90, line_y)], fill=COLORS["subtitle"], width=3)
        draw.line([(710, line_y), (720, line_y)], fill=COLORS["subtitle"], width=3)
        y += SPACING["line_margin"] * 2
        
        # 2. 核心功能板块（圆角背景+独立区域）
        panel_x1 = 50
        panel_y1 = y
        panel_x2 = MENU_IMG_WIDTH - 50
        panel_y2 = y + 180
        # 绘制圆角板块背景（半透明）
        draw_rounded_rect(draw, (panel_x1, panel_y1, panel_x2, panel_y2), 15, COLORS["panel_bg"])
        # 板块标题
        draw_text_with_shadow(draw, (panel_x1 + 20, panel_y1 + 15), "🔧 核心功能", font_subtitle, COLORS["subtitle"])
        y += 40
        # 功能列表（优化行间距）
        functions = [
            "/超时空星舰菜单   - 显示此菜单",
            "/装备属性        - 查看橙装/金装属性对比（图片版）",
            "/生成吃药方案    - 生成吃药加点方案",
            "/生成训练方案    - 生成训练加点方案"
        ]
        for func in functions:
            draw_text_with_shadow(draw, (panel_x1 + 40, y), func, font_content, COLORS["content"])
            y += SPACING["item_margin"] + 10
        y += 20
        
        # 3. 指令示例板块（圆角背景）
        panel_y1 = y
        panel_y2 = y + 120
        draw_rounded_rect(draw, (panel_x1, panel_y1, panel_x2, panel_y2), 15, COLORS["panel_bg"])
        draw_text_with_shadow(draw, (panel_x1 + 20, panel_y1 + 15), "📌 指令示例", font_subtitle, COLORS["subtitle"])
        y += 40
        examples = [
            "/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base",
            "/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5"
        ]
        for example in examples:
            draw_text_with_shadow(draw, (panel_x1 + 40, y), example, font_small, COLORS["content"])
            y += SPACING["item_margin"] + 8
        y += 20
        
        # 4. 策略说明板块（圆角背景+高亮）
        panel_y1 = y
        panel_y2 = y + 80
        draw_rounded_rect(draw, (panel_x1, panel_y1, panel_x2, panel_y2), 15, COLORS["panel_bg"])
        draw_text_with_shadow(draw, (panel_x1 + 20, panel_y1 + 15), "🎯 策略说明", font_subtitle, COLORS["subtitle"])
        y += 40
        strategy_text = "base - 基础方案 | priorFour - 优先四级药 | saveFive - 最省五药"
        draw_text_with_shadow(draw, (panel_x1 + 40, y), strategy_text, font_content, COLORS["highlight"])
        y += 25
        
        # 5. 小提示板块（圆角背景）
        panel_y1 = y
        panel_y2 = y + 180
        draw_rounded_rect(draw, (panel_x1, panel_y1, panel_x2, panel_y2), 15, COLORS["panel_bg"])
        draw_text_with_shadow(draw, (panel_x1 + 20, panel_y1 + 15), "💡 小提示", font_subtitle, COLORS["subtitle"])
        y += 40
        tips = [
            "输入格式：属性名当前数值目标数值（例：生命当前0目标10）、",
            "         上限数值（默认110，可自定义如：上限100）、",
            "         策略英文标识（例：策略saveFive）",
            "",
            "关键说明：",
            "  ▶ 可配置属性：生命/攻击/维修/能力/武器/引擎/科技/导航/耐力",
            "  ▶ 五级药触发：仅常规药品/训练无法加点时自动使用"
        ]
        for tip in tips:
            if tip:
                draw_text_with_shadow(draw, (panel_x1 + 40, y), tip, font_small, COLORS["content"])
            y += SPACING["item_margin"] + 5
        
        # 底部装饰线
        draw.line([(100, y + 10), (700, y + 10)], fill=COLORS["line"], width=1)
        
        # 保存高质量图片
        img_path = os.path.join(self.plugin_dir, "starship_menu.png")
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
        img.save(img_path, "PNG", quality=95, optimize=True)
        return img_path

    def generate_attr_image(self):
        cell_width = 180
        cell_height = 40
        rows = len(TABLE_DATA)
        cols = len(TABLE_DATA[0])
        img_width = cell_width * cols
        img_height = cell_height * rows
        image = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = get_font(20)

        for i in range(rows + 1):
            y = i * cell_height
            draw.line([(0, y), (img_width, y)], fill=(0, 0, 0), width=2)
        for j in range(cols + 1):
            x = j * cell_width
            draw.line([(x, 0), (x, img_height)], fill=(0, 0, 0), width=2)

        for i in range(rows):
            for j in range(cols):
                text = TABLE_DATA[i][j]
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                except:
                    text_w, text_h = draw.textsize(text, font=font)
                x = j * cell_width + (cell_width - text_w) // 2
                y = i * cell_height + (cell_height - text_h) // 2
                draw.text((x, y), text, fill=(0, 0, 0), font=font)

        img_path = os.path.join(self.plugin_dir, "equip_attr.png")
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
        image.save(img_path, "PNG")
        return img_path

    def parse_plan_params(self, params_str: str, plan_type: str = "medicine") -> dict:
        params = {
            "max_limit": 110, "type": plan_type, "strategy": "base",
            "current": {}, "target": {}
        }
        limit_match = re.search(r"上限(\d+)", params_str)
        if limit_match:
            params["max_limit"] = int(limit_match.group(1))
        strategy_match = re.search(r"策略(\w+)", params_str)
        if strategy_match:
            strategy = strategy_match.group(1)
            if strategy in MEDICINE["order"].keys():
                params["strategy"] = strategy
        elif "priorFour" in params_str:
            params["strategy"] = "priorFour"
        elif "saveFive" in params_str:
            params["strategy"] = "saveFive"

        for attr in ATTRS:
            attr_name = attr["name"]
            attr_match = re.search(f"{attr_name}当前(\d+)目标(\d+)", params_str)
            if attr_match:
                try:
                    params["current"][attr["key"]] = int(attr_match.group(1))
                    params["target"][attr["key"]] = int(attr_match.group(2))
                except:
                    params["current"][attr["key"]] = 0
                    params["target"][attr["key"]] = 0
            else:
                params["current"][attr["key"]] = 0
                params["target"][attr["key"]] = 0
        return params

    def generate_plan(self, params: dict) -> tuple:
        max_limit = params["max_limit"]
        plan_type = params["type"]
        strategy = params["strategy"]
        current = params["current"]
        target = params["target"]

        attr_values = current.copy()
        total_train = sum(attr_values.values())
        start_total = total_train
        five_level_medicine = 0
        five_attr = {k: 0 for k in attr_values.keys()}
        result = []
        last_record = None
        current_focus_attr = None

        while True:
            all_finish = all(attr_values[k] >= target[k] for k in attr_values.keys())
            if all_finish or total_train >= max_limit:
                break

            success = False
            if plan_type == "medicine" and strategy == "priorFour":
                item_list = MEDICINE["order"][strategy]
                for item in item_list:
                    if success:
                        break
                    for f in FATIGUE_ORDER:
                        if success:
                            break
                        f_val = FATIGUE[f]
                        attr_list = [a for a in ATTRS if a["name"] != "维修" and attr_values[a["key"]] < target[a["key"]]]
                        if not attr_list:
                            attr_list = [a for a in ATTRS if attr_values[a["key"]] < target[a["key"]]]
                        for attr in attr_list:
                            attr_key = attr["key"]
                            if success or attr_values[attr_key] >= target[attr_key]:
                                continue
                            if attr["name"] == "耐力":
                                main_factor = MEDICINE["endurance"].get(item, {}).get("main")
                                sub_factor = MEDICINE["endurance"].get(item, {}).get("sub")
                            else:
                                main_factor = MEDICINE["normal"].get(item, {}).get("main")
                                sub_factor = MEDICINE["normal"].get(item, {}).get("sub")
                            if not main_factor:
                                continue
                            if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                                old_val = attr_values[attr_key]
                                attr_values[attr_key] += 1
                                total_train += 1
                                if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                    last_record["end"] = attr_values[attr_key]
                                    result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                                else:
                                    result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                    last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                                success = True
            else:
                for f in FATIGUE_ORDER:
                    if success:
                        break
                    f_val = FATIGUE[f]
                    item_list = MEDICINE["order"][strategy] if plan_type == "medicine" else TRAIN["order"]
                    for item in item_list:
                        if success:
                            break
                        attr_list = [a for a in ATTRS if a["name"] != "维修" and attr_values[a["key"]] < target[a["key"]]]
                        if not attr_list:
                            attr_list = [a for a in ATTRS if attr_values[a["key"]] < target[a["key"]]]
                        if plan_type == "medicine" and strategy == "saveFive":
                            if not current_focus_attr or attr_values[current_focus_attr["key"]] >= target[current_focus_attr["key"]]:
                                current_focus_attr = next((a for a in attr_list if attr_values[a["key"]] < target[a["key"]]), None)
                            if current_focus_attr:
                                attr_list = [current_focus_attr]
                        for attr in attr_list:
                            attr_key = attr["key"]
                            if success or attr_values[attr_key] >= target[attr_key]:
                                continue
                            if attr["name"] == "耐力":
                                if plan_type == "medicine":
                                    main_factor = MEDICINE["endurance"].get(item, {}).get("main")
                                    sub_factor = MEDICINE["endurance"].get(item, {}).get("sub")
                                else:
                                    main_factor = TRAIN["endurance"].get(item, {}).get("main")
                                    sub_factor = TRAIN["endurance"].get(item, {}).get("sub")
                            else:
                                if plan_type == "medicine":
                                    main_factor = MEDICINE["normal"].get(item, {}).get("main")
                                    sub_factor = MEDICINE["normal"].get(item, {}).get("sub")
                                else:
                                    main_factor = TRAIN["normal"].get(item, {}).get("main")
                                    sub_factor = TRAIN["normal"].get(item, {}).get("sub")
                            if not main_factor:
                                continue
                            if can_add(max_limit, total_train, attr_values[attr_key], f_val, main_factor, sub_factor):
                                old_val = attr_values[attr_key]
                                attr_values[attr_key] += 1
                                total_train += 1
                                if last_record and last_record.get("f") == f and last_record.get("item") == item and last_record.get("attr_key") == attr_key:
                                    last_record["end"] = attr_values[attr_key]
                                    result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                                else:
                                    result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                    last_record = {"f": f, "item": item, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}
                                success = True

            if not success:
                target_attr = next((a for a in ATTRS if a["name"] != "维修" and attr_values[a["key"]] < target[a["key"]]), None)
                if not target_attr:
                    target_attr = next((a for a in ATTRS if attr_values[a["key"]] < target[a["key"]]), None)
                if not target_attr:
                    break
                attr_key = target_attr["key"]
                old_val = attr_values[attr_key]
                attr_values[attr_key] += 1
                total_train += 1
                five_level_medicine += 1
                five_attr[attr_key] += 1

                if last_record and last_record.get("isFive") and last_record.get("attr_key") == attr_key:
                    last_record["end"] = attr_values[attr_key]
                    result[-1] = f"[脸黑] - 五级药 - {target_attr['name']} {last_record['start']}→{last_record['end']}"
                else:
                    result.append(f"[脸黑] - 五级药 - {target_attr['name']} {old_val}→{attr_values[attr_key]}")
                    last_record = {"isFive": True, "attr_key": attr_key, "start": old_val, "end": attr_values[attr_key]}

        strategy_cn = STRATEGY_MAP.get(strategy, "基础方案")
        summary = [
            f"🎯 使用策略：{strategy_cn}（{strategy}）",
            f"✅ 总训练次数：{total_train - start_total}",
            f"✅ 五级药使用总量：{five_level_medicine}"
        ]
        five_text = []
        for attr in ATTRS:
            if five_attr[attr["key"]] > 0:
                five_text.append(f"{attr['name']}：{five_attr[attr['key']]}个")
        if five_text:
            summary.append("✅ 五级药分属性：" + " | ".join(five_text))
        final_attrs = []
        for attr in ATTRS:
            if attr_values[attr["key"]] > 0:
                final_attrs.append(f"{attr['name']}{attr_values[attr['key']]}")
        summary.append(f"✅ 最终属性：{' '.join(final_attrs)}")
        summary.append(f"\n{FOOTER_TEXT}")

        return result, summary

    # ===================== 菜单指令（优化后图片输出） =====================
    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        logger.info("收到 /超时空星舰菜单 指令！")
        try:
            menu_img_path = self.generate_menu_image()
            yield event.image_result(menu_img_path)
        except Exception as e:
            logger.error(f"生成菜单图片失败: {str(e)}", exc_info=True)
            fallback_menu = """📋 超时空星舰 功能菜单
------------------------
/超时空星舰菜单   - 显示此菜单
/装备属性 - 查看橙装/金装属性对比（图片版）
/生成吃药方案 - 生成吃药加点方案
/生成训练方案 - 生成训练加点方案
------------------------
📌 指令示例：
/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base
/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5
------------------------
📌 策略说明：
base - 基础方案 | priorFour - 优先四级药 | saveFive - 最省五药
------------------------
💡 小提示：
▸ 输入格式：属性名当前数值目标数值（例：生命当前0目标10）、上限数值（默认110，可自定义如：上限100）、策略英文标识（例：策略saveFive）
▸ 关键说明
  ▶ 可配置属性：生命/攻击/维修/能力/武器/引擎/科技/导航/耐力
  ▶ 五级药触发：仅常规药品/训练无法加点时自动使用
"""
            yield event.plain_result(fallback_menu)

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        logger.info("收到 /装备属性 指令！")
        try:
            img_path = self.generate_attr_image()
            yield event.image_result(img_path)
        except Exception as e:
            logger.error(f"生成图片失败: {str(e)}")
            fallback_text = """📊 超时空星舰装备属性对比表
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
└──────────┴─────────────────┴────────┴────────┘
"""
            yield event.plain_result(fallback_text)

    @filter.command("生成吃药方案")
    async def generate_medicine_plan(self, event: AstrMessageEvent):
        logger.info("收到 /生成吃药方案 指令！")
        try:
            params_str = self.get_event_params(event)
            if not params_str:
                yield event.plain_result("❌ 未获取到有效参数！\n请按照示例格式发送：\n/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base")
                return
            params = self.parse_plan_params(params_str, plan_type="medicine")
            if all(v == 0 for v in params["target"].values()):
                yield event.plain_result("❌ 请至少设置一个属性的目标值！\n示例：生命当前0目标10")
                return
            plan_lines, summary_lines = self.generate_plan(params)
            result_text = "📋 吃药加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成吃药方案失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base")

    @filter.command("生成训练方案")
    async def generate_train_plan(self, event: AstrMessageEvent):
        logger.info("收到 /生成训练方案 指令！")
        try:
            params_str = self.get_event_params(event)
            if not params_str:
                yield event.plain_result("❌ 未获取到有效参数！\n请按照示例格式发送：\n/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5")
                return
            params = self.parse_plan_params(params_str, plan_type="train")
            if all(v == 0 for v in params["target"].values()):
                yield event.plain_result("❌ 请至少设置一个属性的目标值！\n示例：生命当前0目标10")
                return
            plan_lines, summary_lines = self.generate_plan(params)
            result_text = "📋 训练加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成训练方案失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5")
