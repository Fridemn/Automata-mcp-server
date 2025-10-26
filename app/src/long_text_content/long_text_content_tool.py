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
        将文本分页，避免标点符号单独被分到下一页，优先考虑段落分隔
        """
        # 定义句子结束符、段落分隔符和所有标点符号
        sentence_endings = "。？！"
        paragraph_separator = "\n\n"
        all_punctuation = "。？！，；：" "''（）【】《》" "'"

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

            # 在允许的范围内找到最佳分割点
            max_search_pos = min(
                len(remaining_text), int(self.max_chars_per_page * 1.3)
            )  # 允许30%超限
            search_text = remaining_text[:max_search_pos]

            # 找到所有可能的分割位置：段落分隔和句子结束
            split_candidates = []

            # 首先查找段落分隔符
            para_pos = search_text.find(paragraph_separator)
            while para_pos != -1:
                split_candidates.append(
                    (para_pos + len(paragraph_separator), "paragraph")
                )
                para_pos = search_text.find(paragraph_separator, para_pos + 1)

            # 然后查找句子结束符
            for i, char in enumerate(search_text):
                if char in sentence_endings:
                    split_candidates.append((i + 1, "sentence"))

            # 按位置排序
            split_candidates.sort(key=lambda x: x[0], reverse=True)

            split_pos = self.max_chars_per_page

            # 从后往前检查每个可能的分割点
            for pos, split_type in split_candidates:
                if pos < self.max_chars_per_page * 0.5:  # 太靠前了，跳过
                    continue

                candidate_split = pos

                # 检查分割后下一页的第一个字符
                if candidate_split < len(remaining_text):
                    next_page_first_char = remaining_text[candidate_split]

                    # 检查下一页是否以标点开头或是否太短（可能是标题）
                    is_bad_start = (
                        next_page_first_char in all_punctuation  # 以标点开头
                        or self._is_likely_title(
                            remaining_text[candidate_split:].strip()
                        )  # 可能是标题
                    )

                    if not is_bad_start:
                        # 找到了好的分割点
                        split_pos = candidate_split
                        break

                    # 如果是段落分隔，稍微放宽条件
                    if split_type == "paragraph":
                        # 检查下一段是否太短（可能是标题）
                        next_paragraph = remaining_text[candidate_split:].strip()
                        if len(next_paragraph) > 20:  # 如果下一段够长，接受这个分割点
                            split_pos = candidate_split
                            break

                else:
                    # 已经是文本末尾
                    split_pos = candidate_split
                    break

            # 如果没找到合适的分割点，使用字符数限制
            if split_pos == self.max_chars_per_page:
                # 最后尝试避免在标点前断开
                if self.max_chars_per_page < len(remaining_text):
                    next_char = remaining_text[self.max_chars_per_page]
                    if next_char in all_punctuation:
                        # 向后查找非标点位置
                        for offset in range(
                            1,
                            min(30, len(remaining_text) - self.max_chars_per_page + 1),
                        ):
                            check_pos = self.max_chars_per_page + offset
                            if check_pos >= len(remaining_text):
                                break
                            check_char = remaining_text[check_pos]
                            if check_char not in all_punctuation:
                                split_pos = check_pos
                                break

            page_content = remaining_text[:split_pos]
            pages.append(page_content)
            remaining_text = remaining_text[split_pos:]

        return pages

    def _is_likely_title(self, text):
        """
        判断文本是否可能是标题
        """
        if not text:
            return False

        # 标题特征：较短、没有句子结束符、以特定字符开头等
        lines = text.split("\n")
        first_line = lines[0].strip()

        # 如果第一行很短（少于20字符），可能是标题
        if len(first_line) < 20:
            return True

        # 如果第一行没有句子结束符，也可能是标题
        if not any(char in first_line for char in "。？！"):
            return True

        return False


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
                    # 对于空行，绘制一个空格以保持行间距
                    line_to_draw = line if line.strip() else " "

                    # 计算文字宽度，用于水平居中
                    bbox = draw.textbbox((0, 0), line_to_draw, font=font)
                    text_width = bbox[2] - bbox[0]

                    # 根据图片比例计算水平位置
                    x = text_margin_left + (max_text_width - text_width) // 2

                    # y坐标应该是基线位置，使用实际的行高
                    y = (
                        y_start + i * line_height + (bbox[3] - bbox[1])
                    )  # bbox[3]-bbox[1]是文字高度

                    # 绘制文字
                    text_color = self._get_font_color() + (255,)  # 添加alpha通道
                    draw.text((x, y), font=font, fill=text_color, text=line_to_draw)

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
        """将文字按宽度换行，正确处理已有的换行符，避免标点符号单独成行"""
        # 定义完整的标点符号集合（包括中文和英文标点）
        punctuation = "。？！，；：" "''（）【】《》" "'.,?!:;()[]{}、—…"

        # 首先按已有的换行符分割文本
        paragraphs = text.split("\n")
        all_lines = []

        for paragraph in paragraphs:
            if not paragraph.strip():  # 空行
                all_lines.append("")
                continue

            # 对每个段落按宽度换行
            lines = []
            current_line = ""

            i = 0
            while i < len(paragraph):
                char = paragraph[i]

                # 测试添加字符后的宽度
                test_line = current_line + char
                bbox = font.getbbox(test_line)
                test_width = bbox[2] - bbox[0]

                if test_width <= max_width:
                    # 可以添加这个字符
                    current_line = test_line
                    i += 1
                else:
                    # 无法添加这个字符，需要处理换行
                    if current_line:
                        # 当前行不为空，检查是否可以特殊处理标点符号
                        if char in punctuation:
                            # 对于标点符号，允许稍微超过宽度（15%）以避免单独成行
                            extended_width = max_width * 1.15
                            if test_width <= extended_width:
                                current_line = test_line
                                i += 1
                                continue

                            # 如果还是无法合并，尝试在句子结束符处分割
                            remaining_text = paragraph[i:]
                            best_split_pos = 1

                            # 优先在句子结束符（。？！）处分割
                            sentence_enders = "。？！"
                            for j, c in enumerate(
                                remaining_text[:15]
                            ):  # 向前看15个字符
                                if c in sentence_enders:
                                    candidate_line = (
                                        current_line + remaining_text[: j + 1]
                                    )
                                    candidate_bbox = font.getbbox(candidate_line)
                                    candidate_width = (
                                        candidate_bbox[2] - candidate_bbox[0]
                                    )
                                    if candidate_width <= extended_width:
                                        best_split_pos = j + 1
                                        break

                            if best_split_pos > 1:
                                # 找到了合适的分割点
                                current_line = (
                                    current_line + remaining_text[:best_split_pos]
                                )
                                i += best_split_pos
                                lines.append(current_line)
                                current_line = ""
                                continue

                        # 普通换行：添加当前行，新起一行
                        lines.append(current_line)
                        current_line = char
                        i += 1
                    else:
                        # 当前行为空，直接添加字符
                        current_line = char
                        i += 1

            # 添加最后一行
            if current_line:
                lines.append(current_line)

            all_lines.extend(lines)

        return all_lines

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

        # 将文字按行分割，正确处理已有的换行符
        lines = []

        # 首先按换行符分割
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph.strip():  # 空行
                lines.append("")
                continue

            # 对每个段落按字符数和标点符号换行
            line = ""
            for char in paragraph:
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
            if not line.strip():  # 空行
                y += line_height  # 只是增加行间距，不绘制文字
                continue

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
        # 处理常见的转义字符，如 \n, \t, \\, \" 等
        # 使用更安全的方法，只替换已知的转义序列
        self.input_content = self._decode_safe_escapes(self.input_content)
        self.background_image_path = args.background_image_path
        self.output_folder_path = args.output_folder_path
        self.font_color = getattr(args, "font_color", "black")

        # 初始化组件
        self.image_renderer = ImageTextRenderer(font_color=self.font_color)

    def _decode_safe_escapes(self, text):
        """
        安全地解码常见的转义序列，避免破坏正常的Unicode字符
        只处理 \n, \t, \\, \" 等基本转义序列
        """
        if not isinstance(text, str):
            return text

        # 定义需要处理的转义序列映射
        escape_map = {
            "\\n": "\n",  # 换行
            "\\t": "\t",  # 制表符
            "\\r": "\r",  # 回车
            "\\\\": "\\",  # 反斜杠
            '\\"': '"',  # 双引号
            "\\'": "'",  # 单引号
        }

        result = text
        for escape_seq, actual_char in escape_map.items():
            result = result.replace(escape_seq, actual_char)

        return result

    def _prepare_background_image(self):
        """
        检查背景图片比例，如果不是9:16则自动裁剪，然后缩放到1080*1920
        """
        image = cv2.imread(self.background_image_path)
        if image is None:
            raise ValueError(f"无法读取图片文件: {self.background_image_path}")

        height, width = image.shape[:2]
        aspect_ratio = width / height
        target_ratio = 9 / 16  # 0.5625

        processed_image = image
        processed_height, processed_width = height, width

        if abs(aspect_ratio - target_ratio) < 0.01:  # 已经接近9:16
            self.logger.info(f"背景图片已经是9:16比例 ({width}x{height})")
        else:
            # 需要裁剪
            self.logger.info(f"背景图片比例 {aspect_ratio:.3f} 不为9:16，准备裁剪")

            if aspect_ratio > target_ratio:  # 图片更宽，裁剪宽度
                new_width = int(height * target_ratio)
                offset = (width - new_width) // 2
                processed_image = image[:, offset : offset + new_width]
                processed_height, processed_width = height, new_width
                self.logger.info(f"裁剪宽度: {width} -> {new_width}, 高度保持 {height}")
            else:  # 图片更高，裁剪高度
                new_height = int(width / target_ratio)
                offset = (height - new_height) // 2
                processed_image = image[offset : offset + new_height, :]
                processed_height, processed_width = new_height, width
                self.logger.info(
                    f"裁剪高度: {height} -> {new_height}, 宽度保持 {width}"
                )

        # 缩放到1080*1920
        target_width, target_height = 1080, 1920
        if processed_width != target_width or processed_height != target_height:
            self.logger.info(
                f"缩放图片: {processed_width}x{processed_height} -> {target_width}x{target_height}"
            )
            processed_image = cv2.resize(
                processed_image,
                (target_width, target_height),
                interpolation=cv2.INTER_LANCZOS4,
            )
            processed_height, processed_width = target_height, target_width

        # 保存处理后的图片
        processed_path = os.path.join(
            self.output_folder_path, "processed_background.png"
        )
        cv2.imwrite(processed_path, processed_image)
        self.logger.info(
            f"处理后的图片保存到: {processed_path} ({processed_width}x{processed_height})"
        )

        return processed_path

    def _calculate_page_lines(self, page_content, max_text_width):
        """
        预计算页面内容的行数
        """
        try:
            # 尝试使用PIL进行精确计算
            from PIL import ImageFont

            font = self.image_renderer._find_chinese_font()
            if font:
                font = ImageFont.truetype(font, self.image_renderer.font_size)
                lines = self.image_renderer._wrap_text(
                    page_content, max_text_width, font
                )
                return len(lines)
        except ImportError:
            pass

        # 如果没有PIL，使用估算方法
        # 简单估算：假设每行大约30个字符
        chars_per_line = max(
            20, int(max_text_width / (self.image_renderer.font_size * 0.6))
        )
        lines = page_content.split("\n")
        total_lines = 0
        for line in lines:
            if not line.strip():
                total_lines += 1  # 空行算一行
            else:
                total_lines += max(
                    1,
                    len(line) // chars_per_line
                    + (1 if len(line) % chars_per_line else 0),
                )
        return total_lines

    def _is_likely_title(self, text):
        """
        判断文本是否可能是标题
        """
        if not text:
            return False

        # 标题特征：较短、没有句子结束符、以特定字符开头等
        lines = text.split("\n")
        first_line = lines[0].strip()

        # 如果第一行很短（少于20字符），可能是标题
        if len(first_line) < 20:
            return True

        # 如果第一行没有句子结束符，也可能是标题
        if not any(char in first_line for char in "。？！"):
            return True

        return False

    def _adjust_pagination_for_overflow(self, pages, available_height, max_text_width):
        """
        检测并调整分页以避免内容溢出
        """
        font_size = 32
        line_height = int(font_size * 1.4)  # 1.4倍行间距
        max_lines_per_page = int(available_height / line_height)

        self.logger.info(f"每页最大行数: {max_lines_per_page}")

        # 检查每一页是否会溢出
        adjusted_pages = []

        for page_content in pages:
            page_lines = self._calculate_page_lines(page_content, max_text_width)
            self.logger.info(f"页面行数: {page_lines}, 内容长度: {len(page_content)}")

            if page_lines <= max_lines_per_page:
                # 页面适合，直接添加
                adjusted_pages.append(page_content)
            else:
                # 页面会溢出，需要重新分页
                self.logger.warning(
                    f"检测到页面溢出 ({page_lines} > {max_lines_per_page} 行)，重新分页"
                )

                # 将溢出的内容拆分，使用智能分页避免标点单独成页
                remaining_content = page_content

                while remaining_content:
                    # 计算当前剩余内容的行数
                    current_lines = self._calculate_page_lines(
                        remaining_content, max_text_width
                    )

                    if current_lines <= max_lines_per_page:
                        # 剩余内容适合一页
                        adjusted_pages.append(remaining_content)
                        break

                    # 需要分割，找到合适的分割点
                    # 估算目标长度
                    target_ratio = max_lines_per_page / current_lines
                    estimated_target_length = max(
                        100, int(len(remaining_content) * target_ratio * 0.9)
                    )

                    # 在估算长度范围内寻找最佳分割点
                    max_search_length = min(
                        len(remaining_content), int(estimated_target_length * 1.3)
                    )
                    search_text = remaining_content[:max_search_length]

                    # 找到所有可能的分割位置：段落分隔和句子结束
                    split_candidates = []
                    paragraph_separator = "\n\n"

                    # 首先查找段落分隔符
                    para_pos = search_text.find(paragraph_separator)
                    while para_pos != -1:
                        split_candidates.append(
                            (para_pos + len(paragraph_separator), "paragraph")
                        )
                        para_pos = search_text.find(paragraph_separator, para_pos + 1)

                    # 然后查找句子结束符
                    sentence_endings = "。？！"
                    for i, char in enumerate(search_text):
                        if char in sentence_endings:
                            split_candidates.append((i + 1, "sentence"))

                    # 按位置排序
                    split_candidates.sort(key=lambda x: x[0], reverse=True)

                    split_pos = estimated_target_length

                    # 从后往前检查每个可能的分割点
                    for pos, split_type in split_candidates:
                        if pos < estimated_target_length * 0.5:  # 太靠前了，跳过
                            continue

                        candidate_split = pos

                        # 检查分割后下一页的第一个字符
                        if candidate_split < len(remaining_content):
                            next_page_first_char = remaining_content[candidate_split]

                            # 检查下一页是否以标点开头或是否太短（可能是标题）
                            all_punctuation = '。？！，；：""\'\'（）【】《》""\''
                            is_bad_start = (
                                next_page_first_char in all_punctuation  # 以标点开头
                                or self._is_likely_title(
                                    remaining_content[candidate_split:].strip()
                                )  # 可能是标题
                            )

                            if not is_bad_start:
                                # 找到了好的分割点
                                split_pos = candidate_split
                                break

                            # 如果是段落分隔，稍微放宽条件
                            if split_type == "paragraph":
                                # 检查下一段是否太短（可能是标题）
                                next_paragraph = remaining_content[
                                    candidate_split:
                                ].strip()
                                if (
                                    len(next_paragraph) > 20
                                ):  # 如果下一段够长，接受这个分割点
                                    split_pos = candidate_split
                                    break

                        else:
                            # 已经是文本末尾
                            split_pos = candidate_split
                            break

                    # 确保分割位置不会太小
                    split_pos = max(split_pos, 50)

                    page_part = remaining_content[:split_pos]
                    adjusted_pages.append(page_part)
                    remaining_content = remaining_content[split_pos:]

                    if not remaining_content.strip():
                        break

        return adjusted_pages

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

        # 将估算值调整为原来的1.3倍以增加每页文字量
        estimated = lines_per_page * chars_per_line
        max_chars_per_page = max(50, int(estimated * 1.3))
        self.logger.info(
            f"图片尺寸：{width}x{height}, 原估算每页{estimated}字符，调整为{max_chars_per_page}字符 (1.3倍)"
        )

        # 初始化文本分页器
        self.text_pager = TextPager(max_chars_per_page=max_chars_per_page)

        # 对文本进行分页
        pages = self.text_pager.paginate(self.input_content)

        # 检测并调整分页以避免内容溢出
        pages = self._adjust_pagination_for_overflow(
            pages, available_height, max_text_width
        )

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
