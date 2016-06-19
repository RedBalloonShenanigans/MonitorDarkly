import binascii
import usb
import usb.core
import usb.util
import time
import struct
import traceback

DDC2BI3_VCP_PREFIX = '\xc2\x00\x00'

VENDOR_ID = 0x0424
PRODUCT_ID = 0x4060


class CommandBlock:
    """
    Class for building Command Block Wrapper (CBW) USB packets. See
    http://www.usb.org/developers/docs/devclass_docs/usbmassbulk_10.pdf
    for documentation.
    """

    def __init__(self, tag, transLen, flags, lun, cbStr):
        self._sig = "\x55\x53\x42\x43"
        self._tag = tag
        self._transLen = transLen
        self._flags = flags
        self._lun = lun
        self._cbLen = len(cbStr)
        self._cbStr = cbStr

    def ret_bin(self):
        resStr = self._sig + \
            struct.pack("<I", self._tag) + \
            struct.pack("<I", self._transLen) + \
            struct.pack('<B', self._flags) + \
            struct.pack("<B", self._lun) + \
            struct.pack("<B", self._cbLen) + \
            self._cbStr
        return resStr

    def __str__(self):
        return binascii.hexlify(self.ret_bin())


class USBI2CWritePacket:
    """
    Class for building a USB Mass Storage Bulk Write packet that sends an i2c write.
    """

    pak_type = '\x01'  # i2c write

    def __init__(self, unk_header, dest_addr, payload):
        self._dest_addr = struct.pack(">B", dest_addr)
        self._len_str = struct.pack(">B", len(payload))
        self._unk_header = unk_header
        self._payload = payload

    def toBytes(self):
        payload = self.pak_type + self._dest_addr + '\xc0\x00' + self._len_str \
            + self._unk_header + self._payload
        return payload


class USBI2CReadPacket:
    """
    Class for building a USB Mass Storage Bulk Read packet that reads i2c data.
    To get the response data, you need to send a CBW with the special 'i2c
    read' command.
    """

    pak_type = '\x02'  # i2c read

    def __init__(self, src_addr, pak_bytes):
        self._src_addr = struct.pack(">B", src_addr)
        self._bytes = struct.pack(">B", pak_bytes)

    def toBytes(self):
        payload = self.pak_type + self._src_addr + self._bytes + '\xc0\x00'
        return payload


class CommandPacket:
    """
    Class for building a DDC2Bi (i2c) packet that carries a GProbe payload.
    """

    def __init__(self, payload,
                 vcp_prefix=DDC2BI3_VCP_PREFIX):
        self._ddc_source = '\x51'       # as per gprobe documentation
        self._len_payload = chr(0x80 | (len(vcp_prefix) + len(payload)))
        self._vcp_prefix = vcp_prefix
        self._payload = payload
        self._checksum = self.chksum()

    def ddc2bi3_checksum(self, d):
        chksum = 0
        for i in d:
            i = ord(i)
            chksum = (chksum ^ i)
        return chksum

    def chksum(self):
        # per the DDC spec, we need to include the source address in the checksum
        cData = '\x6e' + self._ddc_source + self._len_payload + self._vcp_prefix + \
                self._payload
        return chr(self.ddc2bi3_checksum(cData))

    def toBytes(self):
        return self._ddc_source + self._len_payload + self._vcp_prefix + \
            self._payload + self._checksum


class CommandPayload:
    """
    Class for building a GProbe packet. See the GProbe documentation for
    details on the different command types.
    """

    def __init__(self, cmd_type, cmd_payload):
        self._cmd_type = cmd_type
        self._cmd_payload = cmd_payload
        self._cmd_len = len(cmd_type) + len(cmd_payload) + 2

    def toBytes(self):
        len_str = struct.pack(">B", self._cmd_len)
        return len_str + self._cmd_type + self._cmd_payload

VERBOSE = False


class Dell2410:
    """
    This class handles communication with the monitor over GProbe through USB.
    It includes most of the GProbe commands as methods that can be called to
    send them to the device. For example::

        dev = Dell2410() # opens a USB connection to the device
        dev.initialize() # sends commands to the device to initialize GProbe
        dev.debug_on() # must be done before sending any other commands
        print dev.reg_read(0xc800)
        dev.debug_off() # returns control to the firmware, so that e.g. buttons work
    """
    payload_len = 512
    scsi_cmd_opcode = "\xcf"
    padding_byte = "\xcc"

    def __init__(self, verbose=VERBOSE):
        self.verbose = verbose
        self.dev = None
        self._hook()

    def __del__(self):
        self._release()

    def _hook(self):
        try:
            self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        except Exception as e:
            if self.verbose:
                traceback.print_exc()
                print(e)
            raise Exception("USB error!")
        if self.dev is None:
            raise Exception("Could not hook dell monitor, please verify connection!")
        if self.verbose:
            print("USB handle:")
            print(self.dev)
        # Default kernel driver sometimes hooks it first
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)

    def _release(self):
        if self.dev is None:
            return
        import time
        time.sleep(2)
        try:
            usb.util.dispose_resources(self.dev)
        except Exception:
            pass

    def _parse_response(self, resp):
        print("\n\t%s\n" % (binascii.hexlify(resp)))
        r_code = resp[0]
        src_addr = resp[2]
        packet_len = resp[3] - 0x80
        vcp_content = resp[4:4 + packet_len]
        vcp_meat = vcp_content[3:]
        vcp_content_str = binascii.hexlify(vcp_meat)
        chksum = resp[4 + packet_len]
        print("\t[%02x] FRM: [%02x] LEN: [%02x] [%s] CHKSUM: [%02x]" % (
            r_code, src_addr, packet_len, vcp_content_str, chksum))

    def _print_response(self, resp):
        print("resp1: " + binascii.hexlify(resp[0]))
        self._parse_response(resp[1])
        print("resp3: " + binascii.hexlify(resp[2]))

    def _do_cmd(self, cmd_bytes):
        if self.verbose:
            print binascii.hexlify(cmd_bytes)

        payload_padd = self.payload_len - len(cmd_bytes)
        cmd_bytes = cmd_bytes + payload_padd * self.padding_byte

        # magic cmd block to send i2c request
        cb_send_i2c = self.scsi_cmd_opcode + "\x20" + '\x00' * 14
        cmd_send_i2c = CommandBlock(12, self.payload_len, 0x00, 0, cb_send_i2c)

        # magic cmd block to receive i2c response
        cb_recv_i2c = self.scsi_cmd_opcode + "\x21" + '\x00' * 14
        cmd_recv_i2c = CommandBlock(12, self.payload_len, 0x80, 0, cb_recv_i2c)

        # Timeout values should be at least 5000ms
        self.dev.write(0x2, cmd_send_i2c.ret_bin(), 5000)
        self.dev.write(0x2, cmd_bytes, 5000)
        usb_resp = self.dev.read(0x82, self.payload_len, 5000)

        self.dev.write(0x2, cmd_recv_i2c.ret_bin())
        i2c_data = self.dev.read(0x82, self.payload_len, 5000)
        usb_resp_2 = self.dev.read(0x82, self.payload_len, 5000)

        resp = (usb_resp, i2c_data, usb_resp_2)

        if self.verbose:
            self._print_response(resp)

        return i2c_data

    def _i2c_write(self, cmd_bytes, address, unk_header):
        data = USBI2CWritePacket(unk_header,
                                 address,
                                 cmd_bytes).toBytes()
        self._do_cmd(data)

    def _i2c_read(self, addr, num_bytes):
        packet = USBI2CReadPacket(addr, num_bytes)
        i2c_data = self._do_cmd(packet.toBytes())
        # the first two bytes of the response seems to be USB header
        return i2c_data[2:2 + num_bytes]

    def _send_ddc_cmd(self, unk_header, payload, *args):
        packet = CommandPacket(payload, *args)
        self._i2c_write(packet.toBytes(), 0x6e, unk_header)

    def _recv_ddc_resp(self, bytes):
        # 3 bytes for source + length + checksum
        resp = self._i2c_read(0x6f, bytes + 3)
        # strip off source + length + checksum
        # TODO verify checksum
        length = resp[1] & 0x7f
        return resp[2:2 + length]

    def _send_gprobe_cmd(self, unk_header, type, payload):
        packet = CommandPayload(type, payload)
        self._send_ddc_cmd(unk_header, packet.toBytes())

    def _recv_gprobe_resp(self, bytes=2):
        # 3 bytes for VCP prefix
        bytes = self._recv_ddc_resp(bytes + 3)
        # strip off VCP prefix
        return bytes[3:]

    def initialize(self):
        ready_cmd = '\x0f\xff'
        pad_len = self.payload_len - len(ready_cmd)
        is_ready_cmd = ready_cmd + self.padding_byte * pad_len
        # Send the ready1 command
        # This should return 0400*511
        val = self._do_cmd(is_ready_cmd)
        if self.verbose:
            self._print_response(val)
        time.sleep(0.03)
        # Send the ready2 command
        # This should return 0400*511
        self._send_ddc_cmd('\xb4', '\x6e\x0e', '\x6e\x0e\x03')
        # Recieve resp
        time.sleep(0.03)
        self._recv_ddc_resp(2)

    def gen_apps_test(self, tNum):
        """TODO: make this actually execute the command"""
        cp = CommandPacket('\x0a', CommandPayload('\x12', chr(tNum)).toBytes())
        return cp

    def gen_apps_param(self, index, val):
        """TODO: make this actually execute the command"""
        index -= 1
        cp = CommandPacket('\x19',
                           CommandPayload('\x11',
                                          chr(index) + struct.pack(">I", val)).toBytes())
        return cp

    def debug_on(self):
        self._send_gprobe_cmd('\xf9', '\x09', '')

    def debug_off(self):
        self._send_gprobe_cmd('\xf9', '\x0a', '')

    def execute(self, addr):
        self._send_gprobe_cmd('\x62', '\x1d', struct.pack(">H", addr))
        self._recv_gprobe_resp()

    def ram_write(self, address, byte):
        if len(byte) > 120:
            raise Exception('Not allowed to write more than 120 bytes: %d' % len(byte))
        self._send_gprobe_cmd('\x1a', '\x13', struct.pack(">H", address) + byte)
        self._recv_gprobe_resp()

    def flash_read(self, address, byte_count):
        self._send_gprobe_cmd('\x00', '\x1b', struct.pack(">H", address) +
                              struct.pack(">B", byte_count))

    def reg_read(self, address):
        self._send_gprobe_cmd('\x0a', '\x06', struct.pack(">H", address))
        resp = self._recv_gprobe_resp(6)
        return struct.pack('<BB', resp[5], resp[4])

    def reg_write(self, address, value):
        self._send_gprobe_cmd('\x0a', '\x07', struct.pack(">H", address) +
                              struct.pack(">H", value))

    def reset(self):
        self._send_gprobe_cmd('\xf9', '\x20', '\x00')
        time.sleep(0.5)
        self._recv_gprobe_resp()

    def reset_on(self):
        self._send_gprobe_cmd('\xf9', '\x20', '\x01')
        time.sleep(0.5)
        self._recv_gprobe_resp()

    def flash_erase(self):
        self._recv_gprobe_resp()
        self._send_gprobe_cmd('\x00', '\x19', '\xff\xff')
        time.sleep(0.5)

    def flash_id(self):
        self._send_gprobe_cmd('\x32', '\x1c', '\xff\x00\x00\x20\x00\x00')
        time.sleep(0.03)
        self._recv_gprobe_resp()
