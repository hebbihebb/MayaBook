# core/progress_tracker.py
"""
Enhanced progress tracking with ETA, speed metrics, and detailed status
"""
import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ChunkProgress:
    """Progress information for a single chunk"""
    index: int
    text_preview: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    audio_path: Optional[str] = None
    char_count: int = 0
    word_count: int = 0


@dataclass
class ProgressStats:
    """Statistics for overall progress"""
    total_chunks: int
    completed_chunks: int = 0
    failed_chunks: int = 0
    total_chars: int = 0
    processed_chars: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)

    # Performance metrics
    chunks_per_second: float = 0.0
    chars_per_second: float = 0.0
    avg_chunk_time: float = 0.0
    eta_seconds: float = 0.0

    # Current chunk info
    current_chunk_index: Optional[int] = None
    current_chunk_text: str = ""

    def update(self, chunk: ChunkProgress):
        """Update stats with completed chunk"""
        if chunk.success:
            self.completed_chunks += 1
            self.processed_chars += chunk.char_count
        else:
            self.failed_chunks += 1

        self.last_update_time = time.time()
        self._recalculate_metrics()

    def _recalculate_metrics(self):
        """Recalculate performance metrics"""
        elapsed = self.last_update_time - self.start_time

        if elapsed > 0 and self.completed_chunks > 0:
            self.chunks_per_second = self.completed_chunks / elapsed
            self.chars_per_second = self.processed_chars / elapsed
            self.avg_chunk_time = elapsed / self.completed_chunks

            # Calculate ETA
            remaining_chunks = self.total_chunks - self.completed_chunks - self.failed_chunks
            if self.chunks_per_second > 0:
                self.eta_seconds = remaining_chunks / self.chunks_per_second
            else:
                self.eta_seconds = 0

    def get_progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100

    def get_eta_string(self) -> str:
        """Get ETA as human-readable string"""
        if self.eta_seconds <= 0:
            return "Calculating..."

        eta = timedelta(seconds=int(self.eta_seconds))

        # Format based on duration
        hours = eta.seconds // 3600
        minutes = (eta.seconds % 3600) // 60
        seconds = eta.seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_elapsed_string(self) -> str:
        """Get elapsed time as human-readable string"""
        elapsed = time.time() - self.start_time
        elapsed_delta = timedelta(seconds=int(elapsed))

        hours = elapsed_delta.seconds // 3600
        minutes = (elapsed_delta.seconds % 3600) // 60
        seconds = elapsed_delta.seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_speed_string(self) -> str:
        """Get synthesis speed as human-readable string"""
        if self.completed_chunks == 0:
            return "N/A"

        if self.chunks_per_second >= 1:
            return f"{self.chunks_per_second:.1f} chunks/sec"
        elif self.chunks_per_second > 0:
            chunks_per_min = self.chunks_per_second * 60
            return f"{chunks_per_min:.1f} chunks/min"
        else:
            return "N/A"

    def get_summary_dict(self) -> Dict:
        """Get summary as dictionary for display"""
        return {
            'progress_pct': self.get_progress_percentage(),
            'completed': self.completed_chunks,
            'failed': self.failed_chunks,
            'total': self.total_chunks,
            'eta': self.get_eta_string(),
            'elapsed': self.get_elapsed_string(),
            'speed': self.get_speed_string(),
            'chars_per_sec': f"{self.chars_per_second:.0f}" if self.chars_per_second > 0 else "N/A",
            'avg_chunk_time': f"{self.avg_chunk_time:.1f}s" if self.avg_chunk_time > 0 else "N/A",
            'current_chunk': self.current_chunk_index,
            'current_text': self.current_chunk_text[:100] + "..." if len(self.current_chunk_text) > 100 else self.current_chunk_text,
        }


class ProgressTracker:
    """Manages progress tracking for TTS synthesis"""

    def __init__(self, total_chunks: int, total_chars: int = 0):
        self.stats = ProgressStats(
            total_chunks=total_chunks,
            total_chars=total_chars
        )
        self.chunks: List[ChunkProgress] = []
        self.callbacks: List[callable] = []

    def add_callback(self, callback: callable):
        """Add callback to be called on progress updates"""
        self.callbacks.append(callback)

    def start_chunk(self, index: int, text: str):
        """Mark chunk as started"""
        chunk = ChunkProgress(
            index=index,
            text_preview=text[:100] + "..." if len(text) > 100 else text,
            start_time=time.time(),
            char_count=len(text),
            word_count=len(text.split())
        )
        self.chunks.append(chunk)

        self.stats.current_chunk_index = index
        self.stats.current_chunk_text = text

        self._notify_callbacks()
        logger.debug(f"Started chunk {index+1}/{self.stats.total_chunks}")

    def complete_chunk(self, index: int, audio_path: str, success: bool = True, error: Optional[str] = None):
        """Mark chunk as completed"""
        # Find chunk
        chunk = next((c for c in self.chunks if c.index == index), None)
        if chunk:
            chunk.end_time = time.time()
            chunk.success = success
            chunk.error = error
            chunk.audio_path = audio_path

            self.stats.update(chunk)
            self._notify_callbacks()

            if success:
                duration = chunk.end_time - chunk.start_time
                logger.info(
                    f"Completed chunk {index+1}/{self.stats.total_chunks} "
                    f"in {duration:.1f}s ({chunk.word_count} words)"
                )
            else:
                logger.error(f"Chunk {index+1} failed: {error}")

    def _notify_callbacks(self):
        """Notify all registered callbacks"""
        summary = self.stats.get_summary_dict()
        for callback in self.callbacks:
            try:
                callback(summary)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def get_stats(self) -> ProgressStats:
        """Get current statistics"""
        return self.stats

    def get_failed_chunks(self) -> List[ChunkProgress]:
        """Get list of failed chunks"""
        return [c for c in self.chunks if not c.success and c.end_time is not None]

    def is_complete(self) -> bool:
        """Check if all chunks are processed"""
        return (self.stats.completed_chunks + self.stats.failed_chunks) >= self.stats.total_chunks

    def get_completion_summary(self) -> str:
        """Get human-readable completion summary"""
        total_time = self.stats.get_elapsed_string()
        success_rate = (self.stats.completed_chunks / self.stats.total_chunks * 100) if self.stats.total_chunks > 0 else 0

        summary = (
            f"Synthesis complete!\n"
            f"  Processed: {self.stats.completed_chunks}/{self.stats.total_chunks} chunks ({success_rate:.1f}% success)\n"
            f"  Failed: {self.stats.failed_chunks} chunks\n"
            f"  Total time: {total_time}\n"
            f"  Average speed: {self.stats.get_speed_string()}\n"
            f"  Characters processed: {self.stats.processed_chars:,}"
        )

        if self.stats.failed_chunks > 0:
            summary += f"\n\n⚠️ Warning: {self.stats.failed_chunks} chunks failed"

        return summary


def format_progress_message(stats_dict: Dict) -> str:
    """
    Format progress statistics as a display message

    Args:
        stats_dict: Dictionary from ProgressStats.get_summary_dict()

    Returns:
        Formatted string for display
    """
    lines = [
        f"Progress: {stats_dict['completed']}/{stats_dict['total']} chunks ({stats_dict['progress_pct']:.1f}%)",
        f"Speed: {stats_dict['speed']} | Avg: {stats_dict['avg_chunk_time']}/chunk",
        f"Elapsed: {stats_dict['elapsed']} | ETA: {stats_dict['eta']}",
    ]

    if stats_dict['current_chunk'] is not None:
        lines.append(f"Current: Chunk {stats_dict['current_chunk']+1}")
        if stats_dict['current_text']:
            lines.append(f"  \"{stats_dict['current_text']}\"")

    if stats_dict['failed'] > 0:
        lines.append(f"⚠️ Failed: {stats_dict['failed']} chunks")

    return "\n".join(lines)
