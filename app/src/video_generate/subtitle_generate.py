import asyncio
import edge_tts
import sys
import logging
import re
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

MIN_CHARS_PER_SUBTITLE = 5
MAX_CHARS_PER_SUBTITLE = 30

P_SPLIT = r"([，。？！；：,.?!;:“”])"
P_TERMINAL = "，。？！；：,.?!;:"
P_TO_REMOVE = "，。？！；：,.?!;:"
QUOTES = "“”"


def _format_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds_int = int(seconds)
    minutes, seconds_int = divmod(seconds_int, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}.{milliseconds:03d}"


def _split_sentence_respecting_quotes(sentence: str) -> List[str]:
    if not sentence:
        return []

    result = []
    current_part = ""
    in_quotes = False
    last_index = 0

    for match in re.finditer(P_SPLIT, sentence):
        char = match.group(1)
        start, end = match.span()

        current_part += sentence[last_index:start]

        if char in QUOTES:
            in_quotes = not in_quotes
            current_part += char
        elif char in P_TERMINAL and not in_quotes:
            current_part += char
            result.append(current_part.strip())
            current_part = ""
        else:
            current_part += char

        last_index = end

    remaining = sentence[last_index:].strip()
    if remaining:
        current_part += remaining
        result.append(current_part.strip())
    elif current_part:
        result.append(current_part.strip())

    return [p for p in result if p]


async def generate_tts_optimized_split(
    text: str,
    voice: str = "zh-CN-YunxiNeural",
    audio_output_file: str = "output.mp3",
    vtt_output_file: str = "output.vtt",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> bool:
    logger.info(
        f"开始生成任务（优化字幕切分，尊重引号）：音频 -> {audio_output_file}, 字幕 -> {vtt_output_file}"
    )
    try:
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, volume=volume, pitch=pitch
        )
    except Exception as e:
        logger.error(f"初始化 Communicate 时出错: {e}")
        return False

    sentence_boundaries: List[Dict[str, Any]] = []
    audio_saved = False
    success = False

    try:
        logger.info("正在处理音频流并收集句子边界数据...")
        with open(audio_output_file, "wb") as audio_file:
            async for chunk in communicate.stream():
                chunk_type = chunk.get("type")
                if chunk_type == "audio":
                    audio_data = chunk.get("data")
                    if audio_data:
                        audio_file.write(audio_data)
                        audio_saved = True
                elif chunk_type == "SentenceBoundary":
                    offset_ns = chunk.get("offset")
                    duration_ns = chunk.get("duration")
                    sentence_text = chunk.get("text")
                    if (
                        offset_ns is not None
                        and duration_ns is not None
                        and sentence_text is not None
                    ):
                        sentence_boundaries.append(
                            {
                                "start_ns": offset_ns,
                                "duration_ns": duration_ns,
                                "text": sentence_text.strip(),
                            }
                        )
                    else:
                        logger.warning(
                            f"收到的 SentenceBoundary 块缺少必要信息: {chunk}"
                        )

        if not audio_saved:
            logger.warning("未能写入任何音频数据。")
            return False
        logger.info(f"音频文件已成功写入: {audio_output_file}")

    except Exception as e:
        logger.exception("处理流时发生错误")
        return False

    fine_subtitles: List[Dict[str, Any]] = []
    if sentence_boundaries:
        logger.info("正在根据标点（尊重引号）切分句子并估算初始时间戳...")
        for sentence_info in sentence_boundaries:
            sentence_text = sentence_info["text"]
            sentence_start_ns = sentence_info["start_ns"]
            sentence_duration_ns = sentence_info["duration_ns"]

            parts_with_punctuation = _split_sentence_respecting_quotes(sentence_text)

            if not parts_with_punctuation:
                continue

            cleaned_sentence_for_length = ""
            temp_parts_cleaned_for_length = []
            for part in parts_with_punctuation:
                temp_cleaned = part
                if temp_cleaned and temp_cleaned[-1] in P_TO_REMOVE:
                    temp_cleaned = temp_cleaned[:-1].strip()

                if temp_cleaned:
                    cleaned_sentence_for_length += temp_cleaned
                    temp_parts_cleaned_for_length.append(temp_cleaned)

            total_cleaned_chars = len(cleaned_sentence_for_length)
            if total_cleaned_chars == 0:
                continue

            current_offset_ns = sentence_start_ns
            for i, part_text_with_punc in enumerate(parts_with_punctuation):
                if i >= len(temp_parts_cleaned_for_length):
                    continue
                cleaned_part_text_for_length = temp_parts_cleaned_for_length[i]
                part_cleaned_chars = len(cleaned_part_text_for_length)
                if part_cleaned_chars == 0:
                    continue

                part_duration_ns = int(
                    (part_cleaned_chars / total_cleaned_chars) * sentence_duration_ns
                )
                part_duration_ns = max(part_duration_ns, 1)

                if i == len(parts_with_punctuation) - 1:
                    part_end_ns = sentence_start_ns + sentence_duration_ns
                    part_duration_ns = part_end_ns - current_offset_ns
                    part_duration_ns = max(part_duration_ns, 1)
                else:
                    part_end_ns = current_offset_ns + part_duration_ns

                part_start_s = current_offset_ns / 10_000_000
                part_end_s = part_end_ns / 10_000_000
                part_end_s = max(part_start_s + 0.001, part_end_s)

                if part_text_with_punc:
                    fine_subtitles.append(
                        {
                            "start": part_start_s,
                            "end": part_end_s,
                            "text": part_text_with_punc,
                        }
                    )
                current_offset_ns += part_duration_ns
    else:
        logger.warning("未能收集到有效的句子边界信息。")

    optimized_subtitles: List[Dict[str, Any]] = []
    buffer: Optional[Dict[str, Any]] = None
    if fine_subtitles:
        logger.info("正在优化字幕：合并短行，最后移除末尾标点...")
        for i, part in enumerate(fine_subtitles):
            current_text_original = part["text"]
            if not current_text_original:
                continue

            text_for_length_check = current_text_original
            if text_for_length_check and text_for_length_check[-1] in P_TO_REMOVE:
                text_for_length_check = text_for_length_check[:-1].strip()
            if not text_for_length_check:
                continue

            current_part_data = {
                "start": part["start"],
                "end": part["end"],
                "text": current_text_original,
            }

            if buffer is None:
                buffer = current_part_data
            else:
                buffer_text_for_length_check = buffer["text"]
                if (
                    buffer_text_for_length_check
                    and buffer_text_for_length_check[-1] in P_TO_REMOVE
                ):
                    buffer_text_for_length_check = buffer_text_for_length_check[
                        :-1
                    ].strip()

                combined_length = len(buffer_text_for_length_check) + len(
                    text_for_length_check
                )

                if (
                    len(buffer_text_for_length_check) < MIN_CHARS_PER_SUBTITLE
                    and combined_length <= MAX_CHARS_PER_SUBTITLE
                ):
                    buffer["text"] += " " + current_part_data["text"]
                    buffer["end"] = current_part_data["end"]
                else:
                    final_text = buffer["text"]
                    if final_text and final_text[-1] in P_TO_REMOVE:
                        cleaned_text = final_text[:-1].strip()
                        if cleaned_text:
                            buffer["text"] = cleaned_text
                        else:
                            buffer = None
                    if buffer and buffer["text"]:
                        optimized_subtitles.append(buffer)

                    buffer = current_part_data

        if buffer is not None:
            final_text = buffer["text"]
            if final_text and final_text[-1] in P_TO_REMOVE:
                cleaned_text = final_text[:-1].strip()
                if cleaned_text:
                    buffer["text"] = cleaned_text
                else:
                    buffer = None

            if buffer and buffer["text"]:
                optimized_subtitles.append(buffer)

    logger.info(f"正在构建并写入 VTT 文件: {vtt_output_file}...")
    vtt_content = ["WEBVTT", ""]
    if optimized_subtitles:
        for i, part in enumerate(optimized_subtitles):
            start_s = part.get("start", 0.0)
            end_s = part.get("end", 0.0)
            text_content = part.get("text", "")

            start_s = min(start_s, end_s)
            end_s = max(start_s, end_s)

            start_formatted = _format_time(start_s)
            end_formatted = _format_time(end_s)

            vtt_content.append(str(i + 1))
            vtt_content.append(f"{start_formatted} --> {end_formatted}")
            vtt_content.append(text_content)
            vtt_content.append("")
    else:
        logger.info("没有可写入的字幕数据。")

    try:
        with open(vtt_output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(vtt_content))
        logger.info("VTT 文件写入成功。")
        success = True
    except Exception as e:
        logger.exception("写入 VTT 文件时出错")
        success = False

    return audio_saved and success


async def run_example():
    text_to_convert = "冰冷的雨水混杂着霓虹灯扭曲的光影，砸在艾拉的全息护目镜上，瞬间蒸发成迷蒙的雾气。她驾驶着“流萤”号悬浮摩托，像一道青蓝色的闪电，在层叠交错的空中廊道间穿梭。今晚的货很重要，是一块加密的数据核心，必须在午夜钟声敲响前送达城市另一端的“蜂巢”数据中心。引擎的嗡鸣盖过了雨声，也盖过了艾拉略显急促的呼吸。为了抄近路，她冒险钻进了一条鲜有人至的低空巷道。这里的建筑更加老旧，斑驳的墙体上爬满了荧光苔藓，与上方流光溢彩的摩天巨楼形成了诡异的对比。突然，一阵强烈的能量干扰让“流萤”的导航系统瞬间失灵，悬浮引擎也跟着剧烈抖动起来。艾拉惊呼一声，猛地拉动操纵杆，车身擦着布满管道的墙壁险险停下，溅起一片水花和老旧金属摩擦的刺耳声响。干扰源似乎来自巷道深处一个毫不起眼的门面。那扇古旧的木门上方，挂着一个几乎快要熄灭的灯牌，上面用古老的印刷体写着：“发条心工坊”。好奇心驱使着艾拉，她跳下悬浮车，推开了那扇吱呀作响的木门。门内是一个截然不同的世界。没有闪烁的全息屏幕，没有冰冷的金属合金，只有温暖的灯光，空气中弥漫着机油和木屑混合的奇特味道。齿轮、弹簧、发条……各种精密而古老的机械零件堆满了工作台和货架。一位头发花白的老者正戴着放大镜，专注地修复着一只黄铜制成的机械鸟，他身上穿着沾满油污的工装围裙，与这个时代格格入。老者抬起头，看到门口的艾拉，眼中闪过一丝惊讶，随即又恢复了平静。“躲雨吗，小姑娘？这鬼天气。”他的声音有些沙哑，却带着一种久经岁月沉淀的温和。艾拉一时不知如何回答，只是点了点头，目光被工作台上那只内部结构复杂精巧的机械鸟深深吸引。“这是……什么？”她忍不住问道。“老古董了，”老者笑了笑，放下手中的工具，“在你们这个时代，大概只能算是一堆无用的零件吧。”"
    voice_to_use = "zh-CN-YunxiNeural"
    audio_file_path = "output.mp3"
    vtt_file_path = "output.vtt"

    result = await generate_tts_optimized_split(
        text=text_to_convert,
        rate="+5%",
    )

    if result:
        logger.info("\n任务成功完成！")
    else:
        logger.error("\n任务失败。请检查上面的日志信息。")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_example())
