# core/pipeline.py
import queue
import threading
import logging
import sys
import os
import numpy as np
import soundfile as sf
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from .chunking import chunk_text
from .tts_maya1_local import synthesize_chunk_local
from .tts_maya1_hf import synthesize_chunk_hf
from .audio_combine import concat_wavs
from .video_export import export_mp4
from .m4b_export import create_m4b_stream, write_chapter_metadata_file, add_chapters_to_m4b
from .utils import sanitize_name_for_os, sanitize_chapter_name, find_unique_path

# Configure logging
log_filename = f"mayabook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_pipeline(
    epub_text: str,
    model_path: str,
    voice_desc: str,
    chunk_size: int,
    gap_s: float,
    out_wav: str,
    out_mp4: str,
    cover_image: str,
    temperature: float = 0.4,
    top_p: float = 0.9,
    n_ctx: int = 4096,
    n_gpu_layers: int = -1,
    workers: int = 1,
    max_tokens: int = 2500,
    model_type: str = "gguf",  # "gguf" or "huggingface"
    progress_cb=None,
    stop_flag=None,
):
    """
    Runs the full text-to-video pipeline.

    Args:
        model_type: "gguf" for llama.cpp GGUF models, "huggingface" for HF safetensor models
    """
    logger.info("="*60)
    logger.info("Starting MayaBook pipeline")
    logger.info(f"Model type: {model_type}")
    logger.info(f"Model path: {model_path}")
    logger.info(f"Voice description: {voice_desc}")
    logger.info(f"Chunk size: {chunk_size}")
    logger.info(f"Temperature: {temperature}, Top-p: {top_p}")
    logger.info(f"Max tokens: {max_tokens}")
    if model_type == "gguf":
        logger.info(f"Context size: {n_ctx}, GPU layers: {n_gpu_layers}")
    logger.info(f"Workers: {workers}")
    logger.info("="*60)

    try:
        # Use word-based chunking for better TTS quality
        # chunk_size parameter is interpreted as max_words when < 500, otherwise max_chars
        if chunk_size < 500:
            # Assume word count (recommended: 80-100 words per chunk)
            chunks = chunk_text(epub_text, max_words=chunk_size)
            logger.info(f"Text chunked into {len(chunks)} parts (max {chunk_size} words per chunk)")
        else:
            # Fallback to character-based chunking
            chunks = chunk_text(epub_text, max_chars=chunk_size)
            logger.info(f"Text chunked into {len(chunks)} parts (max {chunk_size} chars per chunk)")
    except Exception as e:
        logger.error(f"Error chunking text: {e}", exc_info=True)
        raise
    q = queue.Queue()
    for i, t in enumerate(chunks):
        q.put((i, t))

    results = {}
    lock = threading.Lock()
    exceptions = []

    def worker():
        while True:
            if stop_flag and stop_flag.is_set():
                logger.info("Worker stopping due to stop flag")
                return

            try:
                i, t = q.get_nowait()
            except queue.Empty:
                logger.debug("Worker finished - queue empty")
                return

            try:
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                logger.debug(f"Chunk {i} text preview: {t[:100]}...")

                # Use appropriate synthesis function based on model type
                if model_type == "huggingface":
                    wav_path = synthesize_chunk_hf(
                        model_path=model_path,
                        text=t,
                        voice_description=voice_desc,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                    )
                else:  # gguf
                    wav_path = synthesize_chunk_local(
                        model_path=model_path,
                        text=t,
                        voice_description=voice_desc,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        n_ctx=n_ctx,
                        n_gpu_layers=n_gpu_layers,
                    )

                logger.info(f"Chunk {i+1} synthesized successfully: {wav_path}")

                with lock:
                    results[i] = wav_path

                if progress_cb:
                    progress_cb(len(results), len(chunks))
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}", exc_info=True)
                with lock:
                    exceptions.append(e)
            finally:
                q.task_done()

    logger.info(f"Starting {workers} worker threads")
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
    for th in threads:
        th.start()

    logger.info("Waiting for all chunks to complete...")
    q.join()

    if exceptions:
        logger.error(f"Pipeline failed with {len(exceptions)} exception(s)")
        raise exceptions[0]

    if stop_flag and stop_flag.is_set():
        logger.info("Pipeline stopped by user")
        return None, None

    logger.info("All chunks processed successfully")
    ordered_wavs = [results[i] for i in sorted(results.keys())]

    logger.info(f"Concatenating {len(ordered_wavs)} audio files...")
    try:
        final_wav_path = concat_wavs(ordered_wavs, out_wav, gap_seconds=gap_s)
        logger.info(f"Final audio saved: {final_wav_path}")
    except Exception as e:
        logger.error(f"Error concatenating audio: {e}", exc_info=True)
        raise

    logger.info("Creating video from audio and cover image...")
    try:
        final_mp4_path = export_mp4(cover_image, final_wav_path, out_mp4)
        logger.info(f"Final video saved: {final_mp4_path}")
    except Exception as e:
        logger.error(f"Error creating video: {e}", exc_info=True)
        raise

    logger.info("="*60)
    logger.info("Pipeline completed successfully!")
    logger.info(f"Log file: {log_filename}")
    logger.info("="*60)

    return final_wav_path, final_mp4_path


def run_pipeline_with_chapters(
    chapters: List[Tuple[str, str]],
    metadata: Dict[str, str],
    model_path: str,
    voice_desc: str,
    chunk_size: int,
    gap_s: float,
    output_base_path: str,
    cover_image: str,
    output_format: str = "m4b",  # "wav", "mp4", "m4b"
    save_chapters_separately: bool = False,
    merge_chapters: bool = True,
    chapter_silence: float = 2.0,
    temperature: float = 0.45,
    top_p: float = 0.92,
    n_ctx: int = 4096,
    n_gpu_layers: int = -1,
    workers: int = 1,
    max_tokens: int = 2500,
    model_type: str = "gguf",
    progress_cb=None,
    stop_flag=None,
) -> Dict[str, any]:
    """
    Runs the full text-to-audio pipeline with chapter support.

    Args:
        chapters: List of (chapter_title, chapter_text) tuples
        metadata: Dictionary with title, author, year, genre, etc.
        model_path: Path to TTS model (GGUF or HuggingFace)
        voice_desc: Voice description text
        chunk_size: Max words per chunk (if < 500) or max chars
        gap_s: Silence gap between chunks (seconds)
        output_base_path: Base path for output (without extension)
        cover_image: Path to cover image (for MP4)
        output_format: Output format ("wav", "mp4", "m4b")
        save_chapters_separately: Save individual chapter files
        merge_chapters: Create merged output file
        chapter_silence: Silence between chapters (seconds)
        temperature: TTS temperature parameter
        top_p: TTS top-p parameter
        n_ctx: Context size (GGUF only)
        n_gpu_layers: GPU layers (GGUF only)
        workers: Number of worker threads
        max_tokens: Max tokens per generation
        model_type: "gguf" or "huggingface"
        progress_cb: Progress callback function(current, total, chapter_info)
        stop_flag: Threading event to stop processing

    Returns:
        Dictionary with:
            - 'merged_path': Path to merged output file
            - 'chapter_paths': List of individual chapter file paths
            - 'chapter_times': List of chapter timing dicts
            - 'metadata': Metadata dictionary used
    """
    logger.info("="*60)
    logger.info("Starting MayaBook pipeline (Chapter-Aware Mode)")
    logger.info(f"Chapters: {len(chapters)}")
    logger.info(f"Model type: {model_type}")
    logger.info(f"Output format: {output_format}")
    logger.info(f"Save chapters separately: {save_chapters_separately}")
    logger.info(f"Merge chapters: {merge_chapters}")
    logger.info(f"Chapter silence: {chapter_silence}s")
    logger.info("="*60)

    # Sanitize base name for output files
    base_name = os.path.basename(output_base_path)
    base_dir = os.path.dirname(output_base_path) or os.getcwd()
    sanitized_base_name = sanitize_name_for_os(base_name, is_folder=False)

    # Find unique paths for outputs
    avoid_exts = [".wav", ".mp4", ".m4b", ".m4a"]
    merged_path, suffix = find_unique_path(
        os.path.join(base_dir, sanitized_base_name),
        f".{output_format}",
        avoid_exts
    )

    # Prepare chapter output folder if needed
    chapters_out_dir = None
    chapter_paths = []
    if save_chapters_separately:
        chapters_out_dir = os.path.join(base_dir, f"{sanitized_base_name}{suffix}_chapters")
        os.makedirs(chapters_out_dir, exist_ok=True)
        logger.info(f"Chapter output folder: {chapters_out_dir}")

    # Initialize chapter timing tracking
    chapter_times = []
    current_time = 0.0
    sample_rate = 24000

    # Prepare merged output file/stream if needed
    merged_file = None
    ffmpeg_proc = None

    if merge_chapters:
        if output_format in ["wav", "mp3", "flac"]:
            # Soundfile-based incremental writing
            merged_file = sf.SoundFile(
                merged_path,
                "w",
                samplerate=sample_rate,
                channels=1,
                format=output_format.upper()
            )
            logger.info(f"Opened {output_format.upper()} file for writing: {merged_path}")
        elif output_format == "m4b":
            # FFmpeg streaming for M4B
            ffmpeg_proc = create_m4b_stream(merged_path, sample_rate, metadata)
            logger.info(f"Started M4B stream: {merged_path}")
        else:
            logger.warning(f"Unsupported output format: {output_format}, falling back to WAV")
            output_format = "wav"
            merged_path = merged_path.replace(f".{output_format}", ".wav")
            merged_file = sf.SoundFile(merged_path, "w", samplerate=sample_rate, channels=1, format="WAV")

    total_chunks = 0
    processed_chunks = 0

    try:
        # Process each chapter
        for chapter_idx, (chapter_title, chapter_text) in enumerate(chapters, 1):
            if stop_flag and stop_flag.is_set():
                logger.info("Pipeline stopped by user")
                break

            logger.info(f"\nProcessing Chapter {chapter_idx}/{len(chapters)}: {chapter_title}")

            # Track chapter start time
            chapter_start_time = current_time

            # Chunk the chapter text
            if chunk_size < 500:
                chapter_chunks = chunk_text(chapter_text, max_words=chunk_size)
                logger.info(f"  Chapter chunked into {len(chapter_chunks)} parts ({chunk_size} words max)")
            else:
                chapter_chunks = chunk_text(chapter_text, max_chars=chunk_size)
                logger.info(f"  Chapter chunked into {len(chapter_chunks)} parts ({chunk_size} chars max)")

            total_chunks += len(chapter_chunks)

            # Prepare chapter-specific output file if needed
            chapter_file = None
            chapter_path = None
            if save_chapters_separately:
                sanitized_title = sanitize_chapter_name(chapter_title)
                chapter_filename = f"{chapter_idx:02d}_{sanitized_title}.wav"
                chapter_path = os.path.join(chapters_out_dir, chapter_filename)
                chapter_file = sf.SoundFile(chapter_path, "w", samplerate=sample_rate, channels=1, format="WAV")
                logger.info(f"  Opened chapter file: {chapter_path}")

            # Process chapter chunks
            chunk_results = _process_chunks_parallel(
                chunks=chapter_chunks,
                model_path=model_path,
                voice_desc=voice_desc,
                model_type=model_type,
                temperature=temperature,
                top_p=top_p,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                max_tokens=max_tokens,
                workers=workers,
                stop_flag=stop_flag,
                progress_cb=lambda curr, total: progress_cb(
                    processed_chunks + curr,
                    total_chunks,
                    f"Chapter {chapter_idx}/{len(chapters)}: {chapter_title}"
                ) if progress_cb else None
            )

            if stop_flag and stop_flag.is_set():
                if chapter_file:
                    chapter_file.close()
                break

            # Write chapter audio incrementally
            for chunk_wav_path in chunk_results:
                # Read chunk audio
                audio, sr = sf.read(chunk_wav_path, dtype="float32", always_2d=False)
                chunk_duration = len(audio) / sr

                # Write to merged file
                if merge_chapters:
                    if merged_file:
                        merged_file.write(audio)
                    elif ffmpeg_proc:
                        audio_bytes = audio.astype("float32").tobytes()
                        ffmpeg_proc.stdin.write(audio_bytes)

                # Write to chapter file
                if chapter_file:
                    chapter_file.write(audio)

                # Add chunk gap
                if gap_s > 0:
                    silence = np.zeros(int(gap_s * sample_rate), dtype="float32")
                    if merge_chapters:
                        if merged_file:
                            merged_file.write(silence)
                        elif ffmpeg_proc:
                            ffmpeg_proc.stdin.write(silence.tobytes())
                    if chapter_file:
                        chapter_file.write(silence)

                    current_time += gap_s

                current_time += chunk_duration

            processed_chunks += len(chapter_chunks)

            # Close chapter file
            if chapter_file:
                chapter_file.close()
                chapter_paths.append(chapter_path)
                logger.info(f"  Chapter saved: {chapter_path}")

            # Track chapter timing
            chapter_times.append({
                "chapter": chapter_title,
                "start": chapter_start_time,
                "end": current_time
            })

            # Add silence between chapters (except after last)
            if chapter_idx < len(chapters) and merge_chapters:
                silence_samples = int(chapter_silence * sample_rate)
                silence = np.zeros(silence_samples, dtype="float32")

                if merged_file:
                    merged_file.write(silence)
                elif ffmpeg_proc:
                    ffmpeg_proc.stdin.write(silence.tobytes())

                current_time += chapter_silence
                logger.info(f"  Added {chapter_silence}s silence after chapter")

        # Finalize merged output
        if merge_chapters:
            logger.info("\nFinalizing merged output...")

            if merged_file:
                merged_file.close()
                logger.info(f"Merged {output_format.upper()} saved: {merged_path}")

            elif ffmpeg_proc:
                ffmpeg_proc.stdin.close()
                ffmpeg_proc.wait()
                logger.info(f"M4B stream finalized: {merged_path}")

                # Add chapters to M4B if multiple chapters
                if len(chapters) > 1:
                    logger.info("Adding chapter metadata to M4B...")
                    metadata_path = merged_path.replace(".m4b", "_chapters.txt")
                    write_chapter_metadata_file(chapter_times, metadata_path)
                    add_chapters_to_m4b(merged_path, metadata_path, metadata)
                    os.remove(metadata_path)
                    logger.info("Chapter metadata added successfully")

            # Create MP4 from WAV if requested
            if output_format == "mp4":
                wav_path = merged_path.replace(".mp4", ".wav")
                if os.path.exists(wav_path):
                    logger.info("Creating MP4 from WAV and cover image...")
                    export_mp4(cover_image, wav_path, merged_path)
                    logger.info(f"MP4 created: {merged_path}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        # Cleanup
        if merged_file:
            try:
                merged_file.close()
            except:
                pass
        if ffmpeg_proc:
            try:
                ffmpeg_proc.stdin.close()
                ffmpeg_proc.terminate()
            except:
                pass
        raise
    finally:
        # Ensure files are closed
        if merged_file and not merged_file.closed:
            merged_file.close()

    if stop_flag and stop_flag.is_set():
        logger.info("Pipeline stopped by user")
        return {
            "merged_path": None,
            "chapter_paths": chapter_paths,
            "chapter_times": chapter_times,
            "metadata": metadata,
        }

    logger.info("="*60)
    logger.info("Pipeline completed successfully!")
    logger.info(f"Merged output: {merged_path if merge_chapters else 'None'}")
    logger.info(f"Chapter files: {len(chapter_paths)}")
    logger.info(f"Log file: {log_filename}")
    logger.info("="*60)

    return {
        "merged_path": merged_path if merge_chapters else None,
        "chapter_paths": chapter_paths,
        "chapter_times": chapter_times,
        "metadata": metadata,
    }


def _process_chunks_parallel(
    chunks: List[str],
    model_path: str,
    voice_desc: str,
    model_type: str,
    temperature: float,
    top_p: float,
    n_ctx: int,
    n_gpu_layers: int,
    max_tokens: int,
    workers: int,
    stop_flag,
    progress_cb=None,
) -> List[str]:
    """
    Process chunks in parallel using worker threads.

    Returns:
        List of WAV file paths in order
    """
    q = queue.Queue()
    for i, text in enumerate(chunks):
        q.put((i, text))

    results = {}
    lock = threading.Lock()
    exceptions = []

    def worker():
        while True:
            if stop_flag and stop_flag.is_set():
                return

            try:
                i, text = q.get_nowait()
            except queue.Empty:
                return

            try:
                logger.debug(f"Processing chunk {i+1}/{len(chunks)}: {text[:50]}...")

                if model_type == "huggingface":
                    wav_path = synthesize_chunk_hf(
                        model_path=model_path,
                        text=text,
                        voice_description=voice_desc,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                    )
                else:  # gguf
                    wav_path = synthesize_chunk_local(
                        model_path=model_path,
                        text=text,
                        voice_description=voice_desc,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        n_ctx=n_ctx,
                        n_gpu_layers=n_gpu_layers,
                    )

                with lock:
                    results[i] = wav_path

                if progress_cb:
                    progress_cb(len(results), len(chunks))

            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}", exc_info=True)
                with lock:
                    exceptions.append(e)
            finally:
                q.task_done()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
    for th in threads:
        th.start()

    q.join()

    if exceptions:
        raise exceptions[0]

    return [results[i] for i in sorted(results.keys())]
