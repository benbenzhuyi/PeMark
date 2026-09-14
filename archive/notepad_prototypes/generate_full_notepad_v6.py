import struct, hashlib, os, subprocess, textwrap

IMAGE_BASE = 0x140000000
TEXT_RVA = 0x1000
RDATA_RVA = 0x5000
IDATA_RVA = 0x7000
BSS_RVA = 0x8000
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
wstr('title','Direct PE Notepad x64 V6 — No Compiler')
wstr('empty','')
wstr('menu_file','&File')
wstr('menu_edit','&Edit')
wstr('menu_view','&View')
wstr('menu_help','&Help')
wstr('m_new','&New\tCtrl+N')
wstr('m_open','&Open...\tCtrl+O')
wstr('m_save','&Save\tCtrl+S')
wstr('m_saveas','Save &As...\tCtrl+Shift+S')
wstr('m_exit','E&xit\tAlt+F4')
wstr('m_undo','&Undo\tCtrl+Z')
wstr('m_cut','Cu&t\tCtrl+X')
wstr('m_copy','&Copy\tCtrl+C')
wstr('m_paste','&Paste\tCtrl+V')
wstr('m_find','&Find...\tCtrl+F')
wstr('m_findnext','Find &Next\tF3')
wstr('m_replace','&Replace...\tCtrl+H')
wstr('m_selectall','Select &All\tCtrl+A')
wstr('m_zoom','&Zoom')
wstr('m_zoomin','Zoom &In\tCtrl++ / Ctrl+Wheel Up')
wstr('m_zoomout','Zoom &Out\tCtrl+- / Ctrl+Wheel Down')
wstr('m_zoomreset','Restore &Default Zoom\tCtrl+0')
wstr('m_wrap','&Word Wrap\tCtrl+Shift+W')
wstr('m_status','&Status Bar\tCtrl+Shift+B')
wstr('m_about','&About\tF1')
wstr('open_title','Open text file')
wstr('save_title','Save text file as')
wstr('defext','txt')
wstr('class_status','msctls_statusbar32')
wstr('font_face','Segoe UI')
wstr('fmt_lncol','Ln %u, Col %u')
wstr('fmt_zoom','%u%%')
wstr('fmt_chars','Chars: %u')
wstr('fmt_selected','Selected: %u')
wstr('fmt_replaced','Replaced %u occurrence(s).')
wstr('find_not_found','Cannot find the requested text.')
wstr('findmsgstring','commdlg_FindReplace')
wstr('status_crlf','Windows (CRLF)')
wstr('status_utf8','UTF-8')
wstr('status_utf16','UTF-16 LE')
wstr('status_ansi','ANSI')
add_bytes('status_parts', struct.pack('<iiiiii', 210, 330, 455, 545, 690, -1), 4)

# In-memory accelerator table (ACCEL is 6 bytes: BYTE, pad, WORD, WORD).
FVIRTKEY, FSHIFT, FCONTROL, FALT = 0x01, 0x04, 0x08, 0x10
_accels = [
    (FVIRTKEY|FCONTROL, 0x4E, 1001),                  # Ctrl+N
    (FVIRTKEY|FCONTROL, 0x4F, 1002),                  # Ctrl+O
    (FVIRTKEY|FCONTROL, 0x53, 1003),                  # Ctrl+S
    (FVIRTKEY|FCONTROL|FSHIFT, 0x53, 1004),           # Ctrl+Shift+S
    (FVIRTKEY|FALT, 0x73, 1005),                      # Alt+F4
    (FVIRTKEY|FCONTROL, 0x5A, 1101),                  # Ctrl+Z
    (FVIRTKEY|FCONTROL, 0x58, 1102),                  # Ctrl+X
    (FVIRTKEY|FCONTROL, 0x43, 1103),                  # Ctrl+C
    (FVIRTKEY|FCONTROL, 0x56, 1104),                  # Ctrl+V
    (FVIRTKEY|FCONTROL, 0x46, 1106),                  # Ctrl+F
    (FVIRTKEY, 0x72, 1107),                           # F3
    (FVIRTKEY|FCONTROL, 0x48, 1108),                  # Ctrl+H
    (FVIRTKEY|FCONTROL, 0x41, 1105),                  # Ctrl+A
    (FVIRTKEY|FCONTROL|FSHIFT, 0xBB, 1301),           # Ctrl++ (OEM +)
    (FVIRTKEY|FCONTROL, 0x6B, 1301),                  # Ctrl+Num+
    (FVIRTKEY|FCONTROL, 0xBD, 1302),                  # Ctrl+-
    (FVIRTKEY|FCONTROL, 0x6D, 1302),                  # Ctrl+Num-
    (FVIRTKEY|FCONTROL, 0x30, 1303),                  # Ctrl+0
    (FVIRTKEY|FCONTROL|FSHIFT, 0x57, 1304),           # Ctrl+Shift+W
    (FVIRTKEY|FCONTROL|FSHIFT, 0x42, 1305),           # Ctrl+Shift+B
    (FVIRTKEY, 0x70, 1201),                           # F1
]
ACCEL_COUNT=len(_accels)
add_bytes('accels', b''.join(struct.pack('<BxHH', *a) for a in _accels), 2)
# OPENFILENAME filter requires embedded NUL separators and double-NUL terminator.
add_bytes('filter', ('Text files (*.txt)\0*.txt\0All files (*.*)\0*.*\0\0').encode('utf-16le'), 2)
wstr('err_title','Direct PE Notepad')
wstr('err_open','Could not open or read the selected file.')
wstr('err_save','Could not save the file.')
wstr('err_large','The file is too large for this build (limit: about 1 MiB).')
wstr('err_decode','The file could not be decoded as UTF-8/ANSI text.')
wstr('about','Direct PE Notepad x64 V6\r\n\r\nNative PE32+ and x86-64 machine code generated directly, without a C/C++ compiler, assembler, or linker.\r\n\r\nV6 adds Ctrl+mouse-wheel zoom while retaining live resize, status counts, accelerators, and native Find / Replace dialogs.')

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
bss_alloc('hwnd_status', 8, 8)
bss_alloc('hfont', 8, 8)
bss_alloc('old_hfont', 8, 8)
bss_alloc('hmenu_view', 8, 8)
bss_alloc('hmenu_zoom', 8, 8)
bss_alloc('haccel', 8, 8)
bss_alloc('findreplace_hwnd', 8, 8)
bss_alloc('wrap_flag', 4, 4)
bss_alloc('status_flag', 4, 4)
bss_alloc('zoom_pct', 4, 4)
bss_alloc('encoding_state', 4, 4)
bss_alloc('findmsg_id', 4, 4)
bss_alloc('find_flags', 4, 4)
bss_alloc('search_wrap_flag', 4, 4)
bss_alloc('find_len', 4, 4)
bss_alloc('match_start', 4, 4)
bss_alloc('match_end', 4, 4)
bss_alloc('total_chars', 4, 4)
bss_alloc('selected_chars', 4, 4)
bss_alloc('replace_count', 4, 4)
bss_alloc('client_w', 4, 4)
bss_alloc('client_h', 4, 4)
bss_alloc('status_h', 4, 4)
bss_alloc('sel_start', 4, 4)
bss_alloc('sel_end', 4, 4)
bss_alloc('line_zero', 4, 4)
bss_alloc('col_one', 4, 4)
bss_alloc('status_linebuf', 128*2, 16)
bss_alloc('status_zoombuf', 32*2, 16)
bss_alloc('status_charsbuf', 48*2, 16)
bss_alloc('status_selbuf', 48*2, 16)
bss_alloc('status_msgbuf', 96*2, 16)
bss_alloc('findbuf', 256*2, 16)
bss_alloc('replacebuf', 256*2, 16)
bss_alloc('fr', 80, 16)
bss_alloc('icc', 8, 8)
bss_alloc('rect', 16, 8)
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
        'MultiByteToWideChar','WideCharToMultiByte','lstrcpyW','lstrlenW','GetModuleHandleW','CompareStringOrdinal'
    ],
    'USER32.dll': [
        'CreateWindowExW','GetMessageW','TranslateMessage','DispatchMessageW','IsWindow',
        'CreateMenu','CreatePopupMenu','AppendMenuW','GetWindowTextLengthW','GetWindowTextW',
        'SetWindowTextW','SendMessageW','MoveWindow','MessageBoxW','SetFocus',
        'RegisterClassExW','DefWindowProcW','PostQuitMessage','PostMessageW','LoadCursorW',
        'DestroyWindow','ShowWindow','CheckMenuItem','GetWindowRect','wsprintfW','RegisterWindowMessageW',
        'CreateAcceleratorTableW','TranslateAcceleratorW','DestroyAcceleratorTable','IsDialogMessageW','SetForegroundWindow'
    ],
    'COMDLG32.dll': ['GetOpenFileNameW','GetSaveFileNameW','FindTextW','ReplaceTextW'],
    'SHLWAPI.dll': ['StrStrW','StrStrIW'],
    'COMCTL32.dll': ['InitCommonControlsEx'],
    'GDI32.dll': ['CreateFontW','DeleteObject'],
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
    def mov_r32_ripmem(self,reg,target_rva):
        rr=REG[reg]; self.rex(r=(rr>>3)&1); self.emit(0x8B, ((rr&7)<<3)|5)
        disp=target_rva-(self.rva+4)
        self.emit(s32(disp))
    def mov_ripmem_r32(self,target_rva,reg):
        rr=REG[reg]; self.rex(r=(rr>>3)&1); self.emit(0x89, ((rr&7)<<3)|5)
        disp=target_rva-(self.rva+4)
        self.emit(s32(disp))
    def mov_ripmem_imm32(self,target_rva,imm):
        self.emit(0xC7,0x05)
        disp=target_rva-(self.rva+8)
        self.emit(s32(disp),u32(imm))
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
    def add_r32_imm8(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x83,0xC0|(r&7),imm&255)
    def sub_r32_r32(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(r=(s>>3)&1,b=(d>>3)&1); self.emit(0x29,0xC0|((s&7)<<3)|(d&7))
    def add_r32_r32(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(r=(s>>3)&1,b=(d>>3)&1); self.emit(0x01,0xC0|((s&7)<<3)|(d&7))
    def cmp_r32_r32(self,a,b):
        aa,bb=REG[a],REG[b]; self.rex(r=(bb>>3)&1,b=(aa>>3)&1); self.emit(0x39,0xC0|((bb&7)<<3)|(aa&7))
    def sub_r64_r64(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(w=1,r=(s>>3)&1,b=(d>>3)&1); self.emit(0x29,0xC0|((s&7)<<3)|(d&7))
    def shr_r64_imm8(self,reg,imm):
        r=REG[reg]; self.rex(w=1,b=(r>>3)&1); self.emit(0xC1,0xE8|(r&7),imm&255)
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
em.mov_ripmem_imm32(bsyms['wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['status_flag'],1)
em.mov_ripmem_imm32(bsyms['zoom_pct'],100)
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_ripmem_imm32(bsyms['find_flags'],1)
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['client_w'],884)
em.mov_ripmem_imm32(bsyms['client_h'],590)
# Register common-control classes required by the native status bar.
em.lea_rip('r12',bsyms['icc']); em.mov_mr12_imm32(0,8); em.mov_mr12_imm32(4,4)
em.mov_r64_r64('rcx','r12'); em.call_iat('InitCommonControlsEx')
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
# Register the message used by the modeless common Find/Replace dialogs.
em.lea_rip('rcx',rsyms['findmsgstring']); em.call_iat('RegisterWindowMessageW'); em.mov_ripmem_r32(bsyms['findmsg_id'],'rax')

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
append_imm('r13',0,1101,'m_undo'); append_sep('r13'); append_imm('r13',0,1102,'m_cut'); append_imm('r13',0,1103,'m_copy'); append_imm('r13',0,1104,'m_paste'); append_sep('r13'); append_imm('r13',0,1106,'m_find'); append_imm('r13',0,1107,'m_findnext'); append_imm('r13',0,1108,'m_replace'); append_sep('r13'); append_imm('r13',0,1105,'m_selectall')
append_popup('rdi','r13','menu_edit')

# View -> Zoom, Word Wrap, Status Bar
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r14','rax'); em.mov_ripmem_r64(bsyms['hmenu_view'],'r14')
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r12','rax'); em.mov_ripmem_r64(bsyms['hmenu_zoom'],'r12')
append_imm('r12',0,1301,'m_zoomin'); append_imm('r12',0,1302,'m_zoomout'); append_imm('r12',0,1303,'m_zoomreset')
append_popup('r14','r12','m_zoom'); append_sep('r14')
append_imm('r14',0x8,1304,'m_wrap'); append_imm('r14',0x8,1305,'m_status')
append_popup('rdi','r14','menu_view')

em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r14','rax')
append_imm('r14',0,1201,'m_about'); append_popup('rdi','r14','menu_help')

# Standard accelerator table: TranslateAcceleratorW turns these into WM_COMMAND.
em.lea_rip('rcx',rsyms['accels']); em.mov_r32_imm('rdx',ACCEL_COUNT); em.call_iat('CreateAcceleratorTableW'); em.mov_ripmem_r64(bsyms['haccel'],'rax')

# Parent custom top-level window
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_main']); em.lea_rip('r8',rsyms['title']); em.mov_r32_imm('r9',0x10CF0000)
em.mov_mrsp_imm32(0x20,0x80000000); em.mov_mrsp_imm32(0x28,0x80000000); em.mov_mrsp_imm32(0x30,900); em.mov_mrsp_imm32(0x38,650)
em.mov_mrsp_imm32(0x40,0,qword=True); em.mov_mrsp_reg64(0x48,'rdi'); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rbx','rax'); em.test64('rax'); em.jcc(0x84,'exit')
# Child EDIT
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50A11044)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,884); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi')
# Increase edit text limit to ~1M chars
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',MAX_FILE_BYTES); em.xor32('r9'); em.call_iat('SendMessageW')
# Create a real font so zooming can be implemented with WM_SETFONT.
em.call_label('apply_zoom')
em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus')

# Native Windows status bar (common-controls class).
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_status']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50000100)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,2,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_status'],'rax')
em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0404); em.mov_r32_imm('r8',6); em.lea_rip('r9',rsyms['status_parts']); em.call_iat('SendMessageW')
em.call_label('resize_children'); em.call_label('update_status')

# Message pump
em.label('msg_loop')
em.lea_rip('r12',bsyms['msg']); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.call_iat('GetMessageW')
em.test32('rax'); em.jcc(0x8E,'exit') # jle
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x8001); em.jcc(0x84,'command')  # WM_APP+1 posted by wndproc
em.cmp_r32_imm('rax',0x8002); em.jcc(0x84,'resize_event') # legacy/private resize event
em.cmp_r32_imm('rax',0x8003); em.jcc(0x84,'findreplace_event')
# Ctrl+mouse-wheel zoom. WM_MOUSEWHEEL is queued for the focused child EDIT window,
# so intercept it in the thread message pump before DispatchMessageW.
em.cmp_r32_imm('rax',0x020A); em.jcc(0x84,'mousewheel_event')
em.jmp('dispatch')

em.label('mousewheel_event')
# wParam: LOWORD = MK_* key flags; HIWORD = signed wheel delta.
em.mov_rax_mr12(16)
em.mov_r32_r32('r10','rax'); em.and_r32_imm('r10',0x0008); em.test32('r10'); em.jcc(0x84,'dispatch')  # no MK_CONTROL: preserve normal scrolling
em.mov_r32_r32('r10','rax'); em.shr_r32_imm8('r10',16); em.test32('r10'); em.jcc(0x84,'msg_loop')
em.mov_r32_r32('r11','r10'); em.and_r32_imm('r11',0x8000); em.test32('r11'); em.jcc(0x85,'cmd_zoomout')
em.jmp('cmd_zoomin')

em.label('resize_event')
em.call_label('resize_children'); em.call_label('update_status'); em.jmp('msg_loop')

# FINDMSGSTRING notifications are converted by WndProc into WM_APP+3.
em.label('findreplace_event')
em.mov_eax_mr12(16)
em.mov_r32_r32('r10','rax'); em.and_r32_imm('r10',0x40); em.test32('r10'); em.jcc(0x85,'fr_dialogterm')
em.mov_ripmem_r32(bsyms['find_flags'],'rax')
em.mov_r32_r32('r10','rax'); em.and_r32_imm('r10',0x20); em.test32('r10'); em.jcc(0x85,'fr_replaceall')
em.mov_r32_r32('r10','rax'); em.and_r32_imm('r10',0x10); em.test32('r10'); em.jcc(0x85,'fr_replace')
em.and_r32_imm('rax',0x08); em.test32('rax'); em.jcc(0x85,'fr_findnext')
em.jmp('msg_loop')
em.label('fr_dialogterm'); em.xor32('rax'); em.mov_ripmem_r64(bsyms['findreplace_hwnd'],'rax'); em.jmp('msg_loop')

em.label('command')
em.mov_eax_mr12(16); em.and_r32_imm('rax',0xFFFF)
for cid,label in [(1001,'cmd_new'),(1002,'cmd_open'),(1003,'cmd_save'),(1004,'cmd_saveas'),(1005,'cmd_exit'),
                  (1101,'cmd_undo'),(1102,'cmd_cut'),(1103,'cmd_copy'),(1104,'cmd_paste'),(1105,'cmd_selectall'),(1106,'cmd_find'),(1107,'cmd_findnext'),(1108,'cmd_replace'),(1201,'cmd_about'),
                  (1301,'cmd_zoomin'),(1302,'cmd_zoomout'),(1303,'cmd_zoomreset'),(1304,'cmd_wrap'),(1305,'cmd_status')]:
    em.cmp_r32_imm('rax',cid); em.jcc(0x84,label)
em.jmp('dispatch')

em.label('cmd_new')
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rax',bsyms['current_path']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['encoding_state'],0); em.call_label('update_status'); em.jmp('msg_loop')

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
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
# MultiByteToWideChar(CP_UTF8,0,src,len,widebuf,WIDE_CHARS)
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.mov_r64_r64('r8','r14'); em.mov_r32_r32('r9','r15'); em.lea_rip('rax',bsyms['widebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,WIDE_CHARS); em.call_iat('MultiByteToWideChar'); em.test32('rax'); em.jcc(0x85,'decode_done')
# fallback CP_ACP
em.mov_ripmem_imm32(bsyms['encoding_state'],2)
em.xor32('rcx'); em.xor32('rdx'); em.mov_r64_r64('r8','r14'); em.mov_r32_r32('r9','r15'); em.lea_rip('rax',bsyms['widebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,WIDE_CHARS); em.call_iat('MultiByteToWideChar'); em.test32('rax'); em.jcc(0x84,'err_decode')
em.label('decode_done')
em.lea_rip('rdx',bsyms['widebuf']); em.mov_word_index2_zero('rdx','rax'); em.mov_r64_r64('rcx','rsi'); em.mov_r64_r64('rdx','rdx'); em.call_iat('SetWindowTextW')
# copy successful path
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.jmp('msg_loop')

em.label('decode_empty')
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.jmp('msg_loop')

em.label('decode_utf16')
em.mov_ripmem_imm32(bsyms['encoding_state'],1)
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
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.mov_ripmem_imm32(bsyms['encoding_state'],0); em.call_label('update_status'); em.jmp('msg_loop')

em.label('save_fail_close'); em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
em.label('err_save'); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_save']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# Edit commands
for label,msg in [('cmd_undo',0x00C7),('cmd_cut',0x0300),('cmd_copy',0x0301),('cmd_paste',0x0302)]:
    em.label(label); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',msg); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.jmp('msg_loop')
em.label('cmd_selectall'); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.mov_r32_imm('r9',0xFFFFFFFF); em.call_iat('SendMessageW'); em.jmp('msg_loop')

# Native modeless common Find / Replace dialogs.
_fr_seq=[0]
def emit_fr_common():
    _fr_seq[0]+=1; old_label=f'fr_no_old_{_fr_seq[0]}'
    # Only one common Find/Replace dialog at a time. If one already exists,
    # bring it forward rather than destroying/recreating it (avoids stale
    # FR_DIALOGTERM notifications racing with a newly-created dialog).
    em.mov_r64_ripmem('rcx',bsyms['findreplace_hwnd']); em.test64('rcx'); em.jcc(0x84,old_label)
    em.call_iat('IsWindow'); em.test32('rax'); em.jcc(0x84,old_label)
    em.mov_r64_ripmem('rcx',bsyms['findreplace_hwnd']); em.call_iat('SetForegroundWindow'); em.jmp('msg_loop')
    em.label(old_label)
    em.lea_rip('r12',bsyms['fr']); em.mov_mr12_imm32(0,80); em.mov_mr12_reg64(8,'rbx')
    em.xor32('rax'); em.mov_mr12_reg64(16,'rax')
    em.mov_mr12_imm32(24,0x00014001)   # FR_HIDEWHOLEWORD | FR_HIDEUPDOWN | FR_DOWN
    em.lea_rip('rax',bsyms['findbuf']); em.mov_mr12_reg64(32,'rax')
    em.lea_rip('rax',bsyms['replacebuf']); em.mov_mr12_reg64(40,'rax')
    em.mov_mr12_imm32(48,0x02000200)   # buffer lengths are BYTES: 512 + 512

em.label('cmd_find')
emit_fr_common(); em.mov_r64_r64('rcx','r12'); em.call_iat('FindTextW'); em.mov_ripmem_r64(bsyms['findreplace_hwnd'],'rax'); em.jmp('msg_loop')

em.label('cmd_replace')
emit_fr_common(); em.mov_r64_r64('rcx','r12'); em.call_iat('ReplaceTextW'); em.mov_ripmem_r64(bsyms['findreplace_hwnd'],'rax'); em.jmp('msg_loop')

em.label('cmd_findnext')
em.lea_rip('rcx',bsyms['findbuf']); em.call_iat('lstrlenW'); em.test32('rax'); em.jcc(0x84,'cmd_find')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1); em.call_label('find_next_select'); em.test32('rax'); em.jcc(0x85,'msg_loop'); em.jmp('show_find_notfound')

em.label('fr_findnext')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1); em.call_label('find_next_select'); em.test32('rax'); em.jcc(0x85,'msg_loop')
em.label('show_find_notfound')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['find_not_found']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x40); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('fr_replace')
em.call_label('replace_if_match'); em.call_label('find_next_select'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('fr_replaceall')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],0); em.xor32('rax'); em.mov_ripmem_r32(bsyms['replace_count'],'rax')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.label('replaceall_loop')
em.call_label('find_next_select'); em.test32('rax'); em.jcc(0x84,'replaceall_done')
em.call_label('replace_if_match'); em.test32('rax'); em.jcc(0x84,'replaceall_done')
em.mov_r32_ripmem('rax',bsyms['replace_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['replace_count'],'rax'); em.jmp('replaceall_loop')
em.label('replaceall_done')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1); em.call_label('update_status')
em.lea_rip('rcx',bsyms['status_msgbuf']); em.lea_rip('rdx',rsyms['fmt_replaced']); em.mov_r32_ripmem('r8',bsyms['replace_count']); em.call_iat('wsprintfW')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',bsyms['status_msgbuf']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x40); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# View / Zoom commands
em.label('cmd_zoomin')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.cmp_r32_imm('rax',200); em.jcc(0x83,'msg_loop') # jae
em.add_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomout')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.cmp_r32_imm('rax',50); em.jcc(0x86,'msg_loop') # jbe
em.sub_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomreset')
em.mov_ripmem_imm32(bsyms['zoom_pct'],100); em.call_label('apply_zoom'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('cmd_wrap')
em.mov_r32_ripmem('rax',bsyms['wrap_flag']); em.test32('rax'); em.jcc(0x84,'wrap_enable')
em.mov_ripmem_imm32(bsyms['wrap_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1304); em.xor32('r8'); em.call_iat('CheckMenuItem'); em.jmp('wrap_recreate')
em.label('wrap_enable')
em.mov_ripmem_imm32(bsyms['wrap_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1304); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.label('wrap_recreate')
# Preserve text and selection, then recreate the EDIT control with/without horizontal scrolling.
em.mov_r64_r64('rcx','rsi'); em.call_iat('GetWindowTextLengthW'); em.mov_r32_r32('r13','rax')
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',bsyms['widebuf']); em.mov_r32_r32('r8','r13'); em.add_r32_imm8('r8',1); em.call_iat('GetWindowTextW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.call_iat('DestroyWindow')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',bsyms['widebuf'])
em.mov_r32_ripmem('rax',bsyms['wrap_flag']); em.test32('rax'); em.jcc(0x84,'wrap_style_off')
em.mov_r32_imm('r9',0x50A11044); em.jmp('wrap_style_ready')
em.label('wrap_style_off'); em.mov_r32_imm('r9',0x50B110C4)
em.label('wrap_style_ready')
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',MAX_FILE_BYTES); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.mov_r32_ripmem('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus'); em.call_label('resize_children'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('cmd_status')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'status_show')
em.mov_ripmem_imm32(bsyms['status_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1305); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.jmp('msg_loop')
em.label('status_show')
em.mov_ripmem_imm32(bsyms['status_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1305); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('cmd_about'); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['about']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x40); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('cmd_exit'); em.mov_r64_r64('rcx','rbx'); em.mov_r32_imm('rdx',0x0010); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('msg_loop')

em.label('dispatch')
# Let the modeless common Find/Replace dialog consume Tab/Enter/etc. first.
em.mov_r64_ripmem('rcx',bsyms['findreplace_hwnd']); em.test64('rcx'); em.jcc(0x84,'dispatch_accel')
em.call_iat('IsWindow'); em.test32('rax'); em.jcc(0x84,'dispatch_accel')
em.mov_r64_ripmem('rcx',bsyms['findreplace_hwnd']); em.lea_rip('rdx',bsyms['msg']); em.call_iat('IsDialogMessageW'); em.test32('rax'); em.jcc(0x85,'msg_loop')
em.label('dispatch_accel')
em.mov_r64_ripmem('rdx',bsyms['haccel']); em.test64('rdx'); em.jcc(0x84,'dispatch_translate')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('r8',bsyms['msg']); em.call_iat('TranslateAcceleratorW'); em.test32('rax'); em.jcc(0x85,'msg_loop')
em.label('dispatch_translate')
em.lea_rip('rcx',bsyms['msg']); em.call_iat('TranslateMessage'); em.lea_rip('rcx',bsyms['msg']); em.call_iat('DispatchMessageW'); em.call_label('update_status'); em.mov_r64_r64('rcx','rbx'); em.call_iat('IsWindow'); em.test32('rax'); em.jcc(0x85,'msg_loop')

# ------------------------------------------------------------------
# Helper: resize EDIT + native status bar from client_w/client_h.
em.label('resize_children')
em.emit(0x48,0x83,0xEC,0x38)
em.xor32('rax'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'resize_edit')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'resize_edit')
em.mov_r32_imm('rdx',0x0005); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetWindowRect')
em.mov_r32_ripmem('rax',bsyms['rect']+12); em.mov_r32_ripmem('r10',bsyms['rect']+4); em.sub_r32_r32('rax','r10'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.label('resize_edit')
em.mov_r32_ripmem('r10',bsyms['client_w']); em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'resize_ret')
em.xor32('rdx'); em.xor32('r8'); em.mov_r32_r32('r9','r10'); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: create a new EDIT font for current zoom_pct, select it, then retire the old font.
em.label('apply_zoom')
em.emit(0x48,0x81,0xEC,u32(0x88))
em.mov_r64_ripmem('rax',bsyms['hfont']); em.mov_ripmem_r64(bsyms['old_hfont'],'rax')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.emit(0x6B,0xC0,0x10); em.emit(0x99); em.mov_r32_imm('rcx',100); em.emit(0xF7,0xF9); em.emit(0xF7,0xD8)
em.mov_r32_r32('rcx','rax'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9')
em.mov_mrsp_imm32(0x20,400); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0); em.mov_mrsp_imm32(0x40,1); em.mov_mrsp_imm32(0x48,0); em.mov_mrsp_imm32(0x50,0); em.mov_mrsp_imm32(0x58,5); em.mov_mrsp_imm32(0x60,0)
em.lea_rip('rax',rsyms['font_face']); em.mov_mrsp_reg64(0x68,'rax'); em.call_iat('CreateFontW'); em.test64('rax'); em.jcc(0x84,'font_ret')
em.mov_ripmem_r64(bsyms['hfont'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'font_delete_old'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.label('font_delete_old'); em.mov_r64_ripmem('rcx',bsyms['old_hfont']); em.test64('rcx'); em.jcc(0x84,'font_ret'); em.call_iat('DeleteObject')
em.label('font_ret'); em.emit(0x48,0x81,0xC4,u32(0x88)); em.emit(0xC3)

# Helper: find next occurrence using SHLWAPI StrStrW/StrStrIW, select it, and scroll caret.
# Uses the current selection end as the search start and optionally wraps once.
em.label('find_next_select')
em.emit(0x48,0x83,0xEC,0x38)
em.lea_rip('rcx',bsyms['findbuf']); em.call_iat('lstrlenW'); em.mov_ripmem_r32(bsyms['find_len'],'rax'); em.test32('rax'); em.jcc(0x84,'find_none')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
em.mov_r32_r32('r8','rax'); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.lea_rip('rdx',bsyms['widebuf']); em.call_iat('GetWindowTextW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
# pointer = widebuf + 2*sel_end
em.lea_rip('rcx',bsyms['widebuf']); em.mov_r32_ripmem('rax',bsyms['sel_end']); em.add_r64_r64('rax','rax'); em.add_r64_r64('rcx','rax'); em.lea_rip('rdx',bsyms['findbuf'])
em.mov_r32_ripmem('rax',bsyms['find_flags']); em.and_r32_imm('rax',4); em.test32('rax'); em.jcc(0x85,'find_case_first')
em.call_iat('StrStrIW'); em.jmp('find_first_done')
em.label('find_case_first'); em.call_iat('StrStrW')
em.label('find_first_done'); em.test64('rax'); em.jcc(0x85,'find_got')
# Wrap only for ordinary Find Next; Replace All disables this.
em.mov_r32_ripmem('r10',bsyms['search_wrap_flag']); em.test32('r10'); em.jcc(0x84,'find_none')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.test32('r10'); em.jcc(0x84,'find_none')
em.lea_rip('rcx',bsyms['widebuf']); em.lea_rip('rdx',bsyms['findbuf']); em.mov_r32_ripmem('r10',bsyms['find_flags']); em.and_r32_imm('r10',4); em.test32('r10'); em.jcc(0x85,'find_case_wrap')
em.call_iat('StrStrIW'); em.jmp('find_wrap_done')
em.label('find_case_wrap'); em.call_iat('StrStrW')
em.label('find_wrap_done'); em.test64('rax'); em.jcc(0x84,'find_none')
em.label('find_got')
em.lea_rip('r10',bsyms['widebuf']); em.sub_r64_r64('rax','r10'); em.shr_r64_imm8('rax',1); em.mov_ripmem_r32(bsyms['match_start'],'rax')
em.mov_r32_r32('r10','rax'); em.mov_r32_ripmem('r11',bsyms['find_len']); em.add_r32_r32('r10','r11'); em.mov_ripmem_r32(bsyms['match_end'],'r10')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['match_start']); em.mov_r32_ripmem('r9',bsyms['match_end']); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B7); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.mov_r32_imm('rax',1); em.jmp('find_ret')
em.label('find_none'); em.xor32('rax')
em.label('find_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: replace the current selection only if it exactly matches Find What.
em.label('replace_if_match')
em.emit(0x48,0x83,0xEC,0x38)
em.lea_rip('rcx',bsyms['findbuf']); em.call_iat('lstrlenW'); em.mov_ripmem_r32(bsyms['find_len'],'rax'); em.test32('rax'); em.jcc(0x84,'replace_no')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.mov_r32_ripmem('r11',bsyms['sel_start']); em.sub_r32_r32('r10','r11'); em.mov_r32_ripmem('r11',bsyms['find_len']); em.cmp_r32_r32('r10','r11'); em.jcc(0x85,'replace_no')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_r32_r32('r8','rax'); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.lea_rip('rdx',bsyms['widebuf']); em.call_iat('GetWindowTextW')
# CompareStringOrdinal(selected, find_len, findbuf, find_len, ignoreCase)
em.lea_rip('rcx',bsyms['widebuf']); em.mov_r32_ripmem('rax',bsyms['sel_start']); em.add_r64_r64('rax','rax'); em.add_r64_r64('rcx','rax')
em.mov_r32_ripmem('rdx',bsyms['find_len']); em.lea_rip('r8',bsyms['findbuf']); em.mov_r32_ripmem('r9',bsyms['find_len'])
em.mov_r32_ripmem('rax',bsyms['find_flags']); em.and_r32_imm('rax',4); em.test32('rax'); em.jcc(0x85,'replace_matchcase'); em.mov_mrsp_imm32(0x20,1); em.jmp('replace_compare')
em.label('replace_matchcase'); em.mov_mrsp_imm32(0x20,0)
em.label('replace_compare'); em.call_iat('CompareStringOrdinal'); em.cmp_r32_imm('rax',2); em.jcc(0x85,'replace_no')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C2); em.mov_r32_imm('r8',1); em.lea_rip('r9',bsyms['replacebuf']); em.call_iat('SendMessageW'); em.mov_r32_imm('rax',1); em.jmp('replace_ret')
em.label('replace_no'); em.xor32('rax')
em.label('replace_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: Windows-Notepad-style status fields: line/column, total/selected chars, zoom, EOL, encoding.
em.label('update_status')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'status_ret')
em.mov_r64_ripmem('rax',bsyms['hwnd_status']); em.test64('rax'); em.jcc(0x84,'status_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'status_ret')
# EM_GETSEL
em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
# zero-based line from caret
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C9); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['line_zero'],'rax')
# line start index
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00BB); em.mov_r32_ripmem('r8',bsyms['line_zero']); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r32_ripmem('r10',bsyms['sel_start']); em.sub_r32_r32('r10','rax'); em.add_r32_imm8('r10',1); em.mov_ripmem_r32(bsyms['col_one'],'r10')
# "Ln n, Col n"
em.lea_rip('rcx',bsyms['status_linebuf']); em.lea_rip('rdx',rsyms['fmt_lncol']); em.mov_r32_ripmem('r8',bsyms['line_zero']); em.add_r32_imm8('r8',1); em.mov_r32_ripmem('r9',bsyms['col_one']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.xor32('r8'); em.lea_rip('r9',bsyms['status_linebuf']); em.call_iat('SendMessageW')
# character counts
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.mov_r32_ripmem('r11',bsyms['sel_start']); em.sub_r32_r32('r10','r11'); em.mov_ripmem_r32(bsyms['selected_chars'],'r10')
em.lea_rip('rcx',bsyms['status_charsbuf']); em.lea_rip('rdx',rsyms['fmt_chars']); em.mov_r32_ripmem('r8',bsyms['total_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',1); em.lea_rip('r9',bsyms['status_charsbuf']); em.call_iat('SendMessageW')
em.lea_rip('rcx',bsyms['status_selbuf']); em.lea_rip('rdx',rsyms['fmt_selected']); em.mov_r32_ripmem('r8',bsyms['selected_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',2); em.lea_rip('r9',bsyms['status_selbuf']); em.call_iat('SendMessageW')
# zoom percent
em.lea_rip('rcx',bsyms['status_zoombuf']); em.lea_rip('rdx',rsyms['fmt_zoom']); em.mov_r32_ripmem('r8',bsyms['zoom_pct']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',3); em.lea_rip('r9',bsyms['status_zoombuf']); em.call_iat('SendMessageW')
# line endings
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',4); em.lea_rip('r9',rsyms['status_crlf']); em.call_iat('SendMessageW')
# encoding
em.mov_r32_ripmem('rax',bsyms['encoding_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'enc_utf16'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'enc_ansi'); em.lea_rip('r9',rsyms['status_utf8']); em.jmp('enc_send')
em.label('enc_utf16'); em.lea_rip('r9',rsyms['status_utf16']); em.jmp('enc_send')
em.label('enc_ansi'); em.lea_rip('r9',rsyms['status_ansi'])
em.label('enc_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',5); em.call_iat('SendMessageW')
em.label('status_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('exit')
em.mov_r64_ripmem('rcx',bsyms['hfont']); em.test64('rcx'); em.jcc(0x84,'exit_accel'); em.call_iat('DeleteObject')
em.label('exit_accel'); em.mov_r64_ripmem('rcx',bsyms['haccel']); em.test64('rcx'); em.jcc(0x84,'exit_now'); em.call_iat('DestroyAcceleratorTable')
em.label('exit_now'); em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)

# ------------------------------------------------------------------
# Real application WndProc.  Windows sends menu/non-client/resize messages
# directly to this callback (often synchronously), so these cannot be handled
# reliably by peeking only at the outer GetMessage queue.
em.label('wndproc')
em.emit(0x48,0x83,0xEC,0x38)  # sub rsp, 38h: align + shadow + 2 stack args
em.mov_r32_ripmem('r10',bsyms['findmsg_id']); em.cmp_r32_r32('rdx','r10'); em.jcc(0x84,'wp_findreplace')
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
# Live resize must happen synchronously inside WM_SIZE. During caption/border tracking,
# DefWindowProc runs a nested modal sizing loop, so merely posting a resize message can lag.
em.mov_r32_r32('r10','r9'); em.mov_r32_r32('r11','r9'); em.and_r32_imm('r10',0xFFFF); em.shr_r32_imm8('r11',16)
em.mov_ripmem_r32(bsyms['client_w'],'r10'); em.mov_ripmem_r32(bsyms['client_h'],'r11'); em.call_label('resize_children')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_findreplace')
# The common dialog stores its current flags in FINDREPLACE.Flags; forward them to main loop.
em.mov_r32_imm('rdx',0x8003); em.mov_r32_ripmem('r8',bsyms['fr']+24); em.xor32('r9'); em.call_iat('PostMessageW')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_destroy')
em.xor32('rcx'); em.call_iat('PostQuitMessage')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.patch()
text=em.b
if len(text) >= (RDATA_RVA-TEXT_RVA):
    raise RuntimeError(f'text too large: {len(text):x}')

# ---------------- PE writer ----------------
# ---------------- PE writer (v6: one loader-simple section) ----------------
# Keep the exact RVAs used by the machine-code emitter, but put code, strings,
# import table, and the zero-filled runtime buffers into ONE PE section.
# This mirrors the layout style of the earlier 1.5 KiB build that was confirmed
# to load on Windows, while still leaving the big work buffers as virtual-only
# zero-filled memory rather than storing megabytes of zeros in the file.

headers_size = 0x200
section_ptr = headers_size

# Section begins at TEXT_RVA. Preserve the existing absolute RVA plan:
#   code  @ 0x1000
#   rdata @ 0x5000
#   idata @ 0x7000
#   bss   @ 0x8000 (virtual-only tail)
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

out = '/mnt/data/direct_pe_notepad_full_x64_v6.exe'
with open(out, 'wb') as f:
    f.write(hdr)
    f.write(raw)

sha = hashlib.sha256(open(out,'rb').read()).hexdigest()
print(out)
print('size', os.path.getsize(out), 'text', len(text), 'raw', raw_size,
      'section_vsize', section_vsize, 'bss_vsize', BSS_VSIZE)
print('sha256', sha)
