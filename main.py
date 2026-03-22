from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
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

# 属性列表
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

# 策略名称映射（英文→中文）
STRATEGY_MAP = {
    "base": "基础方案",
    "priorFour": "优先四级药方案",
    "saveFive": "最省五级药方案"
}

# 尾部固定文案
FOOTER_TEXT = "天啟舰队欢迎你，群号951239404"

# ===================== 核心计算函数 =====================
def calc_rate(max_limit: int, total_train: int, attr_value: int, fatigue_val: float, factor: float) -> float:
    numerator = (max_limit - total_train) * (max_limit - attr_value) * fatigue_val * factor * 100
    denominator = max_limit * max_limit
    return numerator / denominator

def can_add(max_limit: int, total_train: int, main_attr_value: int, fatigue_val: float, main_factor: float, sub_factor: float) -> bool:
    main_rate = calc_rate(max_limit, total_train, main_attr_value, fatigue_val, main_factor)
    sub_rate = calc_rate(max_limit, total_train, 0, fatigue_val, sub_factor)
    return main_rate >= 1 and sub_rate < 1

@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")

    # ===================== 100%兼容获取指令参数 =====================
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

    # ===================== 参数解析函数 =====================
    def parse_plan_params(self, params_str: str, plan_type: str = "medicine") -> dict:
        params = {
            "max_limit": 110,
            "type": plan_type,
            "strategy": "base",
            "current": {},
            "target": {}
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

        logger.info(f"📊 解析完成的参数: {params}")
        return params

    # ===================== 生成方案核心函数 =====================
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

        # 汇总信息（包含策略显示）
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
        
        # 添加尾部固定文案
        summary.append(f"\n{FOOTER_TEXT}")

        return result, summary

    # ===================== 指令处理函数 =====================
    @filter.command("生成吃药方案")
    async def generate_medicine_plan(self, event: AstrMessageEvent):
        logger.info("收到 /生成吃药方案 指令！")
        try:
            params_str = self.get_event_params(event)
            if not params_str:
                yield event.plain_result(f"❌ 未获取到有效参数！\n请按照示例格式发送：\n/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base\n\n{FOOTER_TEXT}")
                return
            
            params = self.parse_plan_params(params_str, plan_type="medicine")
            
            if all(v == 0 for v in params["target"].values()):
                yield event.plain_result(f"❌ 请至少设置一个属性的目标值！\n示例：生命当前0目标10\n\n{FOOTER_TEXT}")
                return
            
            plan_lines, summary_lines = self.generate_plan(params)
            result_text = "📋 吃药加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成吃药方案失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成吃药方案 上限110 生命当前0目标10 攻击当前0目标5 策略base\n\n{FOOTER_TEXT}")

    @filter.command("生成训练方案")
    async def generate_train_plan(self, event: AstrMessageEvent):
        logger.info("收到 /生成训练方案 指令！")
        try:
            params_str = self.get_event_params(event)
            if not params_str:
                yield event.plain_result(f"❌ 未获取到有效参数！\n请按照示例格式发送：\n/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5\n\n{FOOTER_TEXT}")
                return
            
            params = self.parse_plan_params(params_str, plan_type="train")
            
            if all(v == 0 for v in params["target"].values()):
                yield event.plain_result(f"❌ 请至少设置一个属性的目标值！\n示例：生命当前0目标10\n\n{FOOTER_TEXT}")
                return
            
            plan_lines, summary_lines = self.generate_plan(params)
            result_text = "📋 训练加点方案\n" + "\n".join(plan_lines) + "\n\n" + "\n".join(summary_lines)
            yield event.plain_result(result_text)
        except Exception as e:
            logger.error(f"生成训练方案失败: {str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 生成方案失败：{str(e)}\n请检查输入格式，示例：\n/生成训练方案 上限110 生命当前0目标10 攻击当前0目标5\n\n{FOOTER_TEXT}")
