#!/usr/bin/env python3
"""
Pi Home Dashboard Custom Netdata Collector

Monitors key performance metrics for the Pi Home Dashboard:
- Render delay (time to render dashboard content)
- Display update time (time to update e-ink display)
- Browser memory usage (persistent browser optimization)
- Dashboard update frequency and success rate
- E-ink display refresh cycles (partial vs full)
- System temperature and throttling
"""

import json
import os
import psutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the dashboard source to Python path
dashboard_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(dashboard_root / 'src'))

try:
    from bases.FrameworkServices.SimpleService import SimpleService
except ImportError:
    # Fallback for different netdata versions
    try:
        from bases.SimpleService import SimpleService
    except ImportError:
        # Create a minimal base class if netdata modules aren't available
        class SimpleService:
            def __init__(self, configuration=None, name=None):
                self.configuration = configuration or {}
                self.name = name or 'pi_dashboard'
                self.order = []
                self.definitions = {}
                
            def check(self):
                return True
                
            def create(self):
                return True
                
            def update(self, interval):
                return {}


class PiDashboardCollector(SimpleService):
    """Custom netdata collector for Pi Home Dashboard metrics."""
    
    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration=configuration, name=name)
        
        # Configuration
        self.dashboard_root = dashboard_root
        self.log_dir = self.dashboard_root / 'logs'
        self.cache_dir = self.dashboard_root / 'cache'
        self.metrics_file = self.cache_dir / 'metrics.json'
        
        # Ensure directories exist
        self.log_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.last_update_time = None
        self.render_times = []
        self.display_update_times = []
        self.success_count = 0
        self.failure_count = 0
        
        # Chart definitions
        self.order = [
            'render_performance',
            'display_performance', 
            'browser_memory',
            'update_frequency',
            'success_rate',
            'eink_refresh_cycles',
            'system_health',
            'dashboard_status'
        ]
        
        self.definitions = {
            'render_performance': {
                'options': [None, 'Dashboard Render Performance', 'milliseconds', 'performance', 'pi_dashboard.render', 'line'],
                'lines': [
                    ['render_time_avg', 'Average Render Time', 'absolute', 1, 1],
                    ['render_time_max', 'Max Render Time', 'absolute', 1, 1],
                    ['render_time_min', 'Min Render Time', 'absolute', 1, 1],
                    ['persistent_browser_time', 'Persistent Browser Time', 'absolute', 1, 1],
                    ['standard_render_time', 'Standard Render Time', 'absolute', 1, 1]
                ]
            },
            'display_performance': {
                'options': [None, 'E-ink Display Update Performance', 'milliseconds', 'performance', 'pi_dashboard.display', 'line'],
                'lines': [
                    ['display_update_avg', 'Average Display Update', 'absolute', 1, 1],
                    ['display_update_max', 'Max Display Update', 'absolute', 1, 1],
                    ['full_refresh_time', 'Full Refresh Time', 'absolute', 1, 1],
                    ['partial_refresh_time', 'Partial Refresh Time', 'absolute', 1, 1]
                ]
            },
            'browser_memory': {
                'options': [None, 'Browser Memory Usage', 'MB', 'memory', 'pi_dashboard.browser', 'area'],
                'lines': [
                    ['chromium_memory', 'Chromium Memory', 'absolute', 1, 1024*1024],
                    ['playwright_memory', 'Playwright Memory', 'absolute', 1, 1024*1024],
                    ['total_browser_memory', 'Total Browser Memory', 'absolute', 1, 1024*1024]
                ]
            },
            'update_frequency': {
                'options': [None, 'Dashboard Update Frequency', 'updates/minute', 'frequency', 'pi_dashboard.frequency', 'line'],
                'lines': [
                    ['updates_per_minute', 'Updates per Minute', 'absolute', 1, 1],
                    ['expected_updates', 'Expected Updates', 'absolute', 1, 1]
                ]
            },
            'success_rate': {
                'options': [None, 'Dashboard Success Rate', 'percentage', 'reliability', 'pi_dashboard.success', 'line'],
                'lines': [
                    ['success_rate', 'Success Rate', 'absolute', 1, 1],
                    ['render_success_rate', 'Render Success Rate', 'absolute', 1, 1],
                    ['display_success_rate', 'Display Success Rate', 'absolute', 1, 1]
                ]
            },
            'eink_refresh_cycles': {
                'options': [None, 'E-ink Refresh Cycles', 'count', 'display', 'pi_dashboard.refresh', 'stacked'],
                'lines': [
                    ['partial_refreshes', 'Partial Refreshes', 'incremental', 1, 1],
                    ['full_refreshes', 'Full Refreshes', 'incremental', 1, 1],
                    ['refresh_ratio', 'Partial/Full Ratio', 'absolute', 1, 1]
                ]
            },
            'system_health': {
                'options': [None, 'System Health Metrics', 'various', 'system', 'pi_dashboard.health', 'line'],
                'lines': [
                    ['cpu_temp', 'CPU Temperature', 'absolute', 1, 1000],  # Convert to °C
                    ['throttling_events', 'Throttling Events', 'incremental', 1, 1],
                    ['memory_usage', 'Memory Usage %', 'absolute', 1, 1],
                    ['disk_usage', 'Disk Usage %', 'absolute', 1, 1]
                ]
            },
            'dashboard_status': {
                'options': [None, 'Dashboard Service Status', 'boolean', 'status', 'pi_dashboard.status', 'line'],
                'lines': [
                    ['service_running', 'Service Running', 'absolute', 1, 1],
                    ['persistent_browser_active', 'Persistent Browser Active', 'absolute', 1, 1],
                    ['display_connected', 'Display Connected', 'absolute', 1, 1],
                    ['network_connected', 'Network Connected', 'absolute', 1, 1]
                ]
            }
        }
    
    def check(self):
        """Check if the collector can run."""
        try:
            # Verify dashboard installation
            if not self.dashboard_root.exists():
                return False
                
            # Check if we can access system metrics
            psutil.cpu_percent()
            psutil.virtual_memory()
            
            return True
        except Exception:
            return False
    
    def update(self, interval):
        """Update metrics and return data."""
        try:
            data = {}
            
            # Load cached metrics if available
            metrics = self._load_metrics()
            
            # Collect render performance metrics
            render_metrics = self._collect_render_metrics(metrics)
            data.update(render_metrics)
            
            # Collect display performance metrics
            display_metrics = self._collect_display_metrics(metrics)
            data.update(display_metrics)
            
            # Collect browser memory metrics
            browser_metrics = self._collect_browser_metrics()
            data.update(browser_metrics)
            
            # Collect update frequency metrics
            frequency_metrics = self._collect_frequency_metrics(metrics)
            data.update(frequency_metrics)
            
            # Collect success rate metrics
            success_metrics = self._collect_success_metrics(metrics)
            data.update(success_metrics)
            
            # Collect e-ink refresh metrics
            refresh_metrics = self._collect_refresh_metrics(metrics)
            data.update(refresh_metrics)
            
            # Collect system health metrics
            health_metrics = self._collect_system_health()
            data.update(health_metrics)
            
            # Collect dashboard status metrics
            status_metrics = self._collect_status_metrics()
            data.update(status_metrics)
            
            return data
            
        except Exception as e:
            self.error(f"Error collecting metrics: {e}")
            return {}
    
    def _load_metrics(self):
        """Load cached metrics from file."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _collect_render_metrics(self, metrics):
        """Collect dashboard render performance metrics."""
        data = {}
        
        render_times = metrics.get('render_times', [])
        if render_times:
            data['render_time_avg'] = int(sum(render_times) / len(render_times))
            data['render_time_max'] = int(max(render_times))
            data['render_time_min'] = int(min(render_times))
        else:
            data['render_time_avg'] = 0
            data['render_time_max'] = 0
            data['render_time_min'] = 0
        
        # Persistent browser vs standard rendering times
        data['persistent_browser_time'] = int(metrics.get('persistent_browser_avg', 0))
        data['standard_render_time'] = int(metrics.get('standard_render_avg', 0))
        
        return data
    
    def _collect_display_metrics(self, metrics):
        """Collect e-ink display performance metrics."""
        data = {}
        
        display_times = metrics.get('display_update_times', [])
        if display_times:
            data['display_update_avg'] = int(sum(display_times) / len(display_times))
            data['display_update_max'] = int(max(display_times))
        else:
            data['display_update_avg'] = 0
            data['display_update_max'] = 0
        
        data['full_refresh_time'] = int(metrics.get('full_refresh_avg', 0))
        data['partial_refresh_time'] = int(metrics.get('partial_refresh_avg', 0))
        
        return data
    
    def _collect_browser_metrics(self):
        """Collect browser memory usage metrics."""
        data = {
            'chromium_memory': 0,
            'playwright_memory': 0,
            'total_browser_memory': 0
        }
        
        try:
            chromium_memory = 0
            playwright_memory = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    name = proc.info['name'].lower()
                    if 'chromium' in name or 'chrome' in name:
                        chromium_memory += proc.info['memory_info'].rss
                    elif 'python' in name:
                        # Check if it's our dashboard process
                        cmdline = proc.cmdline()
                        if any('dashboard' in arg or 'playwright' in arg for arg in cmdline):
                            playwright_memory += proc.info['memory_info'].rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            data['chromium_memory'] = chromium_memory
            data['playwright_memory'] = playwright_memory
            data['total_browser_memory'] = chromium_memory + playwright_memory
            
        except Exception:
            pass
        
        return data
    
    def _collect_frequency_metrics(self, metrics):
        """Collect update frequency metrics."""
        data = {}
        
        # Calculate actual update frequency
        update_times = metrics.get('update_timestamps', [])
        current_time = time.time()
        
        # Count updates in the last minute
        recent_updates = [t for t in update_times if current_time - t < 60]
        data['updates_per_minute'] = len(recent_updates)
        
        # Expected updates based on configuration (default 60 second interval)
        update_interval = metrics.get('update_interval', 60)
        data['expected_updates'] = int(60 / update_interval) if update_interval > 0 else 1
        
        return data
    
    def _collect_success_metrics(self, metrics):
        """Collect success rate metrics."""
        data = {}
        
        total_attempts = metrics.get('total_attempts', 0)
        successful_attempts = metrics.get('successful_attempts', 0)
        
        if total_attempts > 0:
            data['success_rate'] = int((successful_attempts / total_attempts) * 100)
        else:
            data['success_rate'] = 100
        
        # Specific success rates
        render_attempts = metrics.get('render_attempts', 0)
        render_successes = metrics.get('render_successes', 0)
        if render_attempts > 0:
            data['render_success_rate'] = int((render_successes / render_attempts) * 100)
        else:
            data['render_success_rate'] = 100
        
        display_attempts = metrics.get('display_attempts', 0)
        display_successes = metrics.get('display_successes', 0)
        if display_attempts > 0:
            data['display_success_rate'] = int((display_successes / display_attempts) * 100)
        else:
            data['display_success_rate'] = 100
        
        return data
    
    def _collect_refresh_metrics(self, metrics):
        """Collect e-ink refresh cycle metrics."""
        data = {}
        
        data['partial_refreshes'] = metrics.get('partial_refresh_count', 0)
        data['full_refreshes'] = metrics.get('full_refresh_count', 0)
        
        # Calculate partial to full refresh ratio
        partial = data['partial_refreshes']
        full = data['full_refreshes']
        if full > 0:
            data['refresh_ratio'] = int(partial / full)
        else:
            data['refresh_ratio'] = 0
        
        return data
    
    def _collect_system_health(self):
        """Collect system health metrics."""
        data = {}
        
        try:
            # CPU temperature (Raspberry Pi specific)
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = int(f.read().strip())
                    data['cpu_temp'] = temp  # Already in millidegrees
            except:
                data['cpu_temp'] = 0
            
            # Throttling events (Raspberry Pi specific)
            try:
                result = subprocess.run(['vcgencmd', 'get_throttled'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    throttled = result.stdout.strip().split('=')[1]
                    data['throttling_events'] = int(throttled, 16)
                else:
                    data['throttling_events'] = 0
            except:
                data['throttling_events'] = 0
            
            # Memory usage
            memory = psutil.virtual_memory()
            data['memory_usage'] = int(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            data['disk_usage'] = int((disk.used / disk.total) * 100)
            
        except Exception:
            data.update({
                'cpu_temp': 0,
                'throttling_events': 0,
                'memory_usage': 0,
                'disk_usage': 0
            })
        
        return data
    
    def _collect_status_metrics(self):
        """Collect dashboard service status metrics."""
        data = {}
        
        try:
            # Check if pi-home-dash service is running
            result = subprocess.run(['systemctl', 'is-active', 'pi-home-dash'], 
                                  capture_output=True, text=True)
            data['service_running'] = 1 if result.returncode == 0 else 0
            
            # Check if persistent browser is active (look for chromium processes)
            chromium_running = False
            for proc in psutil.process_iter(['name']):
                if 'chromium' in proc.info['name'].lower():
                    chromium_running = True
                    break
            data['persistent_browser_active'] = 1 if chromium_running else 0
            
            # Check display connection (SPI interface)
            spi_connected = os.path.exists('/dev/spidev0.0')
            data['display_connected'] = 1 if spi_connected else 0
            
            # Check network connectivity
            try:
                result = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'], 
                                      capture_output=True, timeout=5)
                data['network_connected'] = 1 if result.returncode == 0 else 0
            except:
                data['network_connected'] = 0
                
        except Exception:
            data.update({
                'service_running': 0,
                'persistent_browser_active': 0,
                'display_connected': 0,
                'network_connected': 0
            })
        
        return data


# Netdata service instantiation
SERVICE = PiDashboardCollector
