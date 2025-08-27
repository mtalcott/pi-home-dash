"""
Metrics collection module for Pi Home Dashboard.
Collects performance metrics and sends them directly to statsd/netdata.
"""

import logging
import time
from typing import Optional
import statsd

# Set up logger for this module
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and sends performance metrics directly to statsd for netdata monitoring."""
    
    def __init__(self, statsd_host: str = 'localhost', statsd_port: int = 8125):
        """Initialize the metrics collector with statsd client."""
        self.statsd_client = statsd.StatsClient(host=statsd_host, port=statsd_port, prefix='pi_dashboard')
        
        # Counters for tracking attempts and successes
        self.total_attempts = 0
        self.successful_attempts = 0
        self.render_attempts = 0
        self.render_successes = 0
        self.display_attempts = 0
        self.display_successes = 0
        self.partial_refresh_count = 0
        self.full_refresh_count = 0
        
        logger.info(f"MetricsCollector initialized with statsd at {statsd_host}:{statsd_port}")
        
    def record_render_time(self, render_time_ms: float, render_type: str = 'standard'):
        """Record a dashboard render time."""
        logger.info(f"Recording render time: {render_time_ms:.2f}ms (type: {render_type})")
        
        # Send timing metric to statsd
        self.statsd_client.timing('render.time', render_time_ms)
        self.statsd_client.timing(f'render.time.{render_type}', render_time_ms)
        
        # Increment attempt counter
        self.render_attempts += 1
        self.statsd_client.gauge('render.attempts', self.render_attempts)
    
    def record_render_success(self):
        """Record a successful render."""
        logger.info("Recording successful render")
        self.render_successes += 1
        self.statsd_client.gauge('render.successes', self.render_successes)
        
        # Calculate and send success rate
        if self.render_attempts > 0:
            success_rate = (self.render_successes / self.render_attempts) * 100
            self.statsd_client.gauge('render.success_rate', success_rate)
    
    def record_display_update_time(self, update_time_ms: float, refresh_type: str = 'partial'):
        """Record a display update time."""
        logger.info(f"Recording display update time: {update_time_ms:.2f}ms (type: {refresh_type})")
        
        # Send timing metric to statsd
        self.statsd_client.timing('display.update_time', update_time_ms)
        self.statsd_client.timing(f'display.update_time.{refresh_type}', update_time_ms)
        
        # Track refresh type counters
        if refresh_type == 'full':
            self.full_refresh_count += 1
            self.statsd_client.gauge('display.full_refresh_count', self.full_refresh_count)
        else:
            self.partial_refresh_count += 1
            self.statsd_client.gauge('display.partial_refresh_count', self.partial_refresh_count)
        
        # Increment attempt counter
        self.display_attempts += 1
        self.statsd_client.gauge('display.attempts', self.display_attempts)
    
    def record_display_success(self):
        """Record a successful display update."""
        logger.info("Recording successful display update")
        self.display_successes += 1
        self.statsd_client.gauge('display.successes', self.display_successes)
        
        # Calculate and send success rate
        if self.display_attempts > 0:
            success_rate = (self.display_successes / self.display_attempts) * 100
            self.statsd_client.gauge('display.success_rate', success_rate)
    
    def record_update_attempt(self):
        """Record a dashboard update attempt."""
        logger.info("Recording dashboard update attempt")
        self.total_attempts += 1
        self.statsd_client.gauge('dashboard.total_attempts', self.total_attempts)
        self.statsd_client.incr('dashboard.update_attempt')
    
    def record_update_success(self):
        """Record a successful dashboard update."""
        logger.info("Recording successful dashboard update")
        self.successful_attempts += 1
        self.statsd_client.gauge('dashboard.successful_attempts', self.successful_attempts)
        self.statsd_client.incr('dashboard.update_success')
        
        # Calculate and send overall success rate
        if self.total_attempts > 0:
            success_rate = (self.successful_attempts / self.total_attempts) * 100
            self.statsd_client.gauge('dashboard.success_rate', success_rate)
    
    def set_update_interval(self, interval_seconds: int):
        """Set the expected update interval."""
        self.statsd_client.gauge('dashboard.update_interval', interval_seconds)
    
    def send_system_metrics(self, cpu_temp: Optional[float] = None, memory_usage: Optional[float] = None, 
                           cpu_usage: Optional[float] = None, disk_usage: Optional[float] = None):
        """Send system health metrics."""
        if cpu_temp is not None:
            self.statsd_client.gauge('system.cpu_temp', cpu_temp)
            logger.debug(f"Sent CPU temperature: {cpu_temp}°C")
            
        if memory_usage is not None:
            self.statsd_client.gauge('system.memory_usage', memory_usage)
            logger.debug(f"Sent memory usage: {memory_usage}%")
            
        if cpu_usage is not None:
            self.statsd_client.gauge('system.cpu_usage', cpu_usage)
            logger.debug(f"Sent CPU usage: {cpu_usage}%")
            
        if disk_usage is not None:
            self.statsd_client.gauge('system.disk_usage', disk_usage)
            logger.debug(f"Sent disk usage: {disk_usage}%")
    
    def send_browser_metrics(self, browser_memory: Optional[float] = None, browser_processes: Optional[int] = None):
        """Send browser-related metrics."""
        if browser_memory is not None:
            self.statsd_client.gauge('browser.memory_usage', browser_memory)
            logger.debug(f"Sent browser memory usage: {browser_memory}MB")
            
        if browser_processes is not None:
            self.statsd_client.gauge('browser.process_count', browser_processes)
            logger.debug(f"Sent browser process count: {browser_processes}")
    
    def send_service_status(self, service_running: bool = True, display_connected: bool = True, 
                           network_connected: bool = True):
        """Send service status metrics."""
        self.statsd_client.gauge('service.running', 1 if service_running else 0)
        self.statsd_client.gauge('service.display_connected', 1 if display_connected else 0)
        self.statsd_client.gauge('service.network_connected', 1 if network_connected else 0)
        
        logger.debug(f"Sent service status - running: {service_running}, "
                    f"display: {display_connected}, network: {network_connected}")
    
    def get_refresh_ratio(self) -> float:
        """Get partial to full refresh ratio."""
        if self.full_refresh_count > 0:
            ratio = self.partial_refresh_count / self.full_refresh_count
            self.statsd_client.gauge('display.refresh_ratio', ratio)
            return ratio
        return 0.0
    
    def get_metrics_summary(self) -> dict:
        """Get a summary of current metrics (for logging/debugging)."""
        return {
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'render_attempts': self.render_attempts,
            'render_successes': self.render_successes,
            'display_attempts': self.display_attempts,
            'display_successes': self.display_successes,
            'partial_refreshes': self.partial_refresh_count,
            'full_refreshes': self.full_refresh_count
        }


class PerformanceTimer:
    """Context manager for timing operations and sending metrics to statsd."""
    
    def __init__(self, metrics_collector: MetricsCollector, operation_type: str, **kwargs):
        """Initialize the timer."""
        self.metrics_collector = metrics_collector
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        logger.debug(f"PerformanceTimer initialized for operation: {operation_type}")
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        logger.debug(f"Started timing {self.operation_type} operation")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metrics."""
        self.end_time = time.time()
        
        if self.start_time is not None:
            duration_ms = (self.end_time - self.start_time) * 1000
            
            if exc_type is None:
                logger.info(f"Completed {self.operation_type} operation in {duration_ms:.2f}ms")
            else:
                logger.warning(f"Failed {self.operation_type} operation after {duration_ms:.2f}ms: {exc_val}")
            
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
