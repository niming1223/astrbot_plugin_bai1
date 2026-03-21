from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os

# 表格数据
TABLE_DATA = [
    ["装备属性", "英语", "橙装", "金装"],
    ["HP", "HP", "3.0", "3.0"],
    ["攻击", "Attack", "0.7", "0.7"],
    ["能力", "Ability", "15.7", "15.7"],
    ["火抗", "FireResistance", "63.7", "63.7"],
    ["耐力", "Stamina", "22", "26"],
    ["武器", "Weapon", "6.7", "6.7"],
    ["科技", "Sciece", "9.7", "9.7"],
    ["导航", "Pilot", "10.5", "10.5"],
    ["引擎", "Engine", "7.5", "9"],
    ["维修", "Repair", "0.6", "0.7"],
]

@register("starcitizen_attr_plugin", "YourName", "超时空星舰装备查询插件", "1.0.0")
class StarCitizenAttrPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ 超时空星舰插件加载成功！")

    def generate_attr_image(self):
        """生成装备属性表格图片"""
        # 图片大小
        cell_width = 180
        cell_height = 40
        rows = len(TABLE_DATA)
        cols = len(TABLE_DATA[0])
        
        # 创建图片
        img_width = cell_width * cols
        img_height = cell_height * rows
        image = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 加载字体（支持中文）
        try:
            # 尝试加载系统字体
            font = ImageFont.truetype("simhei.ttf", 20)
        except:
            # 如果没有，用默认字体
            font = ImageFont.load_default()
        
        # 绘制表格
        for i in range(rows + 1):
            draw.line([(0, i*cell_height), (img_width, i*cell_height)], fill='black', width=2)
        for j in range(cols + 1):
            draw.line([(j*cell_width, 0), (j*cell_width, img_height)], fill='black', width=2)
        
        # 绘制文字
        for i in range(rows):
            for j in range(cols):
                text = TABLE_DATA[i][j]
                # 居中文字
                text_width, text_height = draw.textsize(text, font=font)
                x = j*cell_width + (cell_width - text_width)/2
                y = i*cell_height + (cell_height - text_height)/2
                draw.text((x, y), text, fill='black', font=font)
        
        # 保存图片
        img_path = "/tmp/equip_attr.png"
        image.save(img_path)
        return img_path

    @filter.command("超时空星舰菜单")
    async def 超时空星舰菜单(self, event: AstrMessageEvent):
        """显示超时空星舰功能菜单"""
        logger.info("收到 /超时空星舰菜单 指令！")
        menu_content = """📋 超时空星舰 功能菜单
------------------------
/超时空星舰菜单   - 显示此菜单
/装备属性 - 查看橙装/金装属性对比（图片版）
------------------------
发送指令即可使用对应功能~
"""
        yield event.plain_result(menu_content)

    @filter.command("装备属性")
    async def 装备属性(self, event: AstrMessageEvent):
        """查看完整装备属性表（图片版）"""
        logger.info("收到 /装备属性 指令！")
        try:
            # 生成图片
            img_path = self.generate_attr_image()
            # 发送图片
            yield event.image_result(img_path)
        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            yield event.plain_result("生成图片失败， fallback 到文字版：\n| 装备属性 | 英语 | 橙装 | 金装 |\n| -------- | -------- | -------- | -------- |\n| HP | HP | 3.0 | 3.0 |\n| 攻击 | Attack | 0.7 | 0.7 |\n| 能力 | Ability | 15.7 | 15.7 |\n| 火抗 | FireResistance | 63.7 | 63.7 |\n| 耐力 | Stamina | 22 | 26 |\n| 武器 | Weapon | 6.7 | 6.7 |\n| 科技 | Sciece | 9.7 | 9.7 |\n| 导航 | Pilot | 10.5 | 10.5 |\n| 引擎 | Engine | 7.5 | 9 |\n| 维修 | Repair | 0.6 | 0.7 |")
