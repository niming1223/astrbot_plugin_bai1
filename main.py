from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("test_plugin", "Test", "测试插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 测试插件加载成功！")

    @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        logger.info("收到 /test 指令！")
        yield event.plain_result("成功了！")
