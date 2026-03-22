from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import re

# ===================== 训练/吃药计算器核心配置 =====================
# 疲劳值配置
FATIGUE = {"大笑": 1, "微笑": 0.5, "流汗": 0.33}
FATIGUE_ORDER = ["大笑", "微笑", "流汗"]

# 药品配置
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

# 训练配置
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

# 属性列表（与前端保持一致）
ATTRS = [
    {"name": "生命", "key": "life"},
    {"name": "攻击", "key": "atk"},
    {"name": "维修", "key": "repair"},
    {"name": "能力", "key": "ability"},
    {"name": "武器", "key": "weapon"},
    {"name": "引擎", "key": "engine"},
    {"name": "科技", "key": "tech"},
    {"name": "导航", "key": "nav"},
    {"name": "耐力", "key": "endurance"}
]

# ===================== 原有：装备属性表格数据 =====================
TABLE_DATA = [
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

# ===================== 核心计算函数 =====================
def calc_rate(max_limit: int, total_train: int, attr_value: int, fatigue_val: float, factor: float) -> float:
    """计算属性增长率（对应前端calcRate）"""
    numerator = (max_limit - total_train) * (max_limit - attr_value) * fatigue_val * factor * 100
    denominator = max_limit * max_limit
    return numerator / denominator

def can_add(max_limit: int, total_train: int, main_attr_value: int, fatigue_val: float, main_factor: float, sub_factor: float) -> bool:
    """判断是否可以添加该属性（对应前端canAdd）"""
    main_rate = calc_rate(max_limit, total_train, main_attr_value, fatigue_val, main_factor)
    sub_rate = calc_rate(max_limit, total_train, 0, fatigue_val, sub_factor)
    return main_rate >= 1 and sub_rate < 1

@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")
        # 获取插件目录（Windows 绝对路径）
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        # 确保目录存在
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

    # ===================== 工具函数：兼容获取消息内容 =====================
    def get_event_message(self, event: AstrMessageEvent) -> str:
        """
        兼容不同版本astrbot的消息获取方式
        依次尝试：content → raw_message → message → 空字符串
        """
        msg = ""
        # 优先尝试标准属性 content
        if hasattr(event, "content"):
            msg = event.content
        # 备选 raw_message
        elif hasattr(event, "raw_message"):
            msg = event.raw_message
        # 最后尝试 message
        elif hasattr(event, "message"):
            msg = event.message
        # 去除首尾空格和特殊字符（如括号、换行）
        msg = msg.strip().replace("）", "").replace("(", "").replace("）", "").replace("，", " ")
        return msg

    # ===================== 原有功能：字体/图片生成 =====================
    def get_windows_font(self):
        """获取 Windows 系统自带的中文字体（绝对不会找不到）"""
        # Windows 系统自带字体路径
        font_paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc"),
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # 加载字体，大小20
                    return ImageFont.truetype(font_path, 20)
                except:
                    continue
        
        # 终极兜底：使用PIL默认字体（虽然可能不显示中文，但不会崩溃）
        return ImageFont.load_default()

    def generate_attr_image(self):
        """生成装备属性表格图片（Windows 专用）"""
        # 表格单元格大小
        cell_width = 180
        cell_height = 40
        rows = len(TABLE_DATA)
        cols = len(TABLE_DATA[0])
        
        # 创建白色背景图片
        img_width = cell_width * cols
        img_height = cell_height * rows
        image = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 获取 Windows 系统字体
        font = self.get_windows_font()
        
        # 绘制表格边框（黑色实线）
        # 横线
        for i in range(rows + 1):
            y = i * cell_height
            draw.line([(0, y), (img_width, y)], fill=(0, 0, 0), width=2)
        # 竖线
        for j in range(cols + 1):
            x = j * cell_width
            draw.line([(x, 0), (x, img_height)], fill=(0, 0, 0), width=2)
        
        # 绘制表格文字（居中显示）
        for i in range(rows):
            for j in range(cols):
                text = TABLE_DATA[i][j]
                # 计算文字大小（兼容新旧PIL版本）
                try:
                    # 新PIL版本
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                except:
                    # 旧PIL版本
                    text_w, text_h = draw.textsize(text, font=font)
                
                # 计算文字居中坐标
                x = j * cell_width + (cell_width - text_w) // 2
                y = i * cell_height + (cell_height - text_h) // 2
                
                # 绘制黑色文字
                draw.text((x, y), text, fill=(0, 0, 0), font=font)
        
        # 保存图片到插件目录（Windows 有权限）
        img_path = os.path.join(self.plugin_dir, "equip_attr.png")
        # 先删除旧图片（避免权限冲突）
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
        # 保存新图片
        image.save(img_path, "PNG")
        return img_path

    # ===================== 新增：参数解析函数（增加容错） =====================
    def parse_plan_params(self, msg: str) -> dict:
        """
        解析用户输入的参数，格式示例：
        /生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 耐力当前0目标8 策略base
        /生成训练方案 上限110 生命当前0目标10 攻击当前0目标5
        """
        params = {
            "max_limit": 110,  # 默认训练上限
            "type": "medicine", # 默认生成吃药方案
            "strategy": "base", # 默认基础策略
            "current": {},      # 当前属性
            "target": {}        # 目标属性
        }

        # 提取训练上限（容错：无数字则用默认值）
        limit_match = re.search(r"上限(\d+)", msg)
        if limit_match:
            params["max_limit"] = int(limit_match.group(1))

        # 提取方案类型（吃药/训练）
        if "生成训练方案" in msg:
            params["type"] = "train"

        # 提取策略（容错：无策略则用base）
        strategy_match = re.search(r"策略(\w+)", msg)
        if strategy_match:
            strategy = strategy_match.group(1)
            # 校验策略是否合法
            if strategy in MEDICINE["order"].keys():
                params["strategy"] = strategy
        # 兼容用户直接输入策略名（无"策略"前缀）
        elif "priorFour" in msg:
            params["strategy"] = "priorFour"
        elif "saveFive" in msg:
            params["strategy"] = "saveFive"

        # 提取各属性的当前/目标值（增加容错：参数不完整时默认0）
        for attr in ATTRS:
            attr_name = attr["name"]
            # 匹配 "生命当前0目标10" 格式（容错：缺少数字时默认0）
            attr_match = re.search(f"{attr_name}当前(\d+)目标(\d+)", msg)
            if attr_match:
                try:
                    params["current"][attr["key"]] = int(attr_match.group(1))
                    params["target"][attr["key"]] = int(attr_match.group(2))
                except:
                    params["current"][attr["key"]] = 0
                    params["target"][attr["key"]] = 0
            else:
                # 未指定则默认0
                params["current"][attr["key"]] = 0
                params["target"][attr["key"]] = 0

        return params

    # ===================== 新增：生成方案核心函数 =====================
    def generate_plan(self, params: dict) -> tuple:
        """
        生成吃药/训练方案
        返回：(方案文本列表, 汇总信息)
        """
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
            # 检查是否全部完成或达到上限
            all_finish = all(attr_values[k] >= target[k] for k in attr_values.keys())
            if all_finish or total_train >= max_limit:
                break

            success = False

            # 优先四级药策略（priorFour）
            if plan_type == "medicine" and strategy == "priorFour":
                item_list = MEDICINE["order"][strategy]
                for item in item_list:
                    if success:
                        break
                    for f in FATIGUE_ORDER:
                        if success:
                            break
                        f_val = FATIGUE[f]
                        # 先排除维修属性，全满后再包含
                        attr_list = [a for a in ATTRS if a["name"] != "维修" and attr_values[a["key"]] < target[a["key"]]]
                        if not attr_list:
                            attr_list = [a for a in ATTRS if attr_values[a["key"]] < target[a["key"]]]
                        
                        for attr in attr_list:
                            attr_key = attr["key"]
                            if success or attr_values[attr_key] >= target[attr_key]:
                                continue
                            
                            # 获取主/副因子
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
                                # 合并连续记录
                                if last_record and last_record["f"] == f and last_record["item"] == item and last_record["attr_key"] == attr_key:
                                    last_record["end"] = attr_values[attr_key]
                                    result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                                else:
                                    result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                    last_record = {
                                        "f": f, "item": item, "attr_key": attr_key,
                                        "start": old_val, "end": attr_values[attr_key]
                                    }
                                success = True
            # 基础/最省五药策略
            else:
                for f in FATIGUE_ORDER:
                    if success:
                        break
                    f_val = FATIGUE[f]
                    item_list = MEDICINE["order"][strategy] if plan_type == "medicine" else TRAIN["order"]
                    
                    for item in item_list:
                        if success:
                            break
                        # 先排除维修属性，全满后再包含
                        attr_list = [a for a in ATTRS if a["name"] != "维修" and attr_values[a["key"]] < target[a["key"]]]
                        if not attr_list:
                            attr_list = [a for a in ATTRS if attr_values[a["key"]] < target[a["key"]]]
                        
                        # 最省五药策略：聚焦单个属性
                        if plan_type == "medicine" and strategy == "saveFive":
                            if not current_focus_attr or attr_values[current_focus_attr["key"]] >= target[current_focus_attr["key"]]:
                                current_focus_attr = next((a for a in attr_list if attr_values[a["key"]] < target[a["key"]]), None)
                            if current_focus_attr:
                                attr_list = [current_focus_attr]
                        
                        for attr in attr_list:
                            attr_key = attr["key"]
                            if success or attr_values[attr_key] >= target[attr_key]:
                                continue
                            
                            # 获取主/副因子
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
                                # 合并连续记录
                                if last_record and last_record.get("f") == f and last_record.get("item") == item and last_record.get("attr_key") == attr_key:
                                    last_record["end"] = attr_values[attr_key]
                                    result[-1] = f"[{f}] - {item} - {attr['name']} {last_record['start']}→{last_record['end']}"
                                else:
                                    result.append(f"[{f}] - {item} - {attr['name']} {old_val}→{attr_values[attr_key]}")
                                    last_record = {
                                        "f": f, "item": item, "attr_key": attr_key,
                                        "start": old_val, "end": attr_values[attr_key]
                                    }
                                success = True

            # 脸黑用五级药
            if not success:
                # 优先非维修属性
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

                # 合并连续五级药记录
                if last_record and last_record.get("isFive") and last_record.get("attr_key") == attr_key:
                    last_record["end"] = attr_values[attr_key]
                    result[-1] = f"[脸黑] - 五级药 - {target_attr['name']} {last_record['start']}→{last_record['end']}"
                else:
                    result.append(f"[脸黑] - 五级药 - {target_attr['name']} {old_val}→{attr_values[attr_key]}")
                    last_record = {
                        "isFive": True, "attr_key": attr_key,
                        "start": old_val, "end": attr_values[attr_key]
                    }

        # 生成汇总信息
        summary = [
            f"✅ 总训练次数：{total_train - start_total}",
            f"✅ 五级药使用总量：{five_level_medicine}"
        ]
        # 五级药分属性统计
        five_text = []
        for attr in ATTRS:
            if five_attr[attr["key"]] > 0:
                five_text.append(f"{attr['name']}：{five_attr[attr['key']]}个")
        if five_text:
            summary.append("✅ 五级药分属性：" + " | ".join(five_text))
        # 最终属性
        final_attrs = []
        for attr in ATTRS:
            if attr_values[attr["key"]] > 0:
                final_attrs.append(f"{attr['name']}{attr_values[attr['key']]}")
        summary.append(f"✅ 最终属性：{' '.join(final_attrs)}")

        return result, summary

    # ===================== 指令处理函数 =====================
    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        """显示超时空星舰功能菜单（新增吃药/训练方案说明）"""
        logger.info("收到 /超时空星舰菜单 指令！")
        menu_content = """📋 超时空星舰 功能菜单
------------------------
/超时空星舰菜单   - 显示此菜单
/装备属性 - 查看橙装/金装属性对比（图片版）
/生成吃药方案 - 生成吃药加点方案（示例：/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base）
/生成训练方案 - 生成训练加点方案（示例：/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5）
------------------------
策略说明：
base - 基础方案 | priorFour - 优先四级药 | saveFive - 最省五药
------------------------
发送指令即可使用对应功能~
"""
        yield event.plain_result(menu_content)

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        """查看完整装备属性表（图片版）"""
        logger.info("收到 /装备属性 指令！")
        try:
            # 生成图片
            img_path = self.generate_attr_image()
            # 发送图片
            yield event.image_result(img_path)
        except Exception as e:
            logger.error(f"生成图片失败: {str(e)}")
            # 兜底文字版（ASCII表格）
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
        """生成吃药加点方案"""
        logger.info("收到 /生成吃药方案 指令！")
        try:
            # 兼容获取消息内容
            msg = self.get_event_message(event)
            if not msg:
                raise ValueError("未获取到有效指令参数")
            
            # 解析参数
            params = self.parse_plan_params(msg)
            # 生成方案
            plan_lines, summary_lines = self.generate_plan(params)
            # 拼接结果
            result_text = "📋 吃药加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            # 发送结果（超长内容自动分片）
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成吃药方案失败: {str(e)}")
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base")

    @filter.command("生成训练方案")
    async def generate_train_plan(self, event: AstrMessageEvent):
        """生成训练加点方案"""
        logger.info("收到 /生成训练方案 指令！")
        try:
            # 兼容获取消息内容
            msg = self.get_event_message(event)
            if not msg:
                raise ValueError("未获取到有效指令参数")
            
            # 解析参数
            params = self.parse_plan_params(msg)
            params["type"] = "train"  # 强制指定为训练方案
            # 生成方案
            plan_lines, summary_lines = self.generate_plan(params)
            # 拼接结果
            result_text = "📋 训练加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            # 发送结果
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成训练方案失败: {str(e)}")
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5")
