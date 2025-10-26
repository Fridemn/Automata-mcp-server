import asyncio
import os
import shutil
import time
from argparse import Namespace
from typing import Optional, Sequence

import cv2
import numpy as np
from loguru import logger
from mcp.shared.exceptions import McpError
from mcp.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    EmbeddedResource,
    ErrorData,
    ImageContent,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from app.base_tool import BaseMCPTool


class TextPager:
    """
    文本分页器，直接将长文本按字符数进行分页
    """

    def __init__(self, max_chars_per_page=300):
        self.max_chars_per_page = max_chars_per_page

    def paginate(self, text):
        """
        将文本分页
        """
        # 清理文本
        text = text.strip()

        # 如果文本不长，直接返回一页
        if len(text) <= self.max_chars_per_page:
            return [text]

        pages = []
        remaining_text = text

        while remaining_text:
            # 取当前页的内容
            if len(remaining_text) <= self.max_chars_per_page:
                pages.append(remaining_text)
                break

            # 找到合适的分割点（句号、问号、感叹号）
            page_text = remaining_text[: self.max_chars_per_page]
            last_sentence_end = max(
                page_text.rfind("。"),
                page_text.rfind("？"),
                page_text.rfind("！"),
                page_text.rfind("\n\n"),  # 段落分隔
            )

            if (
                last_sentence_end > self.max_chars_per_page * 0.7
            ):  # 如果在文本70%以上找到句子结束
                page_content = remaining_text[: last_sentence_end + 1]
            else:
                # 找不到合适的分割点，强制分割
                page_content = remaining_text[: self.max_chars_per_page]

            pages.append(page_content)
            remaining_text = remaining_text[len(page_content) :]

        return pages


class ImageTextRenderer:
    """
    图片文字渲染器，直接在图片上绘制文字
    """

    def __init__(
        self, font_path=None, font_size=32, line_spacing=1.2, font_color="black"
    ):
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.font_color = font_color.lower()  # 转换为小写

        # 尝试加载中文字体
        self.font_path = font_path or self._find_chinese_font()

    def _get_font_color(self):
        """获取字体颜色"""
        if self.font_color == "white":
            return (255, 255, 255)  # RGB for white
        else:  # default to black
            return (0, 0, 0)  # RGB for black

    def _find_chinese_font(self):
        """查找系统中可用的中文字体"""
        import platform

        system = platform.system()

        if system == "Windows":
            # Windows常见中文字体路径
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
            ]
        elif system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path

        # 如果找不到中文字体，返回None，使用OpenCV默认字体
        return None

    def render_text_on_image(self, image_path, text, output_path):
        """
        在图片上渲染文字并保存
        """
        # 读取背景图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片文件: {image_path}")

        height, width = image.shape[:2]

        # 如果有中文字体文件，使用PIL来渲染（更好的中文字体支持）
        if self.font_path:
            try:
                from PIL import Image, ImageDraw, ImageFont

                # 将OpenCV图像转换为PIL图像
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_image)

                # 加载字体
                try:
                    font = ImageFont.truetype(self.font_path, self.font_size)
                except Exception:
                    font = ImageFont.load_default()

                # 计算文字布局 - 所有图片都按9:16长图处理
                # 长图：最大化文字区域利用率
                text_margin_left = int(width * 0.1)  # 左右各10%的边距，文字宽度80%
                text_margin_right = int(width * 0.1)
                max_text_width = width - text_margin_left - text_margin_right

                # 垂直布局：文字占用70%的垂直空间
                top_margin = int(height * 0.15)  # 顶部15%的边距

                lines = self._wrap_text(text, max_text_width, font)

                # 计算文字块的总高度
                # 使用字体的实际高度来计算行高
                sample_bbox = font.getbbox("测试")
                actual_line_height = (
                    sample_bbox[3] - sample_bbox[1] + int(self.font_size * 0.2)
                )  # 加上一些额外间距
                line_height = max(
                    actual_line_height, int(self.font_size * self.line_spacing)
                )

                # 计算文字起始位置
                # 长图：从顶部边距开始绘制，不居中
                y_start = top_margin

                # 绘制文字
                for i, line in enumerate(lines):
                    # 计算文字宽度，用于水平居中
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]

                    # 根据图片比例计算水平位置
                    x = text_margin_left + (max_text_width - text_width) // 2

                    # y坐标应该是基线位置，使用实际的行高
                    y = (
                        y_start + i * line_height + (bbox[3] - bbox[1])
                    )  # bbox[3]-bbox[1]是文字高度

                    # 绘制文字
                    text_color = self._get_font_color() + (255,)  # 添加alpha通道
                    draw.text((x, y), font=font, fill=text_color, text=line)

                # 转换回OpenCV格式并保存
                result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                cv2.imwrite(output_path, result_image)

            except ImportError:
                # 如果没有PIL，使用OpenCV绘制文字
                self._render_with_opencv(image, text, output_path)
        else:
            # 使用OpenCV绘制文字
            self._render_with_opencv(image, text, output_path)

    def _wrap_text(self, text, max_width, font):
        """将文字按宽度换行"""
        lines = []
        current_line = ""

        for char in text:
            # 测试添加字符后的宽度
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                # 如果当前行不为空，添加到行列表
                if current_line:
                    lines.append(current_line)
                current_line = char

        # 添加最后一行
        if current_line:
            lines.append(current_line)

        return lines

    def _render_with_opencv(self, image, text, output_path):
        """使用OpenCV绘制文字"""
        height, width = image.shape[:2]

        # OpenCV文字参数
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.font_size / 24.0
        thickness = 2

        # 所有图片都按9:16长图处理
        # 长图：最大化文字区域利用率
        chars_per_line = int(width * 0.8 / (self.font_size * 0.6))  # 使用80%的宽度
        text_margin_left = int(width * 0.1)  # 左右各10%的边距
        text_margin_right = int(width * 0.1)
        top_margin = int(height * 0.15)  # 顶部15%的边距

        # 将文字按行分割
        lines = []
        line = ""

        for char in text:
            if len(line) >= chars_per_line and char in "。？！":
                lines.append(line + char)
                line = ""
            else:
                line += char

        if line:
            lines.append(line)

        # 计算行高
        line_height = int(self.font_size * self.line_spacing)

        # 绘制文字
        y = top_margin + line_height
        for line in lines:
            # 获取文字尺寸
            (text_width, text_height), baseline = cv2.getTextSize(
                line, font, font_scale, thickness
            )

            # 水平居中
            x = (
                text_margin_left
                + (width - text_margin_left - text_margin_right - text_width) // 2
            )

            # 绘制文字
            cv2.putText(
                image,
                line,
                (x, y),
                font,
                font_scale,
                self._get_font_color(),
                thickness,
                cv2.LINE_AA,
            )

            y += line_height

        # 保存图片
        cv2.imwrite(output_path, image)


class LongTextContent:
    """
    长文本内容填充器，直接将文字绘制到图片上
    """

    def __init__(self, args: Namespace):
        self.args = args
        self.logger = logger.bind(
            name="long_text_content", output_folder=args.output_folder_path
        )
        self.logger.info("开始初始化长文本内容pipeline")

        # 验证输入
        if not hasattr(args, "input_content") or not args.input_content:
            self.logger.error("input_content不能为空")
            raise ValueError("input_content不能为空")

        if not hasattr(args, "background_image_path") or not args.background_image_path:
            self.logger.error("background_image_path不能为空")
            raise ValueError("background_image_path不能为空")

        self.input_content = args.input_content.strip()
        self.background_image_path = args.background_image_path
        self.output_folder_path = args.output_folder_path
        self.font_color = getattr(args, "font_color", "black")

        # 初始化组件
        self.image_renderer = ImageTextRenderer(font_color=self.font_color)

    def _prepare_background_image(self):
        """
        检查背景图片比例，如果不是9:16则自动裁剪
        """
        image = cv2.imread(self.background_image_path)
        if image is None:
            raise ValueError(f"无法读取图片文件: {self.background_image_path}")

        height, width = image.shape[:2]
        aspect_ratio = width / height
        target_ratio = 9 / 16  # 0.5625

        if abs(aspect_ratio - target_ratio) < 0.01:  # 已经接近9:16
            return self.background_image_path

        # 需要裁剪
        self.logger.info(f"背景图片比例 {aspect_ratio:.3f} 不为9:16，准备裁剪")

        if aspect_ratio > target_ratio:  # 图片更宽，裁剪宽度
            new_width = int(height * target_ratio)
            offset = (width - new_width) // 2
            cropped = image[:, offset : offset + new_width]
            self.logger.info(f"裁剪宽度: {width} -> {new_width}, 高度保持 {height}")
        else:  # 图片更高，裁剪高度
            new_height = int(width / target_ratio)
            offset = (height - new_height) // 2
            cropped = image[offset : offset + new_height, :]
            self.logger.info(f"裁剪高度: {height} -> {new_height}, 宽度保持 {width}")

        # 保存裁剪后的图片
        cropped_path = os.path.join(self.output_folder_path, "cropped_background.png")
        cv2.imwrite(cropped_path, cropped)
        self.logger.info(f"裁剪后的图片保存到: {cropped_path}")

        return cropped_path

    def start(self):
        """
        开始处理长文本内容
        """
        self.logger.info("开始处理长文本内容")

        # 创建输出目录
        os.makedirs(self.output_folder_path, exist_ok=True)

        # 检查并裁剪背景图片为9:16比例
        processed_image_path = self._prepare_background_image()

        # 读取背景图片尺寸，计算每页最大字符数
        image = cv2.imread(processed_image_path)
        if image is None:
            raise ValueError(f"无法读取图片文件: {processed_image_path}")
        height, width = image.shape[:2]

        # 此时图片已经是9:16比例
        # 文字区域：70%高度，80%宽度
        available_height = height * 0.7
        max_text_width = width * 0.8

        # 估算行高和每行字符数
        font_size = 32
        line_height = int(font_size * 1.4)  # 1.4倍行间距
        chars_per_line = int(max_text_width / (font_size * 0.6))  # 估算每行字符数
        lines_per_page = int(available_height / line_height)

        # 将估算值缩减为原来的2/3以避免溢出
        estimated = lines_per_page * chars_per_line
        max_chars_per_page = max(50, int(estimated * 2 / 3))
        self.logger.info(
            f"图片尺寸：{width}x{height}, 原估算每页{estimated}字符，调整为{max_chars_per_page}字符 (2/3)"
        )

        # 初始化文本分页器
        self.text_pager = TextPager(max_chars_per_page=max_chars_per_page)

        # 对文本进行分页
        pages = self.text_pager.paginate(self.input_content)
        self.logger.info(f"文本已分为 {len(pages)} 页")

        # 为每个页面生成图片文件
        image_files = []
        for i, page_content in enumerate(pages):
            # 生成图片文件名
            image_filename = f"img_plan_{i}.png"
            image_filepath = os.path.join(self.output_folder_path, image_filename)

            # 在背景图片上渲染文字
            self.image_renderer.render_text_on_image(
                processed_image_path, page_content, image_filepath
            )

            image_files.append(image_filepath)
            self.logger.info(f"已生成第 {i+1} 页图片: {image_filename}")

        self.logger.info(f"长文本内容处理完成，共生成 {len(image_files)} 个图片文件")
        return image_files


class LongTextContentParams(BaseModel):
    content: str = Field(description="长文本内容")
    background_image_path: str = Field(description="背景图片文件路径")
    output_folder_path: Optional[str] = Field(
        default=None, description="输出目录路径，如果不提供则使用临时目录"
    )
    font_color: Optional[str] = Field(
        default="black", description="字体颜色: black 或 white"
    )


class LongTextContentTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> dict:
        return {
            "endpoint": "/tools/long-text-content",
            "params_class": LongTextContentParams,
            "use_form": True,
            "tool_name": "create_long_text_content",
        }

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="create_long_text_content",
                description="""生成长文本内容类型的图片内容，用于填充小说等长文本到图片。

将长文本按页分割，并在背景图片上渲染文字，生成多张图片文件。
支持自动裁剪背景图片为9:16比例，自动分页和文字布局。""",
                inputSchema=LongTextContentParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "create_long_text_content":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = LongTextContentParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        # 验证背景图片文件是否存在
        if not os.path.exists(args.background_image_path):
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message=f"背景图片文件不存在: {args.background_image_path}",
                )
            )

        # 创建输出目录
        if args.output_folder_path is None:
            args.output_folder_path = f"data/output/temp/{int(time.time())}"

        os.makedirs(args.output_folder_path, exist_ok=True)

        # 复制背景图片到输出目录
        image_filename = os.path.basename(args.background_image_path)
        dest_image_path = os.path.join(args.output_folder_path, image_filename)
        shutil.copy(args.background_image_path, dest_image_path)

        # 创建args对象
        namespace_args = Namespace(
            input_content=args.content,
            background_image_path=dest_image_path,
            output_folder_path=args.output_folder_path,
            font_color=args.font_color,
        )

        try:
            # 执行pipeline
            content_processor = LongTextContent(namespace_args)
            image_files = await asyncio.to_thread(content_processor.start)

            return [
                TextContent(
                    type="text",
                    text=f"长文本内容生成成功\n输出路径: {args.output_folder_path}\n生成图片文件: {len(image_files)} 个\n文件列表: {', '.join(os.path.basename(f) for f in image_files)}",
                )
            ]

        except Exception as e:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"长文本内容生成失败: {str(e)}")
            )
