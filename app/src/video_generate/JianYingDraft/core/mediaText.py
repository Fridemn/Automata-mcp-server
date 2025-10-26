"""
* @file   : materialVideo.py
* @time   : 15:23
* @date   : 2024/3/23
* @mail   : 9727005@qq.com
* @creator: ShanDong Xiedali
* @company: HiLand & RainyTop
"""

from . import template
from .media import Media
from ..utils import tools


class MediaText(Media):
    def __init__(self, **kwargs):
        kwargs.setdefault("media_type", "text")
        # [修改] 初始化时，确保 duration 至少有一个默认值 (例如 5 秒)
        # 否则基类 的 self.duration 可能为 0
        kwargs.setdefault("duration", 5_000_000)
        super().__init__(**kwargs)

    pass

    def _set_material_data_for_content(self):
        ma_id = tools.generate_id()

        self.material_data_for_content["material_animations"] = (
            template.get_material_animation(ma_id)  #
        )
        subtitle = self.kwargs.get("text", "")
        color = self.kwargs.get("color", "#EB0D0D")
        texts = self.__generate_text()
        texts["content"] = texts["content"].replace("[默认文本]", f"[{subtitle}]")

        # +++++【新增代码：正确处理 Scale】+++++
        # (因为 media.py 现在会忽略 text 的 scale)
        # 我们在这里捕获 scale 并将其应用到 text material 的 "initial_scale"

        scale_dict = self.kwargs.get("scale", None)
        if scale_dict and isinstance(scale_dict, dict) and "x" in scale_dict:
            # 应用于 materials.texts (正确)
            texts["initial_scale"] = scale_dict["x"]
        elif isinstance(scale_dict, (int, float)):
            texts["initial_scale"] = scale_dict
        else:
            # 默认 initial_scale 为 1.0，与实际文件匹配
            texts["initial_scale"] = 1.0
        # 设置默认字体大小，与实际文件匹配
        texts["font_size"] = 15.0
        # ++++++++++++++++++++++++++++++

        self.material_data_for_content["texts"] = texts
        self.change_color(color)

        # 将素材的各种业务信息，暂时保存起来，后续供track下的segment使用
        self.material_data_for_content["X.extra_material_refs"] = [
            ma_id,
        ]

    def __generate_text(self):
        _self = self
        entity = template.get_text(self.id)
        return entity

    # +++++【修改：完全重写此方法，不再调用 super()】+++++
    def _set_segment_data_for_content(self):
        """
        设置草稿文件track中的segment部分 (重写)

        [核心修复]:
        1. 不调用 super()，因为基类 会错误地应用 'scale' 到 segment["clip"]。
        2. 我们自己实现 segment 的创建，复制基类的必要逻辑。
        3. 我们只从 kwargs 读取 'transform' 并应用到 segment["clip"]["transform"] (正确)。
        4. 'scale' 参数被有意忽略 (它已在 _set_material_data_for_content 中被用于 texts["initial_scale"])。
        """
        # 1. 获取基础 segment 模板
        segment = template.get_segment()  #

        # 2. 检查 kwargs 是否有 transform (这是正确的)
        if "transform" in self.kwargs:
            segment["clip"]["transform"] = self.kwargs.get("transform")

        # 3. (核心) 有意忽略 kwargs 中的 'scale'，segment["clip"]["scale"] 保持模板默认值 (1.0)

        # 4. 复制基类 的其他必要逻辑
        speed = self.kwargs.get("speed", 1.0)
        segment["speed"] = speed  # 速度
        start_in_media = self.kwargs.get("start_in_media", 0)

        segment["material_id"] = self.id
        segment["extra_material_refs"] = self.material_data_for_content[
            "X.extra_material_refs"
        ]

        segment["source_timerange"] = {
            "duration": self.duration,
            "start": start_in_media,
        }

        segment["target_timerange"] = {
            "duration": self.duration
            / speed,  # self.duration 已在 __init__ 中确保不为0
            "start": 0,
        }

        self.segment_data_for_content = segment

    # ++++++++++++++++++++++++++++++++++++++++++++++

    def set_position(self, x: float, y: float):
        """
        设置字幕的位置
        :param x: x坐标
        :param y: y坐标
        """
        if (
            not hasattr(self, "segment_data_for_content")
            or self.segment_data_for_content is None
        ):
            self._set_segment_data_for_content()

        self.segment_data_for_content["clip"]["transform"] = {"x": x, "y": y}

    def set_font_size(self, size: float):
        """
        设置字幕字体大小
        :param size: 字体大小
        """
        if (
            not hasattr(self, "material_data_for_content")
            or self.material_data_for_content is None
        ):
            self._set_material_data_for_content()

        # 更新 font_size
        self.material_data_for_content["texts"]["font_size"] = size

        # 更新 content 中的 size
        content = self.material_data_for_content["texts"]["content"]
        # 替换现有的 size 值
        import re

        content = re.sub(r"<size=\d+\.\d+>", f"<size={size:.6f}>", content)
        self.material_data_for_content["texts"]["content"] = content

    def change_color(self, color):
        """
        改变文字颜色
        :param color: 以“#”开头后跟6位的颜色值
        """
        self.material_data_for_content["texts"]["text_color"] = color

        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        color1 = "<color=(1.000000, 1.000000, 1.000000, 1.000000)>"
        color2 = f"<color=({round(r / 255, 6):.6f}, {round(g / 255, 6):.6f}, {round(b / 255, 6):.6f}, 1.000000)>"

        # 替换颜色，并调整字体大小为15.0
        content = self.material_data_for_content["texts"]["content"]
        content = content.replace(color1, color2)
        content = content.replace("size=50.000000", "size=15.000000")
        self.material_data_for_content["texts"]["content"] = content


pass
