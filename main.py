from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# 表格数据
TABLE_DATA = [
    ["装备属性", "英语", "橙装", "金装"],
    ["生命", "HP", "3.0", "3.0"],
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
        # 获取插件目录（Windows 绝对路径）
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        # 确保目录存在
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

    def get_windows_font(self):
        """获取 Windows 系统自带的中文字体（绝对不会找不到）"""
        # Windows 系统自带字体路径
        font_paths = [
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simhei.ttf"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "msyh.ttc"),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "simsun.ttc"),
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # 加载字体，大小20
                    return ImageFont.truetype(font_path, 20)
                except:
                    continue
        
        # 终极兜底：使用PIL默认字体（虽然可能不显示中文，但不会崩溃）
        return ImageFont.load_default()

    def generate_attr_image(self):
        """生成装备属性表格图片（Windows 专用）"""
        # 表格单元格大小
        cell_width = 180
        cell_height = 40
        rows = len(TABLE_DATA)
        cols = len(TABLE_DATA[0])
        
        # 创建白色背景图片
        img_width = cell_width * cols
        img_height = cell_height * rows
        image = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 获取 Windows 系统字体
        font = self.get_windows_font()
        
        # 绘制表格边框（黑色实线）
        # 横线
        for i in range(rows + 1):
            y = i * cell_height
            draw.line([(0, y), (img_width, y)], fill=(0, 0, 0), width=2)
        # 竖线
        for j in range(cols + 1):
            x = j * cell_width
            draw.line([(x, 0), (x, img_height)], fill=(0, 0, 0), width=2)
        
        # 绘制表格文字（居中显示）
        for i in range(rows):
            for j in range(cols):
                text = TABLE_DATA[i][j]
                # 计算文字大小（兼容新旧PIL版本）
                try:
                    # 新PIL版本
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                except:
                    # 旧PIL版本
                    text_w, text_h = draw.textsize(text, font=font)
                
                # 计算文字居中坐标
                x = j * cell_width + (cell_width - text_w) // 2
                y = i * cell_height + (cell_height - text_h) // 2
                
                # 绘制黑色文字
                draw.text((x, y), text, fill=(0, 0, 0), font=font)
        
        # 保存图片到插件目录（Windows 有权限）
        img_path = os.path.join(self.plugin_dir, "equip_attr.png")
        # 先删除旧图片（避免权限冲突）
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
        # 保存新图片
        image.save(img_path, "PNG")
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
            logger.error(f"生成图片失败: {str(e)}")
            # 兜底文字版（ASCII表格）
            fallback_text = """📊 超时空星舰装备属性对比表
┌──────────┬─────────────────┬────────┬────────┐
│ 装备属性 │ 英语            │ 橙装   │ 金装   │
├──────────┼─────────────────┼────────┼────────┤
│ HP       │ HP              │ 3.0    │ 3.0    │
│ 攻击     │ Attack          │ 0.7    │ 0.7    │
│ 能力     │ Ability         │ 15.7   │ 15.7   │
│ 火抗     │ FireResistance  │ 63.7   │ 63.7   │
│ 耐力     │ Stamina         │ 22     │ 26     │
│ 武器     │ Weapon          │ 6.7    │ 6.7    │
│ 科技     │ Sciece          │ 9.7    │ 9.7    │
│ 导航     │ Pilot           │ 10.5   │ 10.5   │
│ 引擎     │ Engine          │ 7.5    │ 9      │
│ 维修     │ Repair          │ 0.6    │ 0.7    │
└──────────┴─────────────────┴────────┴────────┘
"""
            yield event.plain_result(fallback_text)
