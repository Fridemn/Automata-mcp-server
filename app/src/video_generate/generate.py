import moviepy.editor as mp
from loguru import logger
import webvtt
import os

from .JianYingDraft.core.draft import Draft
from .subtitle_generate import generate_tts_optimized_split

# --- 时间转换常量 ---
MICROSECONDS_PER_SECOND = 1_000_000


def format_subtitle_text(text: str, max_chars_per_line: int = 10) -> str:
    """
    格式化字幕文本，每 max_chars_per_line 个字符添加一个换行符。
    """
    if len(text) <= max_chars_per_line:
        return text

    # 每 max_chars_per_line 个字符插入换行符
    formatted_lines = []
    for i in range(0, len(text), max_chars_per_line):
        formatted_lines.append(text[i : i + max_chars_per_line])

    return "\n".join(formatted_lines)


def create_video(
    draft_name: str,
    videos_path: list | str,
    subtitle_path: str,
    audio_path: str,
    music_path: str = "",
    video_ratio: str = "9:16",
    drafts_root: str = "",
):
    audio_duration_micros = 0
    # 获取音频长度（单位：微秒）
    try:
        audio_clip = mp.AudioFileClip(audio_path)
        # 直接转换为微秒整数
        audio_duration_micros = int(audio_clip.duration * MICROSECONDS_PER_SECOND)
        logger.info(
            f"音频长度: {audio_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒 ({audio_duration_micros} 微秒)"
        )
        audio_clip.close()
    except Exception as e:
        logger.error(f"无法处理音频文件 '{audio_path}': {e}")
        return

    # 创建视频草稿
    draft = Draft(draft_name, drafts_root)

    # 设置视频比例
    if video_ratio == "16:9":
        draft._draft_content_data["canvas_config"]["width"] = 1920
        draft._draft_content_data["canvas_config"]["height"] = 1080
        draft._draft_content_data["canvas_config"]["ratio"] = "16:9"
        logger.info("设置视频比例为 16:9 (横屏)")
    elif video_ratio == "9:16":
        draft._draft_content_data["canvas_config"]["width"] = 1080
        draft._draft_content_data["canvas_config"]["height"] = 1920
        draft._draft_content_data["canvas_config"]["ratio"] = "9:16"
        logger.info("设置视频比例为 9:16 (竖屏)")
    elif video_ratio == "1:1":
        draft._draft_content_data["canvas_config"]["width"] = 1080
        draft._draft_content_data["canvas_config"]["height"] = 1080
        draft._draft_content_data["canvas_config"]["ratio"] = "1:1"
        logger.info("设置视频比例为 1:1 (正方形)")
    else:
        logger.warning(f"不支持的视频比例: {video_ratio}，使用默认 9:16")
        draft._draft_content_data["canvas_config"]["width"] = 1080
        draft._draft_content_data["canvas_config"]["height"] = 1920
        draft._draft_content_data["canvas_config"]["ratio"] = "9:16"

    current_track_time_micros = 0  #

    # 1. 添加视频片段
    if isinstance(videos_path, str):
        video_file_path = videos_path
        try:
            video_clip = mp.VideoFileClip(video_file_path)
            video_duration_micros = int(video_clip.duration * MICROSECONDS_PER_SECOND)
            video_clip.close()

            if video_duration_micros <= 0:
                raise ValueError("视频时长为 0 或无效")

            logger.info(
                f"处理单个视频: {os.path.basename(video_file_path)}, 时长: {video_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
            )
            if audio_duration_micros <= video_duration_micros:
                logger.info(
                    f"音频时长短于或等于视频时长，添加单个片段，时长: {audio_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                )
                draft.add_media(
                    media_file_full_name=video_file_path,
                    start_at_track=0,
                    duration=audio_duration_micros,
                )
                current_track_time_micros = audio_duration_micros  # 更新轨道时间
            else:
                times = audio_duration_micros // video_duration_micros
                remainder_micros = audio_duration_micros % video_duration_micros
                logger.info(
                    f"音频时长长于视频时长，需要循环 {times} 次完整视频，剩余 {remainder_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                )

                for i in range(times):
                    start_time = i * video_duration_micros
                    logger.info(
                        f"  添加第 {i+1} 个循环片段，起始: {start_time / MICROSECONDS_PER_SECOND:.2f} 秒, 时长: {video_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                    )
                    draft.add_media(
                        media_file_full_name=video_file_path,
                        start_at_track=start_time,
                        duration=video_duration_micros,
                    )

                if remainder_micros > 0:
                    start_time = times * video_duration_micros
                    logger.info(
                        f"  添加剩余片段，起始: {start_time / MICROSECONDS_PER_SECOND:.2f} 秒, 时长: {remainder_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                    )
                    draft.add_media(
                        media_file_full_name=video_file_path,
                        start_at_track=start_time,
                        duration=remainder_micros,
                    )
                current_track_time_micros = audio_duration_micros

        except Exception as e:
            logger.error(f"处理视频 '{video_file_path}' 失败: {e}")

    elif isinstance(videos_path, list):
        logger.info(f"处理视频列表，共 {len(videos_path)} 个视频")
        total_added_video_duration_micros = 0

        for video_file_path in videos_path:
            try:
                video_clip = mp.VideoFileClip(video_file_path)
                current_video_duration_micros = int(
                    video_clip.duration * MICROSECONDS_PER_SECOND
                )
                video_clip.close()

                if current_video_duration_micros <= 0:
                    logger.warning(
                        f"跳过时长为 0 或无效的视频: {os.path.basename(video_file_path)}"
                    )
                    continue

                logger.info(
                    f"  处理视频: {os.path.basename(video_file_path)}, 时长: {current_video_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                )

                remaining_audio_micros = (
                    audio_duration_micros - total_added_video_duration_micros
                )

                if remaining_audio_micros <= 0:
                    logger.info("  已达到所需音频时长，不再添加更多视频。")
                    break

                duration_to_add_micros = min(
                    current_video_duration_micros, remaining_audio_micros
                )

                logger.info(
                    f"    添加到轨道，起始: {total_added_video_duration_micros / MICROSECONDS_PER_SECOND:.2f} 秒, 时长: {duration_to_add_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
                )

                draft.add_media(
                    media_file_full_name=video_file_path,
                    start_at_track=total_added_video_duration_micros,
                    duration=duration_to_add_micros,
                )
                total_added_video_duration_micros += duration_to_add_micros

            except Exception as e:
                logger.error(f"处理视频 '{video_file_path}' 失败: {e}")
                continue

        current_track_time_micros = total_added_video_duration_micros

    # 2. 添加音频 (音频长度会根据视频长度自动剪裁 - 这是库的功能)
    if audio_path and audio_duration_micros > 0:
        logger.info(f"添加音频: {os.path.basename(audio_path)}")
        fade_out_micros = min(2 * MICROSECONDS_PER_SECOND, audio_duration_micros)
        logger.info(
            f"  设置音频淡出时长: {fade_out_micros / MICROSECONDS_PER_SECOND:.2f} 秒"
        )

        draft.add_media(
            media_file_full_name=audio_path,
            fade_in_duration=0,
            fade_out_duration=fade_out_micros,
        )
    else:
        logger.warning("未提供有效音频文件或音频时长为0，跳过添加音频。")

    # 3. 添加字幕（从 VTT 文件读取）
    if subtitle_path:
        try:
            logger.info(f"添加字幕: {os.path.basename(subtitle_path)}")
            captions = webvtt.read(subtitle_path)
            for i, caption in enumerate(captions):
                # 转换时间戳为微秒 (整数)
                start_time_micros = int(
                    float(caption.start_in_seconds) * MICROSECONDS_PER_SECOND
                )
                end_time_micros = int(
                    float(caption.end_in_seconds) * MICROSECONDS_PER_SECOND
                )
                text = caption.text.strip()

                # 格式化字幕文本：每10个字符换行
                formatted_text = format_subtitle_text(text, max_chars_per_line=10)

                # 检查字幕时间是否超出视频总长
                if start_time_micros >= current_track_time_micros:
                    logger.warning(
                        f"  跳过第 {i+1} 条字幕 (起始时间 {start_time_micros / MICROSECONDS_PER_SECOND:.2f} 秒 超出视频总长 {current_track_time_micros / MICROSECONDS_PER_SECOND:.2f} 秒): '{text}'"
                    )
                    continue

                # 如果字幕结束时间超出视频总长，则截断
                adjusted_end_time_micros = min(
                    end_time_micros, current_track_time_micros
                )
                subtitle_duration_micros = adjusted_end_time_micros - start_time_micros

                if subtitle_duration_micros <= 0:
                    logger.warning(
                        f"  跳过第 {i+1} 条字幕 (计算后时长为0或负数): '{text}'"
                    )
                    continue

                logger.info(
                    f"  添加字幕: 开始 {start_time_micros / MICROSECONDS_PER_SECOND:.2f} 秒, 结束 {adjusted_end_time_micros / MICROSECONDS_PER_SECOND:.2f} 秒, 内容: '{formatted_text}'"
                )

                draft.add_subtitle(
                    subtitle=formatted_text,
                    start_time=start_time_micros,
                    end_time=adjusted_end_time_micros,
                    position=(0.0, -0.8),
                    font_size=15.0,
                    color="#FFFF00",
                    start_at_track=start_time_micros,
                    duration=subtitle_duration_micros,
                )
        except Exception as e:
            logger.error(f"加载字幕 '{subtitle_path}' 失败: {e}")
    else:
        logger.warning("未提供字幕文件，跳过添加字幕。")

    # 保存草稿
    logger.info("正在保存草稿...")
    draft.save()
    logger.info(f"草稿 '{draft_name}' 保存成功！")


async def generate_video_from_text(
    text: str,
    videos_path: list | str,
    draft_name: str,
    audio_output_file: str = "generated_audio.mp3",
    vtt_output_file: str = "generated_subtitle.vtt",
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    video_ratio: str = "9:16",
    drafts_root: str = "",
    music_path: str = "",
):
    """
    流水线函数：从文本生成音频和字幕，然后创建视频草稿。

    参数:
    - text: 输入文本，用于生成音频和字幕
    - videos_path: 视频文件路径（单个字符串或列表）
    - draft_name: 草稿名称
    - audio_output_file: 生成的音频文件路径
    - vtt_output_file: 生成的字幕文件路径
    - voice: TTS 语音
    - rate: 语速
    - volume: 音量
    - pitch: 音调
    - video_ratio: 视频比例
    - drafts_root: 草稿保存根目录
    - music_path: 背景音乐路径（可选）
    """
    logger.info("开始流水线：从文本生成视频...")

    # 设置默认输出目录为项目 data/jianyin 目录
    project_root = os.getcwd()
    data_dir = os.path.join(project_root, "data", "jianyin")

    # 确保输出目录存在
    os.makedirs(data_dir, exist_ok=True)

    if audio_output_file == "generated_audio.mp3":
        audio_output_file = os.path.join(data_dir, "generated_audio.mp3")
    if vtt_output_file == "generated_subtitle.vtt":
        vtt_output_file = os.path.join(data_dir, "generated_subtitle.vtt")

    # 步骤1: 生成音频和字幕
    logger.info("步骤1: 生成音频和字幕...")
    tts_success = await generate_tts_optimized_split(
        text=text,
        voice=voice,
        audio_output_file=audio_output_file,
        vtt_output_file=vtt_output_file,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )

    if not tts_success:
        logger.error("TTS 生成失败，无法继续创建视频。")
        return False

    logger.info("步骤1 完成：音频和字幕生成成功。")

    # 步骤2: 创建视频
    logger.info("步骤2: 创建视频草稿...")
    try:
        create_video(
            draft_name=draft_name,
            videos_path=videos_path,
            subtitle_path=vtt_output_file,
            audio_path=audio_output_file,
            music_path=music_path,
            video_ratio=video_ratio,
            drafts_root=drafts_root,
        )
        logger.info("步骤2 完成：视频草稿创建成功。")
        return True
    except Exception as e:
        logger.error(f"视频创建失败: {e}")
        return False


# 使用方法
# from app.src.video_generate.generate import generate_video_from_text
# import asyncio

# asyncio.run(
#     generate_video_from_text(
#         text="Hello, world!",
#         videos_path="D:\\存档\\公司项目\\素材\\混剪\\无声\\1 (1)_silent.mov",
#         draft_name="test_draft",
#     )
# )

# 数据保存到data/jianyin目录下
