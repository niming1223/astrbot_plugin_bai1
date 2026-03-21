from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("test", "Test", "测试插件", "1.0.0")
class TestPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        logger.info("收到测试指令！")
        yield event.plain_result("插件正常工作！")
