import tempfile
import os
import uuid
import asyncio
import shutil
import concurrent.futures
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

import ffmpeg
from itertools import chain
from scipy.ndimage import gaussian_filter
from faster_whisper import WhisperModel
from moviepy.editor import TextClip, CompositeVideoClip, VideoFileClip

from app.models import JobCreation, JobInformation, JobStatus, SubtitleOptions
from app.services.database import create_job_db, get_job_status_db, get_job_download_URL_db, update_job_status_db, update_job_completed_db, update_job_failed_db

from app.core.settings import TEMP_DIR, SUBTITLE_DIR

class Status(Enum):
    """Enumeration for job status codes."""
    NotStarted = 1
    Processing = 2
    Completed = 3
    Failed = 4

class Position(Enum):
    """Enumeration for subtitle position options."""
    bottom = 1
    center = 2
    top = 3


@dataclass
class WordInfo:
    """Stores information about a single word from transcription."""
    start: float
    end: float
    word: str

@dataclass
class LineInfo:
    """Stores information about a single subtitle line."""
    start: float
    end: float
    duration: float
    line: str

class VideoCaption:

    def __init__(self, job_id: str, input_file_path: str, output_file_path: str, subtitle_options: SubtitleOptions):
        """
        Initialize the VideoCaption processor.

        Args:
            job_id (str): Unique job identifier.
            input_file_path (str): Path to the input video file.
            output_file_path (str): Path to save the output video file.
            subtitle_options (SubtitleOptions): Subtitle styling options.
        """
        self.job_id = job_id
        self.input_file_path = str(input_file_path)
        self.output_file_path = str(output_file_path)
        self.subtitle_options = subtitle_options        

    #WIP Keep converting old code to api call
    async def generate_subtitles(self):
        """
        Main pipeline to generate subtitles and render the output video.
        Steps:
            1. Extract audio from video.
            2. Transcribe audio to words.
            3. Combine words into subtitle lines.
            4. Render video with subtitles.
        """
        audio_filename = await self._convert_video_to_mp3(self.input_file_path)

        if not audio_filename:
            raise ValueError(f"Failed to convert video to audio: {self.input_file_path}")

        update_job_status_db(self.job_id, Status.Processing.value, 25)

        raw_output = await self._set_raw_output(audio_filename)
        update_job_status_db(self.job_id, Status.Processing.value, 50)

        modified_output = await self._combine_words(
            raw_output, 
            self.subtitle_options.max_chars, 
            self.subtitle_options.max_duration, 
            self.subtitle_options.max_gap
        )
        
        update_job_status_db(self.job_id, Status.Processing.value, 65)

        video_clip = VideoFileClip(self.input_file_path)
        video_size = video_clip.size

        layers = self._create_caption(modified_output, video_size, self.subtitle_options)
        all_clips = list(chain.from_iterable(layers))

        await self._render_output_video(video_clip, all_clips)        

        if os.path.exists(audio_filename):
            os.remove(audio_filename)

        pass

    async def _convert_video_to_mp3(self, video_file: str) -> str:
        """
        Extracts audio from a video file (any format: MP4, AVI, MOV, MKV, etc.) and saves it as MP3.

        Args:
            video_file (str): Path to the input video file.

        Returns:
            str: Path to the generated MP3 file, or None if failed.
        """
        audio_file_path = str(TEMP_DIR / (Path(video_file).stem + ".mp3"))
        
        if not os.path.exists(video_file):
            print(f"Error: '{video_file}' not found")
            return None

        try:
            # Run ffmpeg in thread pool to extract audio
            loop = asyncio.get_event_loop()
            with concurrent.futures.ProcessPoolExecutor() as executor:
                await loop.run_in_executor(
                    executor,
                    self._run_ffmpeg_conversion,
                    video_file,
                    audio_file_path
                )
           
            print(f"MP3 file generated: {audio_file_path}")
            return str(audio_file_path)
        except ffmpeg.Error as e:
            print(f"ffmpeg error: {e}")
            return None
        
    def _run_ffmpeg_conversion(self, mp4_file: str, audio_file_path: str):
        """
        Synchronous ffmpeg conversion to extract audio from video.

        Args:
            mp4_file (str): Path to the input video file.
            audio_file_path (str): Path to save the extracted audio.
        """
        video_stream = ffmpeg.input(mp4_file)
        audio = video_stream.audio
        audio_stream = ffmpeg.output(audio, audio_file_path, acodec='mp3')
        audio_stream = ffmpeg.overwrite_output(audio_stream)
        ffmpeg.run(audio_stream, quiet=True)

        
    async def _set_raw_output(self, audio_filename: str, model_size: str = 'medium') -> List[WordInfo]: 
        """
        Transcribes audio to word-level timestamps using Whisper.

        Args:
            audio_filename (str): Path to the audio file.
            model_size (str): Whisper model size.

        Returns:
            List[WordInfo]: List of word-level transcription results.
        """       
        loop = asyncio.get_event_loop()
        with concurrent.futures.ProcessPoolExecutor() as executor:
            word_info = await loop.run_in_executor(
                executor,
                self._run_whisper_transcription,
                audio_filename,
                model_size
            )
        return word_info
    
    def _run_whisper_transcription(self, audio_filename: str, model_size: str) -> List[WordInfo]:
        """
        Synchronous Whisper transcription to run in a process pool.

        Args:
            audio_filename (str): Path to the audio file.
            model_size (str): Whisper model size.

        Returns:
            List[WordInfo]: List of word-level transcription results.
        """
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(audio_filename, word_timestamps=True)

        word_info: List[WordInfo] = []
        
        for segment in segments:
            for word in segment.words:
                word_info.append(WordInfo(
                    start=float(word.start), 
                    end=float(word.end), 
                    word=word.word
                ))                

        return word_info
    
    async def _combine_words(self, data: List[WordInfo], max_chars: int = 30, max_duration: float = 2.5, max_gap: float = 1.5) -> List[LineInfo]:
        """
        Combines words into subtitle lines based on constraints.

        Args:
            data (List[WordInfo]): List of word-level transcription results.
            max_chars (int): Maximum characters per subtitle line.
            max_duration (float): Maximum duration per subtitle line.
            max_gap (float): Maximum allowed gap between words in a line.

        Returns:
            List[LineInfo]: List of subtitle lines.
        """
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            line_info = await loop.run_in_executor(
                executor,
                self._run_combine_words,
                data,
                max_chars,
                max_duration,
                max_gap
            )

        return line_info

    def _run_combine_words(
            self, 
            data: List[WordInfo], 
            max_chars: int, 
            max_duration: float, 
            max_gap: float
        ) -> List[LineInfo]:
        """
        Synchronous logic to combine words into subtitle lines.

        Args:
            data (List[WordInfo]): List of word-level transcription results.
            max_chars (int): Maximum characters per subtitle line.
            max_duration (float): Maximum duration per subtitle line.
            max_gap (float): Maximum allowed gap between words in a line.

        Returns:
            List[LineInfo]: List of subtitle lines.
        """
        subtitle_lines: List[LineInfo] =  []
        current_line: LineInfo = LineInfo(
            start=None, 
            end=None, 
            duration=0.0, 
            line=""
        )

        for i, word_data in enumerate(data):         
            word_text = word_data.word    
            word_start = word_data.start
            word_end = word_data.end
            word_duration = word_end - word_start

            #calculate gap from previous word
            gap = 0
            if i > 0:
                gap = word_start - data[i - 1].end

            #Checking if any constraints have been hit
            max_time_hit = (current_line.duration + word_duration) > max_duration
            max_chars_hit = (len(current_line.line) + len(word_text)) >= max_chars
            max_gap_hit = gap > max_gap
                
            if current_line.line and (max_time_hit or max_chars_hit or max_gap_hit):            
                current_line.line = current_line.line.strip()
                subtitle_lines.append(current_line)                
                
                current_line: LineInfo = LineInfo(
                    start=None, 
                    end=None, 
                    duration=0.0, 
                    line=""
                )               
            
            #Start time for the new line if needed
            if current_line.start is None:
                current_line.start = word_start

            current_line.line += word_text
            current_line.end = word_end
            current_line.duration += word_duration

        #Add any remaining text as the last subtitle line
        if current_line.line:
            current_line.line = current_line.line.strip()
            subtitle_lines.append(current_line)            

        return subtitle_lines
    
    def _blur(self, clip: TextClip, sigma: int):
        """
        Applies a Gaussian blur to a TextClip (used for shadow effect).

        Args:
            clip (TextClip): The text clip to blur.
            sigma (int): Blur intensity.

        Returns:
            TextClip: Blurred text clip.
        """
        return clip.fl_image(lambda image: gaussian_filter(image, sigma=sigma), apply_to=['mask'])

    def _add_shadow_caption(
            self, 
            text: str, 
            font: str, 
            font_size: int, 
            start: float, 
            duration: float, 
            position: Tuple[Any, Any], 
            sigma: int, 
            offset: Tuple[int, int]=(2,2)
        ) -> TextClip:
        """
        Creates a shadow effect for subtitles.

        Args:
            text (str): Subtitle text.
            font (str): Font name.
            font_size (int): Font size.
            start (float): Start time.
            duration (float): Duration.
            position (Tuple): Position on video.
            sigma (int): Blur intensity.
            offset (Tuple): Offset for shadow.

        Returns:
            TextClip: Shadow text clip.
        """
        shadow_clip = TextClip(
            text,
            font=font,
            fontsize=font_size,
            color='black'
        ).set_start(start).set_duration(duration)

        shadow_pos = ('center' if position[0] == 'center' else position[0] + offset[1], position[1] + offset[1])

        shadow_clip = shadow_clip.set_position(shadow_pos)
        shadow_clip = self._blur(shadow_clip, sigma=sigma)
        return shadow_clip

    def _get_position(self, video_height: int, position: Position) -> Tuple[str, float]:    
        """
        Maps a Position enum to actual coordinates on the video.

        Args:
            video_height (int): Height of the video.
            position (Position): Subtitle position enum.

        Returns:
            Tuple[str, float]: Position for MoviePy.
        """    
        match position:
            case Position.bottom:
                return ('center', video_height * 3/4 )
            case Position.center:
                return ('center', video_height * 1/2 )
            case Position.top:
                return ('center', video_height * 1/10 )         

    def _create_caption_clip(
            self,
            caption_line_data: LineInfo, 
            video_size: List[int], 
            font: str, 
            font_size: int, 
            font_color: str, 
            stroke_color: str, 
            stroke_width: int, 
            caption_position: str, 
            shadow: bool
        ) -> List[TextClip]:
        """
        Creates MoviePy TextClip(s) for a single subtitle line.

        Args:
            caption_line_data (LineInfo): Subtitle line info.
            video_size (List[int]): [width, height] of video.
            font (str): Font name.
            font_size (int): Font size.
            font_color (str): Font color.
            stroke_color (str): Stroke color.
            stroke_width (int): Stroke width.
            caption_position (str): Position for the caption.
            shadow (bool): Whether to add shadow.

        Returns:
            List[TextClip]: List of TextClip layers (shadow, main).
        """        
        layers = []

        video_width, video_height = video_size[0], video_size[1]

        if caption_position is None:
            caption_position = ('center', video_height * 3/4)     

        full_duration = caption_line_data.end - caption_line_data.start

        caption_clip = TextClip(
            caption_line_data.line,
            font=font,
            fontsize=font_size,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            color=font_color
        ).set_start(caption_line_data.start).set_duration(full_duration)

        caption_clip = caption_clip.set_position(caption_position)

        if shadow:
            shadow_clip = self._add_shadow_caption(
                text=caption_line_data.line,
                font=font,
                font_size=font_size,
                start=caption_line_data.start,
                duration=full_duration,
                position=caption_position,
                sigma=5,            
                offset=(3,3)
            )
            layers.append(shadow_clip)     

        layers.append(caption_clip)
        return layers
    
    def _create_caption(
            self, 
            caption_data: List[LineInfo], 
            frame_size: List[int], 
            subtitle_data: SubtitleOptions
        ) -> List[List[TextClip]]:
        """
        Creates all subtitle TextClips for the video.

        Args:
            caption_data (List[LineInfo]): List of subtitle lines.
            frame_size (List[int]): [width, height] of video.
            subtitle_data (SubtitleOptions): Subtitle styling options.

        Returns:
            List[List[TextClip]]: Nested list of TextClips for each line.
        """
        final_caption_clips: List[List[TextClip]] = []   

        caption_position = self._get_position(frame_size[1], Position(subtitle_data.position_id))

        for caption in caption_data:
            caption_clip = self._create_caption_clip(
                caption_line_data=caption,
                video_size=frame_size,
                font=subtitle_data.font,
                font_size=subtitle_data.font_size,
                font_color=subtitle_data.font_color,
                stroke_color=subtitle_data.stroke_color,
                stroke_width=subtitle_data.stroke_width,
                caption_position=caption_position,
                shadow=subtitle_data.shadow
            )

            for i in range(len(caption_clip)):
                if i >= len(final_caption_clips):
                    final_caption_clips.append([caption_clip[i]])
                    continue

                final_caption_clips[i].append(caption_clip[i])        
        return final_caption_clips
    
    async def _render_output_video(self, video_clip: VideoFileClip, text_clips: List[TextClip]):
        """
        Renders the final video with all subtitle layers.

        Args:
            video_clip (VideoFileClip): The original video clip.
            text_clips (List[TextClip]): List of subtitle TextClips.
        """
        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(
                executor,
                self._run_render_output_video,
                video_clip,
                text_clips
        )

    def _run_render_output_video(self, video_clip: VideoFileClip, text_clips: List[TextClip]):
        """
        Synchronous rendering of the final video with subtitles.

        Args:
            video_clip (VideoFileClip): The original video clip.
            text_clips (List[TextClip]): List of subtitle TextClips.
        """
        final_video_clip = CompositeVideoClip([video_clip] + text_clips)
        final_video_clip.write_videofile(self.output_file_path)        

    
async def process_video_with_subtitles(
    job_id: str,
    input_path: str, 
    output_path: str, 
    subtitle_options: SubtitleOptions
) -> bool:
    """
    Orchestrates the video processing pipeline for a job.

    Args:
        job_id (str): Unique job identifier.
        input_path (str): Path to input video.
        output_path (str): Path to output video.
        subtitle_options (SubtitleOptions): Subtitle styling options.

    Returns:
        bool: True if processing succeeded, False otherwise.
    """
    videoCaption = VideoCaption(job_id, input_path, output_path, subtitle_options)
    await videoCaption.generate_subtitles()

    return True


async def background_video_processing(
    job_id: str,
    input_path: str,
    output_path: str,
    subtitle_options: SubtitleOptions
):
    """
    Background task for processing video with subtitles.
    Updates job status in the database.

    Args:
        job_id (str): Unique job identifier.
        input_path (str): Path to input video.
        output_path (str): Path to output video.
        subtitle_options (SubtitleOptions): Subtitle styling options.
    """
    try:
        update_job_status_db(job_id, status_id=Status.NotStarted.value, progress=10)

        success = await process_video_with_subtitles(job_id, input_path, output_path, subtitle_options)

        if success:
            update_job_completed_db(job_id)            
        else:
            update_job_failed_db(job_id, "Error: Unable to process video")

    except Exception as e:
        update_job_failed_db(job_id, f"Error: {str(e)}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


def create_job(video_filename: str, subtitle_options: SubtitleOptions) -> Dict[str, Any]:
    """
    Create a new job entry in the database.

    Args:
        video_filename (str): Name of the uploaded video file.
        subtitle_options (SubtitleOptions): Subtitle styling options.

    Returns:
        Dict[str, Any]: Job metadata including job ID and file paths.
    """
    job_id = str(uuid.uuid4())
    
    input_filename = f"{job_id}_input{Path(video_filename).suffix}"
    output_filename = f"{job_id}_output.mp4"

    input_path = str(TEMP_DIR / input_filename)
    output_path = str(TEMP_DIR / output_filename)

    job_data = JobCreation(
        job_id=job_id,
        status_id=1,
        progress=0,
        created_at=datetime.now(),
        input_path=input_path,
        output_path=output_path,
        original_filename=video_filename
    )
    
    create_job_db(job_data, subtitle_options)
    return { 
            "Job_Id": job_data.job_id, 
            "Input_Path": input_path, 
            "Output_Path": output_path
    }


def pull_job_status(job_id: str) -> JobStatus:
    """
    Get job status data by job_id.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        JobStatus: Job status information.
    """
    return get_job_status_db(job_id)

def pull_job_download_url(job_id: str) -> JobInformation:
    """
    Get job download information by job_id.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        JobInformation: Download information for the job.
    """
    return get_job_download_URL_db(job_id)


def cleanup_temp_files():
    """
    Clean up temporary files in the TEMP_DIR.
    """
    for file_path in TEMP_DIR.glob("*"):
        if file_path.is_file():
            try:
                os.remove(file_path)
            except:
                pass
