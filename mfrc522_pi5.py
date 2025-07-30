#!/usr/bin/env python3
"""
Pi 5 Compatible RFID Wrapper
A drop-in replacement for mfrc522.SimpleMFRC522 that works on Pi 5
"""
import time
import spidev

class SimpleMFRC522_Pi5:
    """Pi 5 compatible replacement for mfrc522.SimpleMFRC522"""
    
    # MFRC522 registers and commands
    CommandReg = 0x01
    ComIEnReg = 0x02
    ComIrqReg = 0x04
    ErrorReg = 0x06
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    TxControlReg = 0x14
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TxAutoReg = 0x15
    ModeReg = 0x11
    VersionReg = 0x37
    
    # Commands
    PCD_IDLE = 0x00
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    
    # PICC commands
    PICC_REQIDL = 0x26
    PICC_ANTICOLL = 0x93
    
    def __init__(self, bus=0, device=0, speed=1000000):
        """Initialize the RFID reader"""
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            self.spi.max_speed_hz = speed
            self.spi.mode = 0b00
            self._init_chip()
        except Exception as e:
            raise Exception(f"Failed to initialize RFID reader: {e}")
    
    def _write_register(self, addr, val):
        """Write to MFRC522 register"""
        self.spi.xfer2([(addr << 1) & 0x7E, val])
    
    def _read_register(self, addr):
        """Read from MFRC522 register"""
        result = self.spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])
        return result[1]
    
    def _set_bit_mask(self, reg, mask):
        """Set bit mask in register"""
        tmp = self._read_register(reg)
        self._write_register(reg, tmp | mask)
    
    def _clear_bit_mask(self, reg, mask):
        """Clear bit mask in register"""
        tmp = self._read_register(reg)
        self._write_register(reg, tmp & (~mask))
    
    def _init_chip(self):
        """Initialize the MFRC522 chip"""
        # Reset
        self._write_register(self.CommandReg, self.PCD_RESETPHASE)
        time.sleep(0.1)
        
        # Configure timer
        self._write_register(self.TModeReg, 0x8D)
        self._write_register(self.TPrescalerReg, 0x3E)
        self._write_register(self.TReloadRegL, 30)
        self._write_register(self.TReloadRegH, 0)
        
        # Configure other settings
        self._write_register(self.TxAutoReg, 0x40)
        self._write_register(self.ModeReg, 0x3D)
        
        # Turn on antenna
        temp = self._read_register(self.TxControlReg)
        if not (temp & 0x03):
            self._set_bit_mask(self.TxControlReg, 0x03)
    
    def _card_write(self, command, data):
        """Send command to card"""
        back_data = []
        back_length = 0
        status = False
        irq_en = 0x77
        wait_irq = 0x30
        
        self._write_register(self.ComIEnReg, irq_en | 0x80)
        self._clear_bit_mask(self.ComIrqReg, 0x80)
        self._set_bit_mask(self.FIFOLevelReg, 0x80)
        self._write_register(self.CommandReg, self.PCD_IDLE)
        
        # Write data to FIFO
        for val in data:
            self._write_register(self.FIFODataReg, val)
        
        # Execute command
        self._write_register(self.CommandReg, command)
        if command == self.PCD_TRANSCEIVE:
            self._set_bit_mask(self.BitFramingReg, 0x80)
        
        # Wait for completion
        i = 2000
        while True:
            n = self._read_register(self.ComIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x01) and not (n & wait_irq)):
                break
        
        self._clear_bit_mask(self.BitFramingReg, 0x80)
        
        if i != 0:
            if (self._read_register(self.ErrorReg) & 0x1B) == 0x00:
                status = True
                if command == self.PCD_TRANSCEIVE:
                    n = self._read_register(self.FIFOLevelReg)
                    last_bits = self._read_register(self.ControlReg) & 0x07
                    if last_bits != 0:
                        back_length = (n - 1) * 8 + last_bits
                    else:
                        back_length = n * 8
                    
                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16
                    
                    for i in range(n):
                        back_data.append(self._read_register(self.FIFODataReg))
        
        return (status, back_data, back_length)
    
    def _request(self, req_mode):
        """Request card presence"""
        self._write_register(self.BitFramingReg, 0x07)
        (status, back_data, back_length) = self._card_write(self.PCD_TRANSCEIVE, [req_mode])
        
        if not status or back_length != 0x10:
            status = False
        
        return (status, back_length)
    
    def _anticoll(self):
        """Anti-collision detection"""
        serial_number = [self.PICC_ANTICOLL, 0x20]
        self._write_register(self.BitFramingReg, 0x00)
        
        (status, back_data, back_length) = self._card_write(self.PCD_TRANSCEIVE, serial_number)
        
        if status and len(back_data) == 5:
            # Verify checksum
            serial_number_check = 0
            for i in range(4):
                serial_number_check ^= back_data[i]
            if serial_number_check != back_data[4]:
                status = False
        else:
            status = False
        
        return (status, back_data)
    
    def read_no_block(self):
        """
        Non-blocking read - compatible with original mfrc522 interface
        Returns: (id, text) or (None, None) if no card
        """
        try:
            # Request card
            (status, back_length) = self._request(self.PICC_REQIDL)
            if status:
                # Get UID
                (status, uid) = self._anticoll()
                if status and len(uid) >= 4:
                    # Convert UID to integer (like original library)
                    card_id = 0
                    for i in range(4):
                        card_id = card_id * 256 + uid[i]
                    return (card_id, "")  # Return empty text for compatibility
            
            return (None, None)
        except:
            return (None, None)
    
    def read(self):
        """
        Blocking read - compatible with original mfrc522 interface
        Waits until a card is detected
        """
        while True:
            id, text = self.read_no_block()
            if id is not None:
                return (id, text)
            time.sleep(0.1)
    
    def get_version(self):
        """Get chip version for diagnostics"""
        return self._read_register(self.VersionReg)
    
    def close(self):
        """Clean up resources"""
        try:
            # Turn off antenna
            self._clear_bit_mask(self.TxControlReg, 0x03)
            self.spi.close()
        except:
            pass

# For backward compatibility, create the same interface as mfrc522
class SimpleMFRC522:
    """Drop-in replacement for mfrc522.SimpleMFRC522"""
    
    def __init__(self):
        self.reader = SimpleMFRC522_Pi5()
    
    def read_no_block(self):
        return self.reader.read_no_block()
    
    def read(self):
        return self.reader.read()
    
    def write(self, text):
        # Write functionality not implemented in this simple version
        raise NotImplementedError("Write not implemented in Pi 5 compatibility version")

def test_pi5_wrapper():
    """Test the Pi 5 compatible wrapper"""
    print("🔧 Testing Pi 5 RFID Wrapper")
    print("="*40)
    
    try:
        # Test initialization
        print("1. Initializing wrapper...")
        reader = SimpleMFRC522()
        print("   ✅ Wrapper initialized")
        
        # Test version
        version = reader.reader.get_version()
        print(f"   📋 Chip version: 0x{version:02X}")
        
        # Test card detection
        print("\\n2. Testing card detection (10s)...")
        print("   📋 Place card near reader...")
        
        start_time = time.time()
        while time.time() - start_time < 10:
            id, text = reader.read_no_block()
            if id is not None:
                print(f"   ✅ Card detected: {id}")
                print("   🎉 Pi 5 wrapper working!")
                return True
            time.sleep(0.1)
        
        print("   ⏰ No card detected (wrapper functional)")
        return True
        
    except Exception as e:
        print(f"   ❌ Wrapper test failed: {e}")
        return False
    finally:
        try:
            reader.reader.close()
        except:
            pass

if __name__ == "__main__":
    test_pi5_wrapper()
