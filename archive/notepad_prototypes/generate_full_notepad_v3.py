import struct, hashlib, os, subprocess, textwrap

IMAGE_BASE = 0x140000000
TEXT_RVA = 0x1000
RDATA_RVA = 0x3000
IDATA_RVA = 0x4000
BSS_RVA = 0x5000
FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000


def align(x,a): return (x+a-1)&~(a-1)

def u16(x): return struct.pack('<H', x & 0xffff)
def u32(x): return struct.pack('<I', x & 0xffffffff)
def u64(x): return struct.pack('<Q', x & 0xffffffffffffffff)
def s32(x): return struct.pack('<i', x)

# ---------------- RDATA ----------------
rdata = bytearray()
rsyms = {}
def add_bytes(name, b, align_to=1):
    while len(rdata)%align_to: rdata.append(0)
    rsyms[name] = RDATA_RVA + len(rdata)
    rdata.extend(b)
    return rsyms[name]
def wstr(name,s): return add_bytes(name, s.encode('utf-16le')+b'\0\0', 2)
def astr(name,s): return add_bytes(name, s.encode('ascii')+b'\0', 1)

wstr('class_static','STATIC')
wstr('class_edit','EDIT')
wstr('class_main','DirectPE_Notepad_Main')
wstr('title','Direct PE Notepad x64 — No Compiler')
wstr('empty','')
wstr('menu_file','&File')
wstr('menu_edit','&Edit')
wstr('menu_help','&Help')
wstr('m_new','&New')
wstr('m_open','&Open...')
wstr('m_save','&Save')
wstr('m_saveas','Save &As...')
wstr('m_exit','E&xit')
wstr('m_undo','&Undo')
wstr('m_cut','Cu&t')
wstr('m_copy','&Copy')
wstr('m_paste','&Paste')
wstr('m_selectall','Select &All')
wstr('m_about','&About')
wstr('open_title','Open text file')
wstr('save_title','Save text file as')
wstr('defext','txt')
# OPENFILENAME filter requires embedded NUL separators and double-NUL terminator.
add_bytes('filter', ('Text files (*.txt)\0*.txt\0All files (*.*)\0*.*\0\0').encode('utf-16le'), 2)
wstr('err_title','Direct PE Notepad')
wstr('err_open','Could not open or read the selected file.')
wstr('err_save','Could not save the file.')
wstr('err_large','The file is too large for this build (limit: about 1 MiB).')
wstr('err_decode','The file could not be decoded as UTF-8/ANSI text.')
wstr('about','Direct PE Notepad x64\r\n\r\nNative PE32+ and x86-64 machine code generated directly, without a C/C++ compiler, assembler, or linker.\r\n\r\nSupports New, Open, Save, Save As, Undo, Cut, Copy, Paste and Select All.')

# ---------------- BSS layout ----------------
bss_off = 0
bsyms = {}
def bss_alloc(name,size,align_to=8):
    global bss_off
    bss_off = align(bss_off,align_to)
    bsyms[name] = BSS_RVA + bss_off
    bss_off += size
    return bsyms[name]

bss_alloc('msg', 48, 16)
bss_alloc('ofn', 152, 16)
bss_alloc('current_path', 512*2, 16)
bss_alloc('temp_path', 512*2, 16)
bss_alloc('io_count', 8, 8)
bss_alloc('size_high', 4, 4)
bss_alloc('hwnd_edit', 8, 8)
bss_alloc('wc', 80, 16)
WIDE_CHARS = 1_048_576
MAX_FILE_BYTES = 1_048_000
BYTE_CAP = 4_194_304
bss_alloc('widebuf', WIDE_CHARS*2, 16)
bss_alloc('bytebuf', BYTE_CAP+16, 16)
BSS_VSIZE = align(bss_off, 0x1000)

# ---------------- IDATA ----------------
imports = {
    'KERNEL32.dll': [
        'ExitProcess','CreateFileW','ReadFile','WriteFile','CloseHandle','GetFileSize',
        'MultiByteToWideChar','WideCharToMultiByte','lstrcpyW','GetModuleHandleW'
    ],
    'USER32.dll': [
        'CreateWindowExW','GetMessageW','TranslateMessage','DispatchMessageW','IsWindow',
        'CreateMenu','CreatePopupMenu','AppendMenuW','GetWindowTextLengthW','GetWindowTextW',
        'SetWindowTextW','SendMessageW','MoveWindow','MessageBoxW','SetFocus',
        'RegisterClassExW','DefWindowProcW','PostQuitMessage','PostMessageW','LoadCursorW'
    ],
    'COMDLG32.dll': ['GetOpenFileNameW','GetSaveFileNameW'],
}

def build_idata():
    data=bytearray()
    dlls=list(imports)
    desc_off={dll:20*i for i,dll in enumerate(dlls)}
    data.extend(b'\0'*(20*(len(dlls)+1)))
    ilt_off={}
    for dll in dlls:
        while len(data)%8: data.append(0)
        ilt_off[dll]=len(data)
        data.extend(b'\0'*(8*(len(imports[dll])+1)))
    iat_off={}
    for dll in dlls:
        while len(data)%8: data.append(0)
        iat_off[dll]=len(data)
        data.extend(b'\0'*(8*(len(imports[dll])+1)))
    dllname_off={}
    for dll in dlls:
        dllname_off[dll]=len(data)
        data.extend(dll.encode('ascii')+b'\0')
    hn_off={}
    for dll in dlls:
        for fn in imports[dll]:
            if len(data)%2: data.append(0)
            hn_off[(dll,fn)] = len(data)
            data.extend(b'\0\0'+fn.encode('ascii')+b'\0')
    # patch thunks and descriptors
    iat_map={}
    for dll in dlls:
        for i,fn in enumerate(imports[dll]):
            rva = IDATA_RVA + hn_off[(dll,fn)]
            struct.pack_into('<Q',data,ilt_off[dll]+8*i,rva)
            struct.pack_into('<Q',data,iat_off[dll]+8*i,rva)
            iat_map[fn] = IDATA_RVA + iat_off[dll]+8*i
        struct.pack_into('<IIIII',data,desc_off[dll],
                         IDATA_RVA+ilt_off[dll],0,0,IDATA_RVA+dllname_off[dll],IDATA_RVA+iat_off[dll])
    first_iat=min(IDATA_RVA+o for o in iat_off.values())
    last_iat=max(IDATA_RVA+iat_off[d]+8*(len(imports[d])+1) for d in dlls)
    return data, iat_map, first_iat, last_iat-first_iat, 20*(len(dlls)+1)

idata, IAT, IAT_RVA, IAT_SIZE, IMPORT_DESC_SIZE = build_idata()

# ---------------- tiny direct machine-code emitter ----------------
REG={'rax':0,'rcx':1,'rdx':2,'rbx':3,'rsp':4,'rbp':5,'rsi':6,'rdi':7,
     'r8':8,'r9':9,'r10':10,'r11':11,'r12':12,'r13':13,'r14':14,'r15':15}

class E:
    def __init__(self): self.b=bytearray(); self.labels={}; self.fix=[]
    @property
    def off(self): return len(self.b)
    @property
    def rva(self): return TEXT_RVA+len(self.b)
    def emit(self,*xs):
        for x in xs:
            if isinstance(x,int): self.b.append(x&255)
            else: self.b.extend(x)
    def label(self,n): self.labels[n]=self.off
    def rel32(self,label): self.fix.append((self.off,label)); self.b.extend(b'\0\0\0\0')
    def jmp(self,l): self.emit(0xE9); self.rel32(l)
    def jcc(self,cc,l): self.emit(0x0F,cc); self.rel32(l)
    def call_label(self,l): self.emit(0xE8); self.rel32(l)
    def patch(self):
        for p,l in self.fix:
            if l not in self.labels: raise KeyError(l)
            rel=self.labels[l]-(p+4)
            struct.pack_into('<i',self.b,p,rel)
    def rex(self,w=0,r=0,x=0,b=0):
        v=0x40|(w<<3)|(r<<2)|(x<<1)|b
        if v!=0x40: self.emit(v)
    def lea_rip(self,reg,target_rva):
        rr=REG[reg]; self.rex(w=1,r=(rr>>3)&1); self.emit(0x8D, ((rr&7)<<3)|5)
        disp=target_rva-(self.rva+4)
        self.emit(s32(disp))
    def lea_label(self,reg,label):
        rr=REG[reg]; self.rex(w=1,r=(rr>>3)&1); self.emit(0x8D, ((rr&7)<<3)|5)
        self.rel32(label)
    def mov_r64_ripmem(self,reg,target_rva):
        rr=REG[reg]; self.rex(w=1,r=(rr>>3)&1); self.emit(0x8B, ((rr&7)<<3)|5)
        disp=target_rva-(self.rva+4)
        self.emit(s32(disp))
    def mov_ripmem_r64(self,target_rva,reg):
        rr=REG[reg]; self.rex(w=1,r=(rr>>3)&1); self.emit(0x89, ((rr&7)<<3)|5)
        disp=target_rva-(self.rva+4)
        self.emit(s32(disp))
    def call_iat(self,fn):
        self.emit(0xFF,0x15)
        disp=IAT[fn]-(self.rva+4)
        self.emit(s32(disp))
    def mov_r32_imm(self,reg,imm):
        rr=REG[reg]; self.rex(b=(rr>>3)&1); self.emit(0xB8+(rr&7),u32(imm))
    def mov_r64_r64(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(w=1,r=(s>>3)&1,b=(d>>3)&1); self.emit(0x89,0xC0|((s&7)<<3)|(d&7))
    def mov_r32_r32(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(r=(s>>3)&1,b=(d>>3)&1); self.emit(0x89,0xC0|((s&7)<<3)|(d&7))
    def xor32(self,reg):
        r=REG[reg]; self.rex(r=(r>>3)&1,b=(r>>3)&1); self.emit(0x31,0xC0|((r&7)<<3)|(r&7))
    def test64(self,reg):
        r=REG[reg]; self.rex(w=1,r=(r>>3)&1,b=(r>>3)&1); self.emit(0x85,0xC0|((r&7)<<3)|(r&7))
    def test32(self,reg):
        r=REG[reg]; self.rex(r=(r>>3)&1,b=(r>>3)&1); self.emit(0x85,0xC0|((r&7)<<3)|(r&7))
    def cmp_r32_imm(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x81,0xF8|(r&7),u32(imm))
    def and_r32_imm(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x81,0xE0|(r&7),u32(imm))
    def sub_r32_imm8(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x83,0xE8|(r&7),imm&255)
    def add_r64_imm8(self,reg,imm):
        r=REG[reg]; self.rex(w=1,b=(r>>3)&1); self.emit(0x83,0xC0|(r&7),imm&255)
    def shr_r32_imm8(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0xC1,0xE8|(r&7),imm&255)
    def cmp_rax_neg1(self): self.emit(0x48,0x83,0xF8,0xFF)
    def mov_mrsp_imm32(self,off,imm,qword=False):
        if qword: self.emit(0x48)
        self.emit(0xC7,0x44,0x24,off&255,u32(imm))
    def mov_mrsp_reg64(self,off,reg):
        r=REG[reg]; self.rex(w=1,r=(r>>3)&1); self.emit(0x89,0x44|((r&7)<<3),0x24,off&255)
    def mov_mrsp_reg32(self,off,reg):
        r=REG[reg]; self.rex(r=(r>>3)&1); self.emit(0x89,0x44|((r&7)<<3),0x24,off&255)
    def mov_mr12_imm32(self,off,imm):
        # [r12+disp8], imm32
        self.emit(0x41,0xC7,0x44,0x24,off&255,u32(imm))
    def mov_mr12_reg64(self,off,reg):
        r=REG[reg]; self.rex(w=1,r=(r>>3)&1,b=1); self.emit(0x89,0x44|((r&7)<<3),0x24,off&255)
    def mov_eax_mr12(self,off): self.emit(0x41,0x8B,0x44,0x24,off&255)
    def mov_rax_mr12(self,off): self.emit(0x49,0x8B,0x44,0x24,off&255)
    def cmp_mr12_rbx(self): self.emit(0x49,0x39,0x1C,0x24)
    def mov_word_ptr_reg_zero(self,reg):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x66,0xC7,0x00|(r&7),0,0)
    def cmp_word_ptr_reg_zero(self,reg):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x66,0x83,0x38|(r&7),0)
    def movzx_eax_word_ptr(self,reg):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x0F,0xB7,0x00|(r&7))
    def mov_eax_ptr(self,reg):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x8B,0x00|(r&7))
    def add_r64_r64(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(w=1,r=(s>>3)&1,b=(d>>3)&1); self.emit(0x01,0xC0|((s&7)<<3)|(d&7))
    def mov_word_index2_zero(self,base,index):
        # mov word ptr [base + index*2], 0 ; bases used low regs, index low
        b,i=REG[base],REG[index]
        self.rex(x=(i>>3)&1,b=(b>>3)&1)
        self.emit(0x66,0xC7,0x04,0x40|((i&7)<<3)|(b&7),0,0)

em=E()
# stack alignment + ample shadow/stack-arg area
em.emit(0x48,0x81,0xEC,u32(0x88))  # sub rsp, 0x88

# Register a REAL top-level window class.  V2 used the predefined STATIC class
# as the main window; STATIC's system wndproc is not an application frame wndproc,
# so synchronous WM_COMMAND/non-client messages never reached our queue handler.
em.xor32('rcx'); em.call_iat('GetModuleHandleW'); em.mov_r64_r64('r15','rax')
em.lea_rip('r12',bsyms['wc'])
em.mov_mr12_imm32(0,80)       # WNDCLASSEXW.cbSize
em.mov_mr12_imm32(4,3)        # CS_HREDRAW | CS_VREDRAW
em.lea_label('rax','wndproc'); em.mov_mr12_reg64(8,'rax')
em.mov_mr12_reg64(24,'r15')   # hInstance
em.xor32('rcx'); em.mov_r32_imm('rdx',32512); em.call_iat('LoadCursorW')  # IDC_ARROW
em.mov_mr12_reg64(40,'rax')
em.mov_mr12_imm32(48,6)       # (HBRUSH)(COLOR_WINDOW+1)
em.lea_rip('rax',rsyms['class_main']); em.mov_mr12_reg64(64,'rax')
em.mov_r64_r64('rcx','r12'); em.call_iat('RegisterClassExW')
em.test32('rax'); em.jcc(0x84,'exit')

# Menu creation helpers inline.
em.call_iat('CreateMenu'); em.mov_r64_r64('rdi','rax')
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r12','rax')

def append_imm(menu, flags, itemid, text_sym):
    em.mov_r64_r64('rcx',menu); em.mov_r32_imm('rdx',flags); em.mov_r32_imm('r8',itemid); em.lea_rip('r9',rsyms[text_sym]); em.call_iat('AppendMenuW')
def append_sep(menu):
    em.mov_r64_r64('rcx',menu); em.mov_r32_imm('rdx',0x800); em.xor32('r8'); em.xor32('r9'); em.call_iat('AppendMenuW')
def append_popup(main, sub, text_sym):
    em.mov_r64_r64('rcx',main); em.mov_r32_imm('rdx',0x10); em.mov_r64_r64('r8',sub); em.lea_rip('r9',rsyms[text_sym]); em.call_iat('AppendMenuW')

append_imm('r12',0,1001,'m_new'); append_imm('r12',0,1002,'m_open'); append_sep('r12')
append_imm('r12',0,1003,'m_save'); append_imm('r12',0,1004,'m_saveas'); append_sep('r12'); append_imm('r12',0,1005,'m_exit')
append_popup('rdi','r12','menu_file')

em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r13','rax')
append_imm('r13',0,1101,'m_undo'); append_sep('r13'); append_imm('r13',0,1102,'m_cut'); append_imm('r13',0,1103,'m_copy'); append_imm('r13',0,1104,'m_paste'); append_sep('r13'); append_imm('r13',0,1105,'m_selectall')
append_popup('rdi','r13','menu_edit')

em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r14','rax')
append_imm('r14',0,1201,'m_about'); append_popup('rdi','r14','menu_help')

# Parent custom top-level window
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_main']); em.lea_rip('r8',rsyms['title']); em.mov_r32_imm('r9',0x10CF0000)
em.mov_mrsp_imm32(0x20,0x80000000); em.mov_mrsp_imm32(0x28,0x80000000); em.mov_mrsp_imm32(0x30,900); em.mov_mrsp_imm32(0x38,650)
em.mov_mrsp_imm32(0x40,0,qword=True); em.mov_mrsp_reg64(0x48,'rdi'); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rbx','rax'); em.test64('rax'); em.jcc(0x84,'exit')
# Child EDIT
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50B110C4)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,884); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi')
# Increase edit text limit to ~1M chars
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',MAX_FILE_BYTES); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus')

# Message pump
em.label('msg_loop')
em.lea_rip('r12',bsyms['msg']); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.call_iat('GetMessageW')
em.test32('rax'); em.jcc(0x8E,'exit') # jle
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x8001); em.jcc(0x84,'command')  # WM_APP+1 posted by wndproc
em.jmp('dispatch')

em.label('on_size')
em.cmp_mr12_rbx(); em.jcc(0x85,'dispatch')
em.mov_eax_mr12(24); em.mov_r32_r32('r9','rax'); em.and_r32_imm('r9',0xFFFF); em.emit(0xC1,0xE8,0x10) # shr eax,16
em.mov_mrsp_imm32(0x20,0); # overwritten below with eax
# mov [rsp+20], eax
em.emit(0x89,0x44,0x24,0x20)
em.mov_mrsp_imm32(0x28,1,qword=True)
em.mov_r64_r64('rcx','rsi'); em.xor32('rdx'); em.xor32('r8'); em.call_iat('MoveWindow')
em.jmp('dispatch')

em.label('command')
em.mov_eax_mr12(16); em.and_r32_imm('rax',0xFFFF)
for cid,label in [(1001,'cmd_new'),(1002,'cmd_open'),(1003,'cmd_save'),(1004,'cmd_saveas'),(1005,'exit'),
                  (1101,'cmd_undo'),(1102,'cmd_cut'),(1103,'cmd_copy'),(1104,'cmd_paste'),(1105,'cmd_selectall'),(1201,'cmd_about')]:
    em.cmp_r32_imm('rax',cid); em.jcc(0x84,label)
em.jmp('dispatch')

em.label('cmd_new')
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rax',bsyms['current_path']); em.mov_word_ptr_reg_zero('rax'); em.jmp('msg_loop')

# Initialize OFN common fields macro
def emit_ofn(title_sym, flags):
    em.lea_rip('r12',bsyms['ofn']); em.mov_mr12_imm32(0,152); em.mov_mr12_reg64(8,'rbx')
    em.lea_rip('rax',rsyms['filter']); em.mov_mr12_reg64(24,'rax')
    em.mov_mr12_imm32(44,1)
    em.lea_rip('rax',bsyms['temp_path']); em.mov_mr12_reg64(48,'rax'); em.mov_mr12_imm32(56,512)
    em.lea_rip('rax',rsyms[title_sym]); em.mov_mr12_reg64(88,'rax'); em.mov_mr12_imm32(96,flags)
    em.lea_rip('rax',rsyms['defext']); em.mov_mr12_reg64(104,'rax')

em.label('cmd_open')
em.lea_rip('rax',bsyms['temp_path']); em.mov_word_ptr_reg_zero('rax')
em.emit(*[]) ; emit_ofn('open_title',0x00081804)
em.mov_r64_r64('rcx','r12'); em.call_iat('GetOpenFileNameW'); em.test32('rax'); em.jcc(0x84,'msg_loop')
# CreateFileW(temp, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, NORMAL, 0)
em.lea_rip('rcx',bsyms['temp_path']); em.mov_r32_imm('rdx',0x80000000); em.mov_r32_imm('r8',1); em.xor32('r9')
em.mov_mrsp_imm32(0x20,3); em.mov_mrsp_imm32(0x28,0x80); em.mov_mrsp_imm32(0x30,0,qword=True); em.call_iat('CreateFileW'); em.cmp_rax_neg1(); em.jcc(0x84,'err_open'); em.mov_r64_r64('r12','rax')
# GetFileSize with high dword
em.lea_rip('rax',bsyms['size_high']); em.mov_word_ptr_reg_zero('rax'); # zero low word enough, then dword zero explicitly
em.emit(0xC7,0x00,u32(0))
em.mov_r64_r64('rcx','r12'); em.lea_rip('rdx',bsyms['size_high']); em.call_iat('GetFileSize'); em.mov_r32_r32('r13','rax')
em.lea_rip('rax',bsyms['size_high']); em.mov_eax_ptr('rax'); em.test32('rax'); em.jcc(0x85,'too_large_close')
em.cmp_r32_imm('r13',MAX_FILE_BYTES); em.jcc(0x87,'too_large_close')
# ReadFile
em.mov_r64_r64('rcx','r12'); em.lea_rip('rdx',bsyms['bytebuf']); em.mov_r32_r32('r8','r13'); em.lea_rip('r9',bsyms['io_count']); em.mov_mrsp_imm32(0x20,0,qword=True); em.call_iat('ReadFile'); em.test32('rax'); em.jcc(0x84,'read_fail_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
# NUL terminate raw buffer at byte count = r13d (GetFileSize)
em.lea_rip('rdx',bsyms['bytebuf']); em.mov_r32_r32('rax','r13'); em.add_r64_r64('rdx','rax'); em.mov_word_ptr_reg_zero('rdx')
# Empty file is valid text.
em.test32('r13'); em.jcc(0x84,'decode_empty')
# BOM detection
em.lea_rip('r14',bsyms['bytebuf']); em.cmp_r32_imm('r13',2); em.jcc(0x82,'decode_8bit')
em.movzx_eax_word_ptr('r14'); em.cmp_r32_imm('rax',0xFEFF); em.jcc(0x84,'decode_utf16')
em.cmp_r32_imm('r13',3); em.jcc(0x82,'decode_8bit')
em.mov_eax_ptr('r14'); em.and_r32_imm('rax',0x00FFFFFF); em.cmp_r32_imm('rax',0x00BFBBEF); em.jcc(0x85,'decode_8bit')
em.add_r64_imm8('r14',3); em.mov_r32_r32('r15','r13'); em.sub_r32_imm8('r15',3); em.jmp('decode_utf8_call')

em.label('decode_8bit')
em.lea_rip('r14',bsyms['bytebuf']); em.mov_r32_r32('r15','r13')
em.label('decode_utf8_call')
# MultiByteToWideChar(CP_UTF8,0,src,len,widebuf,WIDE_CHARS)
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.mov_r64_r64('r8','r14'); em.mov_r32_r32('r9','r15'); em.lea_rip('rax',bsyms['widebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,WIDE_CHARS); em.call_iat('MultiByteToWideChar'); em.test32('rax'); em.jcc(0x85,'decode_done')
# fallback CP_ACP
em.xor32('rcx'); em.xor32('rdx'); em.mov_r64_r64('r8','r14'); em.mov_r32_r32('r9','r15'); em.lea_rip('rax',bsyms['widebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,WIDE_CHARS); em.call_iat('MultiByteToWideChar'); em.test32('rax'); em.jcc(0x84,'err_decode')
em.label('decode_done')
em.lea_rip('rdx',bsyms['widebuf']); em.mov_word_index2_zero('rdx','rax'); em.mov_r64_r64('rcx','rsi'); em.mov_r64_r64('rdx','rdx'); em.call_iat('SetWindowTextW')
# copy successful path
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.jmp('msg_loop')

em.label('decode_empty')
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.jmp('msg_loop')

em.label('decode_utf16')
em.lea_rip('rdx',bsyms['bytebuf']); em.add_r64_imm8('rdx',2); em.mov_r64_r64('rcx','rsi'); em.call_iat('SetWindowTextW')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.jmp('msg_loop')

em.label('too_large_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle');
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_large']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('read_fail_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.jmp('err_open')

em.label('err_open')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_open']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('err_decode')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_decode']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('cmd_save')
em.lea_rip('rax',bsyms['current_path']); em.cmp_word_ptr_reg_zero('rax'); em.jcc(0x84,'cmd_saveas'); em.jmp('do_save')

em.label('cmd_saveas')
em.lea_rip('rcx',bsyms['temp_path']); em.lea_rip('rdx',bsyms['current_path']); em.call_iat('lstrcpyW')
em.emit(*[]); emit_ofn('save_title',0x00080802)
em.mov_r64_r64('rcx','r12'); em.call_iat('GetSaveFileNameW'); em.test32('rax'); em.jcc(0x84,'msg_loop')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW')

em.label('do_save')
# len = GetWindowTextLengthW(edit)
em.mov_r64_r64('rcx','rsi'); em.call_iat('GetWindowTextLengthW'); em.mov_r32_r32('r13','rax'); em.cmp_r32_imm('r13',WIDE_CHARS-1); em.jcc(0x87,'err_save')
# GetWindowTextW
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',bsyms['widebuf']); em.mov_r32_r32('r8','r13'); em.emit(0x41,0x83,0xC0,0x01) # add r8d,1
em.call_iat('GetWindowTextW')
# Convert if nonempty
em.test32('r13'); em.jcc(0x84,'save_zero_bytes')
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.lea_rip('r8',bsyms['widebuf']); em.mov_r32_r32('r9','r13'); em.lea_rip('rax',bsyms['bytebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,BYTE_CAP); em.mov_mrsp_imm32(0x30,0,qword=True); em.mov_mrsp_imm32(0x38,0,qword=True); em.call_iat('WideCharToMultiByte'); em.test32('rax'); em.jcc(0x84,'err_save'); em.mov_r32_r32('r13','rax'); em.jmp('save_create')
em.label('save_zero_bytes'); em.xor32('r13')
em.label('save_create')
# CreateFile current write
em.lea_rip('rcx',bsyms['current_path']); em.mov_r32_imm('rdx',0x40000000); em.xor32('r8'); em.xor32('r9'); em.mov_mrsp_imm32(0x20,2); em.mov_mrsp_imm32(0x28,0x80); em.mov_mrsp_imm32(0x30,0,qword=True); em.call_iat('CreateFileW'); em.cmp_rax_neg1(); em.jcc(0x84,'err_save'); em.mov_r64_r64('r12','rax')
# WriteFile
em.mov_r64_r64('rcx','r12'); em.lea_rip('rdx',bsyms['bytebuf']); em.mov_r32_r32('r8','r13'); em.lea_rip('r9',bsyms['io_count']); em.mov_mrsp_imm32(0x20,0,qword=True); em.call_iat('WriteFile'); em.test32('rax'); em.jcc(0x84,'save_fail_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.jmp('msg_loop')

em.label('save_fail_close'); em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
em.label('err_save'); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_save']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# Edit commands
for label,msg in [('cmd_undo',0x00C7),('cmd_cut',0x0300),('cmd_copy',0x0301),('cmd_paste',0x0302)]:
    em.label(label); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',msg); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.jmp('msg_loop')
em.label('cmd_selectall'); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.mov_r32_imm('r9',0xFFFFFFFF); em.call_iat('SendMessageW'); em.jmp('msg_loop')
em.label('cmd_about'); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['about']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x40); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('dispatch')
em.lea_rip('rcx',bsyms['msg']); em.call_iat('TranslateMessage'); em.lea_rip('rcx',bsyms['msg']); em.call_iat('DispatchMessageW'); em.mov_r64_r64('rcx','rbx'); em.call_iat('IsWindow'); em.test32('rax'); em.jcc(0x85,'msg_loop')

em.label('exit')
em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)

# ------------------------------------------------------------------
# Real application WndProc.  Windows sends menu/non-client/resize messages
# directly to this callback (often synchronously), so these cannot be handled
# reliably by peeking only at the outer GetMessage queue.
em.label('wndproc')
em.emit(0x48,0x83,0xEC,0x38)  # sub rsp, 38h: align + shadow + 2 stack args
em.cmp_r32_imm('rdx',0x0111); em.jcc(0x84,'wp_command')   # WM_COMMAND
em.cmp_r32_imm('rdx',0x0005); em.jcc(0x84,'wp_size')      # WM_SIZE
em.cmp_r32_imm('rdx',0x0002); em.jcc(0x84,'wp_destroy')   # WM_DESTROY
# Everything else MUST go through DefWindowProcW; this is what makes the
# standard caption, dragging, minimize/maximize, close box, etc. work.
em.call_iat('DefWindowProcW')
em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_command')
# WM_COMMAND from a menu is sent directly to WndProc.  Convert it into a
# queued private message so the existing command implementation can stay in
# the main routine and use its established stack frame/nonvolatile registers.
em.mov_r32_imm('rdx',0x8001); em.call_iat('PostMessageW')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_size')
# Resize the child edit control to the new client area. lParam = MAKELPARAM(w,h).
em.mov_r32_r32('r10','r9'); em.mov_r32_r32('r11','r9')
em.and_r32_imm('r10',0xFFFF); em.shr_r32_imm8('r11',16)
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'wp_zero')
em.xor32('rdx'); em.xor32('r8'); em.mov_r32_r32('r9','r10')
em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True)
em.call_iat('MoveWindow')
em.label('wp_zero')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_destroy')
em.xor32('rcx'); em.call_iat('PostQuitMessage')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.patch()
text=em.b
if len(text) >= (RDATA_RVA-TEXT_RVA):
    raise RuntimeError(f'text too large: {len(text):x}')

# ---------------- PE writer ----------------
# ---------------- PE writer (v2: one loader-simple section) ----------------
# Keep the exact RVAs used by the machine-code emitter, but put code, strings,
# import table, and the zero-filled runtime buffers into ONE PE section.
# This mirrors the layout style of the earlier 1.5 KiB build that was confirmed
# to load on Windows, while still leaving the big work buffers as virtual-only
# zero-filled memory rather than storing megabytes of zeros in the file.

headers_size = 0x200
section_ptr = headers_size

# Section begins at TEXT_RVA. Preserve the existing absolute RVA plan:
#   code  @ 0x1000
#   rdata @ 0x3000
#   idata @ 0x4000
#   bss   @ 0x5000 (virtual-only tail)
raw = bytearray()
raw.extend(text)
if len(raw) > RDATA_RVA - TEXT_RVA:
    raise RuntimeError('text overlaps rdata')
raw.extend(b'\0' * ((RDATA_RVA - TEXT_RVA) - len(raw)))
raw.extend(rdata)
if len(raw) > IDATA_RVA - TEXT_RVA:
    raise RuntimeError('rdata overlaps idata')
raw.extend(b'\0' * ((IDATA_RVA - TEXT_RVA) - len(raw)))
raw.extend(idata)
raw_size = align(len(raw), FILE_ALIGN)
raw.extend(b'\0' * (raw_size - len(raw)))

section_vsize = (BSS_RVA + BSS_VSIZE) - TEXT_RVA
size_image = align(TEXT_RVA + section_vsize, SECT_ALIGN)

hdr = bytearray(b'\0' * headers_size)
hdr[0:2] = b'MZ'
struct.pack_into('<I', hdr, 0x3c, 0x80)
dosmsg = b'This program cannot be run in DOS mode.\r\r\n$'
hdr[0x40:0x40+len(dosmsg)] = dosmsg
p = 0x80
hdr[p:p+4] = b'PE\0\0'; p += 4

# COFF header: AMD64, one section, executable + large-address-aware.
struct.pack_into('<HHIIIHH', hdr, p, 0x8664, 1, 0, 0, 0, 0xF0, 0x0022); p += 20

opt = bytearray(b'\0' * 0xF0)
code_raw = align(len(text), FILE_ALIGN)
init_data = max(0, raw_size - code_raw)
struct.pack_into('<HBBIII', opt, 0, 0x20B, 14, 0, code_raw, init_data, BSS_VSIZE)
struct.pack_into('<II', opt, 16, TEXT_RVA, TEXT_RVA)
struct.pack_into('<Q', opt, 24, IMAGE_BASE)
struct.pack_into('<II', opt, 32, SECT_ALIGN, FILE_ALIGN)
struct.pack_into('<HHHHHH', opt, 40, 6, 0, 0, 0, 6, 0)
struct.pack_into('<I', opt, 52, 0)
struct.pack_into('<II', opt, 56, size_image, headers_size)
struct.pack_into('<I', opt, 64, 0)
struct.pack_into('<HH', opt, 68, 2, 0x0100)  # GUI, NX_COMPAT only (no ASLR/relocs)
struct.pack_into('<QQQQ', opt, 72, 0x100000, 0x1000, 0x100000, 0x1000)
struct.pack_into('<II', opt, 104, 0, 16)
struct.pack_into('<II', opt, 112 + 8*1, IDATA_RVA, IMPORT_DESC_SIZE)
struct.pack_into('<II', opt, 112 + 8*12, IAT_RVA, IAT_SIZE)
hdr[p:p+0xF0] = opt; p += 0xF0

# A single RWX section is deliberate for this experiment: code and writable IAT
# share one mapped section, and the huge zero-filled tail supplies runtime buffers.
name = b'.text\0\0\0'
chars = 0xE00000E0  # CODE | INIT_DATA | UNINIT_DATA | EXECUTE | READ | WRITE
shdr = name + struct.pack('<IIIIIIHHI', section_vsize, TEXT_RVA, raw_size,
                           section_ptr, 0, 0, 0, 0, chars)
hdr[p:p+40] = shdr; p += 40

out = '/mnt/data/direct_pe_notepad_full_x64_v3.exe'
with open(out, 'wb') as f:
    f.write(hdr)
    f.write(raw)

sha = hashlib.sha256(open(out,'rb').read()).hexdigest()
print(out)
print('size', os.path.getsize(out), 'text', len(text), 'raw', raw_size,
      'section_vsize', section_vsize, 'bss_vsize', BSS_VSIZE)
print('sha256', sha)
