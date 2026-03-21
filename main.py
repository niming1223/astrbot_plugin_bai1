from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("HelloWorld 插件初始化成功！")

    # 注册指令的装饰器。指令名为 你好。注册成功后，发送 `/你好` 就会触发这个指令
    @filter.command("你好")
    async def 你好_handler(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""
        user_name = event.get_sender_name()
        message_str = event.message_str  # 用户发的纯文本消息字符串
        message_chain = event.get_messages()  # 用户所发的消息的消息链
        logger.info(f"收到消息链: {message_chain}")
        # 使用 f-string 格式化用户名
        yield event.plain_result(f"你好, {user_name}！")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("HelloWorld 插件已卸载！")
