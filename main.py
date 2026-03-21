from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")

    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        """显示超时空星舰功能菜单"""
        logger.info("收到 /超时空星舰菜单 指令！")
        menu_content = """📋 超时空星舰 功能菜单
------------------------
/超时空星舰菜单   - 显示此菜单
/装备属性 - 查看橙装/金装属性对比
------------------------
发送指令即可使用对应功能~
"""
        yield event.plain_result(menu_content)

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        """查看完整装备属性表"""
        logger.info("收到 /装备属性 指令！")
        # 完全按照你图片里的表格格式
        attr_content = """📊 装备属性数值对比表
| 装备属性 | 英语 | 橙装 | 金装 |
| -------- | -------- | -------- | -------- |
| HP | HP | 3.0 | 3.0 |
| 攻击 | Attack | 0.7 | 0.7 |
| 能力 | Ability | 15.7 | 15.7 |
| 火抗 | FireResistance | 63.7 | 63.7 |
| 耐力 | Stamina | 22 | 26 |
| 武器 | Weapon | 6.7 | 6.7 |
| 科技 | Sciece | 9.7 | 9.7 |
| 导航 | Pilot | 10.5 | 10.5 |
| 引擎 | Engine | 7.5 | 9 |
| 维修 | Repair | 0.6 | 0.7 |
"""
        yield event.plain_result(attr_content)
