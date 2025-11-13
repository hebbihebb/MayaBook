# core/batch_processor.py
"""
Batch processing for multiple EPUB files
"""
import logging
import queue
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class BatchItemStatus(Enum):
    """Status of a batch item"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """A single item in a batch processing queue"""
    index: int
    epub_path: str
    cover_path: Optional[str] = None
    output_folder: Optional[str] = None
    custom_voice: Optional[str] = None  # If None, use default
    custom_settings: Optional[Dict] = None  # Override settings for this item

    status: BatchItemStatus = BatchItemStatus.PENDING
    error_message: Optional[str] = None
    output_files: Optional[Dict] = None  # {'wav': path, 'mp4': path, etc}
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def get_display_name(self) -> str:
        """Get display name for this item"""
        return Path(self.epub_path).stem

    def get_duration_string(self) -> str:
        """Get processing duration as string"""
        if self.start_time is None:
            return "Not started"
        if self.end_time is None:
            return "In progress..."

        duration = self.end_time - self.start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"


class BatchProcessor:
    """Manages batch processing of multiple EPUB files"""

    def __init__(self, process_function: Callable, default_settings: Dict):
        """
        Initialize batch processor

        Args:
            process_function: Function to process a single EPUB
                              Should accept (item: BatchItem, settings: Dict) -> Dict
            default_settings: Default settings for all items
        """
        self.process_function = process_function
        self.default_settings = default_settings
        self.items: List[BatchItem] = []
        self.current_item_index: Optional[int] = None
        self.is_running = False
        self.is_paused = False
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []

    def add_item(self, epub_path: str, cover_path: Optional[str] = None,
                 output_folder: Optional[str] = None, custom_voice: Optional[str] = None,
                 custom_settings: Optional[Dict] = None) -> int:
        """
        Add item to batch queue

        Returns:
            Index of added item
        """
        index = len(self.items)
        item = BatchItem(
            index=index,
            epub_path=epub_path,
            cover_path=cover_path,
            output_folder=output_folder,
            custom_voice=custom_voice,
            custom_settings=custom_settings
        )
        self.items.append(item)
        logger.info(f"Added batch item {index}: {item.get_display_name()}")
        self._notify_callbacks({'event': 'item_added', 'item': item})
        return index

    def remove_item(self, index: int):
        """Remove item from batch queue"""
        if 0 <= index < len(self.items):
            item = self.items[index]
            if item.status == BatchItemStatus.PROCESSING:
                logger.warning(f"Cannot remove item {index} - currently processing")
                return False

            self.items.pop(index)
            # Re-index remaining items
            for i, item in enumerate(self.items):
                item.index = i
            logger.info(f"Removed batch item {index}")
            self._notify_callbacks({'event': 'item_removed', 'index': index})
            return True
        return False

    def clear_completed(self):
        """Remove all completed or failed items"""
        self.items = [item for item in self.items
                      if item.status not in [BatchItemStatus.COMPLETED, BatchItemStatus.FAILED, BatchItemStatus.CANCELLED]]
        # Re-index
        for i, item in enumerate(self.items):
            item.index = i
        logger.info("Cleared completed items")
        self._notify_callbacks({'event': 'cleared_completed'})

    def get_item(self, index: int) -> Optional[BatchItem]:
        """Get item by index"""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def get_pending_count(self) -> int:
        """Get number of pending items"""
        return sum(1 for item in self.items if item.status == BatchItemStatus.PENDING)

    def get_completed_count(self) -> int:
        """Get number of completed items"""
        return sum(1 for item in self.items if item.status == BatchItemStatus.COMPLETED)

    def get_failed_count(self) -> int:
        """Get number of failed items"""
        return sum(1 for item in self.items if item.status == BatchItemStatus.FAILED)

    def add_callback(self, callback: Callable):
        """Add callback to be notified of batch events"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, event_data: Dict):
        """Notify all callbacks of an event"""
        for callback in self.callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in batch callback: {e}")

    def start(self):
        """Start batch processing"""
        if self.is_running:
            logger.warning("Batch processing already running")
            return False

        if not self.items:
            logger.warning("No items in batch queue")
            return False

        self.is_running = True
        self.stop_flag.clear()
        self.pause_flag.clear()

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        logger.info("Started batch processing")
        self._notify_callbacks({'event': 'batch_started', 'total_items': len(self.items)})
        return True

    def stop(self):
        """Stop batch processing"""
        if not self.is_running:
            return

        logger.info("Stopping batch processing...")
        self.stop_flag.set()
        self.is_running = False

        # Mark pending items as cancelled
        for item in self.items:
            if item.status == BatchItemStatus.PENDING:
                item.status = BatchItemStatus.CANCELLED

        self._notify_callbacks({'event': 'batch_stopped'})

    def pause(self):
        """Pause batch processing (after current item completes)"""
        if self.is_running and not self.is_paused:
            logger.info("Pausing batch processing...")
            self.pause_flag.set()
            self.is_paused = True
            self._notify_callbacks({'event': 'batch_paused'})

    def resume(self):
        """Resume batch processing"""
        if self.is_paused:
            logger.info("Resuming batch processing...")
            self.pause_flag.clear()
            self.is_paused = False
            self._notify_callbacks({'event': 'batch_resumed'})

    def _worker_loop(self):
        """Main worker loop for processing batch items"""
        try:
            for item in self.items:
                # Check stop flag
                if self.stop_flag.is_set():
                    logger.info("Batch processing stopped")
                    break

                # Check pause flag
                while self.pause_flag.is_set():
                    if self.stop_flag.is_set():
                        break
                    import time
                    time.sleep(0.5)

                # Skip non-pending items
                if item.status != BatchItemStatus.PENDING:
                    continue

                # Process item
                self.current_item_index = item.index
                self._process_item(item)

            # Batch complete
            self.is_running = False
            self.current_item_index = None

            summary = {
                'event': 'batch_completed',
                'total': len(self.items),
                'completed': self.get_completed_count(),
                'failed': self.get_failed_count(),
            }
            logger.info(f"Batch processing complete: {summary}")
            self._notify_callbacks(summary)

        except Exception as e:
            logger.error(f"Error in batch worker loop: {e}", exc_info=True)
            self.is_running = False
            self._notify_callbacks({'event': 'batch_error', 'error': str(e)})

    def _process_item(self, item: BatchItem):
        """Process a single batch item"""
        import time

        item.status = BatchItemStatus.PROCESSING
        item.start_time = time.time()

        logger.info(f"Processing batch item {item.index + 1}/{len(self.items)}: {item.get_display_name()}")
        self._notify_callbacks({'event': 'item_started', 'item': item})

        try:
            # Merge settings
            settings = self.default_settings.copy()
            if item.custom_settings:
                settings.update(item.custom_settings)

            # Override voice if custom voice specified
            if item.custom_voice:
                settings['voice_description'] = item.custom_voice

            # Override paths
            settings['epub_path'] = item.epub_path
            if item.cover_path:
                settings['cover_path'] = item.cover_path
            if item.output_folder:
                settings['output_folder'] = item.output_folder

            # Call processing function
            result = self.process_function(item, settings, self.stop_flag)

            item.status = BatchItemStatus.COMPLETED
            item.output_files = result
            item.end_time = time.time()

            logger.info(f"Item {item.index} completed in {item.get_duration_string()}")
            self._notify_callbacks({'event': 'item_completed', 'item': item})

        except Exception as e:
            item.status = BatchItemStatus.FAILED
            item.error_message = str(e)
            item.end_time = time.time()

            logger.error(f"Item {item.index} failed: {e}", exc_info=True)
            self._notify_callbacks({'event': 'item_failed', 'item': item, 'error': str(e)})

    def get_summary(self) -> Dict:
        """Get batch processing summary"""
        return {
            'total_items': len(self.items),
            'pending': self.get_pending_count(),
            'completed': self.get_completed_count(),
            'failed': self.get_failed_count(),
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_item': self.current_item_index,
        }

    def export_results(self, export_path: str):
        """Export batch results to JSON file"""
        import json
        from datetime import datetime

        results = {
            'exported_at': datetime.now().isoformat(),
            'total_items': len(self.items),
            'completed': self.get_completed_count(),
            'failed': self.get_failed_count(),
            'items': []
        }

        for item in self.items:
            item_data = {
                'index': item.index,
                'epub_name': Path(item.epub_path).name,
                'status': item.status.value,
                'duration': item.get_duration_string(),
                'error': item.error_message,
                'output_files': item.output_files,
            }
            results['items'].append(item_data)

        with open(export_path, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Batch results exported to {export_path}")
