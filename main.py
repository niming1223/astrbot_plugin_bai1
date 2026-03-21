from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("equip_attr_plugin", "YourName", "装备属性查询插件", "1.0.0")
class EquipAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 装备属性查询插件加载成功！")

    @filter.command("装备属性")
    async def equip_attr_handler(self, event: AstrMessageEvent):
        logger.info("收到 /装备属性 指令！")
        # 整理好的装备属性表
        attr_content = """📊 装备属性数值对比表
| 装备属性 | 英语标识 | 橙装数值 | 金装数值 |
| -------- | -------- | -------- | -------- |
| HP       | HP       | 3.0      | 3.0      |
| 攻击     | Attack   | 0.7      | 0.7      |
| 能力     | Ability  | 15.7     | 15.7     |
| 火抗     | FireResistance | 63.7 | 63.7 |
| 耐力     | Stamina  | 22       | 26       |
| 武器     | Weapon   | 6.7      | 6.7      |
| 科技     | Sciece   | 9.7      | 9.7      |
| 导航     | Pilot    | 10.5     | 10.5     |
| 引擎     | Engine   | 7.5      | 9        |
| 维修     | Repair   | 0.6      | 0.7      |
"""
        yield event.plain_result(attr_content)
