"""
Time validation module for Pi Home Dashboard.
Validates that displayed clock time matches system time when screenshots are taken.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram


class TimeValidator:
    """Validates displayed time against system time from HTML content."""
    
    def __init__(self, prometheus_collector=None):
        """Initialize the time validator."""
        self.logger = logging.getLogger(__name__)
        self.prometheus_collector = prometheus_collector
        
        # Prometheus metrics for time validation
        if prometheus_collector:
            self.time_validation_total = Counter(
                'pi_dashboard_time_validation_total',
                'Total number of time validations performed',
                ['status']
            )
            
            self.time_offset_minutes = Histogram(
                'pi_dashboard_time_offset_minutes',
                'Time offset between displayed and system time in minutes',
                buckets=(-10, -5, -2, -1, 0, 1, 2, 5, 10, float('inf'))
            )
            
            self.time_validation_warnings = Counter(
                'pi_dashboard_time_validation_warnings_total',
                'Total number of time validation warnings issued'
            )
        
        # 12-hour format patterns only (no seconds)
        self.time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*(AM|PM)', re.IGNORECASE)
        
        self.logger.info("TimeValidator initialized")
    
    def validate_time_from_page(self, page) -> Dict[str, Any]:
        """
        Validate displayed time against system time by extracting HTML content from Playwright page.
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict containing validation results
        """
        try:
            # Get current system time
            system_time = datetime.now()
            
            # Extract time from HTML elements with time/clock classes
            displayed_time_info = self._extract_time_from_page(page)
            if not displayed_time_info:
                return self._create_validation_result(
                    success=True,
                    warning="No time displays found in page content",
                    system_time=system_time
                )
            
            # Validate the found time against system time
            validation_result = self._validate_time(displayed_time_info, system_time)
            
            # Record metrics
            if self.prometheus_collector:
                if validation_result.get('error'):
                    self.time_validation_total.labels(status='error').inc()
                elif validation_result.get('warning'):
                    self.time_validation_total.labels(status='warning').inc()
                    self.time_validation_warnings.inc()
                else:
                    self.time_validation_total.labels(status='success').inc()
                
                if 'offset_minutes' in validation_result:
                    self.time_offset_minutes.observe(validation_result['offset_minutes'])
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error during time validation: {e}")
            if self.prometheus_collector:
                self.time_validation_total.labels(status='error').inc()
            
            return self._create_validation_result(
                success=False,
                error=f"Time validation failed: {str(e)}"
            )
    
    def _extract_time_from_page(self, page) -> Optional[Dict[str, Any]]:
        """Extract time from HTML elements with time/clock classes."""
        try:
            # First try to find elements with time or clock classes
            time_selectors = [
                '.time',
                '.clock'
            ]
            
            for selector in time_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        text_content = element.text_content()
                        if text_content:
                            time_info = self._parse_time_text(text_content.strip())
                            if time_info:
                                self.logger.debug(f"Found time in element with selector '{selector}': {text_content.strip()}")
                                return time_info
                except Exception as e:
                    self.logger.debug(f"Error checking selector '{selector}': {e}")
                    continue
            
            # If no time/clock elements found, search the entire page content
            try:
                html_content = page.content()
                # Remove HTML tags for text-based time extraction
                text_content = re.sub(r'<[^>]+>', ' ', html_content)
                time_info = self._parse_time_text(text_content)
                if time_info:
                    self.logger.debug(f"Found time in page content: {time_info['matched_text']}")
                    return time_info
            except Exception as e:
                self.logger.debug(f"Error searching full page content: {e}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to extract time from page: {e}")
            return None
    
    def _parse_time_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse time from text content using 12-hour format pattern."""
        try:
            match = self.time_pattern.search(text)
            if not match:
                return None
            
            hour = int(match.group(1))
            minute = int(match.group(2))
            am_pm = match.group(3).upper()
            matched_text = match.group(0)
            
            # Convert to 24-hour format
            if am_pm == 'PM' and hour != 12:
                hour += 12
            elif am_pm == 'AM' and hour == 12:
                hour = 0
            
            # Validate time values
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return None
            
            return {
                'hour': hour,
                'minute': minute,
                'matched_text': matched_text
            }
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"Failed to parse time from text: {e}")
            return None
    
    def _validate_time(self, time_info: Dict[str, Any], system_time: datetime) -> Dict[str, Any]:
        """Validate displayed time against system time."""
        try:
            # Create datetime object for the displayed time (using today's date)
            displayed_time = system_time.replace(
                hour=time_info['hour'],
                minute=time_info['minute'],
                second=0,
                microsecond=0
            )
            
            # Calculate time difference in minutes
            time_diff = displayed_time - system_time
            offset_minutes = time_diff.total_seconds() / 60
            
            # Handle day boundary crossings
            if abs(offset_minutes) > 12 * 60:  # More than 12 hours difference
                if offset_minutes > 0:
                    displayed_time -= timedelta(days=1)
                else:
                    displayed_time += timedelta(days=1)
                time_diff = displayed_time - system_time
                offset_minutes = time_diff.total_seconds() / 60
            
            # Check if there's any difference at the minute level
            minute_difference = abs(round(offset_minutes))
            has_difference = minute_difference > 0
            
            result = self._create_validation_result(
                success=True,
                displayed_time=displayed_time,
                system_time=system_time,
                offset_minutes=round(offset_minutes, 1),
                has_difference=has_difference,
                matched_text=time_info['matched_text']
            )
            
            if has_difference:
                warning_msg = (
                    f"Time display '{time_info['matched_text']}' differs from system time "
                    f"by {abs(offset_minutes):.1f} minutes. "
                    f"System time: {system_time.strftime('%I:%M %p')}, "
                    f"Displayed time: {displayed_time.strftime('%I:%M %p')}"
                )
                result['warning'] = warning_msg
                self.logger.warning(warning_msg)
            
            return result
            
        except Exception as e:
            error_msg = f"Error validating time '{time_info.get('matched_text', 'unknown')}': {e}"
            self.logger.error(error_msg)
            return self._create_validation_result(
                success=False,
                error=error_msg
            )
    
    def _create_validation_result(self, success: bool, warning: Optional[str] = None, 
                                error: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a standardized validation result dictionary."""
        result = {
            'success': success,
            'timestamp': datetime.now(),
            **kwargs
        }
        
        if warning:
            result['warning'] = warning
        if error:
            result['error'] = error
            
        return result
    
    def log_validation_summary(self, validation_result: Dict[str, Any]):
        """Log a summary of the validation results."""
        if not validation_result.get('success'):
            if validation_result.get('error'):
                self.logger.error(f"Time validation failed: {validation_result['error']}")
            return
        
        # Check if this is a "no time displays found" case
        warning_msg = validation_result.get('warning', '')
        if 'No time displays found' in warning_msg:
            self.logger.info("Time validation completed - no time displays found")
            return
        
        # Handle actual time validation warnings
        if validation_result.get('warning') and validation_result.get('matched_text'):
            offset_minutes = validation_result.get('offset_minutes', 0)
            matched_text = validation_result.get('matched_text', 'unknown')
            self.logger.warning(
                f"Time validation warning - displayed '{matched_text}' "
                f"offset by {abs(offset_minutes):.1f} minutes"
            )
        else:
            matched_text = validation_result.get('matched_text')
            if matched_text:
                self.logger.info(f"Time validation passed - displayed '{matched_text}' is accurate")
            else:
                self.logger.info("Time validation completed - no time displays found")
