#!/usr/bin/env python3
import sys, struct
from pathlib import Path

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u64(b,o): return struct.unpack_from('<Q',b,o)[0]

def main(path):
    p=Path(path); b=p.read_bytes()
    if b[:2] != b'MZ': raise SystemExit('not MZ')
    pe=u32(b,0x3c)
    if b[pe:pe+4] != b'PE\0\0': raise SystemExit('not PE')
    coff=pe+4
    machine=u16(b,coff); nsec=u16(b,coff+2); optsz=u16(b,coff+16)
    opt=coff+20; magic=u16(b,opt)
    entry=u32(b,opt+16); imagebase=u64(b,opt+24) if magic==0x20b else u32(b,opt+28)
    section_align=u32(b,opt+32); file_align=u32(b,opt+36); image_size=u32(b,opt+56); subsystem=u16(b,opt+68); dllchars=u16(b,opt+70)
    print(f'file={p} size={len(b)}')
    print(f'machine=0x{machine:04X} sections={nsec} optional=0x{magic:04X} entryRVA=0x{entry:X}')
    print(f'imageBase=0x{imagebase:X} imageSize=0x{image_size:X} subsystem={subsystem} dllChars=0x{dllchars:04X}')
    print(f'sectionAlign=0x{section_align:X} fileAlign=0x{file_align:X}')
    sh=opt+optsz
    secs=[]
    for i in range(nsec):
        o=sh+40*i; name=b[o:o+8].split(b'\0',1)[0].decode('ascii','replace')
        vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8); ch=u32(b,o+36)
        secs.append((name,va,vs,rp,rs,ch))
        print(f'section {name}: RVA=0x{va:X} VS=0x{vs:X} raw=0x{rp:X}+0x{rs:X} chars=0x{ch:08X}')
    # Data directories: import=1, IAT=12
    dd=opt+112
    imp_rva,imp_sz=struct.unpack_from('<II',b,dd+8)
    iat_rva,iat_sz=struct.unpack_from('<II',b,dd+8*12)
    print(f'importDir=0x{imp_rva:X}/0x{imp_sz:X} IAT=0x{iat_rva:X}/0x{iat_sz:X}')
    def rva_to_off(rva):
        for _,va,vs,rp,rs,_ in secs:
            if va <= rva < va+max(vs,rs): return rp+(rva-va)
        if rva < len(b): return rva
        raise ValueError(hex(rva))
    if imp_rva:
        print('imports:')
        o=rva_to_off(imp_rva)
        while True:
            oft,ts,fc,name_rva,ft=struct.unpack_from('<IIIII',b,o)
            if not any((oft,ts,fc,name_rva,ft)): break
            no=rva_to_off(name_rva); end=b.index(0,no); dll=b[no:end].decode('ascii','replace')
            print(' ',dll)
            thunk=oft or ft; to=rva_to_off(thunk)
            while True:
                val=u64(b,to)
                if val==0: break
                if val>>63:
                    print('    ordinal',val&0xffff)
                else:
                    hn=rva_to_off(val); fn0=hn+2; end=b.index(0,fn0); print('   ',b[fn0:end].decode('ascii','replace'))
                to+=8
            o+=20

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: inspect_pe.py file.exe')
    main(sys.argv[1])
