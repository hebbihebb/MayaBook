# core/pipeline.py
import queue
import threading
from .chunking import chunk_text
from .tts_maya1_local import synthesize_chunk_local
from .audio_combine import concat_wavs
from .video_export import export_mp4

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
    workers: int = 2,
    progress_cb=None,
    stop_flag=None,
):
    """
    Runs the full text-to-video pipeline.
    """
    chunks = chunk_text(epub_text, max_chars=chunk_size)
    q = queue.Queue()
    for i, t in enumerate(chunks):
        q.put((i, t))

    results = {}
    lock = threading.Lock()
    exceptions = []

    def worker():
        while True:
            if stop_flag and stop_flag.is_set():
                return

            try:
                i, t = q.get_nowait()
            except queue.Empty:
                return

            try:
                wav_path = synthesize_chunk_local(
                    model_path=model_path,
                    text=t,
                    voice_description=voice_desc,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=2048,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                )
                with lock:
                    results[i] = wav_path

                if progress_cb:
                    progress_cb(len(results), len(chunks))
            except Exception as e:
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

    if stop_flag and stop_flag.is_set():
        return None, None

    ordered_wavs = [results[i] for i in sorted(results.keys())]

    final_wav_path = concat_wavs(ordered_wavs, out_wav, gap_seconds=gap_s)
    final_mp4_path = export_mp4(cover_image, final_wav_path, out_mp4)

    return final_wav_path, final_mp4_path
