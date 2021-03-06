import spi
import RPi.GPIO as GPIO

# References:   https://pypi.org/project/spidev/
#               https://github.com/mxgxw/MFRC522-python
#
# Pinout Raspberry Pi with RFID-RC522 Shield (SPI comm)
#
#       Raspberry        Shield
#     Pin 24 (GPIO8)     SDA
#     Pin 23 (GPIO11)    SCK
#     Pin 19 (GPIO10)    MOSI
#     Pin 21 (GPIO9)     MISO
#         -              IRQ
#     Pin 22 (GPIO 25)   RST


class RFID():

    RESET_PIN = 22
    MAX_LEN = 16

    PCD_IDLE       = 0x00
    PCD_AUTHENT    = 0x0E
    PCD_RECEIVE    = 0x08
    PCD_TRANSMIT   = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC    = 0x03
  
    PICC_REQIDL    = 0x26
    PICC_REQALL    = 0x52
    PICC_ANTICOLL  = 0x93
    PICC_SElECTTAG = 0x93
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ      = 0x30
    PICC_WRITE     = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE   = 0xC2
    PICC_TRANSFER  = 0xB0
    PICC_HALT      = 0x50

    MI_OK       = 0
    MI_NOTAGERR = 1
    MI_ERR      = 2

    Reserved00     = 0x00
    CommandReg     = 0x01
    CommIEnReg     = 0x02
    DivlEnReg      = 0x03
    CommIrqReg     = 0x04
    DivIrqReg      = 0x05
    ErrorReg       = 0x06
    Status1Reg     = 0x07
    Status2Reg     = 0x08
    FIFODataReg    = 0x09
    FIFOLevelReg   = 0x0A
    WaterLevelReg  = 0x0B
    ControlReg     = 0x0C
    BitFramingReg  = 0x0D
    CollReg        = 0x0E
    Reserved01     = 0x0F

    Reserved10     = 0x10
    ModeReg        = 0x11
    TxModeReg      = 0x12
    RxModeReg      = 0x13
    TxControlReg   = 0x14
    TxAutoReg      = 0x15
    TxSelReg       = 0x16
    RxSelReg       = 0x17
    RxThresholdReg = 0x18
    DemodReg       = 0x19
    Reserved11     = 0x1A
    Reserved12     = 0x1B
    MifareReg      = 0x1C
    Reserved13     = 0x1D
    Reserved14     = 0x1E
    SerialSpeedReg = 0x1F

    Reserved20        = 0x20  
    CRCResultRegM     = 0x21
    CRCResultRegL     = 0x22
    Reserved21        = 0x23
    ModWidthReg       = 0x24
    Reserved22        = 0x25
    RFCfgReg          = 0x26
    GsNReg            = 0x27
    CWGsPReg          = 0x28
    ModGsPReg         = 0x29
    TModeReg          = 0x2A
    TPrescalerReg     = 0x2B
    TReloadRegH       = 0x2C
    TReloadRegL       = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F

    Reserved30      = 0x30
    TestSel1Reg     = 0x31
    TestSel2Reg     = 0x32
    TestPinEnReg    = 0x33
    TestPinValueReg = 0x34
    TestBusReg      = 0x35
    AutoTestReg     = 0x36
    VersionReg      = 0x37
    AnalogTestReg   = 0x38
    TestDAC1Reg     = 0x39
    TestDAC2Reg     = 0x3A
    TestADCReg      = 0x3B
    Reserved31      = 0x3C
    Reserved32      = 0x3D
    Reserved33      = 0x3E
    Reserved34      = 0x3F

    # refer to /dev/spidev<bus>.<device>
    def __init__(self, BUS=0, DEVICE=0):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)
        GPIO.output(self.RESET_PIN, 1)

        #self.spi = spidev.SpiDev()
        self.spi = spi.SPI("/dev/spidev0.0")
        #self.spi.open(BUS, DEVICE)
        self.spi.speed = 1000000
        self.MFRC522_Init()

    def AntennaOn(self):
        temp = self.Read_MFRC522(self.TxControlReg)
        if(~(temp & 0x03)):
            self.SetBitMask(self.TxControlReg, 0x03)

    def MFRC522_Request(self, reqMode):
        status = None
        backBits = None
        TagType = []
        
        self.Write_MFRC522(self.BitFramingReg, 0x07)
        
        TagType.append(reqMode);
        (status,backData,backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, TagType)

        if ((status != self.MI_OK) | (backBits != 0x10)):
            status = self.MI_ERR
      
        return (status,backBits)

    def SetBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp | mask)
    
    def ClearBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg);
        self.Write_MFRC522(reg, tmp & (~mask))
    
    def MFRC522_ToCard(self,command,sendData):
        backData = []
        backLen = 0
        status = self.MI_ERR
        irqEn = 0x00
        waitIRq = 0x00
        lastBits = None
        n = 0
        i = 0
        
        if command == self.PCD_AUTHENT:
            irqEn = 0x12
            waitIRq = 0x10
        
        if command == self.PCD_TRANSCEIVE:
            irqEn = 0x77
            waitIRq = 0x30

        self.Write_MFRC522(self.CommIEnReg, irqEn|0x80)
        self.ClearBitMask(self.CommIrqReg, 0x80)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
    
        self.Write_MFRC522(self.CommandReg, self.PCD_IDLE);  
    
        while(i<len(sendData)):
            self.Write_MFRC522(self.FIFODataReg, sendData[i])
            i = i+1
    
        self.Write_MFRC522(self.CommandReg, command)
      
        if command == self.PCD_TRANSCEIVE:
            self.SetBitMask(self.BitFramingReg, 0x80)
    
        i = 2000
        while True:
            n = self.Read_MFRC522(self.CommIrqReg)
            i = i - 1
            if ~((i!=0) and ~(n&0x01) and ~(n&waitIRq)):
                break
    
        self.ClearBitMask(self.BitFramingReg, 0x80)

        if i != 0:
            if (self.Read_MFRC522(self.ErrorReg) & 0x1B)==0x00:
                status = self.MI_OK

                if n & irqEn & 0x01:
                    status = self.MI_NOTAGERR

                if command == self.PCD_TRANSCEIVE:
                    n = self.Read_MFRC522(self.FIFOLevelReg)
                    lastBits = self.Read_MFRC522(self.ControlReg) & 0x07
                    if lastBits != 0:
                        backLen = (n-1)*8 + lastBits
                    else:
                        backLen = n*8
                    
                    if n == 0:
                        n = 1
                    if n > self.MAX_LEN:
                        n = self.MAX_LEN
    
                    i = 0
                    while i<n:
                        backData.append(self.Read_MFRC522(self.FIFODataReg))
                        i = i + 1;
                else:
                    status = self.MI_ERR
        return (status,backData,backLen)
    
    def Read_MFRC522(self, addr):
        val = self.spi.transfer((((addr<<1)&0x7E) | 0x80,0))
        return val[1]

    def Write_MFRC522(self, addr, val):
        self.spi.transfer(((addr<<1)&0x7E,val))

    def MFRC522_Reset(self):
        self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

    def MFRC522_Request(self, reqMode):
        status = None
        backBits = None
        TagType = []
        
        self.Write_MFRC522(self.BitFramingReg, 0x07)
        
        TagType.append(reqMode);
        (status,backData,backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, TagType)
  
        if ((status != self.MI_OK) | (backBits != 0x10)):
            status = self.MI_ERR
      
        return (status,backBits)

    def MFRC522_StopCrypto1(self):
        self.ClearBitMask(self.Status2Reg, 0x08)

    def MFRC522_Anticoll(self):
        backData = []
        serNumCheck = 0
    
        serNum = []
  
        self.Write_MFRC522(self.BitFramingReg, 0x00)
    
        serNum.append(self.PICC_ANTICOLL)
        serNum.append(0x20)
    
        (status,backData,backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE,serNum)
    
        if(status == self.MI_OK):
            i = 0
            if len(backData)==5:
                while i<4:
                    serNumCheck = serNumCheck ^ backData[i]
                    i = i + 1
                if serNumCheck != backData[i]:
                    status = self.MI_ERR
                else:
                    status = self.MI_ERR
        return (status,backData)

    def MFRC522_Auth(self, authMode, BlockAddr, Sectorkey, serNum):
        buff = []

        # First byte should be the authMode (A or B)
        buff.append(authMode)

        # Second byte is the trailerBlock (usually 7)
        buff.append(BlockAddr)

        # Now we need to append the authKey which usually is 6 bytes of 0xFF
        i = 0
        while(i < len(Sectorkey)):
            buff.append(Sectorkey[i])
            i = i + 1
        i = 0

        # Next we append the first 4 bytes of the UID
        while(i < 4):
            buff.append(serNum[i])
            i = i +1
        
        # Now we start the authentication itself
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_AUTHENT,buff)

        # Check if an error occurred
        if not(status == self.MI_OK):
            print ("AUTH ERROR!!")
        if not (self.Read_MFRC522(self.Status2Reg) & 0x08) != 0:
            print ("AUTH ERROR(status2reg & 0x08) != 0")

        # Return the status
        return status
    
    def CalculateCRC(self, pIndata):
        self.ClearBitMask(self.DivIrqReg, 0x04)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
        i = 0
        while i<len(pIndata):
            self.Write_MFRC522(self.FIFODataReg, pIndata[i])
            i=i+1
            
        self.Write_MFRC522(self.CommandReg, self.PCD_CALCCRC)
        i=0xFF
        while True:
            n=self.Read_MFRC522(self.DivIrqReg)
            i=i-1
            if not ((i!=0) and not (n&0x04)):
                break
            
        pOutData=[]
        pOutData.append(self.Read_MFRC522(self.CRCResultRegL))
        pOutData.append(self.Read_MFRC522(self.CRCResultRegM))
        return pOutData
    
    def MFRC522_SelectTag(self, serNum):
        backData = []
        buf = []
        buf.append(self.PICC_SElECTTAG)
        buf.append(0x70)
        i=0
        while i<5:
            buf.append(serNum[i])
            i=i+1
            
        pOut = self.CalculateCRC(buf)
        buf.append(pOut[0])
        buf.append(pOut[1])
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE,buf)
        
        if (status == self.MI_OK) and (backLen == 0x18):
            print ("Size: " + str(backData[0]))
            return backData[0]
        else:
            return 0

    def MFRC522_Init(self):
        GPIO.output(self.RESET_PIN, 1)
        self.MFRC522_Reset()

        self.Write_MFRC522(self.TModeReg, 0x8D)
        self.Write_MFRC522(self.TPrescalerReg, 0x3E)
        self.Write_MFRC522(self.TReloadRegL, 30)
        self.Write_MFRC522(self.TReloadRegH, 0)
        self.Write_MFRC522(self.TxAutoReg, 0x40)
        self.Write_MFRC522(self.ModeReg, 0x3D)
        self.AntennaOn()

if __name__ == "__main__":
    RFIDReader = RFID()

    continue_reading = True

    while continue_reading:
        # scan for cards
        (status, TagType) = RFIDReader.MFRC522_Request(RFIDReader.PICC_REQIDL)

        # If a card is found
        if status == RFIDReader.MI_OK:
            print ("card detected")

        # Get the UID of the card
        (status, uid) = RFIDReader.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == RFIDReader.MI_OK:
            # Print UID
            print("Card read UID: %s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3]))

            # This is the default key for authentication
            key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

            # Select the scanned tag
            RFIDReader.MFRC522_SelectTag(uid)

            # Authenticate
            status = RFIDReader.MFRC522_Auth(RFIDReader.PICC_AUTHENT1A, 8, key, uid)

            # Check if authenticated
            if status == RFIDReader.MI_OK:
                RFIDReader.MFRC522_Read(8)
                RFIDReader.MFRC522_StopCrypto1()
            else:
                print("Authentication error")
