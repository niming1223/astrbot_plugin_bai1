from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("menu_plugin", "YourName", "菜单插件", "1.0.0")
class MenuPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 菜单插件加载成功！")

    @filter.command("菜单")
    async def menu_handler(self, event: AstrMessageEvent):
        logger.info("收到 /菜单 指令！")
        yield event.plain_result("测试")
