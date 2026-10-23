"""Read-only, exact-build debug-menu branch investigation. Never launches a target.

Only isolated PE instructions run in Unicorn. Sound and screen-activation calls
are explicit boundary doubles, not evidence of rendering or a running game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_RAX, UC_X86_REG_RCX,
    UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP, UC_X86_REG_RIP,
    UC_X86_REG_R12, UC_X86_REG_RDI, UC_X86_REG_RBP, UC_X86_REG_R10,
    UC_X86_REG_RBX, UC_X86_REG_ECX, UC_X86_REG_XMM10, UC_X86_REG_XMM11)
from runtime_patch import ORIGINAL_SHA256, ORIGINAL_SIZE
from workspace_io import validate_output_tree

ROOT = Path(__file__).resolve().parents[1]


class Investigation:
    def __init__(self, data, base=0x140000000):
        if len(data) != ORIGINAL_SIZE or hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
            raise ValueError('Unsupported original executable identity')
        pe = pefile.PE(data=data)
        pe.relocate_image(base)
        self.image = pe.get_memory_mapped_image()
        self.base = base
        pe.close()

    def machine(self):
        u = Uc(UC_ARCH_X86, UC_MODE_64)
        u.mem_map(self.base, (len(self.image) + 4095) & ~4095)
        u.mem_write(self.base, self.image)
        u.mem_map(0x30000000, 0x300000)
        return u

    @staticmethod
    def number(u, address, value, size=4):
        u.mem_write(address, value.to_bytes(size, 'little'))

    @staticmethod
    def ret(u):
        stack = u.reg_read(UC_X86_REG_RSP)
        address = int.from_bytes(u.mem_read(stack, 8), 'little')
        u.reg_write(UC_X86_REG_RSP, stack + 8)
        u.reg_write(UC_X86_REG_RIP, address)

    def call(self, u, rva, rcx=0, rdx=0, r8=0, allow_boundary_stop=False):
        stack, stop = 0x30200008, 0x300f0000
        self.number(u, stack, stop, 8)
        for register, value in [(UC_X86_REG_RSP, stack), (UC_X86_REG_RCX, rcx),
                                (UC_X86_REG_RDX, rdx), (UC_X86_REG_R8, r8)]:
            u.reg_write(register, value)
        u.emu_start(self.base + rva, stop, count=100000)
        if not allow_boundary_stop and u.reg_read(UC_X86_REG_RIP) != stop:
            raise ValueError('Native replay instruction limit or unexpected stop')
        return u.reg_read(UC_X86_REG_RAX)

    def open_case(self, gate, held, pressed, request=0, busy=0):
        u = self.machine()
        manager, inputs, obj = 0x30000000, 0x30010000, 0x30020000
        self.number(u, self.base + 0x3a5348, 0x30030000, 8)
        self.number(u, self.base + 0x3fc468, manager, 8)
        for address, value in [(self.base + 0x3fc398, gate),
                               (self.base + 0x3fc416, request), (manager + 0x64, busy)]:
            self.number(u, address, value, 1)
        self.number(u, inputs, held)
        self.number(u, inputs + 4, pressed)
        calls = []

        def boundary(uc, address, size, user):
            rva = address - self.base
            if rva in (0xfd620, 0xfd730):
                calls.append(hex(rva))
                self.ret(uc)
            elif rva == 0xbbcb0:
                calls.append({'screen_offset': hex(uc.reg_read(UC_X86_REG_RDX) - manager)})
                uc.emu_stop()
        u.hook_add(UC_HOOK_CODE, boundary)
        self.call(u, 0xc0d40, obj, inputs, allow_boundary_stop=True)
        if u.reg_read(UC_X86_REG_RIP) not in (self.base + 0xbbcb0, 0x300f0000):
            raise ValueError('Unexpected opening branch termination')
        opened = any(isinstance(c, dict) and c['screen_offset'] == '0x4f60' for c in calls)
        expected = not busy and (request or (gate and ((held & 0x10000 and pressed & 0x80) or pressed & 0x40000)))
        if opened != bool(expected):
            raise ValueError('Opening truth table mismatch')
        return dict(gate=gate, held=hex(held), pressed=hex(pressed), request=request,
                    busy=busy, opened_debug=opened, boundary_calls=calls)

    def sequence(self):
        u = self.machine()
        obj, inputs = 0x30020000, 0x30010000
        sounds, trace = [], []

        def boundary(uc, address, size, user):
            if address == self.base + 0xfd730:
                sounds.append(hex(uc.reg_read(UC_X86_REG_RDX)))
                self.ret(uc)
        u.hook_add(UC_HOOK_CODE, boundary)
        for turn in range(2):
            for character in 'TTSSLRLRST':
                mask = {'T': 0x80, 'S': 0x100, 'L': 0x1000, 'R': 0x2000}[character]
                self.number(u, inputs + 4, mask)
                self.call(u, 0xcf730, obj, r8=inputs)
                trace.append(dict(turn=turn, character=character,
                    progress=int.from_bytes(u.mem_read(obj + 0x15c, 4), 'little'),
                    gate=u.mem_read(self.base + 0x3fc398, 1)[0]))
            if trace[-1]['gate'] != 1 - turn:
                raise ValueError('Secret sequence did not toggle the gate')
        if sounds != ['0x1000069'] * 2:
            raise ValueError('Unexpected sequence sound dispatch')
        return dict(trace=trace, sound_boundary_calls=sounds)

    def mapping(self):
        u = self.machine()
        raw, result = 0x30010000, 0x30020000
        rows = []
        for bit in range(64):
            u.mem_write(raw, bytes(40))
            self.number(u, raw, 1 << bit, 8)
            self.call(u, 0xb6c00, result, raw)
            rows.append(hex(int.from_bytes(u.mem_read(result, 4), 'little')))
        expected = {2: 0x80, 3: 0x100, 8: 0x1000, 9: 0x2000,
                    14: 0x10000, 48: 0x40000, 25: 0x40, 26: 0x200,
                    27: 1, 28: 2, 29: 8, 30: 4}
        if any(int(rows[bit], 16) != mask for bit, mask in expected.items()):
            raise ValueError('Raw/action input mapping mismatch')
        keys = {}
        for vk in [0x70, 0x09, 0x4d, 0x52, 0x5a, 0x58, 0x0d, 0x1b,
                   0x25, 0x26, 0x27, 0x28, 0x10, 0x11, 0x12]:
            keys[hex(vk)] = hex(self.call(u, 0x1f1210, vk))
        if keys['0x70'] != '0x1c' or keys['0x4d'] != '0x75':
            raise ValueError('Physical VK conversion mismatch')
        return dict(raw_single_bit_to_action=rows, vk_to_kore=keys)

    def xinput_mapping(self):
        """Feed captured values between original stages; no XInput/OS calls."""
        u = self.machine()
        stack, driver, raw, result = 0x30200008, 0x30000000, 0x30001000, 0x30002000
        jump_table = struct.unpack('<16I', u.mem_read(self.base + 0x22b7c8, 64))
        rows = []
        for bit in range(16):
            u.mem_write(self.base + 0xc1b1f4, struct.pack('<HBB', 1 << bit, 0, 0))
            for register, value in [(UC_X86_REG_R12, self.base), (UC_X86_REG_RDI, 0),
                                    (UC_X86_REG_RSP, stack),
                                    (UC_X86_REG_XMM10, 0x3f800000),
                                    (UC_X86_REG_XMM11, 0x41f00000)]:
                u.reg_write(register, value)
            u.emu_start(self.base + 0x22b4ce, self.base + 0x22b63e, count=10000)
            if u.reg_read(UC_X86_REG_RIP) != self.base + 0x22b63e:
                raise ValueError('XInput extraction stage did not finish')
            values = struct.unpack('<16f', u.mem_read(stack + 0x20, 64))
            indices = [i for i, value in enumerate(values) if value]
            enums = []
            u.mem_write(driver, bytes(0x500))
            for index in indices:
                u.emu_start(self.base + jump_table[index], self.base + 0x22b73c, count=20)
                if u.reg_read(UC_X86_REG_RIP) != self.base + 0x22b73c:
                    raise ValueError('Gamepad dispatch case did not finish')
                enum = u.reg_read(UC_X86_REG_ECX)
                enums.append(enum)
                u.reg_write(UC_X86_REG_R9, 1)
                self.call(u, 0x126310, driver, 0, enum)
            for register, value in [(UC_X86_REG_RDI, driver), (UC_X86_REG_RBP, 0),
                                    (UC_X86_REG_RCX, 0), (UC_X86_REG_R10, 0), (UC_X86_REG_RBX, 0)]:
                u.reg_write(register, value)
            u.emu_start(self.base + 0x3ebb5, self.base + 0x3ed86, count=10000)
            if u.reg_read(UC_X86_REG_RIP) != self.base + 0x3ed86:
                raise ValueError('Raw gamepad assembly stage did not finish')
            mask = u.reg_read(UC_X86_REG_RBX)
            u.mem_write(raw, bytes(40))
            self.number(u, raw, mask, 8)
            self.call(u, 0xb6c00, result, raw)
            action = int.from_bytes(u.mem_read(result, 4), 'little')
            rows.append(dict(wButtons=hex(1 << bit), enums=enums, raw=hex(mask), action=hex(action)))
        expected = {15: 0x80, 14: 0x100, 8: 0x1000, 9: 0x2000, 6: 0x10000}
        if any(int(rows[bit]['action'], 16) != mask for bit, mask in expected.items()):
            raise ValueError('Physical XInput mapping mismatch')
        return rows

    def keyboard_emulator(self):
        rows = []
        for enabled in (0, 1):
            for vk, field in [(0x53, 0x224), (0x41, 0x223), (0x51, 0x225),
                              (0x57, 0x226), (0x43, 0x22b)]:
                u = self.machine()
                driver = 0x30000000
                enum = self.call(u, 0x1f1210, vk)
                self.number(u, driver + 0x418, enabled, 1)
                self.call(u, 0x126330, driver, enum, 1)
                actual = u.mem_read(driver + field, 1)[0]
                if actual != enabled:
                    raise ValueError('Conditional keyboard emulation mismatch')
                rows.append(dict(enabled=bool(enabled), vk=hex(vk), field=hex(field), value=actual))
        return rows

    def startup_disable(self):
        u = self.machine()
        driver = 0x30000000
        self.number(u, driver, self.base + 0x3134c8, 8)
        self.number(u, driver + 0x418, 1, 1)
        u.reg_write(UC_X86_REG_R9, driver)
        u.reg_write(UC_X86_REG_RSP, 0x30200008)
        # Exact startup instructions call through the original relocated vtable
        # into the original setter. No function boundary double is installed.
        u.emu_start(self.base + 0xfa60a, self.base + 0xfa619, count=1000)
        if u.reg_read(UC_X86_REG_RIP) != self.base + 0xfa619 or u.mem_read(driver + 0x418, 1)[0] != 0:
            raise ValueError('Original startup did not disable keyboard emulation')
        return dict(before=1, after=0, call_rva='0xFA616', setter_rva='0xF8BC0', boundary_doubles=[])


def investigate(exe):
    data = exe.read_bytes()
    results = []
    for base in (0x140000000, 0x180000000):
        replay = Investigation(data, base)
        cases = [replay.open_case(g, h, p) for g in (0, 1)
                 for h, p in [(0, 0), (0x10000, 0), (0, 0x80), (0x10000, 0x80), (0, 0x40000)]]
        cases += [replay.open_case(0, 0, 0, request=1),
                  replay.open_case(1, 0, 0x40000, busy=1),
                  replay.open_case(0, 0, 0, request=1, busy=1)]
        results.append(dict(base=hex(base), opening_cases=cases,
                            sequence=replay.sequence(), mapping=replay.mapping(),
                            xinput_mapping=replay.xinput_mapping(),
                            conditional_keyboard_emulator=replay.keyboard_emulator(),
                            startup_keyboard_emulator=replay.startup_disable()))
    if exe.read_bytes() != data:
        raise ValueError('Input identity changed during investigation')
    return dict(schema=1, original_sha256=ORIGINAL_SHA256, results=results,
        game_launched=False, input_unchanged=True, executable_modified=False,
        boundary_doubles=['FD620 sound stop', 'FD730 sound play', 'BBCB0 activation request'],
        limits=['Not a live process or UI render test', 'Synthetic manager/input objects',
                'Sequence receives normalized actions, not proof of physical reachability',
                'XInput stages use explicit captured-value feeds; polling/thread/callback scaffolding not run',
                'Keyboard emulation is conditional; positive fixture does not enable it in a file',
                'Screen activation boundary does not execute screen transitions'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/debug-menu-research/replay.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('Research output must stay under repository build/')
    validate_output_tree(output.parent)
    report = investigate(args.exe.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if json.loads(output.read_text(encoding='utf-8')) != report:
        raise ValueError('Reopened report mismatch')
    print('DEBUG RESEARCH PASS bases=2 opening-cases=26 sequence-toggles=4 raw-bits=128 VK-cases=30 xinput-bit-cases=32 keyboard-mode-cases=20 startup-disable=2 input=unchanged executable-modified=false game-launched=false')


if __name__ == '__main__':
    main()
