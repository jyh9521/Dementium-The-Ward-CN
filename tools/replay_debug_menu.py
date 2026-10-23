"""Offline exact-instruction debug-input and menu replay; never starts a process.

OS polling, graphics, sound and effect callbacks are not executed. Native menu
selection and action dispatch execute against bounded synthetic objects.
"""
import hashlib
import itertools
import struct

import pefile
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_RDI, UC_X86_REG_RBX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RBP, UC_X86_REG_RSI
from research_debug_menu import Investigation
from debug_menu import original_guard, rollback_debug


class DebugReplay(Investigation):
    def __init__(self, data, base=0x140000000, restored=False):
        pe = pefile.PE(data=data)
        pe.relocate_image(base)
        self.image = pe.get_memory_mapped_image()
        self.base, self.restored = base, restored
        pe.close()

    def opening(self, gate, held, pressed, request=0, busy=0, machine=None):
        u = machine or self.machine()
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
                self.ret(uc)
            elif rva == 0xbbcb0:
                calls.append(hex(uc.reg_read(UC_X86_REG_RDX) - manager))
                uc.emu_stop()
        hook = u.hook_add(UC_HOOK_CODE, boundary)
        self.call(u, 0xc0d40, obj, inputs, allow_boundary_stop=True)
        u.hook_del(hook)
        if u.reg_read(UC_X86_REG_RIP) not in (self.base + 0xbbcb0, 0x300f0000):
            raise ValueError('Opening replay unexpected termination')
        opened = '0x4f60' in calls
        combo = bool(held & 0x10000 and pressed & 0x80)
        f1 = bool(pressed & 0x40000)
        expected = not busy and (request or (gate and (combo or f1)) or (self.restored and f1))
        if opened != bool(expected):
            raise ValueError('Opening replay truth table mismatch')
        return dict(gate=gate, held=hex(held), pressed=hex(pressed), request=request,
                    busy=busy, opened_debug=opened, activation_offsets=calls)

    def key_event(self, u, key, down):
        self.call(u, 0xf8e50, key, down)
        return int.from_bytes(u.mem_read(self.base + 0x3fc3f8, 8), 'little')

    def raw_bridge(self, u, raw, gamepad=0):
        """Native held/one-shot/neutral-stick merge and final raw-object store.

        Captured gamepad bits replace the earlier polling stage. Mouse position
        normalization and function epilogue are intentionally not executed.
        """
        driver = 0x30070000
        u.mem_write(raw, bytes(40))
        for register, value in [(UC_X86_REG_RDI, driver), (UC_X86_REG_RBP, 0),
                                (UC_X86_REG_RBX, gamepad)]:
            u.reg_write(register, value)
        u.emu_start(self.base + 0x3ed86, self.base + 0x3eef6, count=1000)
        if u.reg_read(UC_X86_REG_RIP) != self.base + 0x3eef6:
            raise ValueError('Native raw keyboard/gamepad merge did not finish')
        u.reg_write(UC_X86_REG_RSI, raw)
        u.emu_start(self.base + 0x3f00a, self.base + 0x3f00d, count=2)
        return int.from_bytes(u.mem_read(raw, 8), 'little')

    def raw_bridge_cases(self):
        rows = []
        for held, gamepad in itertools.product((0, 4, 1 << 48, (1 << 48) | 4), (0, 1 << 14, (1 << 14) | 4)):
            u = self.machine()
            self.number(u, self.base + 0x3fc3f8, held, 8)
            merged = self.raw_bridge(u, 0x30050000, gamepad)
            if merged != held | gamepad:
                raise ValueError('Native raw bridge truth table mismatch')
            rows.append(dict(keyboard=hex(held), gamepad=hex(gamepad), raw=hex(merged)))
        return rows

    def lifecycle(self, layout=0, busy_pattern=(0, 0, 0, 0, 0)):
        u = self.machine()
        raw, action, state = 0x30050000, 0x30050100, 0x30050200
        rows = []
        self.number(u, self.base + 0x39627c, layout << 18)
        enum = self.call(u, 0x1f1210, 0x70)
        if enum != 0x1c:
            raise ValueError('F1 VK conversion changed')
        # Preserve raw bit 2 (Y) while F1 changes raw48; request latch stays zero.
        self.number(u, self.base + 0x3fc3f8, 4, 8)
        for index, (event, down) in enumerate([('down', 1), ('repeat', 1), ('up', 0), ('down-again', 1), ('up-again', 0)]):
            bits = self.key_event(u, enum, down)
            if bits != 4 | ((1 << 48) if down and self.restored else 0):
                raise ValueError('F1 raw-bit preservation mismatch')
            if u.mem_read(self.base + 0x3fc416, 1)[0]:
                raise ValueError('F1 unexpectedly latched a queued request')
            merged = self.raw_bridge(u, raw)
            if merged != bits:
                raise ValueError('Native raw bridge lost F1/other held bits')
            # Run original prologue, B6C00 call, and edge arithmetic together.
            for register, value in [(UC_X86_REG_RSP, 0x30200008),
                                    (UC_X86_REG_RCX, state), (UC_X86_REG_RDX, raw)]:
                u.reg_write(register, value)
            u.emu_start(self.base + 0xbb6e0, self.base + 0xbb74e, count=1000)
            if u.reg_read(UC_X86_REG_RIP) != self.base + 0xbb74e:
                raise ValueError('Native raw/action/edge fragment did not finish')
            held = int.from_bytes(u.mem_read(state + 0x40, 4), 'little')
            pressed = int.from_bytes(u.mem_read(state + 0x44, 4), 'little')
            result = self.opening(0, held, pressed, busy=busy_pattern[index], machine=u)
            expected = self.restored and not busy_pattern[index] and event in ('down', 'down-again')
            if result['opened_debug'] != expected:
                raise ValueError('F1 rising-edge lifecycle mismatch')
            rows.append(dict(event=event, layout=layout, physical_vk='0x70', kore_key=hex(enum), busy=busy_pattern[index], raw=hex(bits), held=hex(held), pressed=hex(pressed),
                             opened_debug=result['opened_debug'], request_latch=0))
        return rows

    def ordinary_keys(self):
        rows = []
        for layout in (0, 1):
            for vk, down in itertools.product((0x09, 0x4d, 0x52, 0x5a, 0x58, 0x0d, 0x1b, 0x25, 0x26, 0x27, 0x28, 0x10, 0x11, 0x12), (0, 1)):
                u = self.machine()
                self.number(u, self.base + 0x39627c, layout << 18)
                self.number(u, self.base + 0x3fc3f8, 0x12345, 8)
                enum = self.call(u, 0x1f1210, vk)
                raw = self.key_event(u, enum, down)
                rows.append(dict(layout=layout, vk=hex(vk), down=down, raw=hex(raw),
                                 request=u.mem_read(self.base + 0x3fc416, 1)[0]))
        return rows

    def native_menu(self):
        """Run original dispatch/navigation with effect callbacks replaced by recorders."""
        rows = []
        for pressed, selected, expected_selected, expected_modes in [
                (8, 1, 1, [-1]), (4, 1, 1, [1]), (0x40, 1, 1, [1]),
                (1, 1, 0, [0, 0]), (2, 1, 2, [0, 0]),
                (1, 0, 3, [0, 0, 0, 0]), (2, 3, 0, [0, 0, 0, 0]),
                (0x200, 1, 1, [])]:
            u = self.machine()
            obj, inputs, table, text, callback = 0x30020000, 0x30010000, 0x30060000, 0x30061000, 0x30062000
            self.number(u, self.base + 0x3fc468, 0x30000000, 8)
            self.number(u, self.base + 0x3a5348, 0x30030000, 8)
            self.number(u, obj + 0xd58, 4, 1)
            self.number(u, obj + 0xd5a, selected, 1)
            self.number(u, obj + 0xd20, table, 8)
            for index in range(4):
                self.number(u, table + index * 16, text, 8)
                self.number(u, table + index * 16 + 8, callback + index * 16, 8)
            u.mem_write(text, b'fixture\0')
            self.number(u, inputs + 4, pressed)
            calls, sounds, activations = [], [], []
            def boundary(uc, address, size, user):
                rva = address - self.base
                if rva in (0xfd620, 0xfd730):
                    sounds.append(hex(rva))
                    self.ret(uc)
                elif rva == 0xbbcb0:
                    activations.append(hex(uc.reg_read(UC_X86_REG_RDX) - 0x30000000))
                    self.ret(uc)
                elif callback <= address < callback + 64:
                    mode = uc.reg_read(UC_X86_REG_RCX) & 0xffffffff
                    mode = mode if mode < 0x80000000 else mode - 0x100000000
                    calls.append(dict(row=(address - callback)//16, mode=mode))
                    uc.mem_write(uc.reg_read(UC_X86_REG_RDX), b'fixture\0')
                    self.ret(uc)
            u.hook_add(UC_HOOK_CODE, boundary)
            self.call(u, 0xc75d0, obj, r8=inputs)
            actual = u.mem_read(obj + 0xd5a, 1)[0]
            if actual != expected_selected or [c['mode'] for c in calls] != expected_modes:
                raise ValueError(f'Native menu dispatch or navigation mismatch: {pressed:x} selected={actual} calls={calls}')
            if activations != (['0x15a8'] if pressed == 0x200 else []) or len(sounds) != (2 if pressed == 0x200 else 0):
                raise ValueError('Native menu back activation mismatch')
            rows.append(dict(pressed=hex(pressed), before=selected, after=actual, callback_boundaries=calls,
                             sound_boundaries=sounds, activation_offsets=activations, returned_normally=True))
        return rows


def verify_debug(original_bytes, modified_bytes, recipe):
    original_guard(original_bytes)
    # Inverse identity validates every changed byte and section before emulation.
    rollback_debug(modified_bytes, recipe)
    results = []
    for base in (0x140000000, 0x180000000):
        pair = [DebugReplay(original_bytes, base), DebugReplay(modified_bytes, base, True)]
        ordinary = [p.ordinary_keys() for p in pair]
        if ordinary[0] != ordinary[1]:
            raise ValueError('Non-F1 keyboard behavior changed')
        native = [p.native_menu() for p in pair]
        if native[0] != native[1]:
            raise ValueError('Native menu navigation changed')
        for replay in pair:
            cases = [replay.opening(g, h, p, q, b)
                     for g, (h, p), q, b in itertools.product((0, 1),
                     [(0, 0), (0x10000, 0), (0, 0x80), (0x10000, 0x80), (0, 0x40000)], (0, 1), (0, 1))]
            results.append(dict(base=hex(base), variant='modified' if replay.restored else 'baseline',
                opening_cases=cases, f1_lifecycle=replay.lifecycle(),
                f1_layout1_lifecycle=replay.lifecycle(layout=1), raw_bridge_cases=replay.raw_bridge_cases(),
                f1_busy_lifecycle=replay.lifecycle(busy_pattern=(1, 0, 0, 0, 0)),
                ordinary_key_cases=len(ordinary[0]), native_menu=native[int(replay.restored)],
                sequence=replay.sequence(), startup_keyboard_emulator=replay.startup_disable(),
                mapping=replay.mapping(), xinput_mapping=replay.xinput_mapping()))
    return dict(schema=1, status='PASS', results=results, game_launched=False,
        steam_directory_modified=False, original_sha256=hashlib.sha256(original_bytes).hexdigest(),
        modified_sha256=hashlib.sha256(modified_bytes).hexdigest(),
        boundary_doubles=['sound stop/play', 'screen activation', 'menu effect callbacks'],
        limits=['Offline synthetic manager/input/menu objects only',
                'No physical keyboard/controller polling, UI render, save or gameplay effect acceptance',
                'Raw bridge executes 3ED86..3EEF6 + 3F00A store with neutral synthetic stick; earlier gamepad polling and mouse normalization are not executed',
                'Native input mapping/edge executes BB6E0..BB74E; later screen callbacks are not executed'])
