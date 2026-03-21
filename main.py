import random
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 装备属性数据
EQUIP_DATA = {
    "橙装": {
        "HP": 3.0, "攻击": 0.7, "能力": 15.7, "火抗": 63.7,
        "耐力": 22, "武器": 6.7, "科技": 9.7, "导航": 10.5,
        "引擎": 7.5, "维修": 0.6
    },
    "金装": {
        "HP": 3.0, "攻击": 0.7, "能力": 15.7, "火抗": 63.7,
        "耐力": 26, "武器": 6.7, "科技": 9.7, "导航": 10.5,
        "引擎": 9.0, "维修": 0.7
    }
}

@register("equip_gacha_plugin", "YourName", "装备赌狗插件", "1.0.0")
class EquipGachaPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 装备赌狗插件加载成功！")

    @filter.command("装备属性")
    async def equip_attr_handler(self, event: AstrMessageEvent):
        """查看完整装备属性表"""
        logger.info("收到 /装备属性 指令！")
        attr_content = """📊 装备属性数值对比表
------------------------
【橙装】
HP: 3.0 | 攻击: 0.7 | 能力: 15.7
火抗: 63.7 | 耐力: 22 | 武器: 6.7
科技: 9.7 | 导航: 10.5 | 引擎: 7.5 | 维修: 0.6
------------------------
【金装】
HP: 3.0 | 攻击: 0.7 | 能力: 15.7
火抗: 63.7 | 耐力: 26 | 武器: 6.7
科技: 9.7 | 导航: 10.5 | 引擎: 9.0 | 维修: 0.7
"""
        yield event.plain_result(attr_content)

    @filter.command("赌装备")
    async def gacha_handler(self, event: AstrMessageEvent):
        """模拟赌装备"""
        logger.info("收到 /赌装备 指令！")
        user_name = event.get_sender_name()
        
        # 抽奖概率：70%橙装，30%金装
        rarity = random.choices(["橙装", "金装"], weights=[70, 30])[0]
        stats = EQUIP_DATA[rarity]
        
        # 构建结果消息
        result_msg = f"🎰 {user_name} 赌装备结果：\n"
        result_msg += f"✨ 恭喜获得【{rarity}】！\n"
        result_msg += "------------------------\n"
        result_msg += f"📈 装备属性：\n"
        result_msg += f"HP: {stats['HP']}\n"
        result_msg += f"攻击: {stats['攻击']}\n"
        result_msg += f"能力: {stats['能力']}\n"
        result_msg += f"火抗: {stats['火抗']}\n"
        result_msg += f"耐力: {stats['耐力']}\n"
        result_msg += f"武器: {stats['武器']}\n"
        result_msg += f"科技: {stats['科技']}\n"
        result_msg += f"导航: {stats['导航']}\n"
        result_msg += f"引擎: {stats['引擎']}\n"
        result_msg += f"维修: {stats['维修']}"
        
        yield event.plain_result(result_msg)
