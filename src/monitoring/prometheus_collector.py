"""
Prometheus metrics collection module for Pi Home Dashboard.
Replaces StatsD-based metrics with Prometheus instrumentation.
"""

import logging
import time
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import threading

logger = logging.getLogger(__name__)


class PrometheusCollector:
    """Collects and exposes performance metrics via Prometheus."""
    
    def __init__(self, port: int = 8000):
        """Initialize the Prometheus metrics collector."""
        self.port = port
        self._server_started = False
        self._server_lock = threading.Lock()
        
        # Define Prometheus metrics
        self.render_duration = Histogram(
            'pi_dashboard_render_duration_seconds',
            'Time taken to render dashboard content',
            ['render_type']
        )
        
        self.display_update_duration = Histogram(
            'pi_dashboard_display_update_duration_seconds', 
            'Time taken to update e-ink display',
            ['refresh_type']
        )
        
        self.full_cycle_duration = Histogram(
            'pi_dashboard_full_cycle_duration_seconds',
            'Time taken for complete render+display update cycle',
            ['render_type', 'refresh_type']
        )
        
        self.dashboard_updates_total = Counter(
            'pi_dashboard_updates_total',
            'Total number of dashboard update attempts',
            ['status']
        )
        
        self.render_attempts_total = Counter(
            'pi_dashboard_render_attempts_total',
            'Total number of render attempts',
            ['render_type', 'status']
        )
        
        self.display_refresh_total = Counter(
            'pi_dashboard_display_refresh_total',
            'Total number of display refreshes',
            ['refresh_type']
        )
        
        # System health gauges
        self.cpu_temperature = Gauge(
            'pi_dashboard_cpu_temperature_celsius',
            'CPU temperature in Celsius'
        )
        
        self.memory_usage_percent = Gauge(
            'pi_dashboard_memory_usage_percent',
            'Memory usage percentage'
        )
        
        self.cpu_usage_percent = Gauge(
            'pi_dashboard_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.disk_usage_percent = Gauge(
            'pi_dashboard_disk_usage_percent',
            'Disk usage percentage'
        )
        
        # Browser metrics
        self.browser_memory_mb = Gauge(
            'pi_dashboard_browser_memory_mb',
            'Browser memory usage in MB'
        )
        
        self.browser_processes = Gauge(
            'pi_dashboard_browser_processes',
            'Number of browser processes'
        )
        
        # Service status
        self.service_status = Gauge(
            'pi_dashboard_service_status',
            'Service status indicators',
            ['component']
        )
        
        # Update interval gauge
        self.update_interval_seconds = Gauge(
            'pi_dashboard_update_interval_seconds',
            'Configured update interval in seconds'
        )
        
        # Update timing offset metric
        self.update_timing_offset_seconds = Histogram(
            'pi_dashboard_update_timing_offset_seconds',
            'Offset between intended update time and actual update completion time',
            buckets=(-5.0, -2.0, -1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float('inf'))
        )
        
        # Time validation metrics
        self.time_validation_total = Counter(
            'pi_dashboard_time_validation_total',
            'Total number of time validations performed',
            ['status']
        )
        
        self.time_offset_minutes = Histogram(
            'pi_dashboard_time_offset_minutes',
            'Time offset between displayed and system time in minutes',
            buckets=(0, 1, 2, 5, 10, float('inf'))
        )
        
        self.time_validation_warnings = Counter(
            'pi_dashboard_time_validation_warnings_total',
            'Total number of time validation warnings issued'
        )
        
        logger.info(f"PrometheusCollector initialized for port {port}")
    
    def start_server(self):
        """Start the Prometheus HTTP server."""
        with self._server_lock:
            if not self._server_started:
                try:
                    start_http_server(self.port)
                    self._server_started = True
                    logger.info(f"Prometheus metrics server started on port {self.port}")
                except Exception as e:
                    logger.error(f"Failed to start Prometheus server: {e}")
                    raise
    
    def record_render_time(self, render_time_seconds: float, render_type: str = 'standard'):
        """Record a dashboard render time."""
        self.render_duration.labels(render_type=render_type).observe(render_time_seconds)
        logger.debug(f"Recorded render time: {render_time_seconds:.3f}s (type: {render_type})")
    
    def record_render_success(self, render_type: str = 'standard'):
        """Record a successful render."""
        self.render_attempts_total.labels(render_type=render_type, status='success').inc()
        logger.debug(f"Recorded successful render (type: {render_type})")
    
    def record_render_failure(self, render_type: str = 'standard'):
        """Record a failed render."""
        self.render_attempts_total.labels(render_type=render_type, status='failure').inc()
        logger.debug(f"Recorded failed render (type: {render_type})")
    
    def record_display_update_time(self, update_time_seconds: float, refresh_type: str = 'partial'):
        """Record a display update time."""
        self.display_update_duration.labels(refresh_type=refresh_type).observe(update_time_seconds)
        self.display_refresh_total.labels(refresh_type=refresh_type).inc()
        logger.debug(f"Recorded display update: {update_time_seconds:.3f}s (type: {refresh_type})")
    
    def record_full_cycle_time(self, cycle_time_seconds: float, render_type: str = 'standard', refresh_type: str = 'partial'):
        """Record a full render+display update cycle time."""
        self.full_cycle_duration.labels(render_type=render_type, refresh_type=refresh_type).observe(cycle_time_seconds)
        logger.debug(f"Recorded full cycle time: {cycle_time_seconds:.3f}s (render: {render_type}, refresh: {refresh_type})")
    
    def record_update_attempt(self):
        """Record a dashboard update attempt."""
        self.dashboard_updates_total.labels(status='attempt').inc()
        logger.debug("Recorded dashboard update attempt")
    
    def record_update_success(self):
        """Record a successful dashboard update."""
        self.dashboard_updates_total.labels(status='success').inc()
        logger.debug("Recorded successful dashboard update")
    
    def record_update_failure(self):
        """Record a failed dashboard update."""
        self.dashboard_updates_total.labels(status='failure').inc()
        logger.debug("Recorded failed dashboard update")
    
    def set_update_interval(self, interval_seconds: int):
        """Set the expected update interval."""
        self.update_interval_seconds.set(interval_seconds)
        logger.debug(f"Set update interval: {interval_seconds}s")
    
    def record_update_timing_offset(self, offset_seconds: float):
        """Record the timing offset between intended and actual update completion time.
        
        Args:
            offset_seconds: Positive values indicate update completed late,
                          negative values indicate update completed early.
        """
        self.update_timing_offset_seconds.observe(offset_seconds)
        if offset_seconds > 0:
            logger.debug(f"Update completed {offset_seconds:.2f}s late")
        elif offset_seconds < 0:
            logger.debug(f"Update completed {abs(offset_seconds):.2f}s early")
        else:
            logger.debug("Update completed exactly on time")
    
    def record_time_validation(self, status: str):
        """Record a time validation attempt.
        
        Args:
            status: 'success', 'warning', or 'error'
        """
        self.time_validation_total.labels(status=status).inc()
        logger.debug(f"Recorded time validation: {status}")
    
    def record_time_offset(self, offset_minutes: float):
        """Record the time offset between displayed and system time.
        
        Args:
            offset_minutes: Time offset in minutes (positive = displayed time is ahead)
        """
        self.time_offset_minutes.observe(offset_minutes)
        logger.debug(f"Recorded time offset: {offset_minutes:.1f} minutes")
    
    def record_time_validation_warning(self):
        """Record a time validation warning."""
        self.time_validation_warnings.inc()
        logger.debug("Recorded time validation warning")
    
    def send_system_metrics(self, cpu_temp: Optional[float] = None, 
                           memory_usage: Optional[float] = None,
                           cpu_usage: Optional[float] = None, 
                           disk_usage: Optional[float] = None):
        """Send system health metrics."""
        if cpu_temp is not None:
            self.cpu_temperature.set(cpu_temp)
            logger.debug(f"Updated CPU temperature: {cpu_temp}°C")
        if memory_usage is not None:
            self.memory_usage_percent.set(memory_usage)
            logger.debug(f"Updated memory usage: {memory_usage}%")
        if cpu_usage is not None:
            self.cpu_usage_percent.set(cpu_usage)
            logger.debug(f"Updated CPU usage: {cpu_usage}%")
        if disk_usage is not None:
            self.disk_usage_percent.set(disk_usage)
            logger.debug(f"Updated disk usage: {disk_usage}%")
    
    def send_browser_metrics(self, browser_memory: Optional[float] = None, 
                           browser_processes: Optional[int] = None):
        """Send browser-related metrics."""
        if browser_memory is not None:
            self.browser_memory_mb.set(browser_memory)
            logger.debug(f"Updated browser memory: {browser_memory}MB")
        if browser_processes is not None:
            self.browser_processes.set(browser_processes)
            logger.debug(f"Updated browser processes: {browser_processes}")
    
    def send_service_status(self, service_running: bool = True, 
                          display_connected: bool = True,
                          network_connected: bool = True):
        """Send service status metrics."""
        self.service_status.labels(component='service').set(1 if service_running else 0)
        self.service_status.labels(component='display').set(1 if display_connected else 0)
        self.service_status.labels(component='network').set(1 if network_connected else 0)
        logger.debug(f"Updated service status - service: {service_running}, "
                    f"display: {display_connected}, network: {network_connected}")
    
    def get_refresh_ratio(self) -> float:
        """Get partial to full refresh ratio (for compatibility with existing code)."""
        # This is a calculated metric that can be derived from the counters in Grafana
        # For now, return 0.0 as a placeholder
        return 0.0
    
    def get_metrics_summary(self) -> dict:
        """Get a summary of current metrics (for logging/debugging)."""
        # Note: Prometheus metrics don't expose current values easily
        # This is mainly for compatibility with existing logging
        return {
            'prometheus_server_running': self._server_started,
            'metrics_port': self.port,
            'note': 'Detailed metrics available at /metrics endpoint'
        }


class PrometheusTimer:
    """Context manager for timing operations with Prometheus metrics."""
    
    def __init__(self, collector: PrometheusCollector, operation_type: str, **kwargs):
        """Initialize the timer."""
        self.collector = collector
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        logger.debug(f"PrometheusTimer initialized for operation: {operation_type}")
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        logger.debug(f"Started timing {self.operation_type} operation")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metrics."""
        self.end_time = time.time()
        
        if self.start_time is not None:
            duration_seconds = self.end_time - self.start_time
            success = exc_type is None
            
            if exc_type is None:
                logger.debug(f"Completed {self.operation_type} operation in {duration_seconds:.3f}s")
            else:
                logger.warning(f"Failed {self.operation_type} operation after {duration_seconds:.3f}s: {exc_val}")
            
            # Record the timing and success/failure based on operation type
            if self.operation_type == 'render':
                render_type = self.kwargs.get('render_type', 'standard')
                self.collector.record_render_time(duration_seconds, render_type)
                if success:
                    self.collector.record_render_success(render_type)
                else:
                    self.collector.record_render_failure(render_type)
            
            elif self.operation_type == 'display_update':
                refresh_type = self.kwargs.get('refresh_type', 'partial')
                self.collector.record_display_update_time(duration_seconds, refresh_type)
            
            elif self.operation_type == 'full_cycle':
                render_type = self.kwargs.get('render_type', 'standard')
                refresh_type = self.kwargs.get('refresh_type', 'partial')
                self.collector.record_full_cycle_time(duration_seconds, render_type, refresh_type)
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get the duration in seconds."""
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None
