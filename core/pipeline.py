# core/pipeline.py
import queue
import threading
import logging
import sys
import os
from datetime import datetime
from .chunking import chunk_text
from .tts_maya1_local import synthesize_chunk_local
from .tts_maya1_hf import synthesize_chunk_hf
from .audio_combine import concat_wavs
from .video_export import export_mp4

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
