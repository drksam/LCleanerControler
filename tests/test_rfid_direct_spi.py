#!/usr/bin/env python3
"""
Pi 5 RFID Test using direct SPI communication
Bypasses the GPIO library issues by using spidev directly
"""
import time
import spidev
import sys

class MFRC522_Pi5:
    """Direct SPI implementation of MFRC522 for Pi 5"""
    
    # MFRC522 registers
    CommandReg = 0x01
    ComIEnReg = 0x02
    DivIEnReg = 0x03
    ComIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    WaterLevelReg = 0x0B
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    ModeReg = 0x11
    TxModeReg = 0x12
    RxModeReg = 0x13
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TxSelReg = 0x16
    RxSelReg = 0x17
    RxThresholdReg = 0x18
    DemodReg = 0x19
    MfTxReg = 0x1C
    MfRxReg = 0x1D
    SerialSpeedReg = 0x1F
    CRCResultRegM = 0x21
    CRCResultRegL = 0x22
    ModWidthReg = 0x24
    RFCfgReg = 0x26
    GsNReg = 0x27
    CWGsPReg = 0x28
    ModGsPReg = 0x29
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F
    TestSel1Reg = 0x31
    TestSel2Reg = 0x32
    TestPinEnReg = 0x33
    TestPinValueReg = 0x34
    TestBusReg = 0x35
    AutoTestReg = 0x36
    VersionReg = 0x37
    AnalogTestReg = 0x38
    TestDAC1Reg = 0x39
    TestDAC2Reg = 0x3A
    TestADCReg = 0x3B
    
    # Commands
    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03
    
    # PICC commands
    PICC_REQIDL = 0x26
    PICC_REQALL = 0x52
    PICC_ANTICOLL = 0x93
    PICC_SElECTTAG = 0x93
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ = 0x30
    PICC_WRITE = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE = 0xC2
    PICC_TRANSFER = 0xB0
    PICC_HALT = 0x50
    
    def __init__(self, bus=0, device=0, speed=1000000):
        """Initialize SPI connection"""
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0b00  # SPI mode 0
        
        print(f"   📡 SPI initialized: Bus {bus}, Device {device}, Speed {speed}Hz")
        
        # Initialize the MFRC522
        self.init()
    
    def write_register(self, addr, val):
        """Write a value to a register"""
        self.spi.xfer2([(addr << 1) & 0x7E, val])
    
    def read_register(self, addr):
        """Read a value from a register"""
        result = self.spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])
        return result[1]
    
    def set_bit_mask(self, reg, mask):
        """Set bit mask in register"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp | mask)
    
    def clear_bit_mask(self, reg, mask):
        """Clear bit mask in register"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp & (~mask))
    
    def antenna_on(self):
        """Turn on antenna"""
        temp = self.read_register(self.TxControlReg)
        if not (temp & 0x03):
            self.set_bit_mask(self.TxControlReg, 0x03)
    
    def antenna_off(self):
        """Turn off antenna"""
        self.clear_bit_mask(self.TxControlReg, 0x03)
    
    def init(self):
        """Initialize the MFRC522"""
        # Reset the chip
        self.write_register(self.CommandReg, self.PCD_RESETPHASE)
        time.sleep(0.1)
        
        # Configure timer
        self.write_register(self.TModeReg, 0x8D)
        self.write_register(self.TPrescalerReg, 0x3E)
        self.write_register(self.TReloadRegL, 30)
        self.write_register(self.TReloadRegH, 0)
        
        # Configure other settings
        self.write_register(self.TxAutoReg, 0x40)
        self.write_register(self.ModeReg, 0x3D)
        
        # Turn on antenna
        self.antenna_on()
        
        print("   ✅ MFRC522 chip initialized")
    
    def card_write(self, command, data):
        """Send command and data to card"""
        back_data = []
        back_length = 0
        status = False
        irq_en = 0x00
        wait_irq = 0x00
        
        if command == self.PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        elif command == self.PCD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30
        
        self.write_register(self.ComIEnReg, irq_en | 0x80)
        self.clear_bit_mask(self.ComIrqReg, 0x80)
        self.set_bit_mask(self.FIFOLevelReg, 0x80)
        
        self.write_register(self.CommandReg, self.PCD_IDLE)
        
        # Write data to FIFO
        for i in range(len(data)):
            self.write_register(self.FIFODataReg, data[i])
        
        # Execute command
        self.write_register(self.CommandReg, command)
        
        if command == self.PCD_TRANSCEIVE:
            self.set_bit_mask(self.BitFramingReg, 0x80)
        
        # Wait for command completion
        i = 2000
        while True:
            n = self.read_register(self.ComIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x01) and not (n & wait_irq)):
                break
        
        self.clear_bit_mask(self.BitFramingReg, 0x80)
        
        if i != 0:
            if (self.read_register(self.ErrorReg) & 0x1B) == 0x00:
                status = True
                
                if n & irq_en & 0x01:
                    status = False
                
                if command == self.PCD_TRANSCEIVE:
                    n = self.read_register(self.FIFOLevelReg)
                    last_bits = self.read_register(self.ControlReg) & 0x07
                    if last_bits != 0:
                        back_length = (n - 1) * 8 + last_bits
                    else:
                        back_length = n * 8
                    
                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16
                    
                    # Read data from FIFO
                    for i in range(n):
                        back_data.append(self.read_register(self.FIFODataReg))
            else:
                status = False
        
        return (status, back_data, back_length)
    
    def request(self, req_mode):
        """Request card"""
        self.write_register(self.BitFramingReg, 0x07)
        (status, back_data, back_length) = self.card_write(self.PCD_TRANSCEIVE, [req_mode])
        
        if not (status) or (back_length != 0x10):
            status = False
        
        return (status, back_length)
    
    def anticoll(self):
        """Anti-collision detection"""
        serial_number = []
        serial_number_check = 0
        
        self.write_register(self.BitFramingReg, 0x00)
        serial_number.append(self.PICC_ANTICOLL)
        serial_number.append(0x20)
        
        (status, back_data, back_length) = self.card_write(self.PCD_TRANSCEIVE, serial_number)
        
        if status:
            if len(back_data) == 5:
                for i in range(4):
                    serial_number_check = serial_number_check ^ back_data[i]
                if serial_number_check != back_data[4]:
                    status = False
            else:
                status = False
        
        return (status, back_data)
    
    def read_no_block(self):
        """Non-blocking read attempt"""
        try:
            # Request card
            (status, back_length) = self.request(self.PICC_REQIDL)
            if status:
                # Get card ID
                (status, uid) = self.anticoll()
                if status and len(uid) >= 4:
                    # Convert UID to integer
                    card_id = 0
                    for i in range(4):
                        card_id = card_id * 256 + uid[i]
                    return (card_id, "")
            return (None, None)
        except:
            return (None, None)
    
    def get_version(self):
        """Get chip version"""
        version = self.read_register(self.VersionReg)
        return version
    
    def close(self):
        """Close SPI connection"""
        self.antenna_off()
        self.spi.close()

def test_rfid_direct_spi():
    """Test RFID using direct SPI communication"""
    print("🔍 Direct SPI RFID Test for Pi 5")
    print("="*50)
    
    # Test 1: SPI availability
    print("1. Testing SPI availability...")
    try:
        import spidev
        print("   ✅ spidev library available")
    except ImportError:
        print("   ❌ spidev not available")
        print("   📥 Install with: pip install spidev")
        return False
    
    # Test 2: Initialize RFID with direct SPI
    print("\\n2. Initializing RFID with direct SPI...")
    try:
        rfid = MFRC522_Pi5()
        print("   ✅ RFID initialized successfully")
    except Exception as e:
        print(f"   ❌ RFID initialization failed: {e}")
        print("   💡 Check SPI wiring connections")
        return False
    
    # Test 3: Check chip version
    print("\\n3. Reading chip version...")
    try:
        version = rfid.get_version()
        print(f"   ✅ Chip version: 0x{version:02X}")
        if version == 0x91 or version == 0x92:
            print("   ✅ Valid MFRC522 chip detected")
        elif version == 0x00 or version == 0xFF:
            print("   ⚠️  No response from chip - check wiring")
            return False
        else:
            print(f"   ⚠️  Unknown chip version: 0x{version:02X}")
    except Exception as e:
        print(f"   ❌ Version read failed: {e}")
        return False
    
    # Test 4: Card detection
    print("\\n4. Testing card detection (15 seconds)...")
    print("   📋 Place an RFID card near the reader...")
    
    start_time = time.time()
    card_detected = False
    attempts = 0
    
    try:
        while time.time() - start_time < 15:
            attempts += 1
            card_id, _ = rfid.read_no_block()
            
            if card_id is not None:
                print(f"   ✅ Card detected!")
                print(f"      Card ID: {card_id}")
                print(f"      Hex: 0x{card_id:08X}")
                print(f"      Attempts: {attempts}")
                card_detected = True
                break
            
            time.sleep(0.1)
            
            # Show progress
            if attempts % 50 == 0:  # Every 5 seconds
                elapsed = time.time() - start_time
                remaining = 15 - elapsed
                print(f"   ⏱️  Still scanning... {remaining:.0f}s remaining")
        
        if not card_detected:
            print(f"   ⏰ No card detected after {attempts} attempts")
            print("   💡 Try positioning card closer to antenna")
    
    except KeyboardInterrupt:
        print("\\n   🛑 Test stopped by user")
    finally:
        rfid.close()
    
    return card_detected

def main():
    """Main test function"""
    print("🚀 Starting Pi 5 Direct SPI RFID Test...")
    
    try:
        success = test_rfid_direct_spi()
        
        print("\\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        if success:
            print("🎉 RFID reader is working with direct SPI!")
            print("✅ Your hardware setup is correct")
            print("\\n🔧 Next steps:")
            print("   1. The issue is with the mfrc522 Python library on Pi 5")
            print("   2. Consider using a Pi 5 compatible RFID library")
            print("   3. Or modify your app to use direct SPI communication")
        else:
            print("⚠️  RFID test failed")
            print("💡 Check:")
            print("   - Wiring connections")
            print("   - Power supply (3.3V)")
            print("   - SPI enable in raspi-config")
        
        print("="*50)
        return success
        
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted")
        return False
    except Exception as e:
        print(f"\\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
