"""
Metrics collection module for Pi Home Dashboard.
Collects performance metrics and saves them for netdata monitoring.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class MetricsCollector:
    """Collects and stores performance metrics for the dashboard."""
    
    def __init__(self, cache_dir: Path):
        """Initialize the metrics collector."""
        self.cache_dir = cache_dir
        self.metrics_file = cache_dir / 'metrics.json'
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize metrics data structure
        self.metrics = self._load_metrics()
        
        # Performance tracking lists (keep last 100 entries)
        self.max_history = 100
        
    def _load_metrics(self) -> Dict:
        """Load existing metrics from file."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Return default metrics structure
        return {
            'render_times': [],
            'display_update_times': [],
            'persistent_browser_times': [],
            'standard_render_times': [],
            'full_refresh_times': [],
            'partial_refresh_times': [],
            'update_timestamps': [],
            'total_attempts': 0,
            'successful_attempts': 0,
            'render_attempts': 0,
            'render_successes': 0,
            'display_attempts': 0,
            'display_successes': 0,
            'partial_refresh_count': 0,
            'full_refresh_count': 0,
            'update_interval': 60,
            'last_updated': time.time()
        }
    
    def _save_metrics(self):
        """Save metrics to file."""
        try:
            self.metrics['last_updated'] = time.time()
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save metrics: {e}")
    
    def _trim_list(self, data_list: List) -> List:
        """Trim list to maximum history size."""
        if len(data_list) > self.max_history:
            return data_list[-self.max_history:]
        return data_list
    
    def record_render_time(self, render_time_ms: float, render_type: str = 'standard'):
        """Record a dashboard render time."""
        self.metrics['render_times'].append(render_time_ms)
        self.metrics['render_times'] = self._trim_list(self.metrics['render_times'])
        
        # Track by render type
        if render_type == 'persistent_browser':
            self.metrics['persistent_browser_times'].append(render_time_ms)
            self.metrics['persistent_browser_times'] = self._trim_list(
                self.metrics['persistent_browser_times']
            )
        else:
            self.metrics['standard_render_times'].append(render_time_ms)
            self.metrics['standard_render_times'] = self._trim_list(
                self.metrics['standard_render_times']
            )
        
        self.metrics['render_attempts'] += 1
        self._save_metrics()
    
    def record_render_success(self):
        """Record a successful render."""
        self.metrics['render_successes'] += 1
        self._save_metrics()
    
    def record_display_update_time(self, update_time_ms: float, refresh_type: str = 'partial'):
        """Record a display update time."""
        self.metrics['display_update_times'].append(update_time_ms)
        self.metrics['display_update_times'] = self._trim_list(
            self.metrics['display_update_times']
        )
        
        # Track by refresh type
        if refresh_type == 'full':
            self.metrics['full_refresh_times'].append(update_time_ms)
            self.metrics['full_refresh_times'] = self._trim_list(
                self.metrics['full_refresh_times']
            )
            self.metrics['full_refresh_count'] += 1
        else:
            self.metrics['partial_refresh_times'].append(update_time_ms)
            self.metrics['partial_refresh_times'] = self._trim_list(
                self.metrics['partial_refresh_times']
            )
            self.metrics['partial_refresh_count'] += 1
        
        self.metrics['display_attempts'] += 1
        self._save_metrics()
    
    def record_display_success(self):
        """Record a successful display update."""
        self.metrics['display_successes'] += 1
        self._save_metrics()
    
    def record_update_attempt(self):
        """Record a dashboard update attempt."""
        self.metrics['total_attempts'] += 1
        self.metrics['update_timestamps'].append(time.time())
        self.metrics['update_timestamps'] = self._trim_list(
            self.metrics['update_timestamps']
        )
        self._save_metrics()
    
    def record_update_success(self):
        """Record a successful dashboard update."""
        self.metrics['successful_attempts'] += 1
        self._save_metrics()
    
    def set_update_interval(self, interval_seconds: int):
        """Set the expected update interval."""
        self.metrics['update_interval'] = interval_seconds
        self._save_metrics()
    
    def get_average_render_time(self) -> float:
        """Get average render time."""
        render_times = self.metrics.get('render_times', [])
        if render_times:
            return sum(render_times) / len(render_times)
        return 0.0
    
    def get_average_display_time(self) -> float:
        """Get average display update time."""
        display_times = self.metrics.get('display_update_times', [])
        if display_times:
            return sum(display_times) / len(display_times)
        return 0.0
    
    def get_success_rate(self) -> float:
        """Get overall success rate as percentage."""
        total = self.metrics.get('total_attempts', 0)
        successful = self.metrics.get('successful_attempts', 0)
        if total > 0:
            return (successful / total) * 100
        return 100.0
    
    def get_persistent_browser_avg(self) -> float:
        """Get average persistent browser render time."""
        times = self.metrics.get('persistent_browser_times', [])
        if times:
            return sum(times) / len(times)
        return 0.0
    
    def get_standard_render_avg(self) -> float:
        """Get average standard render time."""
        times = self.metrics.get('standard_render_times', [])
        if times:
            return sum(times) / len(times)
        return 0.0
    
    def get_refresh_ratio(self) -> float:
        """Get partial to full refresh ratio."""
        partial = self.metrics.get('partial_refresh_count', 0)
        full = self.metrics.get('full_refresh_count', 0)
        if full > 0:
            return partial / full
        return 0.0
    
    def get_metrics_summary(self) -> Dict:
        """Get a summary of current metrics."""
        return {
            'avg_render_time': self.get_average_render_time(),
            'avg_display_time': self.get_average_display_time(),
            'success_rate': self.get_success_rate(),
            'persistent_browser_avg': self.get_persistent_browser_avg(),
            'standard_render_avg': self.get_standard_render_avg(),
            'refresh_ratio': self.get_refresh_ratio(),
            'total_attempts': self.metrics.get('total_attempts', 0),
            'successful_attempts': self.metrics.get('successful_attempts', 0),
            'partial_refreshes': self.metrics.get('partial_refresh_count', 0),
            'full_refreshes': self.metrics.get('full_refresh_count', 0)
        }


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metrics_collector: MetricsCollector, operation_type: str, **kwargs):
        """Initialize the timer."""
        self.metrics_collector = metrics_collector
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metrics."""
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000
        
        # Record the timing based on operation type
        if self.operation_type == 'render':
            render_type = self.kwargs.get('render_type', 'standard')
            self.metrics_collector.record_render_time(duration_ms, render_type)
            if exc_type is None:  # No exception occurred
                self.metrics_collector.record_render_success()
        
        elif self.operation_type == 'display_update':
            refresh_type = self.kwargs.get('refresh_type', 'partial')
            self.metrics_collector.record_display_update_time(duration_ms, refresh_type)
            if exc_type is None:  # No exception occurred
                self.metrics_collector.record_display_success()
    
    def get_duration_ms(self) -> Optional[float]:
        """Get the duration in milliseconds."""
        if self.start_time is not None and self.end_time is not None:
            return (self.end_time - self.start_time) * 1000
        return None
