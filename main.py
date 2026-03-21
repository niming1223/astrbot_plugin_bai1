from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")

    @filter.command("超时空星舰菜单")
    async def menu_handler(self, event: AstrMessageEvent, *args, **kwargs):
        """显示超时空星舰功能菜单"""
        logger.info("收到 /超时空星舰菜单 指令！")
        menu_content = """📋 超时空星舰 功能菜单
------------------------
/超时空星舰菜单   - 显示此菜单
/装备属性 - 查看橙装/金装属性对比
------------------------
发送指令即可使用对应功能~
"""
        await event.send(menu_content)

    @filter.command("装备属性")
    async def equip_attr_handler(self, event: AstrMessageEvent, *args, **kwargs):
        """查看完整装备属性表"""
        logger.info("收到 /装备属性 指令！")
        attr_content = """📊 超时空星舰 装备属性数值对比表
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
        await event.send(attr_content)
