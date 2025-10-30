from bluepy.btle import Peripheral, Scanner, DefaultDelegate, UUID, BTLEException

# 請視情況調整 UUID 與使用的範圍
SERVICE_UUID = UUID(0x180D)      # 這是標準的 Device Information Service
CHAR_UUID = UUID(0x2A37)        # 這是 Manufacturer Name String
CCCD_UUID = UUID(0x2902)        # 標準 CCCD

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        super().__init__()

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

class MyDelegate(DefaultDelegate):
    def __init__(self, char_handle):
        super().__init__()
        self.char_handle = char_handle

    def handleNotification(self, cHandle, data):
        if cHandle == self.char_handle:
            print(f"> Characteristic Value Changed: {data} (hex: {data.hex()})")

def main():
    scanner = Scanner().withDelegate(ScanDelegate())
    print("Scanning for devices (10s)...")
    devices = scanner.scan(10.0)
    addr_list = []
    for idx, dev in enumerate(devices):
        print(f"{idx}: Device {dev.addr} ({dev.addrType}), RSSI={dev.rssi} dB")
        addr_list.append(dev.addr)
        for (adtype, desc, value) in dev.getScanData():
            print(f"   {desc} = {value}")
    number = input('Enter your device number: ')
    num = int(number)
    device_mac = addr_list[num]
    print(f"Connecting to {device_mac} ...")

    dev = None
    try:
        dev = Peripheral(device_mac, 'random')  # 假設 BLE Tool 使用 random address
        print("Connected.")

        svc = dev.getServiceByUUID(SERVICE_UUID)
        ch = None
        for characteristic in svc.getCharacteristics():
            print(f"Characteristic UUID: {characteristic.uuid}")
            if characteristic.uuid == CHAR_UUID:
                ch = characteristic
        if not ch:
            print("Characteristic not found.")
            return
        
        dev.withDelegate(MyDelegate(ch.getHandle()))

        descriptors = ch.getDescriptors(forUUID=CCCD_UUID)
        if not descriptors:
            print("CCCD not found.")
            return
        cccd = descriptors[0]

        cccd_val = cccd.read()
        print(f"Current CCCD: 0x{cccd_val.hex()} (int: {int.from_bytes(cccd_val, 'little')})")

        # 讓user輸入CCCD設定
        while True:
            cccd_choice = int(input("請輸入要寫入的CCCD值（0=關閉, 1=Notification, 2=Indication）："))
            if cccd_choice == 0:
                write_val = b'\x00\x00'
            elif cccd_choice == 1:
                write_val = b'\x01\x00'
            elif cccd_choice == 2:
                write_val = b'\x02\x00'
            else:
                continue

            cccd.write(write_val, withResponse=True)
            print(f"Written {write_val.hex()} to CCCD.")

            cccd_val_after = cccd.read()
            print(f"CCCD after write: 0x{cccd_val_after.hex()} (int: {int.from_bytes(cccd_val_after, 'little')})")

            if cccd_choice in (1, 2):
                print("等待 server 傳送變動資料（按 Ctrl+C 結束）...")
                try:
                    while True:
                        if dev.waitForNotifications(5.0): # 最多等待5秒，期間有收到就自動回呼 handleNotification
                            continue
                        print(".", end="", flush=True)
                except KeyboardInterrupt:
                    print("\n結束監聽 notifications/indications。")
                break


    except BTLEException as e:
        print(f"Bluetooth error: {e}")
    finally:
        if dev:
            dev.disconnect()
            print("Disconnected.")

if __name__ == '__main__':
    main()
