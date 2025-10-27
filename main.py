import time
from bluepy.btle import Peripheral, UUID
from bluepy.btle import Scanner, DefaultDelegate

AUTO_CONNECT = True
TARGET_SVC_UUID = 0x180D
TARGET_CHARACTERISTIC_UUID = 0x2A37

class NotificationDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        print(data[1])

def find_addr(auto_connect, target_svc_uuid):
    '''
    Find the BLE devices, and it will return the device MAC address

    if [auto_connect] set, it will find the BLE device which provide the [target_svc_uuid]
    service and return its device directly.

    Otherwise, it will show all BLE device and the user should enter the numberto choose.
    '''
    target_svc_uuid_str = hex(target_svc_uuid)[2:]

    scanner = Scanner()
    devices = scanner.scan(5.0)

    addr = ""

    if not auto_connect:
        '''
        It will show all BLE devices.
        The user should input the number to choose BLE MAC
        '''
        addrs = []
        num = 0
        for dev in devices:
            addrs.append(dev.addr)
            print("="*20)
            print(num)
            print(f"Device {dev.addr}({dev.addrType}), RSSI={dev.rssi} dB")
            for (adtype, desc, value) in dev.getScanData():
                print(f"{desc} = {value}")
                if target_svc_uuid_str in value:
                    print('*'*50)
            addr = dev.addr
            print("="*20)
            num += 1
        num = input("Number:")
        num = int(num)
        addr = addrs[num]

    else:
        '''
        It will choose the BLE device which contain 0x180D service
        Directly return its BLE MAC adderess
        '''
        for dev in devices:
            show = False
            for (adtype, desc, value) in dev.getScanData():
                if target_svc_uuid_str in value:
                    show = True

            if show:
                print("="*20)
                print(f"Device {dev.addr}({dev.addrType}), RSSI={dev.rssi} dB")
                for (adtype, desc, value) in dev.getScanData():
                    print(f"{desc} = {value}")
                addr = dev.addr
                print("="*20)
                break

    return addr

def controlCCCDNotification(ch, switch_on):
    '''
    if switch_on is true, it will set CCCD to enable notification, vice versa.
    '''
    if switch_on:
        target = b"\x01\x00"
    else:
        target = b"\x00\x00"

    cccd = ch.getDescriptors(forUUID=0x2902)

    if len(cccd) == 0:
        print("No CCCD descriptor")
    else:
        print("================ Change CCCD value =========================")
        print("CCCD: ", cccd[0])

        value = cccd[0].read()
        print("CCCD original value:", value)

        print(f"Write", target, 'to CCCD')
        cccd[0].write(target)
        time.sleep(0.5)

        print('CCCD new value:', cccd[0].read())
        print("============================================================")



if __name__ == '__main__':
    '''
    Find the BLE device(GATT Server) which provide Heart Rate Service.
    Connect it and set CCCD value to 0x01 to open the notification.
    After receiving about 10 data then set CCCD value to disable notifications
    It will resuming receiving(set CCCD to 0x01 again) data after 5 seconds.

    This experiment can proof that our Raspberry Pi 3(GATT Client) can modify
    CCCD values.

    '''
    
    addr = find_addr(AUTO_CONNECT, TARGET_SVC_UUID)
    print(f"addr:{addr}.")

    if addr != "":
        dev = Peripheral(addr, 'random')
        dev.setDelegate(NotificationDelegate())

        svc = dev.getServiceByUUID(UUID(TARGET_SVC_UUID))
        print ("Service: ", str(svc), svc.uuid)

        for ch in svc.getCharacteristics():
            print(ch, ch.uuid)

        ch = svc.getCharacteristics(forUUID=TARGET_CHARACTERISTIC_UUID)[0]
        controlCCCDNotification(ch, True)

        counter = 0
        while True:
            if counter == 10:
                controlCCCDNotification(ch, False)
            elif counter == 15:
                controlCCCDNotification(ch, True)
            counter += 1

            if dev.waitForNotifications(1.0):
                continue

        dev.disconnect()
        time.sleep(1)
    else:
        print("Not found")
