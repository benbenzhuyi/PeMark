import struct, hashlib, os, subprocess, textwrap

IMAGE_BASE = 0x140000000
TEXT_RVA = 0x1000
RDATA_RVA = 0x8000
IDATA_RVA = 0xB000
BSS_RVA = 0xC000
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
wstr('title','Direct PE Markdown Editor x64 V8.3 — No Compiler')
wstr('empty','')
wstr('menu_file','&File')
wstr('menu_edit','&Edit')
wstr('menu_markdown','&Markdown')
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
wstr('m_md_h1','Heading &1\tCtrl+1')
wstr('m_md_h2','Heading &2\tCtrl+2')
wstr('m_md_bold','&Bold\tCtrl+Alt+B')
wstr('m_md_italic','&Italic\tCtrl+I')
wstr('m_md_inlinecode','Inline &Code\tCtrl+`')
wstr('m_md_codeblock','Code Bloc&k\tCtrl+Shift+K')
wstr('m_md_quote','&Quote\tCtrl+Q')
wstr('m_md_bullet','&Bullet List\tCtrl+Shift+8')
wstr('m_md_link','&Link\tCtrl+K')
wstr('m_zoom','&Zoom')
wstr('m_zoomin','Zoom &In\tCtrl++ / Ctrl+Wheel Up')
wstr('m_zoomout','Zoom &Out\tCtrl+- / Ctrl+Wheel Down')
wstr('m_zoomreset','Restore &Default Zoom\tCtrl+0')
wstr('m_wrap','&Word Wrap\tCtrl+Shift+W')
wstr('m_status','&Status Bar\tCtrl+Shift+B')
wstr('m_preview','Markdown &Preview\tCtrl+Shift+P')
wstr('m_outline','&Outline\tCtrl+B')
wstr('m_light','&Light')
wstr('m_dark','&Dark\tCtrl+Alt+T')
wstr('m_about','&About\tF1')
wstr('open_title','Open Markdown or text file')
wstr('save_title','Save Markdown file as')
wstr('defext','md')
wstr('class_status','msctls_statusbar32')
wstr('font_face','Microsoft YaHei UI')
wstr('font_code','Consolas')
wstr('class_richedit','RICHEDIT50W')
wstr('class_listbox','LISTBOX')
wstr('dll_msftedit','Msftedit.dll')
wstr('theme_dark_name','DarkMode_Explorer')
wstr('theme_light_name','Explorer')
wstr('dll_uxtheme','uxtheme.dll')
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
    (FVIRTKEY|FCONTROL|FSHIFT, 0x50, 1306),           # Ctrl+Shift+P Markdown preview/source
    (FVIRTKEY|FCONTROL, 0x42, 1307),                  # Ctrl+B Outline
    (FVIRTKEY|FCONTROL|FALT, 0x54, 1312),             # Ctrl+Alt+T Toggle Light/Dark
    (FVIRTKEY|FCONTROL, 0x31, 1401),                  # Ctrl+1 Heading 1
    (FVIRTKEY|FCONTROL, 0x32, 1402),                  # Ctrl+2 Heading 2
    (FVIRTKEY|FCONTROL|FALT, 0x42, 1403),             # Ctrl+Alt+B Bold (Ctrl+B is Outline)
    (FVIRTKEY|FCONTROL, 0x49, 1404),                  # Ctrl+I Italic
    (FVIRTKEY|FCONTROL, 0xC0, 1405),                  # Ctrl+` Inline code
    (FVIRTKEY|FCONTROL|FSHIFT, 0x4B, 1406),           # Ctrl+Shift+K Code block
    (FVIRTKEY|FCONTROL, 0x51, 1407),                  # Ctrl+Q Quote
    (FVIRTKEY|FCONTROL|FSHIFT, 0x38, 1408),           # Ctrl+Shift+8 Bullet list
    (FVIRTKEY|FCONTROL, 0x4B, 1409),                  # Ctrl+K Link
    (FVIRTKEY, 0x70, 1201),                           # F1
]
ACCEL_COUNT=len(_accels)
add_bytes('accels', b''.join(struct.pack('<BxHH', *a) for a in _accels), 2)
# OPENFILENAME filter requires embedded NUL separators and double-NUL terminator.
add_bytes('filter', ('Markdown files (*.md;*.markdown)\0*.md;*.markdown\0Text files (*.txt)\0*.txt\0All files (*.*)\0*.*\0\0').encode('utf-16le'), 2)
wstr('md_h1','# ')
wstr('md_h2','## ')
wstr('md_bold','**')
wstr('md_italic','*')
wstr('md_inline','`')
wstr('md_code_pre','```\r\n')
wstr('md_code_post','\r\n```')
wstr('md_quote','> ')
wstr('md_bullet','- ')
wstr('md_link_pre','[')
wstr('md_link_post','](https://)')
wstr('err_title','Direct PE Markdown Editor')
wstr('err_open','Could not open or read the selected file.')
wstr('err_save','Could not save the file.')
wstr('err_large','The file is too large for this build (limit: about 1 MiB).')
wstr('err_decode','The file could not be decoded as UTF-8/ANSI text.')
wstr('about','Direct PE Markdown Editor x64 V8.3\r\n\r\nNative PE32+ and x86-64 machine code generated directly, without a C/C++ compiler, assembler, or linker.\r\n\r\nV8.3 repairs the machine-code UTF-16 scanner, Markdown rendering, dark menu chrome, themed preview colors, and the outline presentation.')

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
bss_alloc('hwnd_preview', 8, 8)
bss_alloc('hwnd_outline', 8, 8)
bss_alloc('hwnd_status', 8, 8)
bss_alloc('hfont', 8, 8)
bss_alloc('old_hfont', 8, 8)
bss_alloc('hmenu_view', 8, 8)
bss_alloc('hmenu_zoom', 8, 8)
bss_alloc('haccel', 8, 8)
bss_alloc('hbrush_edit', 8, 8)
bss_alloc('hbrush_outline', 8, 8)
bss_alloc('hbrush_menu', 8, 8)
bss_alloc('findreplace_hwnd', 8, 8)
bss_alloc('wrap_flag', 4, 4)
bss_alloc('status_flag', 4, 4)
bss_alloc('preview_flag', 4, 4)
bss_alloc('outline_flag', 4, 4)
bss_alloc('theme_dark', 4, 4)
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
bss_alloc('content_x', 4, 4)
bss_alloc('content_w', 4, 4)
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
bss_alloc('charfmt', 116, 16)
bss_alloc('theme_bool', 4, 4)
bss_alloc('theme_name_ptr', 8, 8)
bss_alloc('uxtheme_mod', 8, 8)
bss_alloc('fn_allowdark', 8, 8)
bss_alloc('fn_setpreferred', 8, 8)
bss_alloc('fn_flushmenus', 8, 8)
bss_alloc('outline_count', 4, 4)
bss_alloc('heading_index', 4, 4)
bss_alloc('drawitem_ptr', 8, 8)
bss_alloc('draw_rect', 16, 8)
bss_alloc('paint_hdc', 8, 8)
bss_alloc('nav_hwnd', 8, 8)
bss_alloc('style_count', 4, 4)
bss_alloc('style_start', 4096*4, 16)
bss_alloc('style_end', 4096*4, 16)
bss_alloc('style_type', 4096*4, 16)
bss_alloc('outline_srcpos', 2048*4, 16)
bss_alloc('outline_renderpos', 2048*4, 16)
bss_alloc('outline_level', 2048*4, 16)
bss_alloc('outline_titlebuf', 512*2, 16)
bss_alloc('menu_textbuf', 256*2, 16)
bss_alloc('line_src_start', 4, 4)
bss_alloc('heading_out_start', 4, 4)
bss_alloc('heading_out_end', 4, 4)
bss_alloc('heading_level', 4, 4)
bss_alloc('quote_out_start', 4, 4)
bss_alloc('bold_out_start', 4, 4)
bss_alloc('italic_out_start', 4, 4)
bss_alloc('code_out_start', 4, 4)
bss_alloc('link_out_start', 4, 4)
bss_alloc('codeblock_out_start', 4, 4)
bss_alloc('inline_flags', 4, 4)
bss_alloc('line_flags', 4, 4)
bss_alloc('bold_flag', 4, 4)
bss_alloc('italic_flag', 4, 4)
bss_alloc('inlinecode_flag', 4, 4)
bss_alloc('link_flag', 4, 4)
bss_alloc('codeblock_flag', 4, 4)
WIDE_CHARS = 1_048_576
MAX_FILE_BYTES = 1_048_000
BYTE_CAP = 4_194_304
bss_alloc('widebuf', WIDE_CHARS*2, 16)
bss_alloc('previewbuf', WIDE_CHARS*2, 16)
bss_alloc('bytebuf', BYTE_CAP+16, 16)
BSS_VSIZE = align(bss_off, 0x1000)

# ---------------- IDATA ----------------
imports = {
    'KERNEL32.dll': [
        'ExitProcess','CreateFileW','ReadFile','WriteFile','CloseHandle','GetFileSize',
        'MultiByteToWideChar','WideCharToMultiByte','lstrcpyW','lstrlenW','GetModuleHandleW','CompareStringOrdinal','LoadLibraryW','GetProcAddress','MulDiv'
    ],
    'USER32.dll': [
        'CreateWindowExW','GetMessageW','TranslateMessage','DispatchMessageW','IsWindow',
        'CreateMenu','CreatePopupMenu','AppendMenuW','GetWindowTextLengthW','GetWindowTextW',
        'SetWindowTextW','SendMessageW','MoveWindow','MessageBoxW','SetFocus',
        'RegisterClassExW','DefWindowProcW','PostQuitMessage','PostMessageW','LoadCursorW',
        'DestroyWindow','ShowWindow','CheckMenuItem','GetWindowRect','GetClientRect','wsprintfW','RegisterWindowMessageW','InvalidateRect','UpdateWindow',
        'CreateAcceleratorTableW','TranslateAcceleratorW','DestroyAcceleratorTable','IsDialogMessageW','SetForegroundWindow','DrawMenuBar','DrawTextW','FillRect','GetMenuStringW'
    ],
    'COMDLG32.dll': ['GetOpenFileNameW','GetSaveFileNameW','FindTextW','ReplaceTextW'],
    'SHLWAPI.dll': ['StrStrW','StrStrIW'],
    'COMCTL32.dll': ['InitCommonControlsEx'],
    'GDI32.dll': ['CreateFontW','DeleteObject','CreateSolidBrush','SetTextColor','SetBkColor','SetBkMode','GetClipBox'],
    'UXTHEME.dll': ['SetWindowTheme'],
    'DWMAPI.dll': ['DwmSetWindowAttribute'],
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
    def call_r64(self,reg):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0xFF,0xD0|(r&7))
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
        # mov word ptr [base + index*2], 0
        b,i=REG[base],REG[index]
        self.emit(0x66); self.rex(x=(i>>3)&1,b=(b>>3)&1)
        self.emit(0xC7,0x04,0x40|((i&7)<<3)|(b&7),0,0)
    def movzx_r32_word_index2(self,dst,base,index):
        d,b,i=REG[dst],REG[base],REG[index]
        self.rex(r=(d>>3)&1,x=(i>>3)&1,b=(b>>3)&1)
        self.emit(0x0F,0xB7,0x04|((d&7)<<3),0x40|((i&7)<<3)|(b&7))
    def mov_word_index2_reg(self,base,index,src):
        b,i,r=REG[base],REG[index],REG[src]
        self.emit(0x66); self.rex(r=(r>>3)&1,x=(i>>3)&1,b=(b>>3)&1)
        self.emit(0x89,0x04|((r&7)<<3),0x40|((i&7)<<3)|(b&7))
    def mov_word_index2_imm16(self,base,index,imm):
        b,i=REG[base],REG[index]
        self.emit(0x66); self.rex(x=(i>>3)&1,b=(b>>3)&1)
        self.emit(0xC7,0x04,0x40|((i&7)<<3)|(b&7),u16(imm))
    def cmp_r64_r64(self,a,b):
        aa,bb=REG[a],REG[b]; self.rex(w=1,r=(bb>>3)&1,b=(aa>>3)&1); self.emit(0x39,0xC0|((bb&7)<<3)|(aa&7))
    def mov_ptr_r32(self,base,src):
        b,s=REG[base],REG[src]; self.rex(r=(s>>3)&1,b=(b>>3)&1); self.emit(0x89,0x00|((s&7)<<3)|(b&7))
    def mov_r32_ptr(self,dst,base):
        d,b=REG[dst],REG[base]; self.rex(r=(d>>3)&1,b=(b>>3)&1); self.emit(0x8B,0x00|((d&7)<<3)|(b&7))
    def mov_byte_ptr_imm8(self,base,imm):
        b=REG[base]; self.rex(b=(b>>3)&1); self.emit(0xC6,0x00|(b&7),imm&255)
    def mov_mreg_imm32(self,base,off,imm):
        b=REG[base]; self.rex(b=(b>>3)&1); self.emit(0xC7,0x40|(b&7),off&255,u32(imm))
    def mov_mreg_reg32(self,base,off,src):
        b,s=REG[base],REG[src]; self.rex(r=(s>>3)&1,b=(b>>3)&1); self.emit(0x89,0x40|((s&7)<<3)|(b&7),off&255)
    def mov_r32_mreg(self,dst,base,off):
        d,b=REG[dst],REG[base]; self.rex(r=(d>>3)&1,b=(b>>3)&1); self.emit(0x8B,0x40|((d&7)<<3)|(b&7),off&255)
    def mov_r64_mreg(self,dst,base,off):
        d,b=REG[dst],REG[base]; self.rex(w=1,r=(d>>3)&1,b=(b>>3)&1); self.emit(0x8B,0x40|((d&7)<<3)|(b&7),off&255)
    def mov_mreg_reg64(self,base,off,src):
        b,s=REG[base],REG[src]; self.rex(w=1,r=(s>>3)&1,b=(b>>3)&1); self.emit(0x89,0x40|((s&7)<<3)|(b&7),off&255)

em=E()
# stack alignment + ample shadow/stack-arg area
em.emit(0x48,0x81,0xEC,u32(0x88))  # sub rsp, 0x88

# Register a REAL top-level window class.  V2 used the predefined STATIC class
# as the main window; STATIC's system wndproc is not an application frame wndproc,
# so synchronous WM_COMMAND/non-client messages never reached our queue handler.
em.xor32('rcx'); em.call_iat('GetModuleHandleW'); em.mov_r64_r64('r15','rax')
em.mov_ripmem_imm32(bsyms['wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['status_flag'],1)
em.mov_ripmem_imm32(bsyms['preview_flag'],0)
em.mov_ripmem_imm32(bsyms['outline_flag'],1)
em.mov_ripmem_imm32(bsyms['theme_dark'],0)
em.mov_ripmem_imm32(bsyms['zoom_pct'],100)
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_ripmem_imm32(bsyms['find_flags'],1)
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['client_w'],884)
em.mov_ripmem_imm32(bsyms['client_h'],590)
# Resolve the modern Windows dark-mode helpers exported by ordinal from uxtheme.dll.
# These APIs are undocumented but are the mechanism used by native Win32 apps on
# current Windows 10/11 to theme classic menus and scrollbars consistently.
em.lea_rip('rcx',rsyms['dll_uxtheme']); em.call_iat('LoadLibraryW'); em.mov_ripmem_r64(bsyms['uxtheme_mod'],'rax'); em.test64('rax'); em.jcc(0x84,'darkapi_resolved')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',133); em.call_iat('GetProcAddress'); em.mov_ripmem_r64(bsyms['fn_allowdark'],'rax')
em.mov_r64_ripmem('rcx',bsyms['uxtheme_mod']); em.mov_r32_imm('rdx',135); em.call_iat('GetProcAddress'); em.mov_ripmem_r64(bsyms['fn_setpreferred'],'rax')
em.mov_r64_ripmem('rcx',bsyms['uxtheme_mod']); em.mov_r32_imm('rdx',136); em.call_iat('GetProcAddress'); em.mov_ripmem_r64(bsyms['fn_flushmenus'],'rax')
# Start in ForceLight mode (PreferredAppMode = 3) so the first frame matches the checked menu item.
em.mov_r64_ripmem('rax',bsyms['fn_setpreferred']); em.test64('rax'); em.jcc(0x84,'darkapi_resolved'); em.mov_r32_imm('rcx',3); em.call_r64('rax')
em.label('darkapi_resolved')
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

# Markdown editing commands
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r14','rax')
append_imm('r14',0,1401,'m_md_h1'); append_imm('r14',0,1402,'m_md_h2'); append_sep('r14')
append_imm('r14',0,1403,'m_md_bold'); append_imm('r14',0,1404,'m_md_italic'); append_imm('r14',0,1405,'m_md_inlinecode'); append_imm('r14',0,1406,'m_md_codeblock'); append_sep('r14')
append_imm('r14',0,1407,'m_md_quote'); append_imm('r14',0,1408,'m_md_bullet'); append_imm('r14',0,1409,'m_md_link')
append_popup('rdi','r14','menu_markdown')

# View -> Zoom, Preview, Outline, Word Wrap, Status Bar, Light, Dark
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r14','rax'); em.mov_ripmem_r64(bsyms['hmenu_view'],'r14')
em.call_iat('CreatePopupMenu'); em.mov_r64_r64('r12','rax'); em.mov_ripmem_r64(bsyms['hmenu_zoom'],'r12')
append_imm('r12',0,1301,'m_zoomin'); append_imm('r12',0,1302,'m_zoomout'); append_imm('r12',0,1303,'m_zoomreset')
append_popup('r14','r12','m_zoom'); append_sep('r14')
append_imm('r14',0,1306,'m_preview'); append_imm('r14',0x8,1307,'m_outline')
append_sep('r14'); append_imm('r14',0x8,1304,'m_wrap'); append_imm('r14',0x8,1305,'m_status')
append_sep('r14'); append_imm('r14',0x8,1310,'m_light'); append_imm('r14',0,1311,'m_dark')
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
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50211044)
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
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_status']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50000000)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,2,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_status'],'rax')
em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0404); em.mov_r32_imm('r8',6); em.lea_rip('r9',rsyms['status_parts']); em.call_iat('SendMessageW')
# Load the system Rich Edit engine and create a hidden full-window rendered Markdown surface.
em.lea_rip('rcx',rsyms['dll_msftedit']); em.call_iat('LoadLibraryW'); em.test64('rax'); em.jcc(0x84,'exit')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_richedit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x40211844)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,3,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_preview'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Left Markdown outline. A simple native listbox keeps the Direct-PE build small;
# heading levels are represented by indentation and each item stores source/render positions.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_listbox']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x50210151)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,230); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,4,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x01A0); em.xor32('r8'); em.mov_r32_imm('r9',30); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.call_label('apply_theme'); em.call_label('update_preview'); em.call_label('resize_children'); em.call_label('update_status')

# Message pump
em.label('msg_loop')
em.lea_rip('r12',bsyms['msg']); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.call_iat('GetMessageW')
em.test32('rax'); em.jcc(0x8E,'exit') # jle
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x8001); em.jcc(0x84,'command')  # WM_APP+1 posted by wndproc
em.cmp_r32_imm('rax',0x8002); em.jcc(0x84,'resize_event') # legacy/private resize event
em.cmp_r32_imm('rax',0x8003); em.jcc(0x84,'findreplace_event')
em.cmp_r32_imm('rax',0x8004); em.jcc(0x84,'document_changed_event')
em.cmp_r32_imm('rax',0x8005); em.jcc(0x84,'outline_select_event')
# Ctrl+mouse-wheel zoom. WM_MOUSEWHEEL is queued for the focused child EDIT window,
# so intercept it in the thread message pump before DispatchMessageW.
em.cmp_r32_imm('rax',0x020A); em.jcc(0x84,'mousewheel_event')
em.jmp('dispatch')

em.label('document_changed_event')
em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('outline_select_event')
em.call_label('navigate_outline'); em.jmp('msg_loop')

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
                  (1301,'cmd_zoomin'),(1302,'cmd_zoomout'),(1303,'cmd_zoomreset'),(1304,'cmd_wrap'),(1305,'cmd_status'),(1306,'cmd_preview'),(1307,'cmd_outline'),(1310,'cmd_light'),(1311,'cmd_dark'),(1312,'cmd_theme_toggle'),
                  (1401,'cmd_md_h1'),(1402,'cmd_md_h2'),(1403,'cmd_md_bold'),(1404,'cmd_md_italic'),(1405,'cmd_md_inline'),(1406,'cmd_md_codeblock'),(1407,'cmd_md_quote'),(1408,'cmd_md_bullet'),(1409,'cmd_md_link')]:
    em.cmp_r32_imm('rax',cid); em.jcc(0x84,label)
em.jmp('dispatch')

em.label('cmd_new')
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rax',bsyms['current_path']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['encoding_state'],0); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

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
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('decode_empty')
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_r64_r64('rcx','rsi'); em.lea_rip('rdx',rsyms['empty']); em.call_iat('SetWindowTextW')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('decode_utf16')
em.mov_ripmem_imm32(bsyms['encoding_state'],1)
em.lea_rip('rdx',bsyms['bytebuf']); em.add_r64_imm8('rdx',2); em.mov_r64_r64('rcx','rsi'); em.call_iat('SetWindowTextW')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

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
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.mov_ripmem_imm32(bsyms['encoding_state'],0); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('save_fail_close'); em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
em.label('err_save'); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_save']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# Edit commands
for label,msg in [('cmd_undo',0x00C7),('cmd_cut',0x0300),('cmd_paste',0x0302)]:
    em.label(label); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',msg); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_copy'); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x0301); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.jmp('msg_loop')
em.label('cmd_selectall'); em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.mov_r32_imm('r9',0xFFFFFFFF); em.call_iat('SendMessageW'); em.call_label('update_status'); em.jmp('msg_loop')

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
em.call_label('replace_if_match'); em.call_label('find_next_select'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('fr_replaceall')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],0); em.xor32('rax'); em.mov_ripmem_r32(bsyms['replace_count'],'rax')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.label('replaceall_loop')
em.call_label('find_next_select'); em.test32('rax'); em.jcc(0x84,'replaceall_done')
em.call_label('replace_if_match'); em.test32('rax'); em.jcc(0x84,'replaceall_done')
em.mov_r32_ripmem('rax',bsyms['replace_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['replace_count'],'rax'); em.jmp('replaceall_loop')
em.label('replaceall_done')
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1); em.call_label('update_preview'); em.call_label('update_status')
em.lea_rip('rcx',bsyms['status_msgbuf']); em.lea_rip('rdx',rsyms['fmt_replaced']); em.mov_r32_ripmem('r8',bsyms['replace_count']); em.call_iat('wsprintfW')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',bsyms['status_msgbuf']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x40); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# Markdown editing commands. Prefix commands act on the current line; wrappers surround the selection.
em.label('cmd_md_h1'); em.lea_rip('r10',rsyms['md_h1']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_h2'); em.lea_rip('r10',rsyms['md_h2']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_bold'); em.lea_rip('r10',rsyms['md_bold']); em.lea_rip('r11',rsyms['md_bold']); em.call_label('md_wrap_selection'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_italic'); em.lea_rip('r10',rsyms['md_italic']); em.lea_rip('r11',rsyms['md_italic']); em.call_label('md_wrap_selection'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_inline'); em.lea_rip('r10',rsyms['md_inline']); em.lea_rip('r11',rsyms['md_inline']); em.call_label('md_wrap_selection'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_codeblock'); em.lea_rip('r10',rsyms['md_code_pre']); em.lea_rip('r11',rsyms['md_code_post']); em.call_label('md_wrap_selection'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_quote'); em.lea_rip('r10',rsyms['md_quote']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_bullet'); em.lea_rip('r10',rsyms['md_bullet']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_link'); em.lea_rip('r10',rsyms['md_link_pre']); em.lea_rip('r11',rsyms['md_link_post']); em.call_label('md_wrap_selection'); em.call_label('md_select_link_url'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

# View / Zoom commands
em.label('cmd_zoomin')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.cmp_r32_imm('rax',200); em.jcc(0x83,'msg_loop') # jae
em.add_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomout')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.cmp_r32_imm('rax',50); em.jcc(0x86,'msg_loop') # jbe
em.sub_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomreset')
em.mov_ripmem_imm32(bsyms['zoom_pct'],100); em.call_label('apply_zoom'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

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
em.mov_r32_imm('r9',0x50211044); em.jmp('wrap_style_ready')
em.label('wrap_style_off'); em.mov_r32_imm('r9',0x503110C4)
em.label('wrap_style_ready')
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',MAX_FILE_BYTES); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.mov_r32_ripmem('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.call_label('resize_children'); em.call_label('update_preview'); em.call_label('update_status')
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'wrap_focus_source')
em.mov_r64_r64('rcx','rsi'); em.xor32('rdx'); em.call_iat('ShowWindow'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow'); em.call_iat('SetFocus'); em.jmp('msg_loop')
em.label('wrap_focus_source'); em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus'); em.jmp('msg_loop')

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

em.label('cmd_preview')
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'preview_show')
# Back to Markdown source editing mode.
em.mov_ripmem_imm32(bsyms['preview_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.jmp('msg_loop')
em.label('preview_show')
# Full-window rendered Markdown mode: hide the source EDIT and show Rich Edit rendering.
em.mov_ripmem_imm32(bsyms['preview_flag'],1)
em.call_label('update_preview')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_iat('SetFocus'); em.jmp('msg_loop')

em.label('cmd_outline')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'outline_show')
em.mov_ripmem_imm32(bsyms['outline_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.jmp('msg_loop')
em.label('outline_show')
em.mov_ripmem_imm32(bsyms['outline_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.call_label('update_preview'); em.call_label('resize_children'); em.jmp('msg_loop')

em.label('cmd_light')
em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.call_label('apply_theme'); em.call_label('update_preview'); em.jmp('msg_loop')
em.label('cmd_dark')
em.mov_ripmem_imm32(bsyms['theme_dark'],1); em.call_label('apply_theme'); em.call_label('update_preview'); em.jmp('msg_loop')
em.label('cmd_theme_toggle')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_toggle_dark')
em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.jmp('theme_toggle_apply')
em.label('theme_toggle_dark'); em.mov_ripmem_imm32(bsyms['theme_dark'],1)
em.label('theme_toggle_apply'); em.call_label('apply_theme'); em.call_label('update_preview'); em.jmp('msg_loop')

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
# Helper: resize Outline + active full-window Edit/Preview + native status bar.
em.label('resize_children')
em.emit(0x48,0x83,0xEC,0x38)
em.xor32('rax'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'resize_content')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'resize_content')
em.mov_r32_imm('rdx',0x0005); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetWindowRect')
em.mov_r32_ripmem('rax',bsyms['rect']+12); em.mov_r32_ripmem('r10',bsyms['rect']+4); em.sub_r32_r32('rax','r10'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.label('resize_content')
# Cache x/width of the document surface.
em.mov_ripmem_imm32(bsyms['content_x'],0)
em.mov_r32_ripmem('r10',bsyms['client_w']); em.mov_ripmem_r32(bsyms['content_w'],'r10')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'resize_doc')
em.mov_ripmem_imm32(bsyms['content_x'],230)
em.mov_r32_ripmem('r10',bsyms['client_w']); em.sub_r32_imm8('r10',100); em.sub_r32_imm8('r10',100); em.sub_r32_imm8('r10',30); em.mov_ripmem_r32(bsyms['content_w'],'r10')
# Outline fills the usable height on the left.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'resize_doc')
em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax')
em.xor32('rdx'); em.xor32('r8'); em.mov_r32_imm('r9',230); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_doc')
# Source edit surface.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'resize_preview_surface')
em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax'); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_preview_surface')
# Rendered Rich Edit surface, at exactly the same rectangle.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'resize_ret')
em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax'); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'font_preview'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.label('font_preview'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'font_outline'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.label('font_outline'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'font_delete_old'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.label('font_delete_old'); em.mov_r64_ripmem('rcx',bsyms['old_hfont']); em.test64('rcx'); em.jcc(0x84,'font_ret'); em.call_iat('DeleteObject')
em.label('font_ret'); em.emit(0x48,0x81,0xC4,u32(0x88)); em.emit(0xC3)

# Helper: wrap current selection with strings at r10(prefix) and r11(suffix).
em.label('md_wrap_selection')
em.emit(0x48,0x83,0xEC,0x48)
# preserve pointers on stack
em.mov_mrsp_reg64(0x30,'r10'); em.mov_mrsp_reg64(0x38,'r11')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
# suffix at original selection end
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_end']); em.mov_r32_r32('r9','r8'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C2); em.mov_r32_imm('r8',1); em.emit(0x4C,0x8B,0x4C,0x24,0x38); em.call_iat('SendMessageW')
# prefix at original selection start
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.mov_r32_r32('r9','r8'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C2); em.mov_r32_imm('r8',1); em.emit(0x4C,0x8B,0x4C,0x24,0x30); em.call_iat('SendMessageW')
# prefix length
em.emit(0x48,0x8B,0x4C,0x24,0x30); em.call_iat('lstrlenW'); em.mov_r32_r32('r10','rax')
# restore/select inner text; no selection -> caret between delimiters
em.mov_r32_ripmem('r8',bsyms['sel_start']); em.add_r32_r32('r8','r10')
em.mov_r32_ripmem('r9',bsyms['sel_end']); em.add_r32_r32('r9','r10')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.add_r64_imm8('rsp',0x48); em.emit(0xC3)

# Helper: after Ctrl+K wrapping, place the caret immediately after the inserted
# https:// prefix so the user can type the destination URL without another click.
# Original sel_end is still the pre-insertion end; final caret = sel_end + 11.
em.label('md_select_link_url')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('r8',bsyms['sel_end']); em.add_r32_imm8('r8',11)
em.mov_r32_r32('r9','r8')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: prefix current line with string at r10.
em.label('md_prefix_line')
em.emit(0x41,0x55)  # push r13
em.emit(0x48,0x83,0xEC,0x40); em.mov_mrsp_reg64(0x30,'r10')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C9); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r32_r32('r8','rax'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00BB); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r32_r32('r13','rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_r32('r8','r13'); em.mov_r32_r32('r9','r13'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00C2); em.mov_r32_imm('r8',1); em.emit(0x4C,0x8B,0x4C,0x24,0x30); em.call_iat('SendMessageW')
em.emit(0x48,0x8B,0x4C,0x24,0x30); em.call_iat('lstrlenW'); em.mov_r32_r32('r10','rax')
em.mov_r32_ripmem('r8',bsyms['sel_start']); em.add_r32_r32('r8','r10'); em.mov_r32_ripmem('r9',bsyms['sel_end']); em.add_r32_r32('r9','r10')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.add_r64_imm8('rsp',0x40); em.emit(0x41,0x5D); em.emit(0xC3)

# Helper: append a rich-format span. Inputs: r8d=start, r9d=end, r10d=style.
em.label('add_style')
em.mov_r32_ripmem('r11',bsyms['style_count']); em.cmp_r32_imm('r11',4096); em.jcc(0x83,'add_style_ret')
em.mov_r32_r32('rax','r11'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.lea_rip('rcx',bsyms['style_start']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r8')
em.lea_rip('rcx',bsyms['style_end']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r9')
em.lea_rip('rcx',bsyms['style_type']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r10')
em.add_r32_imm8('r11',1); em.mov_ripmem_r32(bsyms['style_count'],'r11')
em.label('add_style_ret'); em.emit(0xC3)

# Helper: rebuild the Markdown outline directly from the SOURCE buffer.
# This is deliberately independent of the Rich Edit render buffer so outline
# population cannot be broken by Rich Edit newline normalization or formatting ranges.
em.label('rebuild_outline')
em.emit(0x56); em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57)
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_imm32(bsyms['outline_count'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'outline_rebuild_ret')
em.mov_r32_imm('rdx',0x0184); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.lea_rip('rsi',bsyms['widebuf']); em.xor32('r12'); em.mov_r32_imm('r14',1)
em.label('outline_scan_loop')
em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'outline_rebuild_ret')
# LF starts a new logical source line. CR is ignored and consumed normally.
em.cmp_r32_imm('rax',0x0A); em.jcc(0x85,'outline_scan_not_lf'); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.jmp('outline_scan_loop')
em.label('outline_scan_not_lf')
em.test32('r14'); em.jcc(0x84,'outline_scan_advance')
# ATX headings may be indented by up to three ASCII spaces.
em.xor32('r10')
em.label('outline_leadspace_loop'); em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x20); em.jcc(0x85,'outline_leadspace_done'); em.cmp_r32_imm('r10',3); em.jcc(0x83,'outline_leadspace_done'); em.add_r32_imm8('r12',1); em.add_r32_imm8('r10',1); em.jmp('outline_leadspace_loop')
em.label('outline_leadspace_done'); em.movzx_r32_word_index2('rax','rsi','r12')
# ATX heading = 1..6 hashes followed by one space.
em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'outline_mark_nonheading')
em.xor32('r13'); em.mov_r32_r32('r11','r12')
em.label('outline_hash_loop'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'outline_hash_done'); em.cmp_r32_imm('r13',6); em.jcc(0x83,'outline_hash_done'); em.add_r32_imm8('r13',1); em.add_r32_imm8('r11',1); em.jmp('outline_hash_loop')
em.label('outline_hash_done'); em.test32('r13'); em.jcc(0x84,'outline_mark_nonheading'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x20); em.jcc(0x85,'outline_mark_nonheading')
# Build visible title with two-space indentation per depth below H1.
em.lea_rip('rcx',bsyms['outline_titlebuf']); em.xor32('r8'); em.mov_r32_r32('r15','r13')
em.label('outline_rb_indent'); em.cmp_r32_imm('r15',1); em.jcc(0x86,'outline_rb_copy_setup'); em.mov_word_index2_imm16('rcx','r8',0x20); em.add_r32_imm8('r8',1); em.mov_word_index2_imm16('rcx','r8',0x20); em.add_r32_imm8('r8',1); em.sub_r32_imm8('r15',1); em.jmp('outline_rb_indent')
em.label('outline_rb_copy_setup'); em.mov_r32_r32('r10','r11'); em.add_r32_imm8('r10',1)
em.label('outline_rb_copy'); em.movzx_r32_word_index2('rax','rsi','r10'); em.test32('rax'); em.jcc(0x84,'outline_rb_copy_done'); em.cmp_r32_imm('rax',0x0D); em.jcc(0x84,'outline_rb_copy_done'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x84,'outline_rb_copy_done'); em.cmp_r32_imm('r8',500); em.jcc(0x83,'outline_rb_copy_done'); em.mov_word_index2_reg('rcx','r8','rax'); em.add_r32_imm8('r8',1); em.add_r32_imm8('r10',1); em.jmp('outline_rb_copy')
em.label('outline_rb_copy_done'); em.mov_word_index2_zero('rcx','r8')
# Add the row. Preserve the source line terminator across SendMessageW in nonvolatile r14.
em.mov_r32_r32('r14','r10')
# Store the SOURCE line start at the actual returned listbox index.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0180); em.xor32('r8'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'outline_after_add'); em.cmp_r32_imm('rax',2048); em.jcc(0x83,'outline_after_add')
em.mov_r32_r32('r11','rax'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.lea_rip('rcx',bsyms['outline_srcpos']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r12'); em.lea_rip('rcx',bsyms['outline_renderpos']); em.add_r64_r64('rcx','rax'); em.xor32('r15'); em.mov_ptr_r32('rcx','r15'); em.lea_rip('rcx',bsyms['outline_level']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r13')
em.mov_r32_ripmem('r15',bsyms['outline_count']); em.add_r32_imm8('r15',1); em.mov_ripmem_r32(bsyms['outline_count'],'r15')
em.label('outline_after_add')
# Continue scanning from the preserved heading-line terminator.
em.mov_r32_r32('r12','r14'); em.xor32('r14'); em.jmp('outline_scan_loop')
em.label('outline_mark_nonheading'); em.xor32('r14')
em.label('outline_scan_advance'); em.add_r32_imm8('r12',1); em.jmp('outline_scan_loop')
em.label('outline_rebuild_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0x5E); em.emit(0xC3)

# Legacy helper retained but no longer used by V8.1's source-driven outline builder.
em.label('add_outline_heading')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rax',bsyms['hwnd_outline']); em.test64('rax'); em.jcc(0x84,'outline_add_ret')
em.mov_r32_ripmem('r11',bsyms['heading_level']); em.test32('r11'); em.jcc(0x84,'outline_add_ret')
em.lea_rip('rcx',bsyms['outline_titlebuf']); em.xor32('r8')
# Indent two spaces for every heading level below H1.
em.label('outline_indent_loop'); em.cmp_r32_imm('r11',1); em.jcc(0x86,'outline_copy_setup')
em.mov_word_index2_imm16('rcx','r8',0x20); em.add_r32_imm8('r8',1); em.mov_word_index2_imm16('rcx','r8',0x20); em.add_r32_imm8('r8',1); em.sub_r32_imm8('r11',1); em.jmp('outline_indent_loop')
em.label('outline_copy_setup')
em.mov_r32_ripmem('r9',bsyms['heading_out_start']); em.mov_r32_ripmem('r10',bsyms['heading_out_end'])
# Do not include the CR from CRLF in the outline title.
em.test32('r10'); em.jcc(0x84,'outline_copy_loop')
em.mov_r32_r32('rax','r10'); em.sub_r32_imm8('rax',1); em.lea_rip('rdx',bsyms['previewbuf']); em.movzx_r32_word_index2('r11','rdx','rax'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x85,'outline_copy_loop'); em.sub_r32_imm8('r10',1)
em.label('outline_copy_loop')
em.cmp_r32_r32('r9','r10'); em.jcc(0x83,'outline_copy_done'); em.cmp_r32_imm('r8',500); em.jcc(0x83,'outline_copy_done')
em.lea_rip('rdx',bsyms['previewbuf']); em.movzx_r32_word_index2('rax','rdx','r9'); em.mov_word_index2_reg('rcx','r8','rax'); em.add_r32_imm8('r8',1); em.add_r32_imm8('r9',1); em.jmp('outline_copy_loop')
em.label('outline_copy_done'); em.mov_word_index2_zero('rcx','r8')
# LB_ADDSTRING(outline, title)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0180); em.xor32('r8'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'outline_add_ret'); em.cmp_r32_imm('rax',2048); em.jcc(0x83,'outline_add_ret')
# Store source and rendered positions at returned listbox index.
em.mov_r32_r32('r11','rax'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.lea_rip('rcx',bsyms['outline_srcpos']); em.add_r64_r64('rcx','rax'); em.mov_r32_ripmem('r10',bsyms['line_src_start']); em.mov_ptr_r32('rcx','r10')
em.lea_rip('rcx',bsyms['outline_renderpos']); em.add_r64_r64('rcx','rax'); em.mov_r32_ripmem('r10',bsyms['heading_out_start']); em.mov_ptr_r32('rcx','r10')
em.label('outline_add_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: apply base font, text color and page background to the Rich Edit preview.
em.label('apply_preview_base')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.test64('rax'); em.jcc(0x84,'preview_base_ret')
# Rich Edit background.
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0443); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['theme_dark']); em.test32('r9'); em.jcc(0x84,'preview_bg_light'); em.mov_r32_imm('r9',0x001E1E1E); em.jmp('preview_bg_send')
em.label('preview_bg_light'); em.mov_r32_imm('r9',0x00FFFFFF)
em.label('preview_bg_send'); em.call_iat('SendMessageW')
# CHARFORMATW: base size / color / face for the whole rendered document.
em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_imm32('r11',0,116); em.mov_mreg_imm32('r11',4,0xE0000000); em.mov_mreg_imm32('r11',8,0)
em.mov_r32_imm('rcx',220); em.mov_r32_ripmem('rdx',bsyms['zoom_pct']); em.mov_r32_imm('r8',100); em.call_iat('MulDiv'); em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_reg32('r11',12,'rax')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'preview_text_light'); em.mov_mreg_imm32('r11',20,0x00D4D4D4); em.jmp('preview_text_ready')
em.label('preview_text_light'); em.mov_mreg_imm32('r11',20,0x00202020)
em.label('preview_text_ready'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_face']); em.call_iat('lstrcpyW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.mov_r32_imm('r8',4); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW')
em.label('preview_base_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: format all recorded Markdown spans in the Rich Edit preview.
# style 1..6 = heading levels, 10 bold, 11 italic, 12 inline code,
# 13 quote, 14 link, 15 fenced code block.  V8.3 uses CHARFORMAT2W
# so inline/code/quote spans can carry restrained background colors too.
em.label('apply_styles')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x48,0x83,0xEC,0x28)
em.xor32('r12')
em.label('style_loop')
em.mov_r32_ripmem('rax',bsyms['style_count']); em.cmp_r32_r32('r12','rax'); em.jcc(0x83,'styles_done')
em.mov_r32_r32('rax','r12'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.lea_rip('rcx',bsyms['style_start']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r8','rcx')
em.lea_rip('rcx',bsyms['style_end']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r9','rcx')
em.lea_rip('rcx',bsyms['style_type']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r13','rcx')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_imm32('r11',0,116); em.mov_mreg_imm32('r11',8,0); em.mov_mreg_imm32('r11',96,0)
# Headings: size + bold + semantic blue/cyan/teal palette.
em.cmp_r32_imm('r13',6); em.jcc(0x87,'style_nonheading')
em.cmp_r32_imm('r13',1); em.jcc(0x82,'style_nonheading')
em.mov_mreg_imm32('r11',4,0xC0000001); em.mov_mreg_imm32('r11',8,1)
for lvl,tw,darkc,lightc in [
    (1,480,0x00F0A34A,0x00C06515), # RGB 4AA3F0 / 1565C0
    (2,400,0x00F4C843,0x00D78F0B), # 43C8F4 / 0B8FD7
    (3,340,0x00BED338,0x008C9E12), # 38D3BE / 129E8C
    (4,300,0x009DC674,0x006C8C3A),
    (5,270,0x00A7D6A5,0x006A7E45),
    (6,245,0x00AEA490,0x007F6E4A),
]:
    em.cmp_r32_imm('r13',lvl); em.jcc(0x84,f'style_h{lvl}')
em.jmp('style_next')
for lvl,tw,darkc,lightc in [
    (1,480,0x00F0A34A,0x00C06515),(2,400,0x00F4C843,0x00D78F0B),(3,340,0x00BED338,0x008C9E12),
    (4,300,0x009DC674,0x006C8C3A),(5,270,0x00A7D6A5,0x006A7E45),(6,245,0x00AEA490,0x007F6E4A),
]:
    em.label(f'style_h{lvl}'); em.mov_r32_imm('rcx',tw); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,f'style_h{lvl}_light'); em.mov_mreg_imm32('r11',20,darkc); em.jmp(f'style_h{lvl}_color_done'); em.label(f'style_h{lvl}_light'); em.mov_mreg_imm32('r11',20,lightc); em.label(f'style_h{lvl}_color_done'); em.jmp('style_heading_size')
em.label('style_heading_size'); em.mov_r32_ripmem('rdx',bsyms['zoom_pct']); em.mov_r32_imm('r8',100); em.call_iat('MulDiv'); em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_reg32('r11',12,'rax'); em.jmp('style_send')

em.label('style_nonheading')
em.cmp_r32_imm('r13',10); em.jcc(0x84,'style_bold')
em.cmp_r32_imm('r13',11); em.jcc(0x84,'style_italic')
em.cmp_r32_imm('r13',12); em.jcc(0x84,'style_code')
em.cmp_r32_imm('r13',13); em.jcc(0x84,'style_quote')
em.cmp_r32_imm('r13',14); em.jcc(0x84,'style_link')
em.cmp_r32_imm('r13',15); em.jcc(0x84,'style_codeblock')
em.jmp('style_next')
# Bold: warm cream/gold in dark mode, restrained brown in light mode.
em.label('style_bold'); em.mov_mreg_imm32('r11',4,0x60000001); em.mov_mreg_imm32('r11',8,1); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_bold_light'); em.mov_mreg_imm32('r11',20,0x006DC3D7); em.jmp('style_bold_face'); em.label('style_bold_light'); em.mov_mreg_imm32('r11',20,0x00005B7A); em.label('style_bold_face'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_face']); em.call_iat('lstrcpyW'); em.jmp('style_send')
# Italic: warm orange accent.
em.label('style_italic'); em.mov_mreg_imm32('r11',4,0x60000002); em.mov_mreg_imm32('r11',8,2); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_italic_light'); em.mov_mreg_imm32('r11',20,0x005C8BE4); em.jmp('style_italic_face'); em.label('style_italic_light'); em.mov_mreg_imm32('r11',20,0x00234BA6); em.label('style_italic_face'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_face']); em.call_iat('lstrcpyW'); em.jmp('style_send')
# Inline code: Consolas + muted foreground + compact background chip.
em.label('style_code'); em.mov_mreg_imm32('r11',4,0x64000000); em.mov_mreg_imm32('r11',8,0); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_code_light'); em.mov_mreg_imm32('r11',20,0x00DADADA); em.mov_mreg_imm32('r11',96,0x002B2B2B); em.jmp('style_code_face'); em.label('style_code_light'); em.mov_mreg_imm32('r11',20,0x00803A6B); em.mov_mreg_imm32('r11',96,0x00F1F1F1); em.label('style_code_face'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_code']); em.call_iat('lstrcpyW'); em.jmp('style_send')
# Quote: green text on a subtle green-tinted background.
em.label('style_quote'); em.mov_mreg_imm32('r11',4,0x44000002); em.mov_mreg_imm32('r11',8,2); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_quote_light'); em.mov_mreg_imm32('r11',20,0x0095C984); em.mov_mreg_imm32('r11',96,0x00202820); em.jmp('style_send'); em.label('style_quote_light'); em.mov_mreg_imm32('r11',20,0x004B7A3D); em.mov_mreg_imm32('r11',96,0x00EEF7EE); em.jmp('style_send')
# Link: cyan/blue underline.
em.label('style_link'); em.mov_mreg_imm32('r11',4,0x40000004); em.mov_mreg_imm32('r11',8,4); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_link_light'); em.mov_mreg_imm32('r11',20,0x00F7C34F); em.jmp('style_send'); em.label('style_link_light'); em.mov_mreg_imm32('r11',20,0x00D27619); em.jmp('style_send')
# Fenced code block: monospace and dark/light code surface.
em.label('style_codeblock'); em.mov_mreg_imm32('r11',4,0x64000000); em.mov_mreg_imm32('r11',8,0); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'style_codeblock_light'); em.mov_mreg_imm32('r11',20,0x00E9DED8); em.mov_mreg_imm32('r11',96,0x00262626); em.jmp('style_codeblock_face'); em.label('style_codeblock_light'); em.mov_mreg_imm32('r11',20,0x00333333); em.mov_mreg_imm32('r11',96,0x00F4F4F4); em.label('style_codeblock_face'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_code']); em.call_iat('lstrcpyW')
em.label('style_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.mov_r32_imm('r8',1); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW')
em.label('style_next'); em.add_r32_imm8('r12',1); em.jmp('style_loop')
em.label('styles_done')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Helper: rebuild Markdown render buffer, formatting spans and outline from source text.
em.label('update_preview')
em.emit(0x56); em.emit(0x57); em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57)
em.emit(0x48,0x83,0xEC,0x28)
# Read source text.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'pv_render_ret')
em.call_iat('GetWindowTextLengthW'); em.mov_r32_r32('r8','rax'); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.lea_rip('rdx',bsyms['widebuf']); em.call_iat('GetWindowTextW')
# Rebuild outline from raw source, then reset renderer state.
em.call_label('rebuild_outline')
# In source-edit mode the preview is hidden.  Keep the outline current, but do not
# parse/format the hidden RichEdit surface.  This also makes incomplete Markdown
# safe while the user is in the middle of typing it.
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
em.mov_ripmem_imm32(bsyms['style_count'],0); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0); em.mov_ripmem_imm32(bsyms['heading_index'],0)
em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_ripmem_imm32(bsyms['link_flag'],0)
em.lea_rip('rsi',bsyms['widebuf']); em.lea_rip('rdi',bsyms['previewbuf']); em.xor32('r12'); em.xor32('r13'); em.mov_r32_imm('r14',1); em.xor32('r15')

em.label('pv8_loop')
em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'pv8_eof')
# Start-of-line block parsing.
em.test32('r14'); em.jcc(0x84,'pv8_not_line_start')
em.mov_ripmem_r32(bsyms['line_src_start'],'r12'); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0)
# CommonMark permits up to three leading spaces before block markers. Probe after
# those spaces, but restore them if the line turns out to be ordinary text.
em.mov_r32_r32('r11','r12'); em.xor32('r10')
em.label('pv8_leadspace_loop'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x20); em.jcc(0x85,'pv8_leadspace_done'); em.cmp_r32_imm('r10',3); em.jcc(0x83,'pv8_leadspace_done'); em.add_r32_imm8('r11',1); em.add_r32_imm8('r10',1); em.jmp('pv8_leadspace_loop')
em.label('pv8_leadspace_done'); em.mov_r32_r32('r12','r11'); em.movzx_r32_word_index2('rax','rsi','r12')
# Fenced code block marker ``` (recognized both entering and exiting code mode).
em.cmp_r32_imm('rax',0x60); em.jcc(0x85,'pv8_line_after_fence_check')
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x60); em.jcc(0x85,'pv8_line_after_fence_check')
em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x60); em.jcc(0x85,'pv8_line_after_fence_check')
# Toggle code block. Closing fence records one monospace span for the whole block.
em.test32('r15'); em.jcc(0x85,'pv8_close_fence')
em.mov_r32_imm('r15',1); em.mov_ripmem_r32(bsyms['codeblock_out_start'],'r13'); em.jmp('pv8_skip_fence_line')
em.label('pv8_close_fence'); em.xor32('r15'); em.mov_r32_ripmem('r8',bsyms['codeblock_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',15); em.call_label('add_style')
em.label('pv8_skip_fence_line')
# Skip marker/language text until LF, preserve a single line break.
em.label('pv8_fence_skip_loop'); em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'pv8_eof'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x84,'pv8_fence_lf'); em.add_r32_imm8('r12',1); em.jmp('pv8_fence_skip_loop')
em.label('pv8_fence_lf'); em.mov_word_index2_imm16('rdi','r13',0x0D); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.jmp('pv8_loop')

em.label('pv8_line_after_fence_check')
# Inside fenced code: no Markdown marker stripping, copy verbatim until next line-start fence.
em.test32('r15'); em.jcc(0x85,'pv8_codeblock_copy')
# ATX heading: one to six #'s followed by a space.
em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'pv8_line_quote')
em.xor32('r10'); em.mov_r32_r32('r11','r12')
em.label('pv8_hash_count'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'pv8_hash_done'); em.cmp_r32_imm('r10',6); em.jcc(0x83,'pv8_hash_done'); em.add_r32_imm8('r10',1); em.add_r32_imm8('r11',1); em.jmp('pv8_hash_count')
em.label('pv8_hash_done'); em.test32('r10'); em.jcc(0x84,'pv8_line_quote'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x20); em.jcc(0x85,'pv8_line_quote')
# Record render position for the same ordinal heading already placed in the outline.
em.mov_r32_ripmem('r8',bsyms['heading_index']); em.cmp_r32_imm('r8',2048); em.jcc(0x83,'pv8_heading_map_done'); em.mov_r32_ripmem('r9',bsyms['outline_count']); em.cmp_r32_r32('r8','r9'); em.jcc(0x83,'pv8_heading_map_done'); em.mov_r32_r32('rax','r8'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.lea_rip('rcx',bsyms['outline_renderpos']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r13'); em.add_r32_imm8('r8',1); em.mov_ripmem_r32(bsyms['heading_index'],'r8')
em.label('pv8_heading_map_done')
em.mov_ripmem_r32(bsyms['heading_level'],'r10'); em.mov_ripmem_r32(bsyms['heading_out_start'],'r13'); em.mov_r32_r32('r12','r11'); em.add_r32_imm8('r12',1); em.xor32('r14'); em.jmp('pv8_loop')

em.label('pv8_line_quote')
em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x3E); em.jcc(0x85,'pv8_line_bullet')
em.mov_ripmem_imm32(bsyms['line_flags'],1); em.mov_ripmem_r32(bsyms['quote_out_start'],'r13'); em.add_r32_imm8('r12',1)
# Optional single ASCII space after the blockquote marker.
em.movzx_r32_word_index2('r11','rsi','r12'); em.cmp_r32_imm('r11',0x20); em.jcc(0x85,'pv8_quote_ready'); em.add_r32_imm8('r12',1)
em.label('pv8_quote_ready'); em.xor32('r14'); em.jmp('pv8_loop')

em.label('pv8_line_bullet')
em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x2D); em.jcc(0x84,'pv8_bullet_check'); em.cmp_r32_imm('rax',0x2A); em.jcc(0x85,'pv8_normal_line')
em.label('pv8_bullet_check'); em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x20); em.jcc(0x84,'pv8_bullet_ws_ok'); em.cmp_r32_imm('r11',0x09); em.jcc(0x85,'pv8_normal_line')
em.label('pv8_bullet_ws_ok'); em.mov_word_index2_imm16('rdi','r13',0x2022); em.add_r32_imm8('r13',1); em.mov_word_index2_imm16('rdi','r13',0x20); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',2); em.xor32('r14'); em.jmp('pv8_loop')
em.label('pv8_normal_line'); em.mov_r32_ripmem('r12',bsyms['line_src_start']); em.xor32('r14')

em.label('pv8_not_line_start')
# Fenced code content copies literally.
em.test32('r15'); em.jcc(0x85,'pv8_codeblock_copy')
em.movzx_r32_word_index2('rax','rsi','r12')
# Rich Edit internally indexes one paragraph mark per source line. Drop source CR
# and emit a single CR for each LF so formatting ranges stay aligned on every line.
em.cmp_r32_imm('rax',0x0D); em.jcc(0x85,'pv8_after_cr_skip'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_after_cr_skip')
# LF finalizes line-scoped formatting.
em.cmp_r32_imm('rax',0x0A); em.jcc(0x84,'pv8_lf')
# **bold**
em.cmp_r32_imm('rax',0x2A); em.jcc(0x85,'pv8_inline_code_check')
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x2A); em.jcc(0x85,'pv8_single_italic')
em.mov_r32_ripmem('r11',bsyms['bold_flag']); em.test32('r11'); em.jcc(0x85,'pv8_bold_close')
# Do not strip an unmatched ** opener. Probe to the end of this logical line first.
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',2)
em.label('pv8_bold_probe'); em.movzx_r32_word_index2('r11','rsi','r10'); em.test32('r11'); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0A); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x2A); em.jcc(0x85,'pv8_bold_probe_next'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x2A); em.jcc(0x84,'pv8_bold_probe_ok')
em.label('pv8_bold_probe_next'); em.add_r32_imm8('r10',1); em.jmp('pv8_bold_probe')
em.label('pv8_bold_probe_ok'); em.mov_ripmem_imm32(bsyms['bold_flag'],1); em.mov_ripmem_r32(bsyms['bold_out_start'],'r13'); em.add_r32_imm8('r12',2); em.jmp('pv8_loop')
em.label('pv8_bold_close'); em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_r32_ripmem('r8',bsyms['bold_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',10); em.call_label('add_style'); em.add_r32_imm8('r12',2); em.jmp('pv8_loop')
# *italic*
em.label('pv8_single_italic'); em.mov_r32_ripmem('r11',bsyms['italic_flag']); em.test32('r11'); em.jcc(0x85,'pv8_italic_close')
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1)
em.label('pv8_italic_probe'); em.movzx_r32_word_index2('r11','rsi','r10'); em.test32('r11'); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0A); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x2A); em.jcc(0x84,'pv8_italic_probe_ok'); em.add_r32_imm8('r10',1); em.jmp('pv8_italic_probe')
em.label('pv8_italic_probe_ok'); em.mov_ripmem_imm32(bsyms['italic_flag'],1); em.mov_ripmem_r32(bsyms['italic_out_start'],'r13'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_italic_close'); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_r32_ripmem('r8',bsyms['italic_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',11); em.call_label('add_style'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

# `inline code`
em.label('pv8_inline_code_check'); em.cmp_r32_imm('rax',0x60); em.jcc(0x85,'pv8_link_open_check')
em.mov_r32_ripmem('r11',bsyms['inlinecode_flag']); em.test32('r11'); em.jcc(0x85,'pv8_code_close')
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1)
em.label('pv8_code_probe'); em.movzx_r32_word_index2('r11','rsi','r10'); em.test32('r11'); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0A); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x60); em.jcc(0x84,'pv8_code_probe_ok'); em.add_r32_imm8('r10',1); em.jmp('pv8_code_probe')
em.label('pv8_code_probe_ok'); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],1); em.mov_ripmem_r32(bsyms['code_out_start'],'r13'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_code_close'); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_r32_ripmem('r8',bsyms['code_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',12); em.call_label('add_style'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

# [link text](destination) -- keep/display text, hide destination, format visible text.
em.label('pv8_link_open_check'); em.cmp_r32_imm('rax',0x5B); em.jcc(0x85,'pv8_link_close_check')
# Only consume Markdown link markers when a complete [text](destination) exists
# on this logical line. Malformed/incomplete links remain literal source text.
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1)
em.label('pv8_link_probe_text'); em.movzx_r32_word_index2('r11','rsi','r10'); em.test32('r11'); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0A); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x5D); em.jcc(0x84,'pv8_link_probe_paren'); em.add_r32_imm8('r10',1); em.jmp('pv8_link_probe_text')
em.label('pv8_link_probe_paren'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x28); em.jcc(0x85,'pv8_copy'); em.add_r32_imm8('r10',1)
em.label('pv8_link_probe_url'); em.movzx_r32_word_index2('r11','rsi','r10'); em.test32('r11'); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0D); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x0A); em.jcc(0x84,'pv8_copy'); em.cmp_r32_imm('r11',0x29); em.jcc(0x84,'pv8_link_probe_ok'); em.add_r32_imm8('r10',1); em.jmp('pv8_link_probe_url')
em.label('pv8_link_probe_ok'); em.mov_ripmem_imm32(bsyms['link_flag'],1); em.mov_ripmem_r32(bsyms['link_out_start'],'r13'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_link_close_check'); em.cmp_r32_imm('rax',0x5D); em.jcc(0x85,'pv8_copy')
em.mov_r32_ripmem('r11',bsyms['link_flag']); em.test32('r11'); em.jcc(0x84,'pv8_copy')
em.mov_r32_r32('r10','r12'); em.add_r32_imm8('r10',1); em.movzx_r32_word_index2('r11','rsi','r10'); em.cmp_r32_imm('r11',0x28); em.jcc(0x85,'pv8_copy')
em.mov_ripmem_imm32(bsyms['link_flag'],0); em.mov_r32_ripmem('r8',bsyms['link_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',14); em.call_label('add_style')
em.add_r32_imm8('r12',2)
em.label('pv8_url_skip'); em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'pv8_eof'); em.cmp_r32_imm('rax',0x29); em.jcc(0x84,'pv8_url_done'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x84,'pv8_lf'); em.add_r32_imm8('r12',1); em.jmp('pv8_url_skip')
em.label('pv8_url_done'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

em.label('pv8_copy'); em.mov_word_index2_reg('rdi','r13','rax'); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

em.label('pv8_codeblock_copy'); em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x0D); em.jcc(0x85,'pv8_codeblock_not_cr'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_codeblock_not_cr'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x85,'pv8_codeblock_plain'); em.mov_word_index2_imm16('rdi','r13',0x0D); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.jmp('pv8_loop')
em.label('pv8_codeblock_plain'); em.mov_word_index2_reg('rdi','r13','rax'); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

em.label('pv8_lf')
# Close malformed/unclosed inline spans at line end so formatting stays local.
em.mov_r32_ripmem('rax',bsyms['bold_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_italic'); em.mov_r32_ripmem('r8',bsyms['bold_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',10); em.call_label('add_style')
em.label('pv8_lf_italic'); em.mov_r32_ripmem('rax',bsyms['italic_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_code'); em.mov_r32_ripmem('r8',bsyms['italic_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',11); em.call_label('add_style')
em.label('pv8_lf_code'); em.mov_r32_ripmem('rax',bsyms['inlinecode_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_heading'); em.mov_r32_ripmem('r8',bsyms['code_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',12); em.call_label('add_style')
em.label('pv8_lf_heading'); em.mov_r32_ripmem('r10',bsyms['heading_level']); em.test32('r10'); em.jcc(0x84,'pv8_lf_quote'); em.mov_ripmem_r32(bsyms['heading_out_end'],'r13'); em.mov_r32_ripmem('r8',bsyms['heading_out_start']); em.mov_r32_r32('r9','r13'); em.call_label('add_style')
em.label('pv8_lf_quote'); em.mov_r32_ripmem('rax',bsyms['line_flags']); em.test32('rax'); em.jcc(0x84,'pv8_lf_copy'); em.mov_r32_ripmem('r8',bsyms['quote_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',13); em.call_label('add_style')
em.label('pv8_lf_copy'); em.mov_word_index2_imm16('rdi','r13',0x0D); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0); em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_ripmem_imm32(bsyms['link_flag'],0); em.jmp('pv8_loop')

em.label('pv8_eof')
# Finalize last line and open fenced block if the file does not end with LF.
em.mov_r32_ripmem('r10',bsyms['heading_level']); em.test32('r10'); em.jcc(0x84,'pv8_eof_quote'); em.mov_ripmem_r32(bsyms['heading_out_end'],'r13'); em.mov_r32_ripmem('r8',bsyms['heading_out_start']); em.mov_r32_r32('r9','r13'); em.call_label('add_style')
em.label('pv8_eof_quote'); em.mov_r32_ripmem('rax',bsyms['line_flags']); em.test32('rax'); em.jcc(0x84,'pv8_eof_codeblock'); em.mov_r32_ripmem('r8',bsyms['quote_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',13); em.call_label('add_style')
em.label('pv8_eof_codeblock'); em.test32('r15'); em.jcc(0x84,'pv8_finish'); em.mov_r32_ripmem('r8',bsyms['codeblock_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',15); em.call_label('add_style')
em.label('pv8_finish'); em.mov_word_index2_zero('rdi','r13')
# Populate the hidden or visible Rich Edit render surface.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'pv_render_ret'); em.lea_rip('rdx',bsyms['previewbuf']); em.call_iat('SetWindowTextW'); em.call_label('apply_preview_base'); em.call_label('apply_styles')
em.label('pv_render_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0x5F); em.emit(0x5E); em.emit(0xC3)

# Helper: clicking an outline heading navigates either source or rendered mode.
em.label('navigate_outline')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'navigate_ret'); em.mov_r32_imm('rdx',0x0188); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'navigate_ret'); em.cmp_r32_imm('rax',2048); em.jcc(0x83,'navigate_ret')
em.mov_r32_r32('r10','rax'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.mov_r32_ripmem('r11',bsyms['preview_flag']); em.test32('r11'); em.jcc(0x84,'navigate_source')
em.lea_rip('rcx',bsyms['outline_renderpos']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r8','rcx'); em.mov_r32_r32('r9','r8'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_ripmem_r64(bsyms['nav_hwnd'],'rcx'); em.jmp('navigate_send')
em.label('navigate_source'); em.lea_rip('rcx',bsyms['outline_srcpos']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r8','rcx'); em.mov_r32_r32('r9','r8'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_ripmem_r64(bsyms['nav_hwnd'],'rcx')
em.label('navigate_send'); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW'); em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.mov_r32_imm('rdx',0x00B7); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.call_iat('SetFocus')
em.label('navigate_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: apply Light/Dark display theme to source editor, outline, preview, status and title bar.
em.label('apply_theme')
em.emit(0x48,0x83,0xEC,0x38)
# Retire old brushes.
em.mov_r64_ripmem('rcx',bsyms['hbrush_edit']); em.test64('rcx'); em.jcc(0x84,'theme_del_outline'); em.call_iat('DeleteObject')
em.label('theme_del_outline'); em.mov_r64_ripmem('rcx',bsyms['hbrush_outline']); em.test64('rcx'); em.jcc(0x84,'theme_del_menu'); em.call_iat('DeleteObject')
em.label('theme_del_menu'); em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'theme_make'); em.call_iat('DeleteObject')
em.label('theme_make'); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_make_light')
em.mov_r32_imm('rcx',0x001E1E1E); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x00222222); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x00202020); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax'); em.jmp('theme_controls')
em.label('theme_make_light'); em.mov_r32_imm('rcx',0x00FFFFFF); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax')
em.label('theme_controls')
# Tell current Windows 10/11 to redraw classic menus in the selected app mode.
em.mov_r64_ripmem('rax',bsyms['fn_setpreferred']); em.test64('rax'); em.jcc(0x84,'theme_pref_done')
em.mov_r32_ripmem('rcx',bsyms['theme_dark']); em.test32('rcx'); em.jcc(0x84,'theme_pref_light'); em.mov_r32_imm('rcx',2); em.jmp('theme_pref_call')
em.label('theme_pref_light'); em.mov_r32_imm('rcx',3)
em.label('theme_pref_call'); em.call_r64('rax')
em.label('theme_pref_done')
# Allow/deny dark mode on the frame and every child that owns native scrollbars.
em.mov_r64_ripmem('rax',bsyms['fn_allowdark']); em.test64('rax'); em.jcc(0x84,'theme_child_themes')
em.mov_r64_r64('rcx','rbx'); em.mov_r32_ripmem('rdx',bsyms['theme_dark']); em.call_r64('rax')
em.mov_r64_ripmem('rax',bsyms['fn_allowdark']); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_ripmem('rdx',bsyms['theme_dark']); em.call_r64('rax')
em.mov_r64_ripmem('rax',bsyms['fn_allowdark']); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_ripmem('rdx',bsyms['theme_dark']); em.call_r64('rax')
em.mov_r64_ripmem('rax',bsyms['fn_allowdark']); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_ripmem('rdx',bsyms['theme_dark']); em.call_r64('rax')
em.mov_r64_ripmem('rax',bsyms['fn_allowdark']); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_ripmem('rdx',bsyms['theme_dark']); em.call_r64('rax')
em.label('theme_child_themes')
# SetWindowTheme is what gives EDIT/RichEdit/ListBox their dark native scrollbars.
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_child_light_names')
em.lea_rip('rax',rsyms['theme_dark_name']); em.mov_ripmem_r64(bsyms['theme_name_ptr'],'rax'); em.jmp('theme_child_names_ready')
em.label('theme_child_light_names'); em.lea_rip('rax',rsyms['theme_light_name']); em.mov_ripmem_r64(bsyms['theme_name_ptr'],'rax')
em.label('theme_child_names_ready')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r64_ripmem('rdx',bsyms['theme_name_ptr']); em.xor32('r8'); em.call_iat('SetWindowTheme')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r64_ripmem('rdx',bsyms['theme_name_ptr']); em.xor32('r8'); em.call_iat('SetWindowTheme')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r64_ripmem('rdx',bsyms['theme_name_ptr']); em.xor32('r8'); em.call_iat('SetWindowTheme')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r64_ripmem('rdx',bsyms['theme_name_ptr']); em.xor32('r8'); em.call_iat('SetWindowTheme')
# Flush cached popup/menu themes after changing PreferredAppMode.
em.mov_r64_ripmem('rax',bsyms['fn_flushmenus']); em.test64('rax'); em.jcc(0x84,'theme_menu_flush_done'); em.call_r64('rax')
em.label('theme_menu_flush_done'); em.mov_r64_r64('rcx','rbx'); em.call_iat('DrawMenuBar')
# Status bar background and theme.
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'theme_dwm'); em.mov_r32_imm('rdx',0x2001); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['theme_dark']); em.test32('r9'); em.jcc(0x84,'theme_status_light'); em.mov_r32_imm('r9',0x00222222); em.jmp('theme_status_send')
em.label('theme_status_light'); em.mov_r32_imm('r9',0x00F3F3F3)
em.label('theme_status_send'); em.call_iat('SendMessageW')
em.label('theme_dwm')
# Dark/light non-client title bar on modern Windows.
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.mov_ripmem_r32(bsyms['theme_bool'],'rax'); em.mov_r64_r64('rcx','rbx'); em.mov_r32_imm('rdx',20); em.lea_rip('r8',bsyms['theme_bool']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute')
# Check Light/Dark menu items.
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1310); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x85,'theme_light_unchecked'); em.mov_r32_imm('r8',0x8); em.jmp('theme_light_check')
em.label('theme_light_unchecked'); em.xor32('r8')
em.label('theme_light_check'); em.call_iat('CheckMenuItem')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1311); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_dark_unchecked'); em.mov_r32_imm('r8',0x8); em.jmp('theme_dark_check')
em.label('theme_dark_unchecked'); em.xor32('r8')
em.label('theme_dark_check'); em.call_iat('CheckMenuItem')
em.call_label('apply_preview_base')
# Repaint child surfaces so WM_CTLCOLOR* immediately uses the new brushes/colors.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.call_iat('UpdateWindow')
em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

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
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1000); em.lea_rip('r9',bsyms['status_linebuf']); em.call_iat('SendMessageW')
# character counts
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.mov_r32_ripmem('r11',bsyms['sel_start']); em.sub_r32_r32('r10','r11'); em.mov_ripmem_r32(bsyms['selected_chars'],'r10')
em.lea_rip('rcx',bsyms['status_charsbuf']); em.lea_rip('rdx',rsyms['fmt_chars']); em.mov_r32_ripmem('r8',bsyms['total_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1001); em.lea_rip('r9',bsyms['status_charsbuf']); em.call_iat('SendMessageW')
em.lea_rip('rcx',bsyms['status_selbuf']); em.lea_rip('rdx',rsyms['fmt_selected']); em.mov_r32_ripmem('r8',bsyms['selected_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1002); em.lea_rip('r9',bsyms['status_selbuf']); em.call_iat('SendMessageW')
# zoom percent
em.lea_rip('rcx',bsyms['status_zoombuf']); em.lea_rip('rdx',rsyms['fmt_zoom']); em.mov_r32_ripmem('r8',bsyms['zoom_pct']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1003); em.lea_rip('r9',bsyms['status_zoombuf']); em.call_iat('SendMessageW')
# line endings
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1004); em.lea_rip('r9',rsyms['status_crlf']); em.call_iat('SendMessageW')
# encoding
em.mov_r32_ripmem('rax',bsyms['encoding_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'enc_utf16'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'enc_ansi'); em.lea_rip('r9',rsyms['status_utf8']); em.jmp('enc_send')
em.label('enc_utf16'); em.lea_rip('r9',rsyms['status_utf16']); em.jmp('enc_send')
em.label('enc_ansi'); em.lea_rip('r9',rsyms['status_ansi'])
em.label('enc_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1005); em.call_iat('SendMessageW')
em.label('status_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('exit')
em.mov_r64_ripmem('rcx',bsyms['hfont']); em.test64('rcx'); em.jcc(0x84,'exit_accel'); em.call_iat('DeleteObject')
em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'exit_accel'); em.call_iat('DeleteObject')
em.label('exit_accel'); em.mov_r64_ripmem('rcx',bsyms['haccel']); em.test64('rcx'); em.jcc(0x84,'exit_now'); em.call_iat('DestroyAcceleratorTable')
em.label('exit_now'); em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)

# ------------------------------------------------------------------
# Real application WndProc. Windows delivers menu, child notifications,
# live sizing and control-color messages synchronously to this callback.
em.label('wndproc')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('r10',bsyms['findmsg_id']); em.cmp_r32_r32('rdx','r10'); em.jcc(0x84,'wp_findreplace')
em.cmp_r32_imm('rdx',0x0111); em.jcc(0x84,'wp_command')      # WM_COMMAND
em.cmp_r32_imm('rdx',0x0005); em.jcc(0x84,'wp_size')         # WM_SIZE
em.cmp_r32_imm('rdx',0x0002); em.jcc(0x84,'wp_destroy')      # WM_DESTROY
em.cmp_r32_imm('rdx',0x002B); em.jcc(0x84,'wp_drawitem')     # WM_DRAWITEM (status + outline)
em.cmp_r32_imm('rdx',0x002C); em.jcc(0x84,'wp_measureitem')  # WM_MEASUREITEM (outline row height)
em.cmp_r32_imm('rdx',0x0091); em.jcc(0x84,'wp_uah_drawmenu') # WM_UAHDRAWMENU
em.cmp_r32_imm('rdx',0x0092); em.jcc(0x84,'wp_uah_drawitem') # WM_UAHDRAWMENUITEM
em.cmp_r32_imm('rdx',0x0014); em.jcc(0x84,'wp_erasebkgnd')   # WM_ERASEBKGND
em.cmp_r32_imm('rdx',0x0133); em.jcc(0x84,'wp_ctlcolor_edit') # WM_CTLCOLOREDIT
em.cmp_r32_imm('rdx',0x0134); em.jcc(0x84,'wp_ctlcolor_list') # WM_CTLCOLORLISTBOX
em.label('wp_default'); em.call_iat('DefWindowProcW'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_command')
# Source EDIT notifications: EN_CHANGE -> rebuild outline/render on the outer message loop.
em.mov_r64_ripmem('rax',bsyms['hwnd_edit']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_cmd_outline_check')
em.mov_r32_r32('r10','r8'); em.shr_r32_imm8('r10',16); em.cmp_r32_imm('r10',0x0300); em.jcc(0x85,'wp_child_return')
em.mov_r32_imm('rdx',0x8004); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('wp_child_return')
# Outline selection notification.
em.label('wp_cmd_outline_check'); em.mov_r64_ripmem('rax',bsyms['hwnd_outline']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_cmd_other_child')
em.mov_r32_r32('r10','r8'); em.shr_r32_imm8('r10',16); em.cmp_r32_imm('r10',1); em.jcc(0x85,'wp_child_return')
em.mov_r32_imm('rdx',0x8005); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('wp_child_return')
# Ignore notifications from preview/status and other child controls; menu WM_COMMAND has lParam == 0.
em.label('wp_cmd_other_child'); em.test64('r9'); em.jcc(0x85,'wp_child_return')
# Menu/accelerator command. Preserve original wParam in r8 for the private message.
em.mov_r32_imm('rdx',0x8001); em.xor32('r9'); em.call_iat('PostMessageW')
em.label('wp_child_return'); em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_size')
em.mov_r32_r32('r10','r9'); em.mov_r32_r32('r11','r9'); em.and_r32_imm('r10',0xFFFF); em.shr_r32_imm8('r11',16)
em.mov_ripmem_r32(bsyms['client_w'],'r10'); em.mov_ripmem_r32(bsyms['client_h'],'r11'); em.call_label('resize_children')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_findreplace')
em.mov_r32_imm('rdx',0x8003); em.mov_r32_ripmem('r8',bsyms['fr']+24); em.xor32('r9'); em.call_iat('PostMessageW')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Give the owner-drawn outline a relaxed, fixed row height.
em.label('wp_measureitem')
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',4); em.jcc(0x85,'wp_default'); em.mov_mreg_imm32('r9',16,30); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Owner-draw status bar and outline rows.
em.label('wp_drawitem')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',2); em.jcc(0x84,'wp_draw_status'); em.cmp_r32_imm('rax',4); em.jcc(0x84,'wp_draw_outline'); em.jmp('wp_default')

em.label('wp_draw_status')
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_status_text_light'); em.mov_r32_imm('rdx',0x00E6E6E6); em.jmp('wp_status_text_send')
em.label('wp_status_text_light'); em.mov_r32_imm('rdx',0x00202020)
em.label('wp_status_text_send'); em.call_iat('SetTextColor')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',1); em.call_iat('SetBkMode')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_mreg('rdx','r9',56); em.mov_r32_imm('r8',0xFFFFFFFF); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.add_r64_imm8('r9',40); em.mov_mrsp_imm32(0x20,0x0824); em.call_iat('DrawTextW')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Outline: 30px rows, per-level accent colors, selection surface, more breathing room.
em.label('wp_draw_outline')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('r10','r9',8); em.cmp_r32_imm('r10',0xFFFFFFFF); em.jcc(0x84,'wp_draw_outline_done')
# selected state chooses a slightly lighter surface, otherwise regular outline brush.
em.mov_r32_mreg('rax','r9',16); em.and_r32_imm('rax',1); em.test32('rax'); em.jcc(0x84,'wp_outline_fill_normal')
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_outline_fill_sel_light'); em.mov_r64_ripmem('r8',bsyms['hbrush_edit']); em.call_iat('FillRect'); em.jmp('wp_outline_text')
em.label('wp_outline_fill_sel_light'); em.mov_r64_ripmem('r8',bsyms['hbrush_edit']); em.call_iat('FillRect'); em.jmp('wp_outline_text')
em.label('wp_outline_fill_normal'); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.label('wp_outline_text')
# Fetch item text from LISTBOX.
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('r10','r9',8); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0189); em.mov_r32_r32('r8','r10'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
# level = outline_level[itemID]
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',8); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.lea_rip('rcx',bsyms['outline_level']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r10','rcx')
# Select color by depth and theme.
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_outline_color_light')
em.cmp_r32_imm('r10',1); em.jcc(0x84,'wp_outline_dark_h1'); em.cmp_r32_imm('r10',2); em.jcc(0x84,'wp_outline_dark_h2'); em.cmp_r32_imm('r10',3); em.jcc(0x84,'wp_outline_dark_h3'); em.mov_r32_imm('rdx',0x00AFAFAF); em.jmp('wp_outline_color_send')
em.label('wp_outline_dark_h1'); em.mov_r32_imm('rdx',0x00F0A34A); em.jmp('wp_outline_color_send')
em.label('wp_outline_dark_h2'); em.mov_r32_imm('rdx',0x00F4C843); em.jmp('wp_outline_color_send')
em.label('wp_outline_dark_h3'); em.mov_r32_imm('rdx',0x00BED338); em.jmp('wp_outline_color_send')
em.label('wp_outline_color_light'); em.cmp_r32_imm('r10',1); em.jcc(0x84,'wp_outline_light_h1'); em.cmp_r32_imm('r10',2); em.jcc(0x84,'wp_outline_light_h2'); em.cmp_r32_imm('r10',3); em.jcc(0x84,'wp_outline_light_h3'); em.mov_r32_imm('rdx',0x00606060); em.jmp('wp_outline_color_send')
em.label('wp_outline_light_h1'); em.mov_r32_imm('rdx',0x00C06515); em.jmp('wp_outline_color_send')
em.label('wp_outline_light_h2'); em.mov_r32_imm('rdx',0x00D78F0B); em.jmp('wp_outline_color_send')
em.label('wp_outline_light_h3'); em.mov_r32_imm('rdx',0x008C9E12)
em.label('wp_outline_color_send'); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.call_iat('SetTextColor'); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',1); em.call_iat('SetBkMode')
# Copy rect to scratch, add 8px left inset, then draw single-line vertically centered.
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',40); em.lea_rip('rcx',bsyms['draw_rect']); em.mov_ptr_r32('rcx','rax'); em.mov_r32_mreg('rax','r9',44); em.mov_mreg_reg32('rcx',4,'rax'); em.mov_r32_mreg('rax','r9',48); em.mov_mreg_reg32('rcx',8,'rax'); em.mov_r32_mreg('rax','r9',52); em.mov_mreg_reg32('rcx',12,'rax'); em.mov_r32_mreg('rax','rcx',0); em.add_r32_imm8('rax',8); em.mov_ptr_r32('rcx','rax')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.lea_rip('rdx',bsyms['outline_titlebuf']); em.mov_r32_imm('r8',0xFFFFFFFF); em.lea_rip('r9',bsyms['draw_rect']); em.mov_mrsp_imm32(0x20,0x0824); em.call_iat('DrawTextW')
em.label('wp_draw_outline_done'); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Dark-mode UAH menu-bar painting.  These are Windows' undocumented menu-bar draw
# messages; popup menus are still themed through PreferredAppMode/SetWindowTheme.
em.label('wp_uah_drawmenu')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_default')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
# UAHMENU.hdc is at lParam+8; GetClipBox gives the exact current menu-bar paint clip.
em.mov_r64_mreg('rcx','r9',8); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('GetClipBox')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',8); em.lea_rip('rdx',bsyms['draw_rect']); em.mov_r64_ripmem('r8',bsyms['hbrush_menu']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_uah_drawitem')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_default')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
# Fill item with menu surface (or subtle hover surface for selected/hot states).
em.mov_r32_mreg('rax','r9',16); em.and_r32_imm('rax',0x41); em.test32('rax'); em.jcc(0x84,'wp_uah_item_normal')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect'); em.jmp('wp_uah_item_text')
em.label('wp_uah_item_normal'); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_menu']); em.call_iat('FillRect')
em.label('wp_uah_item_text')
# Get menu text by position: UAHMENU starts at +64, UAHMENUITEM.iPosition at +88.
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',64); em.mov_r32_mreg('rdx','r9',88); em.lea_rip('r8',bsyms['menu_textbuf']); em.mov_r32_imm('r9',255); em.mov_mrsp_imm32(0x20,0x400); em.call_iat('GetMenuStringW')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',0x00E8E8E8); em.call_iat('SetTextColor'); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',1); em.call_iat('SetBkMode')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.lea_rip('rdx',bsyms['menu_textbuf']); em.mov_r32_imm('r8',0xFFFFFFFF); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.add_r64_imm8('r9',40); em.mov_mrsp_imm32(0x20,0x0025); em.call_iat('DrawTextW')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Paint exposed main-client gaps (including the bottom-right status corner) with the theme surface.
em.label('wp_erasebkgnd')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_default')
# WM_ERASEBKGND supplies the HDC in wParam (r8), not lParam.
em.mov_ripmem_r64(bsyms['paint_hdc'],'r8'); em.mov_r64_r64('rcx','r8'); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('GetClipBox'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.lea_rip('rdx',bsyms['draw_rect']); em.mov_r64_ripmem('r8',bsyms['hbrush_edit']); em.call_iat('FillRect'); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Theme coloring for the source EDIT control.
em.label('wp_ctlcolor_edit')
em.mov_ripmem_r64(bsyms['paint_hdc'],'r8')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_edit_light')
em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00D4D4D4); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x001E1E1E); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_edit']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_edit_light'); em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00202020); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x00FFFFFF); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_edit']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Theme coloring for the outline LISTBOX.
em.label('wp_ctlcolor_list')
em.mov_ripmem_r64(bsyms['paint_hdc'],'r8')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_list_light')
em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00E6E6E6); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x00222222); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_outline']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_list_light'); em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00202020); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x00F3F3F3); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_outline']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_destroy')
em.xor32('rcx'); em.call_iat('PostQuitMessage'); em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.patch()
text=em.b
if len(text) >= (RDATA_RVA-TEXT_RVA):
    raise RuntimeError(f'text too large: {len(text):x}')

# ---------------- PE writer ----------------
# ---------------- PE writer (v8: one loader-simple section) ----------------
# Keep the exact RVAs used by the machine-code emitter, but put code, strings,
# import table, and the zero-filled runtime buffers into ONE PE section.
# This mirrors the layout style of the earlier 1.5 KiB build that was confirmed
# to load on Windows, while still leaving the big work buffers as virtual-only
# zero-filled memory rather than storing megabytes of zeros in the file.

headers_size = 0x200
section_ptr = headers_size

# Section begins at TEXT_RVA. Preserve the existing absolute RVA plan:
#   code  @ 0x1000
#   rdata @ 0x8000
#   idata @ 0xB000
#   bss   @ 0xC000 (virtual-only tail)
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

out = '/mnt/data/direct_pe_markdown_editor_x64_v8_3.exe'
with open(out, 'wb') as f:
    f.write(hdr)
    f.write(raw)

sha = hashlib.sha256(open(out,'rb').read()).hexdigest()
print(out)
print('size', os.path.getsize(out), 'text', len(text), 'raw', raw_size,
      'section_vsize', section_vsize, 'bss_vsize', BSS_VSIZE)
print('sha256', sha)
