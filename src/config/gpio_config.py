"""
GPIO pin configuration for Waveshare 10.3" e-Paper HAT connection to Raspberry Pi Zero 2 W.
"""


class GPIOConfig:
    """GPIO pin definitions for e-ink display connection."""
    
    # SPI pins (hardware SPI)
    SPI_MOSI = 19  # GPIO 19 (Pin 35) - Master Out Slave In
    SPI_MISO = 21  # GPIO 21 (Pin 40) - Master In Slave Out  
    SPI_SCLK = 23  # GPIO 23 (Pin 16) - Serial Clock
    SPI_CS = 24    # GPIO 24 (Pin 18) - Chip Select
    CS_PIN = 24    # Alias for SPI_CS for compatibility
    
    # Control pins
    RST_PIN = 22   # GPIO 22 (Pin 15) - Reset
    BUSY_PIN = 18  # GPIO 18 (Pin 12) - Busy signal
    
    # Power pins (for reference, not GPIO controlled)
    VCC_PIN = 2    # 5V Power (Pin 2 or 4)
    GND_PIN = 6    # Ground (Pin 6)
    
    # SPI device settings
    SPI_BUS = 0    # SPI bus number
    SPI_DEVICE = 0 # SPI device number
    SPI_SPEED = 2000000  # 2MHz SPI speed
    
    @classmethod
    def get_pin_mapping(cls):
        """Get a dictionary of pin mappings for documentation."""
        return {
            'VCC (5V)': cls.VCC_PIN,
            'GND': cls.GND_PIN,
            'DIN (MOSI)': cls.SPI_MOSI,
            'DOUT (MISO)': cls.SPI_MISO,
            'CLK (SCLK)': cls.SPI_SCLK,
            'CS': cls.SPI_CS,
            'HRDY (BUSY)': cls.BUSY_PIN,
            'RST': cls.RST_PIN
        }
    
    @classmethod
    def validate_pins(cls):
        """Validate that all required pins are defined."""
        required_pins = [
            cls.SPI_MOSI, cls.SPI_MISO, cls.SPI_SCLK, cls.SPI_CS,
            cls.RST_PIN, cls.BUSY_PIN
        ]
        
        # Check for duplicate pins
        if len(set(required_pins)) != len(required_pins):
            raise ValueError("Duplicate GPIO pins detected in configuration")
        
        # Check pin ranges (valid GPIO pins for Pi Zero 2 W)
        valid_gpio_range = range(2, 28)  # GPIO 2-27 are available
        for pin in required_pins:
            if pin not in valid_gpio_range:
                raise ValueError(f"Invalid GPIO pin: {pin}")
        
        return True
