from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("helloworld", "YourName", "我的第一个插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 我的插件加载成功啦！")

    @filter.command("你好")
    async def 你好_handler(self, event: AstrMessageEvent):
        logger.info("收到 /你好 指令！")
        user_name = event.get_sender_name()
        yield event.plain_result(f"你好呀, {user_name}！")
