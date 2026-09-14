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
wstr('title','Direct PE Markdown Editor x64 V8.4.13 — No Compiler')
wstr('empty','')
wstr('menu_file','&File')
wstr('menu_edit','&Edit')
wstr('menu_markdown','&Markdown')
wstr('menu_view','&View')
wstr('menu_help','&Help')
wstr('m_new','&New\tCtrl+N')
wstr('m_open','&Open...\tCtrl+O')
wstr('m_save','&Save\tCtrl+S')
wstr('m_saveas','Save &As...\tCtrl+Alt+S')
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
wstr('m_md_h3','Heading &3\tCtrl+3')
wstr('m_md_h4','Heading &4\tCtrl+4')
wstr('m_md_h5','Heading &5\tCtrl+5')
wstr('m_md_h6','Heading &6\tCtrl+6')
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
wstr('m_status','&Status Bar\tCtrl+Shift+S')
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
wstr('class_scrollbar','SCROLLBAR')
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
    (FVIRTKEY|FCONTROL|FALT, 0x53, 1004),             # Ctrl+Alt+S Save As (Ctrl+Shift+S reserved for Status Bar)
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
    (FVIRTKEY|FCONTROL|FSHIFT, 0x53, 1305),           # Ctrl+Shift+S Status Bar
    (FVIRTKEY|FCONTROL|FSHIFT, 0x50, 1306),           # Ctrl+Shift+P Markdown preview/source
    (FVIRTKEY|FCONTROL, 0x42, 1307),                  # Ctrl+B Outline
    (FVIRTKEY|FCONTROL|FALT, 0x54, 1312),             # Ctrl+Alt+T Toggle Light/Dark
    (FVIRTKEY|FCONTROL, 0x31, 1401),                  # Ctrl+1 Heading 1
    (FVIRTKEY|FCONTROL, 0x32, 1402),                  # Ctrl+2 Heading 2
    (FVIRTKEY|FCONTROL, 0x33, 1410),                  # Ctrl+3 Heading 3
    (FVIRTKEY|FCONTROL, 0x34, 1411),                  # Ctrl+4 Heading 4
    (FVIRTKEY|FCONTROL, 0x35, 1412),                  # Ctrl+5 Heading 5
    (FVIRTKEY|FCONTROL, 0x36, 1413),                  # Ctrl+6 Heading 6
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
wstr('md_h3','### ')
wstr('md_h4','#### ')
wstr('md_h5','##### ')
wstr('md_h6','###### ')
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
wstr('err_large','The file is too large for this build (limit: 4 MiB).')
wstr('err_decode','The file could not be decoded as UTF-8/ANSI text.')
wstr('about','Direct PE Markdown Editor x64 V8.4.13\r\n\r\nNative PE32+ and x86-64 machine code generated directly, without a C/C++ compiler, assembler, or linker.\r\n\r\nV8.4.13 separates the 1px visual divider from an 8px logical drag hit-zone, unifies all content heights through one layout metric, and visually trims the Outline native scrollbar to match the document scrollbar while preserving native drag behavior.')

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
bss_alloc('hwnd_splitter', 8, 8)
bss_alloc('hwnd_outline_scroll', 8, 8)
bss_alloc('hwnd_scroll_trim', 8, 8)
bss_alloc('hwnd_status', 8, 8)
bss_alloc('hwnd_corner', 8, 8)
bss_alloc('hfont', 8, 8)
bss_alloc('hfont_outline', 8, 8)
bss_alloc('hfont_status', 8, 8)
bss_alloc('old_hfont', 8, 8)
bss_alloc('hmenu_main', 8, 8)
bss_alloc('hmenu_view', 8, 8)
bss_alloc('hmenu_zoom', 8, 8)
bss_alloc('hwnd_main', 8, 8)
bss_alloc('haccel', 8, 8)
bss_alloc('hbrush_edit', 8, 8)
bss_alloc('hbrush_outline', 8, 8)
bss_alloc('hbrush_splitter', 8, 8)
bss_alloc('hbrush_status', 8, 8)
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
bss_alloc('content_h', 4, 4)
bss_alloc('sel_start', 4, 4)
bss_alloc('sel_end', 4, 4)
bss_alloc('line_zero', 4, 4)
bss_alloc('col_one', 4, 4)
bss_alloc('view_hwnd', 8, 8)
bss_alloc('view_sel_start', 4, 4)
bss_alloc('view_sel_end', 4, 4)
bss_alloc('view_line', 4, 4)
bss_alloc('view_col', 4, 4)
bss_alloc('view_line_start', 4, 4)
bss_alloc('view_line_len', 4, 4)
bss_alloc('view_top_pos', 4, 4)
bss_alloc('outline_scroll_top', 4, 4)
bss_alloc('outline_scroll_count', 4, 4)
bss_alloc('outline_width', 4, 4)
bss_alloc('splitter_drag', 4, 4)
bss_alloc('outline_scroll_visible', 4, 4)
bss_alloc('scrollbar_w', 4, 4)
bss_alloc('scroll_trim_w', 4, 4)
bss_alloc('preview_visible_format_only', 4, 4)
bss_alloc('preview_theme_dirty', 4, 4)
bss_alloc('format_visible_end', 4, 4)
bss_alloc('vscroll_wparam', 4, 4)
bss_alloc('wheel_x', 4, 4)
bss_alloc('wheel_y', 4, 4)
bss_alloc('cursor_pt', 8, 4)
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
bss_alloc('theme_color', 4, 4)
bss_alloc('nc_winrect', 16, 8)
bss_alloc('nc_itemrect', 16, 8)
bss_alloc('theme_name_ptr', 8, 8)
bss_alloc('uxtheme_mod', 8, 8)
bss_alloc('fn_allowdark', 8, 8)
bss_alloc('fn_setpreferred', 8, 8)
bss_alloc('fn_flushmenus', 8, 8)
bss_alloc('outline_count', 4, 4)
bss_alloc('heading_index', 4, 4)
bss_alloc('drawitem_ptr', 8, 8)
bss_alloc('draw_old_font', 8, 8)
bss_alloc('draw_rect', 16, 8)
bss_alloc('menuinfo', 40, 8)
bss_alloc('paint_hdc', 8, 8)
bss_alloc('defproc_result', 8, 8)
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
# V8.4.5 document architecture:
#   Document Model (canonical CRLF) -> Source Editor / Markdown Renderer -> Outline Parser.
# Keep enough UTF-16 capacity for worst-case LF->CRLF expansion of a ~1 MiB ASCII file.
# V8.4.5: robust large-document capacities. The previous build also had a
# verified ABI bug in rebuild_outline (misaligned RSP at Win32 API calls); fixed below. A 4 MiB ASCII LF-only file can
# expand to almost 8.4M UTF-16 code units when normalized to CRLF.
WIDE_CHARS = 8_500_000
MAX_FILE_BYTES = 4_194_304
# Saving UTF-16 source as UTF-8 can take up to 4 bytes/code unit; leave headroom.
BYTE_CAP = 34_500_000
bss_alloc('document_len', 4, 4)
bss_alloc('suppress_edit_change', 4, 4)
bss_alloc('render_len', 4, 4)
# For each visible Preview UTF-16 code unit, remember which source UTF-16 index produced it.
# This makes Source <-> Preview caret mapping independent of word-wrap and RichEdit line semantics.
bss_alloc('render_srcmap', WIDE_CHARS*4, 16)
bss_alloc('document_model', WIDE_CHARS*2, 16)
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
        'SetWindowTextW','SendMessageW','MoveWindow','SetWindowPos','MessageBoxW','SetFocus',
        'RegisterClassExW','DefWindowProcW','PostQuitMessage','PostMessageW','LoadCursorW',
        'DestroyWindow','ShowWindow','CheckMenuItem','GetWindowRect','GetClientRect','wsprintfW','RegisterWindowMessageW','InvalidateRect','UpdateWindow','RedrawWindow',
        'GetCursorPos','ScreenToClient','SetCapture','ReleaseCapture','SetCursor','SetScrollRange','SetScrollPos','ShowScrollBar','GetSystemMetrics','SetTimer','KillTimer',
        'CreateAcceleratorTableW','TranslateAcceleratorW','DestroyAcceleratorTable','IsDialogMessageW','SetForegroundWindow','DrawMenuBar','DrawTextW','FillRect','GetMenuStringW','SetMenuInfo','GetWindowDC','ReleaseDC','GetMenuItemRect'
    ],
    'COMDLG32.dll': ['GetOpenFileNameW','GetSaveFileNameW','FindTextW','ReplaceTextW'],
    'SHLWAPI.dll': ['StrStrW','StrStrIW'],
    'COMCTL32.dll': ['InitCommonControlsEx'],
    'GDI32.dll': ['CreateFontW','DeleteObject','CreateSolidBrush','SetTextColor','SetBkColor','SetBkMode','GetClipBox','SelectObject'],
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
    def movsxd_r64_r32(self,dst,src):
        d,s=REG[dst],REG[src]; self.rex(w=1,r=(d>>3)&1,b=(s>>3)&1); self.emit(0x63,0xC0|((d&7)<<3)|(s&7))
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
    def shl_r32_imm8(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0xC1,0xE0|(r&7),imm&255)
    def sar_r32_imm8(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0xC1,0xF8|(r&7),imm&255)
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
em.mov_ripmem_imm32(bsyms['outline_width'],228)
em.mov_ripmem_imm32(bsyms['splitter_drag'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],0)
em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],0)
em.mov_ripmem_imm32(bsyms['theme_dark'],0)
em.mov_ripmem_imm32(bsyms['zoom_pct'],100)
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_ripmem_imm32(bsyms['find_flags'],1)
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['client_w'],884)
em.mov_ripmem_imm32(bsyms['client_h'],590)
# Use the system vertical-scrollbar metric as the single scrollbar width source.
# The Outline's ListBox scrollbar has slightly heavier themed chrome than RichEdit
# on current Windows, so cover a tiny DPI-proportional strip on its *left* edge.
em.mov_r32_imm('rcx',2); em.call_iat('GetSystemMetrics'); em.mov_ripmem_r32(bsyms['scrollbar_w'],'rax')  # SM_CXVSCROLL
em.mov_r32_r32('r10','rax'); em.shr_r32_imm8('r10',3)  # ~1/8 of native width: 2px at 100%, scales with DPI
em.cmp_r32_imm('r10',1); em.jcc(0x83,'scroll_trim_min_ok'); em.mov_r32_imm('r10',1)
em.label('scroll_trim_min_ok'); em.cmp_r32_imm('r10',3); em.jcc(0x86,'scroll_trim_max_ok'); em.mov_r32_imm('r10',3)
em.label('scroll_trim_max_ok'); em.mov_ripmem_r32(bsyms['scroll_trim_w'],'r10')
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
em.call_iat('CreateMenu'); em.mov_r64_r64('rdi','rax'); em.mov_ripmem_r64(bsyms['hmenu_main'],'rax')
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
append_imm('r14',0,1401,'m_md_h1'); append_imm('r14',0,1402,'m_md_h2'); append_imm('r14',0,1410,'m_md_h3'); append_imm('r14',0,1411,'m_md_h4'); append_imm('r14',0,1412,'m_md_h5'); append_imm('r14',0,1413,'m_md_h6'); append_sep('r14')
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
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_main']); em.lea_rip('r8',rsyms['title']); em.mov_r32_imm('r9',0x12CF0000)  # WS_CLIPCHILDREN
em.mov_mrsp_imm32(0x20,0x80000000); em.mov_mrsp_imm32(0x28,0x80000000); em.mov_mrsp_imm32(0x30,900); em.mov_mrsp_imm32(0x38,650)
em.mov_mrsp_imm32(0x40,0,qword=True); em.mov_mrsp_reg64(0x48,'rdi'); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rbx','rax'); em.mov_ripmem_r64(bsyms['hwnd_main'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# Child EDIT
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x54211044)  # WS_CLIPSIBLINGS
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,884); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi')
# Increase edit text limit to ~1M chars
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',WIDE_CHARS-1); em.xor32('r9'); em.call_iat('SendMessageW')
# Unified 10px left/right Source inset (EM_SETMARGINS, EC_LEFT|EC_RIGHT).
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00D3); em.mov_r32_imm('r8',3); em.mov_r32_imm('r9',0x000A000A); em.call_iat('SendMessageW')
# Create a real font so zooming can be implemented with WM_SETFONT.
em.call_label('apply_zoom')
# V8.4.5: Outline and status bar are UI chrome, not document content.
# Give them fixed ClearType fonts so document zoom does not make them huge and
# so the very first owner-draw paint uses deterministic glyph rasterization.
# Outline: ~11pt/15px. Status: ~9pt/12px at 96 DPI.
em.mov_r32_imm('rcx',0xFFFFFFF1); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9')
em.mov_mrsp_imm32(0x20,400); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0); em.mov_mrsp_imm32(0x40,1); em.mov_mrsp_imm32(0x48,0); em.mov_mrsp_imm32(0x50,0); em.mov_mrsp_imm32(0x58,5); em.mov_mrsp_imm32(0x60,0)
em.lea_rip('rax',rsyms['font_face']); em.mov_mrsp_reg64(0x68,'rax'); em.call_iat('CreateFontW'); em.mov_ripmem_r64(bsyms['hfont_outline'],'rax')
em.mov_r32_imm('rcx',0xFFFFFFF4); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9')
em.mov_mrsp_imm32(0x20,400); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0); em.mov_mrsp_imm32(0x40,1); em.mov_mrsp_imm32(0x48,0); em.mov_mrsp_imm32(0x50,0); em.mov_mrsp_imm32(0x58,5); em.mov_mrsp_imm32(0x60,0)
em.lea_rip('rax',rsyms['font_face']); em.mov_mrsp_reg64(0x68,'rax'); em.call_iat('CreateFontW'); em.mov_ripmem_r64(bsyms['hfont_status'],'rax')
em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus')

# Native Windows status bar (common-controls class).
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_status']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x54000040)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,2,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_status'],'rax')
em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont_status']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x0404); em.mov_r32_imm('r8',6); em.lea_rip('r9',rsyms['status_parts']); em.call_iat('SendMessageW')
# Small theme-colored STATIC overlay at the status bar's lower-right edge. Some
# Windows builds still paint a legacy light sizing-grip there even without
# SBARS_SIZEGRIP; this child masks only that decorative corner.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,56); em.mov_mrsp_imm32(0x38,24)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,5,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_corner'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# Load the system Rich Edit engine and create a hidden full-window rendered Markdown surface.
em.lea_rip('rcx',rsyms['dll_msftedit']); em.call_iat('LoadLibraryW'); em.test64('rax'); em.jcc(0x84,'exit')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_richedit']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x44211844)  # WS_CLIPSIBLINGS
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,3,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_preview'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# Rich Edit 2.0+ requires EM_EXLIMITTEXT (WM_USER+53 = 0x0435) for limits
# above 64K. Without this, large Preview documents can become unstable/truncated.
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0435); em.xor32('r8'); em.mov_r32_imm('r9',WIDE_CHARS-1); em.call_iat('SendMessageW')
# Same 10px document inset in rendered mode.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00D3); em.mov_r32_imm('r8',3); em.mov_r32_imm('r9',0x000A000A); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Left Markdown outline. A simple native listbox keeps the Direct-PE build small;
# heading levels are represented by indentation and each item stores source/render positions.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_listbox']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x54210151)  # WS_CLIPSIBLINGS
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,230); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,4,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x01A0); em.xor32('r8'); em.mov_r32_imm('r9',30); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont_outline']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Keep the ListBox's own themed scrollbar hidden until the pointer approaches the divider.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.xor32('r8'); em.call_iat('ShowScrollBar')
# V8.4.13: the *visual* divider is only one pixel wide. Mouse resizing uses a
# separate logical 8px hit-zone in the message pump, so visible geometry and
# interaction geometry can no longer fight each other.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)  # SS_OWNERDRAW | WS_CLIPSIBLINGS
em.mov_mrsp_imm32(0x20,228); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,1); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,6,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_splitter'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# A tiny owner-drawn strip overlays only the left edge of the ListBox's native
# scrollbar while it is visible. The remaining native thumb/track stays fully
# clickable and draggable, but its visual width matches the slimmer RichEdit bar.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x4400000D)  # hidden SS_OWNERDRAW | WS_CLIPSIBLINGS
em.mov_mrsp_imm32(0x20,210); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,2); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,7,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_scroll_trim'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# The Outline's own native themed scrollbar is still the real interactive bar.
# It is shown/hidden dynamically with ShowScrollBar; the trim changes appearance only.
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
em.cmp_r32_imm('rax',0x0113); em.jcc(0x84,'timer_event')  # WM_TIMER: debounced Preview theme maintenance
# Splitter hover/drag is handled in the thread pump because mouse messages are
# delivered to child controls, not the top-level WndProc.
em.cmp_r32_imm('rax',0x0200); em.jcc(0x84,'mousemove_event')
em.cmp_r32_imm('rax',0x0201); em.jcc(0x84,'lbuttondown_event')
em.cmp_r32_imm('rax',0x0202); em.jcc(0x84,'lbuttonup_event')
# Ctrl+mouse-wheel zoom. WM_MOUSEWHEEL is queued for the focused child EDIT window,
# so intercept it in the thread message pump before DispatchMessageW.
em.cmp_r32_imm('rax',0x020A); em.jcc(0x84,'mousewheel_event')
em.jmp('dispatch')

em.label('mousemove_event')
# If splitter is being dragged, resize Outline live from current screen cursor.
em.mov_r32_ripmem('rax',bsyms['splitter_drag']); em.test32('rax'); em.jcc(0x84,'mousemove_hover_only')
em.call_label('splitter_drag_move'); em.jmp('msg_loop')
em.label('mousemove_hover_only'); em.call_label('update_outline_hover'); em.jmp('dispatch')

em.label('lbuttondown_event')
# Logical 8px resize hit-zone centered on the 1px divider. We hit-test in main
# client coordinates regardless of which child received WM_LBUTTONDOWN.
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'dispatch')
em.lea_rip('rcx',bsyms['cursor_pt']); em.call_iat('GetCursorPos'); em.test32('rax'); em.jcc(0x84,'dispatch')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient'); em.test32('rax'); em.jcc(0x84,'dispatch')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width'])
# If the native Outline scrollbar is showing, its left side must remain click/drag owned by Windows.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'split_hit_full_zone'); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'dispatch')
em.label('split_hit_full_zone')
em.mov_r32_r32('rax','r11'); em.sub_r32_imm8('rax',4); em.cmp_r32_r32('r10','rax'); em.jcc(0x8C,'dispatch'); em.add_r32_imm8('r11',4); em.cmp_r32_r32('r10','r11'); em.jcc(0x8F,'dispatch')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.test32('r10'); em.jcc(0x88,'dispatch'); em.mov_r32_ripmem('r11',bsyms['content_h']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'dispatch')
em.mov_ripmem_imm32(bsyms['splitter_drag'],1); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.call_iat('SetCapture')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.xor32('r8'); em.call_iat('ShowScrollBar'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.call_label('splitter_drag_move'); em.jmp('msg_loop')

em.label('lbuttonup_event')
em.mov_r32_ripmem('rax',bsyms['splitter_drag']); em.test32('rax'); em.jcc(0x84,'dispatch')
em.mov_ripmem_imm32(bsyms['splitter_drag'],0); em.call_iat('ReleaseCapture'); em.call_label('update_outline_hover'); em.jmp('msg_loop')

# Theme restyling is never performed synchronously inside WM_MOUSEWHEEL anymore.
# Repeated wheel/scroll messages restart this short timer; only after scrolling
# has been idle for ~180 ms do we refresh semantic colors in the visible viewport.
em.label('timer_event')
em.mov_rax_mr12(16); em.cmp_r32_imm('rax',0x4D); em.jcc(0x85,'dispatch')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',0x4D); em.call_iat('KillTimer')
em.call_label('refresh_preview_visible_theme'); em.jmp('msg_loop')

em.label('document_changed_event')
em.call_label('sync_model_from_editor'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('outline_select_event')
em.call_label('navigate_outline'); em.jmp('msg_loop')

em.label('mousewheel_event')
# wParam: LOWORD = MK_* key flags; HIWORD = signed wheel delta.
# Ctrl+wheel remains document zoom.  A plain wheel over the borderless Outline
# scrolls the ListBox manually so we keep wheel navigation without a bulky native scrollbar.
em.mov_rax_mr12(16)
em.mov_r32_r32('r10','rax'); em.and_r32_imm('r10',0x0008); em.test32('r10'); em.jcc(0x85,'mousewheel_zoom')
# No Ctrl: hit-test the wheel's screen coordinates against Outline, independent
# of keyboard focus. This keeps hover-wheel navigation even though the native scrollbar is hidden.
em.mov_rax_mr12(24); em.mov_r32_r32('r10','rax'); em.shl_r32_imm8('r10',16); em.sar_r32_imm8('r10',16); em.mov_ripmem_r32(bsyms['wheel_x'],'r10'); em.mov_r32_r32('r11','rax'); em.sar_r32_imm8('r11',16); em.mov_ripmem_r32(bsyms['wheel_y'],'r11')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'dispatch'); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetWindowRect'); em.test32('rax'); em.jcc(0x84,'dispatch')
em.mov_r32_ripmem('r10',bsyms['wheel_x']); em.mov_r32_ripmem('r11',bsyms['rect']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'dispatch'); em.mov_r32_ripmem('r11',bsyms['rect']+8); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'dispatch')
em.mov_r32_ripmem('r10',bsyms['wheel_y']); em.mov_r32_ripmem('r11',bsyms['rect']+4); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'dispatch'); em.mov_r32_ripmem('r11',bsyms['rect']+12); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'dispatch')
# Read current top index and row count.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018E); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['outline_scroll_count'],'rax')
# Direction from signed HIWORD; scroll three 30px rows per wheel notch.
em.mov_rax_mr12(16); em.mov_r32_r32('r10','rax'); em.shr_r32_imm8('r10',16); em.mov_r32_r32('r11','r10'); em.and_r32_imm('r11',0x8000); em.test32('r11'); em.jcc(0x85,'outline_wheel_down')
em.label('outline_wheel_up')
em.mov_r32_ripmem('r8',bsyms['outline_scroll_top']); em.cmp_r32_imm('r8',3); em.jcc(0x83,'outline_wheel_up_sub'); em.xor32('r8'); em.jmp('outline_wheel_send')
em.label('outline_wheel_up_sub'); em.sub_r32_imm8('r8',3); em.jmp('outline_wheel_send')
em.label('outline_wheel_down')
em.mov_r32_ripmem('r8',bsyms['outline_scroll_top']); em.add_r32_imm8('r8',3)
em.mov_r32_ripmem('r11',bsyms['outline_scroll_count']); em.test32('r11'); em.jcc(0x84,'msg_loop'); em.sub_r32_imm8('r11',1); em.cmp_r32_r32('r8','r11'); em.jcc(0x86,'outline_wheel_send'); em.mov_r32_r32('r8','r11')
em.label('outline_wheel_send')
em.mov_ripmem_r32(bsyms['outline_scroll_top'],'r8'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.xor32('r9'); em.call_iat('SendMessageW'); em.jmp('msg_loop')
em.label('mousewheel_zoom')
em.mov_rax_mr12(16); em.mov_r32_r32('r10','rax'); em.shr_r32_imm8('r10',16); em.test32('r10'); em.jcc(0x84,'msg_loop')
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
                  (1401,'cmd_md_h1'),(1402,'cmd_md_h2'),(1410,'cmd_md_h3'),(1411,'cmd_md_h4'),(1412,'cmd_md_h5'),(1413,'cmd_md_h6'),(1403,'cmd_md_bold'),(1404,'cmd_md_italic'),(1405,'cmd_md_inline'),(1406,'cmd_md_codeblock'),(1407,'cmd_md_quote'),(1408,'cmd_md_bullet'),(1409,'cmd_md_link')]:
    em.cmp_r32_imm('rax',cid); em.jcc(0x84,label)
em.jmp('dispatch')

em.label('cmd_new')
em.lea_rip('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['document_len'],0); em.call_label('load_model_into_editor')
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
em.mov_r32_ripmem('r13',bsyms['io_count'])
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
# NUL terminate raw buffer at actual byte count returned by ReadFile
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
em.lea_rip('rdx',bsyms['widebuf']); em.mov_word_index2_zero('rdx','rax')
em.lea_rip('rcx',bsyms['widebuf']); em.call_label('normalize_to_document_model'); em.call_label('load_model_into_editor')
# copy successful path
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('decode_empty')
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.lea_rip('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['document_len'],0); em.call_label('load_model_into_editor')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('decode_utf16')
em.mov_ripmem_imm32(bsyms['encoding_state'],1)
em.lea_rip('rcx',bsyms['bytebuf']); em.add_r64_imm8('rcx',2); em.call_label('normalize_to_document_model'); em.call_label('load_model_into_editor')
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
# Persist only the canonical Document Model. Synchronize once in case a queued EN_CHANGE is pending.
em.call_label('sync_model_from_editor'); em.mov_r32_ripmem('r13',bsyms['document_len']); em.cmp_r32_imm('r13',WIDE_CHARS-1); em.jcc(0x87,'err_save')
# Convert if nonempty
em.test32('r13'); em.jcc(0x84,'save_zero_bytes')
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.lea_rip('r8',bsyms['document_model']); em.mov_r32_r32('r9','r13'); em.lea_rip('rax',bsyms['bytebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_mrsp_imm32(0x28,BYTE_CAP); em.mov_mrsp_imm32(0x30,0,qword=True); em.mov_mrsp_imm32(0x38,0,qword=True); em.call_iat('WideCharToMultiByte'); em.test32('rax'); em.jcc(0x84,'err_save'); em.mov_r32_r32('r13','rax'); em.jmp('save_create')
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
em.label('cmd_md_h3'); em.lea_rip('r10',rsyms['md_h3']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_h4'); em.lea_rip('r10',rsyms['md_h4']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_h5'); em.lea_rip('r10',rsyms['md_h5']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_md_h6'); em.lea_rip('r10',rsyms['md_h6']); em.call_label('md_prefix_line'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')
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
em.call_label('capture_zoom_anchor'); em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.add_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('restore_zoom_anchor'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomout')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.cmp_r32_imm('rax',50); em.jcc(0x86,'msg_loop') # jbe
em.call_label('capture_zoom_anchor'); em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.sub_r32_imm8('rax',10); em.mov_ripmem_r32(bsyms['zoom_pct'],'rax'); em.call_label('apply_zoom'); em.call_label('restore_zoom_anchor'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_zoomreset')
em.call_label('capture_zoom_anchor'); em.mov_ripmem_imm32(bsyms['zoom_pct'],100); em.call_label('apply_zoom'); em.call_label('restore_zoom_anchor'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('cmd_wrap')
em.mov_r32_ripmem('rax',bsyms['wrap_flag']); em.test32('rax'); em.jcc(0x84,'wrap_enable')
em.mov_ripmem_imm32(bsyms['wrap_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1304); em.xor32('r8'); em.call_iat('CheckMenuItem'); em.jmp('wrap_recreate')
em.label('wrap_enable')
em.mov_ripmem_imm32(bsyms['wrap_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1304); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.label('wrap_recreate')
# Preserve selection and canonical Document Model, then recreate the EDIT control.
em.call_label('sync_model_from_editor')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.call_iat('DestroyWindow')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.lea_rip('r8',bsyms['document_model'])
em.mov_r32_ripmem('rax',bsyms['wrap_flag']); em.test32('rax'); em.jcc(0x84,'wrap_style_off')
em.mov_r32_imm('r9',0x54211044)  # WS_CLIPSIBLINGS; em.jmp('wrap_style_ready')
em.label('wrap_style_off'); em.mov_r32_imm('r9',0x503110C4)
em.label('wrap_style_ready')
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',WIDE_CHARS-1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Apply the 10px Source text gutter after WM_SETFONT so it cannot be reset by the font change.
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00D3); em.mov_r32_imm('r8',3); em.mov_r32_imm('r9',0x000A000A); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.mov_r32_ripmem('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.call_label('resize_children'); em.call_label('update_preview'); em.call_label('update_status')
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'wrap_focus_source')
em.mov_r64_r64('rcx','rsi'); em.xor32('rdx'); em.call_iat('ShowWindow'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow'); em.call_iat('SetFocus'); em.jmp('msg_loop')
em.label('wrap_focus_source'); em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus'); em.jmp('msg_loop')

em.label('cmd_status')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'status_show')
em.mov_ripmem_imm32(bsyms['status_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1305); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.jmp('msg_loop')
em.label('status_show')
em.mov_ripmem_imm32(bsyms['status_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1305); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.call_label('resize_children'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('cmd_preview')
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'preview_show')
# Preview -> Source: capture selection AND the first visible paragraph anchor,
# map both back into source coordinates, then restore the same viewport after switching.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('capture_surface_state')
em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_sel_start'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_sel_end']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_sel_end'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_top_pos'],'rax')
em.mov_ripmem_imm32(bsyms['preview_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.jmp('msg_loop')

em.label('preview_show')
# Source -> Preview: capture source viewport/caret, render once, map selection +
# top-visible anchor through render_srcmap, then restore them in RichEdit.
em.call_label('sync_model_from_editor')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_label('capture_surface_state')
em.mov_ripmem_imm32(bsyms['preview_flag'],1)
em.call_label('update_preview')
em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_sel_start'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_sel_end']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_sel_end'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_top_pos'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_iat('SetFocus'); em.jmp('msg_loop')

em.label('cmd_outline')
# Sidebar visibility changes only layout.  Do NOT rebuild Markdown/SetWindowText.
# Freeze the active document surface while RichEdit/EDIT recalculates wrapping,
# then restore its exact caret and top-visible anchor in one final paint.
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'outline_capture_source')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.jmp('outline_capture_ready')
em.label('outline_capture_source'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit'])
em.label('outline_capture_ready'); em.call_label('capture_surface_state')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'outline_show')
em.mov_ripmem_imm32(bsyms['outline_flag'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.xor32('r8'); em.call_iat('ShowScrollBar'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.xor32('r8'); em.call_iat('CheckMenuItem'); em.jmp('outline_layout')
em.label('outline_show')
em.mov_ripmem_imm32(bsyms['outline_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.label('outline_layout')
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.jmp('msg_loop')

# Theme changes reuse the already parsed render buffer/style table. They never
# rescan Markdown or replace the RichEdit text.  In Preview mode repaint is frozen
# while base colors + <=4096 recorded spans are restyled, then viewport is restored.
em.label('cmd_light'); em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.jmp('theme_fast_apply')
em.label('cmd_dark'); em.mov_ripmem_imm32(bsyms['theme_dark'],1); em.jmp('theme_fast_apply')
em.label('cmd_theme_toggle')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_toggle_dark')
em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.jmp('theme_fast_apply')
em.label('theme_toggle_dark'); em.mov_ripmem_imm32(bsyms['theme_dark'],1)
em.label('theme_fast_apply')
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'theme_fast_source')
# Theme switching in Preview is viewport-scoped: only currently visible text and
# intersecting Markdown spans are reformatted synchronously. Offscreen regions
# are lazily refreshed when the user scrolls, avoiding multi-second full-doc stalls.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('capture_surface_state')
em.call_label('set_visible_format_window'); em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],1); em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.call_label('apply_theme'); em.call_label('apply_styles'); em.call_label('apply_preview_zoom')
em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.jmp('msg_loop')
em.label('theme_fast_source'); em.call_label('apply_theme'); em.jmp('msg_loop')

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
em.lea_rip('rcx',bsyms['msg']); em.call_iat('TranslateMessage'); em.lea_rip('rcx',bsyms['msg']); em.call_iat('DispatchMessageW')
# If a theme switch left offscreen Preview ranges stale, never restyle RichEdit
# synchronously inside wheel/scroll dispatch.  Doing so caused every wheel notch
# to change the selection/format ranges while RichEdit was also scrolling, which
# looked like a whole-document 'shake'.  Debounce the maintenance until scrolling
# has been idle for ~180 ms.
em.mov_r32_ripmem('rax',bsyms['preview_theme_dirty']); em.test32('rax'); em.jcc(0x84,'dispatch_theme_refresh_done')
em.mov_rax_mr12(0); em.mov_r64_ripmem('r10',bsyms['hwnd_preview']); em.cmp_r64_r64('rax','r10'); em.jcc(0x85,'dispatch_theme_refresh_done')
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x0115); em.jcc(0x84,'dispatch_theme_schedule'); em.cmp_r32_imm('rax',0x020A); em.jcc(0x85,'dispatch_theme_refresh_done')
em.label('dispatch_theme_schedule')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',0x4D); em.mov_r32_imm('r8',180); em.xor32('r9'); em.call_iat('SetTimer')
em.label('dispatch_theme_refresh_done')
# V8.4.4: do NOT refresh the owner-drawn status bar after every dispatched
# message. WM_MOUSEMOVE used to cause six SB_SETTEXT redraws per message,
# producing visible flicker. Refresh only after input that can change caret/selection.
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x0100); em.jcc(0x84,'dispatch_status_refresh') # WM_KEYDOWN
em.cmp_r32_imm('rax',0x0101); em.jcc(0x84,'dispatch_status_refresh')                     # WM_KEYUP
em.cmp_r32_imm('rax',0x0201); em.jcc(0x84,'dispatch_status_refresh')                     # WM_LBUTTONDOWN
em.cmp_r32_imm('rax',0x0202); em.jcc(0x84,'dispatch_status_refresh')                     # WM_LBUTTONUP
em.jmp('dispatch_status_done')
em.label('dispatch_status_refresh'); em.call_label('update_status')
em.label('dispatch_status_done'); em.mov_r64_r64('rcx','rbx'); em.call_iat('IsWindow'); em.test32('rax'); em.jcc(0x85,'msg_loop')

# ------------------------------------------------------------------
# Helper: synchronize floating Outline scrollbar range/position.
em.label('sync_outline_scrollbar')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.test64('rcx'); em.jcc(0x84,'sync_os_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r32_r32('r10','rax'); em.test32('r10'); em.jcc(0x85,'sync_os_have'); em.xor32('r10'); em.jmp('sync_os_range')
em.label('sync_os_have'); em.sub_r32_imm8('r10',1)
em.label('sync_os_range'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',2); em.xor32('r8'); em.mov_r32_r32('r9','r10'); em.mov_mrsp_imm32(0x20,1); em.call_iat('SetScrollRange')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018E); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r32_r32('r8','rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',2); em.mov_r32_imm('r9',1); em.call_iat('SetScrollPos')
em.label('sync_os_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: reveal the Outline's own native themed scrollbar only while the pointer
# is near the divider. A tiny overlay trims its left edge to visually match the
# document scrollbar; the native thumb itself remains the draggable control.
em.label('update_outline_hover')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'hover_hide')
em.mov_r32_ripmem('rax',bsyms['splitter_drag']); em.test32('rax'); em.jcc(0x85,'hover_hide')
em.lea_rip('rcx',bsyms['cursor_pt']); em.call_iat('GetCursorPos'); em.test32('rax'); em.jcc(0x84,'hover_hide')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient'); em.test32('rax'); em.jcc(0x84,'hover_hide')
# Hover zone: rightmost 20px of Outline plus 8px around the divider.
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.mov_r32_r32('rax','r11'); em.sub_r32_imm8('rax',20); em.cmp_r32_r32('r10','rax'); em.jcc(0x8C,'hover_hide'); em.add_r32_imm8('r11',4); em.cmp_r32_r32('r10','r11'); em.jcc(0x8F,'hover_hide')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.test32('r10'); em.jcc(0x88,'hover_hide'); em.mov_r32_ripmem('r11',bsyms['content_h']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'hover_hide')
# Show native ListBox scrollbar + its narrow visual trim only once.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x85,'hover_cursor')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.mov_r32_imm('r8',1); em.call_iat('ShowScrollBar'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
# Keep the trim above the ListBox non-client scrollbar while preserving its geometry.
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0x0013); em.call_iat('SetWindowPos')
em.call_label('repaint_splitter_surface')
em.label('hover_cursor')
# Size-WE cursor in the logical 8px hit-zone, except over the visible native scrollbar.
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width'])
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'hover_cursor_zone'); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'hover_done')
em.label('hover_cursor_zone')
em.mov_r32_r32('rax','r11'); em.sub_r32_imm8('rax',4); em.cmp_r32_r32('r10','rax'); em.jcc(0x8C,'hover_done'); em.add_r32_imm8('r11',4); em.cmp_r32_r32('r10','r11'); em.jcc(0x8F,'hover_done')
em.xor32('rcx'); em.mov_r32_imm('rdx',32644); em.call_iat('LoadCursorW'); em.mov_r64_r64('rcx','rax'); em.call_iat('SetCursor'); em.jmp('hover_done')
em.label('hover_hide')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'hover_done')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.xor32('r8'); em.call_iat('ShowScrollBar'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.call_iat('ShowWindow'); em.call_label('repaint_splitter_surface')
em.label('hover_done'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: live splitter drag; clamp Outline to 140..500 px while preserving at least 240px document width.
em.label('splitter_drag_move')
em.emit(0x48,0x83,0xEC,0x28)
em.lea_rip('rcx',bsyms['cursor_pt']); em.call_iat('GetCursorPos'); em.test32('rax'); em.jcc(0x84,'split_drag_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient'); em.test32('rax'); em.jcc(0x84,'split_drag_ret')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.cmp_r32_imm('r10',140); em.jcc(0x83,'split_drag_min_ok'); em.mov_r32_imm('r10',140)
em.label('split_drag_min_ok'); em.mov_r32_ripmem('r11',bsyms['client_w']); em.mov_r32_imm('rax',240); em.sub_r32_r32('r11','rax'); em.cmp_r32_imm('r11',500); em.jcc(0x86,'split_drag_max_ready'); em.mov_r32_imm('r11',500)
em.label('split_drag_max_ready'); em.cmp_r32_imm('r11',140); em.jcc(0x83,'split_drag_have_max'); em.mov_r32_imm('r11',140)
em.label('split_drag_have_max'); em.cmp_r32_r32('r10','r11'); em.jcc(0x86,'split_drag_store'); em.mov_r32_r32('r10','r11')
em.label('split_drag_store'); em.mov_ripmem_r32(bsyms['outline_width'],'r10'); em.call_label('resize_children')
em.label('split_drag_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: compute the current theme-format window without touching RichEdit
# character metrics. Used by the fast theme path before apply_styles.
em.label('set_visible_format_window')
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.mov_r32_r32('r9','r8'); em.mov_r32_imm('rax',40000); em.add_r32_r32('r9','rax'); em.mov_r32_ripmem('rax',bsyms['render_len']); em.cmp_r32_r32('r9','rax'); em.jcc(0x86,'visible_window_ok'); em.mov_r32_r32('r9','rax')
em.label('visible_window_ok'); em.mov_ripmem_r32(bsyms['format_visible_end'],'r9'); em.emit(0xC3)

# Helper: after a theme change, lazily repaint only semantic styles in the current Preview viewport.
em.label('refresh_preview_visible_theme')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'refresh_visible_ret')
em.mov_r32_ripmem('rax',bsyms['preview_theme_dirty']); em.test32('rax'); em.jcc(0x84,'refresh_visible_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('capture_surface_state')
# Suppress all intermediate paints while selection/ranges are temporarily changed.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.call_label('set_visible_format_window'); em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],1); em.call_label('apply_styles'); em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.label('refresh_visible_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: force an owner-drawn repaint of the splitter.  Moving the RichEdit
# from x=0 back to the right when Outline is reopened can leave a few glyph pixels
# in the narrow uncovered strip unless that child repaints synchronously.
em.label('repaint_splitter_surface')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'repaint_splitter_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.test64('rcx'); em.jcc(0x84,'repaint_splitter_ret')
# Standard EDIT/RichEdit controls can finish an asynchronous paint after a MoveWindow.
# Keep the separator above them and clip sibling drawing so glyphs cannot leak into it.
em.xor32('rdx')  # HWND_TOP
em.xor32('r8'); em.xor32('r9')
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0x0013)  # SWP_NOSIZE|NOMOVE|NOACTIVATE
em.call_iat('SetWindowPos')
# Synchronously erase+paint only the splitter itself.
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.xor32('r8'); em.mov_r32_imm('r9',0x0105); em.call_iat('RedrawWindow')
em.label('repaint_splitter_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: resize Outline + active full-window Edit/Preview + native status bar.
em.label('resize_children')
em.emit(0x48,0x83,0xEC,0x38)
em.xor32('rax'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'resize_content')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'resize_content')
em.mov_r32_imm('rdx',0x0005); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetWindowRect')
em.mov_r32_ripmem('rax',bsyms['rect']+12); em.mov_r32_ripmem('r10',bsyms['rect']+4); em.sub_r32_r32('rax','r10'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
# Keep the corner cover aligned with the status bar's right edge.
em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.test64('rcx'); em.jcc(0x84,'resize_content')
# Put the owner-drawn corner cover at the top of the child Z-order *after*
# the native status bar has processed WM_SIZE; otherwise comctl32 may repaint
# its resize corner above our cover.
em.xor32('rdx')
em.mov_r32_ripmem('r8',bsyms['client_w']); em.sub_r32_imm8('r8',56)
em.mov_r32_ripmem('r9',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r9','rax')
em.mov_mrsp_imm32(0x20,56); em.mov_r32_ripmem('r11',bsyms['status_h']); em.mov_mrsp_reg32(0x28,'r11'); em.mov_mrsp_imm32(0x30,0x0040); em.call_iat('SetWindowPos')
em.label('resize_content')
# One geometry source of truth: every content child ends at the exact same
# contentBottom = clientHeight - statusHeight. This prevents the divider from
# ever stopping short and exposing a bright parent strip near the bottom.
em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax'); em.mov_ripmem_r32(bsyms['content_h'],'r11')
em.mov_ripmem_imm32(bsyms['content_x'],0)
em.mov_r32_ripmem('r10',bsyms['client_w']); em.mov_ripmem_r32(bsyms['content_w'],'r10')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'resize_hide_sidebar_chrome')
# Visual divider = exactly 1px. The 8px drag target is logical only and consumes no layout width.
em.mov_r32_ripmem('r10',bsyms['outline_width']); em.mov_r32_r32('r11','r10'); em.add_r32_imm8('r11',1); em.mov_ripmem_r32(bsyms['content_x'],'r11')
em.mov_r32_ripmem('rax',bsyms['client_w']); em.sub_r32_r32('rax','r11'); em.mov_ripmem_r32(bsyms['content_w'],'rax')
# Outline, visual divider, and both document surfaces all use content_h verbatim.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'resize_splitter')
em.xor32('rdx'); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_splitter')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.test64('rcx'); em.jcc(0x84,'resize_scroll_trim')
em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.xor32('r8'); em.mov_r32_imm('r9',1); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_scroll_trim')
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.test64('rcx'); em.jcc(0x84,'resize_doc')
# Position trim over the *left* edge of the native ListBox vertical scrollbar.
em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.mov_r32_ripmem('rax',bsyms['scrollbar_w']); em.sub_r32_r32('rdx','rax'); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['scroll_trim_w']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow'); em.jmp('resize_doc')
em.label('resize_hide_sidebar_chrome')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',1); em.xor32('r8'); em.call_iat('ShowScrollBar'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.label('resize_doc')
# Source edit surface.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'resize_preview_surface')
em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_preview_surface')
# Rendered Rich Edit surface, at exactly the same rectangle.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'resize_ret')
em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_ret'); em.call_label('repaint_splitter_surface'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: create a new source EDIT font for current zoom_pct. Preview uses
# RichEdit EM_SETZOOM, so changing zoom never reparses/reformats the whole Markdown document.
em.label('apply_zoom')
em.emit(0x48,0x81,0xEC,u32(0x88))
em.mov_r64_ripmem('rax',bsyms['hfont']); em.mov_ripmem_r64(bsyms['old_hfont'],'rax')
em.mov_r32_ripmem('rax',bsyms['zoom_pct']); em.emit(0x6B,0xC0,0x10); em.emit(0x99); em.mov_r32_imm('rcx',100); em.emit(0xF7,0xF9); em.emit(0xF7,0xD8)
em.mov_r32_r32('rcx','rax'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9')
em.mov_mrsp_imm32(0x20,400); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0); em.mov_mrsp_imm32(0x38,0); em.mov_mrsp_imm32(0x40,1); em.mov_mrsp_imm32(0x48,0); em.mov_mrsp_imm32(0x50,0); em.mov_mrsp_imm32(0x58,5); em.mov_mrsp_imm32(0x60,0)
em.lea_rip('rax',rsyms['font_face']); em.mov_mrsp_reg64(0x68,'rax'); em.call_iat('CreateFontW'); em.test64('rax'); em.jcc(0x84,'font_preview_zoom')
em.mov_ripmem_r64(bsyms['hfont'],'rax')
# redraw=FALSE: restore the caret/viewport first, then invalidate once.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'font_preview_zoom'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.xor32('r9'); em.call_iat('SendMessageW')
# WM_SETFONT can restore EDIT's default text margins; restore our 10px gutter after the font change.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00D3); em.mov_r32_imm('r8',3); em.mov_r32_imm('r9',0x000A000A); em.call_iat('SendMessageW')
em.label('font_preview_zoom'); em.call_label('apply_preview_zoom')
em.mov_r64_ripmem('rcx',bsyms['old_hfont']); em.test64('rcx'); em.jcc(0x84,'font_ret'); em.call_iat('DeleteObject')
em.label('font_ret'); em.emit(0x48,0x81,0xC4,u32(0x88)); em.emit(0xC3)

# RichEdit display-only zoom: EM_SETZOOM = WM_USER + 225 = 0x04E1.
em.label('apply_preview_zoom')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'preview_zoom_ret')
em.mov_r32_imm('rdx',0x04E1); em.mov_r32_ripmem('r8',bsyms['zoom_pct']); em.mov_r32_imm('r9',100); em.call_iat('SendMessageW')
em.label('preview_zoom_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Capture exact selection in the currently visible document surface before zoom.
em.label('capture_zoom_anchor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'zoom_anchor_source')
em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.jmp('zoom_anchor_ready')
em.label('zoom_anchor_source'); em.mov_r64_ripmem('rax',bsyms['hwnd_edit'])
em.label('zoom_anchor_ready'); em.mov_ripmem_r64(bsyms['view_hwnd'],'rax'); em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['view_sel_start']); em.lea_rip('r9',bsyms['view_sel_end']); em.call_iat('SendMessageW')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Restore the exact selection and force the caret back into view after a zoom reflow.
em.label('restore_zoom_anchor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.test64('rcx'); em.jcc(0x84,'zoom_restore_ret'); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.mov_r32_ripmem('r9',bsyms['view_sel_end']); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00B7); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.xor32('rdx'); em.xor32('r8'); em.call_iat('InvalidateRect')
em.label('zoom_restore_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Capture selection plus the character offset of the first visible logical line
# in the supplied EDIT/RichEdit control.  This survives width changes much better
# than simply calling EM_SCROLLCARET on the caret.
em.label('capture_surface_state')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_r64(bsyms['view_hwnd'],'rcx')
em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['view_sel_start']); em.lea_rip('r9',bsyms['view_sel_end']); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00CE); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r32_r32('r8','rax')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00BB); em.xor32('r9'); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x85,'surface_capture_top_ok'); em.xor32('rax')
em.label('surface_capture_top_ok'); em.mov_ripmem_r32(bsyms['view_top_pos'],'rax')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Scroll supplied control so view_top_pos's logical line returns to the top,
# then restore the exact selection/caret without asking EM_SCROLLCARET to move it.
em.label('restore_surface_state')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_r64(bsyms['view_hwnd'],'rcx')
# target line from saved character anchor. RichEdit 2.0+ uses EM_EXLINEFROMCHAR
# for reliable 32-bit character indices; the classic EDIT uses EM_LINEFROMCHAR.
em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.mov_r64_ripmem('r10',bsyms['view_hwnd']); em.cmp_r64_r64('r10','rax'); em.jcc(0x84,'surface_restore_preview_line')
em.mov_r64_r64('rcx','r10'); em.mov_r32_imm('rdx',0x00C9); em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.xor32('r9'); em.call_iat('SendMessageW'); em.jmp('surface_restore_line_ready')
em.label('surface_restore_preview_line'); em.mov_r64_r64('rcx','r10'); em.mov_r32_imm('rdx',0x0436); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['view_top_pos']); em.call_iat('SendMessageW')
em.label('surface_restore_line_ready'); em.mov_ripmem_r32(bsyms['view_line'],'rax')
# current first visible line
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00CE); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
# delta = target-current, passed as signed LPARAM to EM_LINESCROLL
em.mov_r32_ripmem('r9',bsyms['view_line']); em.sub_r32_r32('r9','rax'); em.movsxd_r64_r32('r9','r9')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00B6); em.xor32('r8'); em.call_iat('SendMessageW')
# restore exact selection/caret after viewport scroll
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.mov_r32_ripmem('r9',bsyms['view_sel_end']); em.call_iat('SendMessageW')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Capture logical line/column in a source or preview control passed in RCX.
em.label('capture_view_anchor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_r64(bsyms['view_hwnd'],'rcx')
em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['view_sel_start']); em.lea_rip('r9',bsyms['view_sel_end']); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00C9); em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['view_line'],'rax')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00BB); em.mov_r32_ripmem('r8',bsyms['view_line']); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['view_line_start'],'rax')
em.mov_r32_ripmem('r10',bsyms['view_sel_start']); em.sub_r32_r32('r10','rax'); em.mov_ripmem_r32(bsyms['view_col'],'r10')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Restore the saved logical line/column into a control passed in RCX and scroll it into view.
em.label('restore_view_anchor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_r64(bsyms['view_hwnd'],'rcx')
em.mov_r32_imm('rdx',0x00BB); em.mov_r32_ripmem('r8',bsyms['view_line']); em.xor32('r9'); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x85,'view_line_ok'); em.xor32('rax')
em.label('view_line_ok'); em.mov_ripmem_r32(bsyms['view_line_start'],'rax')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00C1); em.mov_r32_r32('r8','rax'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['view_line_len'],'rax')
em.mov_r32_ripmem('r10',bsyms['view_col']); em.cmp_r32_r32('r10','rax'); em.jcc(0x86,'view_col_ok'); em.mov_r32_r32('r10','rax')
em.label('view_col_ok'); em.mov_r32_ripmem('r8',bsyms['view_line_start']); em.add_r32_r32('r8','r10'); em.mov_r32_r32('r9','r8')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x00B7); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.label('view_restore_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Map a Source UTF-16 index (r8d) to the nearest Preview index using the
# monotonic render_srcmap. Returns EAX; end-of-document maps to render_len.
em.label('map_source_to_render')
em.mov_r32_ripmem('r9',bsyms['render_len']); em.test32('r9'); em.jcc(0x85,'msr_nonempty'); em.xor32('rax'); em.emit(0xC3)
em.label('msr_nonempty'); em.xor32('r10'); em.mov_r32_r32('r11','r9')  # lo=0, hi=len
em.label('msr_loop'); em.cmp_r32_r32('r10','r11'); em.jcc(0x83,'msr_done')
em.mov_r32_r32('rax','r10'); em.add_r32_r32('rax','r11'); em.shr_r32_imm8('rax',1)
em.mov_r32_r32('rdx','rax'); em.add_r32_r32('rdx','rdx'); em.add_r32_r32('rdx','rdx'); em.lea_rip('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','rdx'); em.mov_r32_ptr('rdx','rcx')
em.cmp_r32_r32('rdx','r8'); em.jcc(0x82,'msr_move_lo'); em.mov_r32_r32('r11','rax'); em.jmp('msr_loop')
em.label('msr_move_lo'); em.mov_r32_r32('r10','rax'); em.add_r32_imm8('r10',1); em.jmp('msr_loop')
em.label('msr_done'); em.mov_r32_r32('rax','r10'); em.emit(0xC3)

# Map a Preview UTF-16 index (r8d) back to its exact source-producing index.
# A caret at Preview EOF maps to Document EOF.
em.label('map_render_to_source')
em.mov_r32_ripmem('r9',bsyms['render_len']); em.test32('r9'); em.jcc(0x85,'mrs_nonempty'); em.xor32('rax'); em.emit(0xC3)
em.label('mrs_nonempty'); em.cmp_r32_r32('r8','r9'); em.jcc(0x82,'mrs_inrange'); em.mov_r32_ripmem('rax',bsyms['document_len']); em.emit(0xC3)
em.label('mrs_inrange'); em.mov_r32_r32('rax','r8'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.lea_rip('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('rax','rcx'); em.emit(0xC3)

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

# V8.4.1 Document Model helpers.  These are the only paths that synchronize
# source text into the canonical model.  Renderer/Outline never read the EDIT directly.
# normalize_to_document_model(rcx = NUL-terminated UTF-16 source): normalize CRLF/LF/CR -> CRLF.
em.label('normalize_to_document_model')
em.emit(0x56); em.emit(0x57); em.emit(0x41,0x54); em.emit(0x41,0x55)
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('rsi','rcx'); em.lea_rip('rdi',bsyms['document_model']); em.xor32('r12'); em.xor32('r13')
em.label('doc_norm_loop')
em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'doc_norm_done')
em.cmp_r32_imm('r13',WIDE_CHARS-3); em.jcc(0x83,'doc_norm_done')
em.cmp_r32_imm('rax',0x0D); em.jcc(0x84,'doc_norm_cr')
em.cmp_r32_imm('rax',0x0A); em.jcc(0x84,'doc_norm_lf')
em.mov_word_index2_reg('rdi','r13','rax'); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.jmp('doc_norm_loop')
em.label('doc_norm_cr')
# Consume CR and consume a following LF if present; emit one canonical CRLF pair.
em.add_r32_imm8('r12',1); em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x85,'doc_norm_emit_crlf'); em.add_r32_imm8('r12',1)
em.label('doc_norm_emit_crlf')
em.mov_word_index2_imm16('rdi','r13',0x0D); em.add_r32_imm8('r13',1); em.mov_word_index2_imm16('rdi','r13',0x0A); em.add_r32_imm8('r13',1); em.jmp('doc_norm_loop')
em.label('doc_norm_lf')
em.add_r32_imm8('r12',1); em.mov_word_index2_imm16('rdi','r13',0x0D); em.add_r32_imm8('r13',1); em.mov_word_index2_imm16('rdi','r13',0x0A); em.add_r32_imm8('r13',1); em.jmp('doc_norm_loop')
em.label('doc_norm_done')
em.mov_word_index2_zero('rdi','r13'); em.mov_ripmem_r32(bsyms['document_len'],'r13')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0x5F); em.emit(0x5E); em.emit(0xC3)

# Source Editor -> Document Model. Standard multiline EDIT returns canonical CRLF.
em.label('sync_model_from_editor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'sync_model_ret')
em.call_iat('GetWindowTextLengthW'); em.cmp_r32_imm('rax',WIDE_CHARS-1); em.jcc(0x87,'sync_model_ret')
em.mov_r32_r32('r8','rax'); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.lea_rip('rdx',bsyms['document_model']); em.call_iat('GetWindowTextW')
em.mov_ripmem_r32(bsyms['document_len'],'rax')
em.label('sync_model_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Document Model -> Source Editor. Suppress EN_CHANGE and visible incremental redraw.
# For very large documents SetWindowText can otherwise visibly repaint/scroll while layout is built.
em.label('load_model_into_editor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_imm32(bsyms['suppress_edit_change'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'load_model_unsuppress')
# Hide the EDIT while the native control builds line/wrap structures for a large file.
# WM_SETREDRAW alone still allowed visible progressive layout on some Windows builds.
em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.lea_rip('rdx',bsyms['document_model']); em.call_iat('SetWindowTextW')
# A newly opened document starts at its true beginning.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
# Only expose Source when Source mode is active; Preview mode keeps it hidden.
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x85,'load_model_invalidate')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.label('load_model_invalidate'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.label('load_model_unsuppress'); em.mov_ripmem_imm32(bsyms['suppress_edit_change'],0)
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

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
# Five nonvolatile pushes leave RSP 16-byte aligned; reserve exactly 32 bytes of shadow space.
em.emit(0x48,0x83,0xEC,0x20)
em.mov_ripmem_imm32(bsyms['outline_count'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'outline_rebuild_pop')
# Freeze ListBox painting while rebuilding a potentially large outline.
em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0184); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.lea_rip('rsi',bsyms['document_model']); em.xor32('r12'); em.mov_r32_imm('r14',1)
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
# Hard-cap native listbox rows BEFORE LB_ADDSTRING. This prevents huge heading-heavy files
# from continuously allocating listbox strings after our position arrays reach capacity.
em.mov_r32_ripmem('r15',bsyms['outline_count']); em.cmp_r32_imm('r15',2048); em.jcc(0x83,'outline_after_add')
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
em.label('outline_rebuild_ret')
# One final ListBox paint after the full outline is populated.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'outline_rebuild_pop'); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.call_label('sync_outline_scrollbar')
em.label('outline_rebuild_pop'); em.add_r64_imm8('rsp',0x20); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0x5E); em.emit(0xC3)

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
em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_imm32('r11',12,220)
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'preview_text_light'); em.mov_mreg_imm32('r11',20,0x00D4D4D4); em.jmp('preview_text_ready')
em.label('preview_text_light'); em.mov_mreg_imm32('r11',20,0x00202020)
em.label('preview_text_ready'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_face']); em.call_iat('lstrcpyW')
em.mov_r32_ripmem('rax',bsyms['preview_visible_format_only']); em.test32('rax'); em.jcc(0x84,'preview_base_all')
# Visible-theme window: format roughly 40K UTF-16 code units around the top anchor.
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.mov_r32_r32('r9','r8'); em.mov_r32_imm('rax',40000); em.add_r32_r32('r9','rax'); em.mov_r32_ripmem('rax',bsyms['render_len']); em.cmp_r32_r32('r9','rax'); em.jcc(0x86,'preview_base_end_ok'); em.mov_r32_r32('r9','rax')
em.label('preview_base_end_ok'); em.mov_ripmem_r32(bsyms['format_visible_end'],'r9')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.mov_r32_imm('r8',1); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW'); em.jmp('preview_base_ret')
em.label('preview_base_all'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.mov_r32_imm('r8',4); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW')
em.label('preview_base_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: theme-only Preview base update. Background changes immediately; existing
# text receives only a COLOR mask for the whole control, so RichEdit does not
# recompute font metrics/line layout for hundreds of thousands of characters.
em.label('apply_preview_theme_color')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.test64('rax'); em.jcc(0x84,'preview_theme_color_ret')
# Background.
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0443); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['theme_dark']); em.test32('r9'); em.jcc(0x84,'preview_theme_bg_light'); em.mov_r32_imm('r9',0x001E1E1E); em.jmp('preview_theme_bg_send')
em.label('preview_theme_bg_light'); em.mov_r32_imm('r9',0x00FFFFFF)
em.label('preview_theme_bg_send'); em.call_iat('SendMessageW')
# CHARFORMATW color only, SCF_ALL. This preserves heading sizes, bold/italic,
# code fonts and paragraph layout, so theme toggles do not trigger a full reflow.
em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_imm32('r11',0,116); em.mov_mreg_imm32('r11',4,0x40000000); em.mov_mreg_imm32('r11',8,0)
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'preview_theme_text_light'); em.mov_mreg_imm32('r11',20,0x00D4D4D4); em.jmp('preview_theme_text_ready')
em.label('preview_theme_text_light'); em.mov_mreg_imm32('r11',20,0x00202020)
em.label('preview_theme_text_ready'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.mov_r32_imm('r8',4); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW')
em.label('preview_theme_color_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

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
# During a theme-only viewport refresh, skip spans completely outside the current
# visible formatting window. The style array scan is cheap; expensive RichEdit
# range formatting is limited to what can actually be seen.
em.mov_r32_ripmem('rax',bsyms['preview_visible_format_only']); em.test32('rax'); em.jcc(0x84,'style_range_send')
em.mov_r32_ripmem('rax',bsyms['view_top_pos']); em.cmp_r32_r32('r9','rax'); em.jcc(0x86,'style_next')
em.mov_r32_ripmem('rax',bsyms['format_visible_end']); em.cmp_r32_r32('r8','rax'); em.jcc(0x83,'style_next')
em.label('style_range_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW')
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
em.label('style_heading_size'); em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_reg32('r11',12,'rcx'); em.jmp('style_send')

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

# Emit one render-position -> source-position map write. r13d is the output index,
# r12d is the source index. r10/rcx are scratch at these copy sites.
def emit_render_map_current_source():
    em.mov_r32_r32('r10','r13'); em.add_r32_r32('r10','r10'); em.add_r32_r32('r10','r10')
    em.lea_rip('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','r10'); em.mov_ptr_r32('rcx','r12')

# Helper: rebuild Markdown render buffer, formatting spans and outline from source text.
em.label('update_preview')
em.emit(0x56); em.emit(0x57); em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57)
em.emit(0x48,0x83,0xEC,0x28)
# Read ONLY the canonical Document Model. Renderer is deliberately isolated from Source EDIT.
em.lea_rip('rcx',bsyms['document_model']); em.cmp_word_ptr_reg_zero('rcx');
# Outline always parses the same Document Model, independently of Preview formatting.
em.call_label('rebuild_outline')
# In source-edit mode the preview is hidden.  Keep the outline current, but do not
# parse/format the hidden RichEdit surface.  This also makes incomplete Markdown
# safe while the user is in the middle of typing it.
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
em.mov_ripmem_imm32(bsyms['style_count'],0); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0); em.mov_ripmem_imm32(bsyms['heading_index'],0); em.mov_ripmem_imm32(bsyms['render_len'],0)
em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_ripmem_imm32(bsyms['link_flag'],0)
em.lea_rip('rsi',bsyms['document_model']); em.lea_rip('rdi',bsyms['previewbuf']); em.xor32('r12'); em.xor32('r13'); em.mov_r32_imm('r14',1); em.xor32('r15')

em.label('pv8_loop')
# Never let malformed input or a future renderer rule overrun Preview Buffer.
em.cmp_r32_imm('r13',WIDE_CHARS-8); em.jcc(0x83,'pv8_eof')
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
em.label('pv8_fence_lf'); em.mov_word_index2_imm16('rdi','r13',0x0D); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.jmp('pv8_loop')

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
em.label('pv8_bullet_ws_ok'); em.mov_word_index2_imm16('rdi','r13',0x2022); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.mov_word_index2_imm16('rdi','r13',0x20); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',2); em.xor32('r14'); em.jmp('pv8_loop')
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

em.label('pv8_copy'); em.mov_word_index2_reg('rdi','r13','rax'); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

em.label('pv8_codeblock_copy'); em.movzx_r32_word_index2('rax','rsi','r12'); em.cmp_r32_imm('rax',0x0D); em.jcc(0x85,'pv8_codeblock_not_cr'); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')
em.label('pv8_codeblock_not_cr'); em.cmp_r32_imm('rax',0x0A); em.jcc(0x85,'pv8_codeblock_plain'); em.mov_word_index2_imm16('rdi','r13',0x0D); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.jmp('pv8_loop')
em.label('pv8_codeblock_plain'); em.mov_word_index2_reg('rdi','r13','rax'); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.jmp('pv8_loop')

em.label('pv8_lf')
# Close malformed/unclosed inline spans at line end so formatting stays local.
em.mov_r32_ripmem('rax',bsyms['bold_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_italic'); em.mov_r32_ripmem('r8',bsyms['bold_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',10); em.call_label('add_style')
em.label('pv8_lf_italic'); em.mov_r32_ripmem('rax',bsyms['italic_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_code'); em.mov_r32_ripmem('r8',bsyms['italic_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',11); em.call_label('add_style')
em.label('pv8_lf_code'); em.mov_r32_ripmem('rax',bsyms['inlinecode_flag']); em.test32('rax'); em.jcc(0x84,'pv8_lf_heading'); em.mov_r32_ripmem('r8',bsyms['code_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',12); em.call_label('add_style')
em.label('pv8_lf_heading'); em.mov_r32_ripmem('r10',bsyms['heading_level']); em.test32('r10'); em.jcc(0x84,'pv8_lf_quote'); em.mov_ripmem_r32(bsyms['heading_out_end'],'r13'); em.mov_r32_ripmem('r8',bsyms['heading_out_start']); em.mov_r32_r32('r9','r13'); em.call_label('add_style')
em.label('pv8_lf_quote'); em.mov_r32_ripmem('rax',bsyms['line_flags']); em.test32('rax'); em.jcc(0x84,'pv8_lf_copy'); em.mov_r32_ripmem('r8',bsyms['quote_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',13); em.call_label('add_style')
em.label('pv8_lf_copy'); em.mov_word_index2_imm16('rdi','r13',0x0D); emit_render_map_current_source(); em.add_r32_imm8('r13',1); em.add_r32_imm8('r12',1); em.mov_r32_imm('r14',1); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0); em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_ripmem_imm32(bsyms['link_flag'],0); em.jmp('pv8_loop')

em.label('pv8_eof')
# Finalize last line and open fenced block if the file does not end with LF.
em.mov_r32_ripmem('r10',bsyms['heading_level']); em.test32('r10'); em.jcc(0x84,'pv8_eof_quote'); em.mov_ripmem_r32(bsyms['heading_out_end'],'r13'); em.mov_r32_ripmem('r8',bsyms['heading_out_start']); em.mov_r32_r32('r9','r13'); em.call_label('add_style')
em.label('pv8_eof_quote'); em.mov_r32_ripmem('rax',bsyms['line_flags']); em.test32('rax'); em.jcc(0x84,'pv8_eof_codeblock'); em.mov_r32_ripmem('r8',bsyms['quote_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',13); em.call_label('add_style')
em.label('pv8_eof_codeblock'); em.test32('r15'); em.jcc(0x84,'pv8_finish'); em.mov_r32_ripmem('r8',bsyms['codeblock_out_start']); em.mov_r32_r32('r9','r13'); em.mov_r32_imm('r10',15); em.call_label('add_style')
em.label('pv8_finish'); em.mov_ripmem_r32(bsyms['render_len'],'r13'); em.mov_word_index2_zero('rdi','r13')
# Populate the hidden or visible Rich Edit render surface.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'pv_render_ret'); em.lea_rip('rdx',bsyms['previewbuf']); em.call_iat('SetWindowTextW'); em.call_label('apply_preview_base'); em.call_label('apply_styles'); em.call_label('apply_preview_zoom')
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

# Helper: explicitly repaint the native non-client menu gap and bottom separator.
# Classic Win32 menus do not consistently honor dark brushes for the empty area to
# the right of the last top-level item.  Paint only that uncovered rectangle and a
# 2px separator in the window DC; menu items themselves remain system/UAH drawn.
em.label('paint_menu_gaps')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'paint_menu_gap_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.test64('rcx'); em.jcc(0x84,'paint_menu_gap_ret')
em.mov_r64_ripmem('rdx',bsyms['hmenu_main']); em.mov_r32_imm('r8',4); em.lea_rip('r9',bsyms['nc_itemrect']); em.call_iat('GetMenuItemRect'); em.test32('rax'); em.jcc(0x84,'paint_menu_gap_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['nc_winrect']); em.call_iat('GetWindowRect'); em.test32('rax'); em.jcc(0x84,'paint_menu_gap_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.call_iat('GetWindowDC'); em.test64('rax'); em.jcc(0x84,'paint_menu_gap_ret'); em.mov_ripmem_r64(bsyms['paint_hdc'],'rax')
# draw_rect = {lastItem.right-win.left, lastItem.top-win.top, win.right-win.left, lastItem.bottom-win.top+2}
em.mov_r32_ripmem('rax',bsyms['nc_itemrect']+8); em.mov_r32_ripmem('r10',bsyms['nc_winrect']); em.sub_r32_r32('rax','r10'); em.lea_rip('rcx',bsyms['draw_rect']); em.mov_ptr_r32('rcx','rax')
em.mov_r32_ripmem('rax',bsyms['nc_itemrect']+4); em.mov_r32_ripmem('r10',bsyms['nc_winrect']+4); em.sub_r32_r32('rax','r10'); em.mov_mreg_reg32('rcx',4,'rax')
em.mov_r32_ripmem('rax',bsyms['nc_winrect']+8); em.mov_r32_ripmem('r10',bsyms['nc_winrect']); em.sub_r32_r32('rax','r10'); em.mov_mreg_reg32('rcx',8,'rax')
em.mov_r32_ripmem('rax',bsyms['nc_itemrect']+12); em.mov_r32_ripmem('r10',bsyms['nc_winrect']+4); em.sub_r32_r32('rax','r10'); em.add_r32_imm8('rax',2); em.mov_mreg_reg32('rcx',12,'rax')
em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.lea_rip('rdx',bsyms['draw_rect']); em.mov_r64_ripmem('r8',bsyms['hbrush_menu']); em.call_iat('FillRect')
# Paint the full-width two-pixel separator immediately below the top-level menu row.
em.lea_rip('rcx',bsyms['draw_rect']); em.xor32('rax'); em.mov_ptr_r32('rcx','rax')
em.mov_r32_ripmem('rax',bsyms['nc_itemrect']+12); em.mov_r32_ripmem('r10',bsyms['nc_winrect']+4); em.sub_r32_r32('rax','r10'); em.mov_mreg_reg32('rcx',4,'rax')
em.mov_r32_ripmem('r10',bsyms['nc_winrect']+8); em.mov_r32_ripmem('r11',bsyms['nc_winrect']); em.sub_r32_r32('r10','r11'); em.mov_mreg_reg32('rcx',8,'r10'); em.add_r32_imm8('rax',2); em.mov_mreg_reg32('rcx',12,'rax')
em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.lea_rip('rdx',bsyms['draw_rect']); em.mov_r64_ripmem('r8',bsyms['hbrush_menu']); em.call_iat('FillRect')
# V8.4.5: lower-right client corner is handled by an owner-drawn topmost child cover.

em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r64_ripmem('rdx',bsyms['paint_hdc']); em.call_iat('ReleaseDC')
em.label('paint_menu_gap_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: apply Light/Dark display theme to source editor, outline, preview, status and title bar.
em.label('apply_theme')
em.emit(0x48,0x83,0xEC,0x38)
# Retire old brushes.
em.mov_r64_ripmem('rcx',bsyms['hbrush_edit']); em.test64('rcx'); em.jcc(0x84,'theme_del_outline'); em.call_iat('DeleteObject')
em.label('theme_del_outline'); em.mov_r64_ripmem('rcx',bsyms['hbrush_outline']); em.test64('rcx'); em.jcc(0x84,'theme_del_splitter'); em.call_iat('DeleteObject')
em.label('theme_del_splitter'); em.mov_r64_ripmem('rcx',bsyms['hbrush_splitter']); em.test64('rcx'); em.jcc(0x84,'theme_del_status'); em.call_iat('DeleteObject')
em.label('theme_del_status'); em.mov_r64_ripmem('rcx',bsyms['hbrush_status']); em.test64('rcx'); em.jcc(0x84,'theme_del_menu'); em.call_iat('DeleteObject')
em.label('theme_del_menu'); em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'theme_make'); em.call_iat('DeleteObject')
em.label('theme_make'); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_make_light')
em.mov_r32_imm('rcx',0x001A1A1A); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x001F1F1F); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x001D1D1D); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_splitter'],'rax'); em.mov_r32_imm('rcx',0x00202020); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_status'],'rax'); em.mov_r32_imm('rcx',0x00202020); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax'); em.jmp('theme_controls')
em.label('theme_make_light'); em.mov_r32_imm('rcx',0x00FFFFFF); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x00F3F4F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x00E8EAED); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_splitter'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_status'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax')
em.label('theme_controls')
# Documented MENUINFO background fills the *entire* menu bar, including the empty
# area to the right of Help, and applies the brush recursively to submenus.
em.lea_rip('r12',bsyms['menuinfo']); em.mov_mr12_imm32(0,40); em.mov_mr12_imm32(4,0x80000002)
em.mov_r64_ripmem('rax',bsyms['hbrush_menu']); em.mov_mr12_reg64(16,'rax')
em.mov_r64_ripmem('rcx',bsyms['hmenu_main']); em.mov_r64_r64('rdx','r12'); em.call_iat('SetMenuInfo')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'theme_dwm'); em.mov_r32_imm('rdx',0x2001); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['theme_dark']); em.test32('r9'); em.jcc(0x84,'theme_status_light'); em.mov_r32_imm('r9',0x00202020); em.jmp('theme_status_send')
em.label('theme_status_light'); em.mov_r32_imm('r9',0x00F5F5F5)
em.label('theme_status_send'); em.call_iat('SendMessageW')
em.label('theme_dwm')
# Dark/light non-client title bar on modern Windows.
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.mov_ripmem_r32(bsyms['theme_bool'],'rax'); em.mov_r64_r64('rcx','rbx'); em.mov_r32_imm('rdx',20); em.lea_rip('r8',bsyms['theme_bool']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute')
# Windows 11: explicitly color border/caption/text.  The border color also removes
# the stubborn light resize-corner/frame pixels that child controls cannot cover.
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_dwm_light_colors')
em.mov_ripmem_imm32(bsyms['theme_color'],0x001A1A1A); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',34); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute')
em.mov_ripmem_imm32(bsyms['theme_color'],0x00202020); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',35); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute')
em.mov_ripmem_imm32(bsyms['theme_color'],0x00E8E8E8); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',36); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute'); em.jmp('theme_dwm_colors_done')
em.label('theme_dwm_light_colors'); em.mov_ripmem_imm32(bsyms['theme_color'],0xFFFFFFFF); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',34); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute'); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',35); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute'); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',36); em.lea_rip('r8',bsyms['theme_color']); em.mov_r32_imm('r9',4); em.call_iat('DwmSetWindowAttribute')
em.label('theme_dwm_colors_done')
# Check Light/Dark menu items.
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1310); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x85,'theme_light_unchecked'); em.mov_r32_imm('r8',0x8); em.jmp('theme_light_check')
em.label('theme_light_unchecked'); em.xor32('r8')
em.label('theme_light_check'); em.call_iat('CheckMenuItem')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1311); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_dark_unchecked'); em.mov_r32_imm('r8',0x8); em.jmp('theme_dark_check')
em.label('theme_dark_unchecked'); em.xor32('r8')
em.label('theme_dark_check'); em.call_iat('CheckMenuItem')
em.call_label('apply_preview_theme_color')
# Repaint child surfaces so WM_CTLCOLOR* immediately uses the new brushes/colors.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_scroll_trim']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.call_iat('UpdateWindow'); em.call_label('paint_menu_gaps')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1100); em.lea_rip('r9',bsyms['status_linebuf']); em.call_iat('SendMessageW')
# character counts
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.mov_r32_ripmem('r11',bsyms['sel_start']); em.sub_r32_r32('r10','r11'); em.mov_ripmem_r32(bsyms['selected_chars'],'r10')
em.lea_rip('rcx',bsyms['status_charsbuf']); em.lea_rip('rdx',rsyms['fmt_chars']); em.mov_r32_ripmem('r8',bsyms['total_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1101); em.lea_rip('r9',bsyms['status_charsbuf']); em.call_iat('SendMessageW')
em.lea_rip('rcx',bsyms['status_selbuf']); em.lea_rip('rdx',rsyms['fmt_selected']); em.mov_r32_ripmem('r8',bsyms['selected_chars']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1102); em.lea_rip('r9',bsyms['status_selbuf']); em.call_iat('SendMessageW')
# zoom percent
em.lea_rip('rcx',bsyms['status_zoombuf']); em.lea_rip('rdx',rsyms['fmt_zoom']); em.mov_r32_ripmem('r8',bsyms['zoom_pct']); em.call_iat('wsprintfW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1103); em.lea_rip('r9',bsyms['status_zoombuf']); em.call_iat('SendMessageW')
# line endings
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1104); em.lea_rip('r9',rsyms['status_crlf']); em.call_iat('SendMessageW')
# encoding
em.mov_r32_ripmem('rax',bsyms['encoding_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'enc_utf16'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'enc_ansi'); em.lea_rip('r9',rsyms['status_utf8']); em.jmp('enc_send')
em.label('enc_utf16'); em.lea_rip('r9',rsyms['status_utf16']); em.jmp('enc_send')
em.label('enc_ansi'); em.lea_rip('r9',rsyms['status_ansi'])
em.label('enc_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1105); em.call_iat('SendMessageW')
em.label('status_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('exit')
em.mov_r64_ripmem('rcx',bsyms['hfont']); em.test64('rcx'); em.jcc(0x84,'exit_font_outline'); em.call_iat('DeleteObject')
em.label('exit_font_outline'); em.mov_r64_ripmem('rcx',bsyms['hfont_outline']); em.test64('rcx'); em.jcc(0x84,'exit_font_status'); em.call_iat('DeleteObject')
em.label('exit_font_status'); em.mov_r64_ripmem('rcx',bsyms['hfont_status']); em.test64('rcx'); em.jcc(0x84,'exit_brush_menu'); em.call_iat('DeleteObject')
em.label('exit_brush_menu'); em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'exit_accel'); em.call_iat('DeleteObject')
em.label('exit_accel'); em.mov_r64_ripmem('rcx',bsyms['haccel']); em.test64('rcx'); em.jcc(0x84,'exit_now'); em.call_iat('DestroyAcceleratorTable')
em.label('exit_now'); em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)

# ------------------------------------------------------------------
# Real application WndProc. Windows delivers menu, child notifications,
# live sizing and control-color messages synchronously to this callback.
em.label('wndproc')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('r10',bsyms['findmsg_id']); em.cmp_r32_r32('rdx','r10'); em.jcc(0x84,'wp_findreplace')
em.cmp_r32_imm('rdx',0x0111); em.jcc(0x84,'wp_command')      # WM_COMMAND
em.cmp_r32_imm('rdx',0x0115); em.jcc(0x84,'wp_vscroll')      # WM_VSCROLL (floating Outline scrollbar)
em.cmp_r32_imm('rdx',0x0005); em.jcc(0x84,'wp_size')         # WM_SIZE
em.cmp_r32_imm('rdx',0x0002); em.jcc(0x84,'wp_destroy')      # WM_DESTROY
em.cmp_r32_imm('rdx',0x0006); em.jcc(0x84,'wp_activation')    # WM_ACTIVATE
em.cmp_r32_imm('rdx',0x0085); em.jcc(0x84,'wp_ncpaint')       # WM_NCPAINT
em.cmp_r32_imm('rdx',0x0086); em.jcc(0x84,'wp_activation')    # WM_NCACTIVATE
em.cmp_r32_imm('rdx',0x002B); em.jcc(0x84,'wp_drawitem')     # WM_DRAWITEM (status + outline)
em.cmp_r32_imm('rdx',0x002C); em.jcc(0x84,'wp_measureitem')  # WM_MEASUREITEM (outline row height)
em.cmp_r32_imm('rdx',0x0091); em.jcc(0x84,'wp_uah_drawmenu') # WM_UAHDRAWMENU
em.cmp_r32_imm('rdx',0x0092); em.jcc(0x84,'wp_uah_drawitem') # WM_UAHDRAWMENUITEM
em.cmp_r32_imm('rdx',0x0014); em.jcc(0x84,'wp_erasebkgnd')   # WM_ERASEBKGND
em.cmp_r32_imm('rdx',0x0133); em.jcc(0x84,'wp_ctlcolor_edit') # WM_CTLCOLOREDIT
em.cmp_r32_imm('rdx',0x0134); em.jcc(0x84,'wp_ctlcolor_list') # WM_CTLCOLORLISTBOX
em.cmp_r32_imm('rdx',0x0138); em.jcc(0x84,'wp_ctlcolor_static') # WM_CTLCOLORSTATIC (corner cover)
em.label('wp_default'); em.call_iat('DefWindowProcW'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_vscroll')
# Handle only our floating Outline scrollbar; other controls keep default behavior.
em.mov_r64_ripmem('rax',bsyms['hwnd_outline_scroll']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_default')
# preserve wParam across API calls, then read current top index
em.mov_ripmem_r32(bsyms['vscroll_wparam'],'r8')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018E); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r32_r32('r10','rax')
# code = LOWORD(wParam), track pos = HIWORD(wParam)
em.mov_r32_ripmem('rax',bsyms['vscroll_wparam']); em.and_r32_imm('rax',0xFFFF)
em.cmp_r32_imm('rax',4); em.jcc(0x84,'wp_vs_thumb'); em.cmp_r32_imm('rax',5); em.jcc(0x84,'wp_vs_thumb')
em.cmp_r32_imm('rax',0); em.jcc(0x84,'wp_vs_lineup'); em.cmp_r32_imm('rax',1); em.jcc(0x84,'wp_vs_linedown'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'wp_vs_pageup'); em.cmp_r32_imm('rax',3); em.jcc(0x84,'wp_vs_pagedown'); em.jmp('wp_vs_apply')
em.label('wp_vs_thumb'); em.mov_r32_ripmem('r10',bsyms['vscroll_wparam']); em.shr_r32_imm8('r10',16); em.jmp('wp_vs_apply')
em.label('wp_vs_lineup'); em.test32('r10'); em.jcc(0x84,'wp_vs_apply'); em.sub_r32_imm8('r10',1); em.jmp('wp_vs_apply')
em.label('wp_vs_linedown'); em.add_r32_imm8('r10',1); em.jmp('wp_vs_clamp')
em.label('wp_vs_pageup'); em.cmp_r32_imm('r10',10); em.jcc(0x83,'wp_vs_pageup_sub'); em.xor32('r10'); em.jmp('wp_vs_apply')
em.label('wp_vs_pageup_sub'); em.sub_r32_imm8('r10',10); em.jmp('wp_vs_apply')
em.label('wp_vs_pagedown'); em.add_r32_imm8('r10',10)
em.label('wp_vs_clamp'); em.mov_r32_ripmem('r11',bsyms['outline_count']); em.test32('r11'); em.jcc(0x84,'wp_vs_zero'); em.sub_r32_imm8('r11',1); em.cmp_r32_r32('r10','r11'); em.jcc(0x86,'wp_vs_apply'); em.mov_r32_r32('r10','r11'); em.jmp('wp_vs_apply')
em.label('wp_vs_zero'); em.xor32('r10')
em.label('wp_vs_apply'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'r10'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.mov_r32_ripmem('r8',bsyms['outline_scroll_top']); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',2); em.mov_r32_ripmem('r8',bsyms['outline_scroll_top']); em.mov_r32_imm('r9',1); em.call_iat('SetScrollPos')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_command')
# Source EDIT notifications: EN_CHANGE -> rebuild outline/render on the outer message loop.
em.mov_r64_ripmem('rax',bsyms['hwnd_edit']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_cmd_outline_check')
em.mov_r32_r32('r10','r8'); em.shr_r32_imm8('r10',16); em.cmp_r32_imm('r10',0x0300); em.jcc(0x85,'wp_child_return')
# Programmatic Source loads/recreation must not feed back into the Document Model.
em.mov_r32_ripmem('r10',bsyms['suppress_edit_change']); em.test32('r10'); em.jcc(0x85,'wp_child_return')
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

# For non-client repaints, let Windows draw the frame/menu items first, then cover
# only the classic light menu gap/separator with our dark brush.
em.label('wp_ncpaint')
em.call_iat('DefWindowProcW'); em.mov_ripmem_r64(bsyms['defproc_result'],'rax'); em.call_label('paint_menu_gaps'); em.mov_r64_ripmem('rax',bsyms['defproc_result']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Let Windows perform its normal activate/non-client handling first, then force
# every themed child to repaint. This prevents stale black backing pixels from
# remaining when another app becomes the foreground window.
em.label('wp_activation')
em.call_iat('DefWindowProcW'); em.mov_ripmem_r64(bsyms['defproc_result'],'rax'); em.call_label('paint_menu_gaps')
for child in ('hwnd_edit','hwnd_preview','hwnd_outline','hwnd_status'):
    em.mov_r64_ripmem('rcx',bsyms[child]); em.test64('rcx'); em.jcc(0x84,f'wp_act_skip_{child}'); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms[child]); em.call_iat('UpdateWindow'); em.label(f'wp_act_skip_{child}')
em.mov_r64_ripmem('rax',bsyms['defproc_result']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Give the owner-drawn outline a relaxed, fixed row height.
em.label('wp_measureitem')
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',4); em.jcc(0x85,'wp_default'); em.mov_mreg_imm32('r9',16,30); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Owner-draw status bar and outline rows.
em.label('wp_drawitem')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',2); em.jcc(0x84,'wp_draw_status'); em.cmp_r32_imm('rax',4); em.jcc(0x84,'wp_draw_outline'); em.cmp_r32_imm('rax',5); em.jcc(0x84,'wp_draw_corner'); em.cmp_r32_imm('rax',6); em.jcc(0x84,'wp_draw_splitter'); em.cmp_r32_imm('rax',7); em.jcc(0x84,'wp_draw_scroll_trim'); em.jmp('wp_default')

em.label('wp_draw_status')
# Owner-draw callbacks do not guarantee our WM_SETFONT font is selected into
# the supplied HDC. Select the ClearType UI font explicitly for deterministic text quality.
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_ripmem('rdx',bsyms['hfont_status']); em.call_iat('SelectObject'); em.mov_ripmem_r64(bsyms['draw_old_font'],'rax')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_status']); em.call_iat('FillRect')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_status_text_light'); em.mov_r32_imm('rdx',0x00E6E6E6); em.jmp('wp_status_text_send')
em.label('wp_status_text_light'); em.mov_r32_imm('rdx',0x00202020)
em.label('wp_status_text_send'); em.call_iat('SetTextColor')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',1); em.call_iat('SetBkMode')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_mreg('rdx','r9',56); em.mov_r32_imm('r8',0xFFFFFFFF); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.add_r64_imm8('r9',40); em.mov_mrsp_imm32(0x20,0x0824); em.call_iat('DrawTextW')
# Restore the HDC's previous font before returning it to common-controls.
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_ripmem('rdx',bsyms['draw_old_font']); em.test64('rdx'); em.jcc(0x84,'wp_draw_status_no_restore'); em.call_iat('SelectObject')
em.label('wp_draw_status_no_restore'); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Owner-drawn lower-right status corner. This avoids the native light sizing
# triangle entirely and uses the current theme brush on every repaint.
em.label('wp_draw_corner')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_status']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Splitter is owner-drawn so every pixel is deterministically filled after
# sidebar show/hide/resize; this wipes stale RichEdit glyph fragments.
em.label('wp_draw_splitter')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_splitter']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Visual scrollbar trim: same surface as Outline; this only masks the heavy
# left chrome of the ListBox scrollbar and never implements scrolling itself.
em.label('wp_draw_scroll_trim')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Outline: 30px rows, per-level accent colors, selection surface, more breathing room.
em.label('wp_draw_outline')
em.mov_ripmem_imm32(bsyms['draw_old_font'],0)
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('r10','r9',8); em.cmp_r32_imm('r10',0xFFFFFFFF); em.jcc(0x84,'wp_draw_outline_done')
# Explicitly select the current ClearType font into the owner-draw HDC. This
# removes the jagged/default-font first paint that previously disappeared only after zoom.
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_ripmem('rdx',bsyms['hfont_outline']); em.call_iat('SelectObject'); em.mov_ripmem_r64(bsyms['draw_old_font'],'rax')
# SelectObject follows the Windows x64 ABI and may clobber volatile R9.
# V8.4.4 accidentally dereferenced that stale R9 here, crashing as soon as an
# outline item was owner-drawn (normally immediately after opening any file).
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr'])
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
em.label('wp_draw_outline_done')
# itemID == -1 can arrive without a selected font; restoring NULL is harmless.
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_ripmem('rdx',bsyms['draw_old_font']); em.test64('rdx'); em.jcc(0x84,'wp_draw_outline_no_restore'); em.call_iat('SelectObject')
em.label('wp_draw_outline_no_restore'); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Dark-mode UAH menu-bar painting.  These are Windows' undocumented menu-bar draw
# messages; popup menus are still themed through PreferredAppMode/SetWindowTheme.
em.label('wp_uah_drawmenu')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_default')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
# UAHMENU.hdc is at lParam+8; GetClipBox gives the exact current menu-bar paint clip.
em.mov_r64_mreg('rcx','r9',8); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('GetClipBox')
# Activation can report a full-window clip for the UAH menu DC. Restrict painting
# to a 36px menu band so the menu repaint can never cover EDIT/Preview/Outline.
em.lea_rip('r10',bsyms['draw_rect']); em.mov_r32_mreg('rax','r10',4); em.add_r32_imm8('rax',36); em.mov_mreg_reg32('r10',12,'rax')
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
em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00D4D4D4); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x001A1A1A); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_edit']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_edit_light'); em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00202020); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x00FFFFFF); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_edit']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Theme coloring for the outline LISTBOX.
em.label('wp_ctlcolor_list')
em.mov_ripmem_r64(bsyms['paint_hdc'],'r8')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_list_light')
em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00E6E6E6); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x001F1F1F); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_outline']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_list_light'); em.mov_r64_r64('rcx','r8'); em.mov_r32_imm('rdx',0x00202020); em.call_iat('SetTextColor'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.mov_r32_imm('rdx',0x00F3F3F3); em.call_iat('SetBkColor'); em.mov_r64_ripmem('rax',bsyms['hbrush_outline']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_ctlcolor_static')
# Splitter and lower-right corner are both STATIC children; give each its own surface.
em.mov_r64_ripmem('rax',bsyms['hwnd_splitter']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_static_corner')
em.mov_r64_ripmem('rax',bsyms['hbrush_splitter']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_static_corner'); em.mov_r64_ripmem('rax',bsyms['hbrush_status']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

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

out = '/mnt/data/direct_pe_markdown_editor_x64_v8_4_13.exe'
with open(out, 'wb') as f:
    f.write(hdr)
    f.write(raw)

sha = hashlib.sha256(open(out,'rb').read()).hexdigest()
print(out)
print('size', os.path.getsize(out), 'text', len(text), 'raw', raw_size,
      'section_vsize', section_vsize, 'bss_vsize', BSS_VSIZE)
print('sha256', sha)
