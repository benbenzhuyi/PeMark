import struct, hashlib, os, re, subprocess, textwrap, glob

try:
    WRITE_INJECTION_MODE
except NameError:
    WRITE_INJECTION_MODE = 'release'
try:
    OPEN_TEST_BUILD
except NameError:
    OPEN_TEST_BUILD = False
try:
    OPEN_READ_INJECTION_MODE
except NameError:
    OPEN_READ_INJECTION_MODE = 'release'
try:
    OUTLINE_ALLOC_INJECTION_MODE
except NameError:
    OUTLINE_ALLOC_INJECTION_MODE = 'release'
try:
    ARENA_ALLOC_INJECTION_MODE
except NameError:
    # V8.6 早期只有 Outline 注入；保留旧开关名作为别名。
    ARENA_ALLOC_INJECTION_MODE = OUTLINE_ALLOC_INJECTION_MODE
_OPEN_READ_INJECTION_MODES = {'release', 'short_then_complete', 'zero_success',
                              'fail_first', 'late_failure'}
if OPEN_READ_INJECTION_MODE not in _OPEN_READ_INJECTION_MODES:
    raise ValueError('unknown OPEN_READ_INJECTION_MODE: %r' % OPEN_READ_INJECTION_MODE)
_ARENA_ALLOC_INJECTION_MODES = {'release', 'fail_first', 'fail_second',
                                'style_fail_first', 'style_fail_second',
                                'render_fail_first', 'render_fail_second',
                                'document_fail_first', 'document_fail_second',
                                'wide_fail_first', 'wide_fail_second',
                                'byte_fail_first', 'byte_fail_second'}
if ARENA_ALLOC_INJECTION_MODE not in _ARENA_ALLOC_INJECTION_MODES:
    raise ValueError('unknown ARENA_ALLOC_INJECTION_MODE: %r' %
                     ARENA_ALLOC_INJECTION_MODE)
OUTLINE_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'fail_first',
                                                        'fail_second'}
STYLE_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'style_fail_first',
                                                      'style_fail_second'}
RENDER_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'render_fail_first',
                                                       'render_fail_second'}
DOCUMENT_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'document_fail_first',
                                                         'document_fail_second'}
WIDE_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'wide_fail_first',
                                                     'wide_fail_second'}
BYTE_ALLOC_INJECTED = ARENA_ALLOC_INJECTION_MODE in {'byte_fail_first',
                                                     'byte_fail_second'}
OPEN_TEST_BUILD = OPEN_TEST_BUILD or OPEN_READ_INJECTION_MODE != 'release'
_WRITE_INJECTION_MODES = {'release', 'short_then_complete', 'zero_success',
                          'fail_first', 'late_failure', 'flush_failure',
                          'replace_failure', 'create_failure', 'close_failure'}
if WRITE_INJECTION_MODE not in _WRITE_INJECTION_MODES:
    raise ValueError('unknown WRITE_INJECTION_MODE: %r' % WRITE_INJECTION_MODE)
INJECTED_BUILD = (WRITE_INJECTION_MODE != 'release' or OPEN_TEST_BUILD or
                  ARENA_ALLOC_INJECTION_MODE != 'release')
WRITE_CALL_INJECTED = WRITE_INJECTION_MODE in {
    'short_then_complete', 'zero_success', 'fail_first', 'late_failure'}

IMAGE_BASE = 0x140000000
# V8.6：NX_COMPAT 保证数据页不可执行，DYNAMIC_BASE 允许加载器选择随机基址。
DLL_CHARACTERISTICS = 0x0100 | 0x0040
TEXT_RVA = 0x1000
# V8.6 candidate：在 V8.5.1 基线上建立 document revision 所有权。
# 原 0x8000 起的 RDATA/IDATA/BSS 整体后移 0x8000，相对间距不变
# （rdata 预算 0x3000、idata 预算 0x1000、BSS 仍为 virtual-only 尾部）。
# 文件代价：text 与 rdata 之间填充约 34KB 零（单节布局下 RVA 间隙必须
# 在文件中存在）；文件从 45KB 增至约 66KB，换取 V8.5 重构的全部代码空间。
RDATA_RVA = 0x10000
IDATA_RVA = 0x13000
BSS_RVA = 0x14000
FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000
# V8.6 Phase E：样式表改为动态 arena。
# 每个样式 span 至少消耗 2 个源字符（*x*、`x`、> x 等），
# 因此 len/2 + 16 项是规范化文档长度的安全上界；下限 4096 项，进程内不缩小。
STYLE_MIN_ENTRIES = 4096
STYLE_SPAN_DIVISOR = 2


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
# 发布通道：src/current 产出正式二进制与正式标题，src/candidate 保留 Candidate 标记。
_BUILD_CHANNEL = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
_RELEASE_CHANNEL = _BUILD_CHANNEL == 'current'
_VERSION_LABEL = 'V8.6' if _RELEASE_CHANNEL else 'V8.6 Candidate'
if ARENA_ALLOC_INJECTION_MODE != 'release':
    _window_title = ('PeMark x64 V8.6 ARENA-ALLOC TEST [%s]' %
                     ARENA_ALLOC_INJECTION_MODE)
elif OPEN_READ_INJECTION_MODE != 'release':
    _window_title = 'PeMark x64 V8.6 OPEN-READ TEST [%s]' % OPEN_READ_INJECTION_MODE
elif OPEN_TEST_BUILD:
    _window_title = 'PeMark x64 V8.6 OPEN-TRANSACTION TEST'
elif WRITE_INJECTION_MODE != 'release':
    _window_title = 'PeMark x64 V8.6 WRITE-INJECTION [%s]' % WRITE_INJECTION_MODE
else:
    _window_title = 'PeMark x64 %s — Direct-PE Markdown Editor' % _VERSION_LABEL
wstr('title', _window_title)
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
wstr('m_close','&Close\tCtrl+W')
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
wstr('m_md_codeblock','Code Bloc&k\tCtrl+Alt+K')
wstr('m_md_quote','&Quote\tCtrl+Q')
wstr('m_md_bullet','&Bullet List\tCtrl+Shift+8')
wstr('m_md_link','&Link\tCtrl+Alt+L')
wstr('m_zoom','&Zoom')
wstr('m_zoomin','Zoom &In\tCtrl++ / Ctrl+Wheel Up')
wstr('m_zoomout','Zoom &Out\tCtrl+- / Ctrl+Wheel Down')
wstr('m_zoomreset','Restore &Default Zoom\tCtrl+0')
wstr('m_wrap','&Word Wrap\tCtrl+Shift+W')
wstr('m_status','&Status Bar\tCtrl+Alt+S')
wstr('m_preview','Markdown &Preview\tCtrl+Shift+P')
wstr('m_outline','Left &Sidebar\tCtrl+B')
wstr('m_openfolder','Open &Folder...\tCtrl+Shift+O')
wstr('m_panel_files','&Files Panel')
wstr('m_panel_outline','&Outline Panel')
wstr('panel_files','Files')
wstr('panel_outline','Outline')
wstr('m_light','&Light')
wstr('m_dark','&Dark\tCtrl+Alt+T')
wstr('m_about','&About\tF1')
wstr('open_title','Open Markdown or text file')
wstr('folder_title','Choose a workspace folder')
wstr('save_title','Save Markdown file as')
wstr('defext','md')
wstr('class_status','msctls_statusbar32')
wstr('font_face','Microsoft YaHei UI')
wstr('font_code','Consolas')
wstr('class_richedit','RICHEDIT50W')
wstr('class_listbox','LISTBOX')
wstr('class_scrollbar','SCROLLBAR')
wstr('class_scroll_surface','DirectPEOutlineScroll')
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
wstr('status_lf','Unix (LF)')
wstr('status_cr','Classic Mac (CR)')
wstr('status_utf8','UTF-8')
wstr('status_utf8_bom','UTF-8 BOM')
wstr('status_utf16','UTF-16 LE')
add_bytes('status_parts', struct.pack('<iiiiiii', 210, 330, 455, 545, 690, 810, -1), 4)

# In-memory accelerator table (ACCEL is 6 bytes: BYTE, pad, WORD, WORD).
FVIRTKEY, FSHIFT, FCONTROL, FALT = 0x01, 0x04, 0x08, 0x10
_accels = [
    (FVIRTKEY|FCONTROL, 0x4E, 1001),                  # Ctrl+N
    (FVIRTKEY|FCONTROL, 0x4F, 1002),                  # Ctrl+O
    (FVIRTKEY|FCONTROL, 0x53, 1003),                  # Ctrl+S
    (FVIRTKEY|FCONTROL|FSHIFT, 0x53, 1004),           # Ctrl+Shift+S Save As (Rabbit parity)
    (FVIRTKEY|FCONTROL|FSHIFT, 0x4F, 1006),           # Ctrl+Shift+O Open Folder (Rabbit parity)
    (FVIRTKEY|FCONTROL, 0x57, 1007),                  # Ctrl+W Close file (Rabbit parity)
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
    (FVIRTKEY|FCONTROL|FALT, 0x53, 1305),             # Ctrl+Alt+S Status Bar (Ctrl+Shift+S is Save As)
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
    (FVIRTKEY|FCONTROL|FALT, 0x4B, 1406),             # Ctrl+Alt+K Code block (Ctrl+Shift+K is Delete Line in Rabbit)
    (FVIRTKEY|FCONTROL, 0x51, 1407),                  # Ctrl+Q Quote
    (FVIRTKEY|FCONTROL|FSHIFT, 0x38, 1408),           # Ctrl+Shift+8 Bullet list
    (FVIRTKEY|FCONTROL|FALT, 0x4C, 1409),             # Ctrl+Alt+L Link (Ctrl+K is the V9 AI quick edit)
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
wstr('err_title','PeMark')
wstr('err_open','Could not open or read the selected file.')
wstr('err_save','Could not save the file.')
wstr('err_recovery_exists','A PeMark recovery file already exists beside this document (.pemark.tmp). Inspect, rename, or remove it before saving again.')
wstr('err_large','The file is too large for this build (limit: 4 MiB).')
wstr('err_decode','The file could not be decoded as UTF-8/ANSI text.')
wstr('err_alloc','Not enough memory to complete this document operation safely.')
wstr('unsaved_prompt','Save changes before continuing?')
wstr('about','PeMark x64 ' + _VERSION_LABEL + '\r\nDirect-PE Markdown Editor\r\n\r\nNative PE32+ and x86-64 machine code generated directly, without a C/C++ compiler, assembler, or linker.\r\n\r\n' + ('V8.6 protects unsaved work and makes saving transactional: revision-based dirty state, one shared unsaved-change controller, atomic replace through a sibling staging file, and strict encoding-preserving open/save.' if _RELEASE_CHANNEL else 'This candidate establishes revision-based dirty state, transactional save and encoding-preserving documents.'))

# ---------------- BSS layout ----------------
bss_off = 0
bsyms = {}
bss_sizes = {}  # 符号名 -> 字节数，仅用于自动导出 PE_MEMORY_MAP.md
def bss_alloc(name,size,align_to=8):
    global bss_off
    bss_off = align(bss_off,align_to)
    bsyms[name] = BSS_RVA + bss_off
    bss_sizes[name] = size
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
bss_alloc('hwnd_outline_gutter', 8, 8)
# V8.6.1 双面板：文件面板拥有自己的列表与 gutter（标题栏与分界线在后续步骤加入）。
bss_alloc('hwnd_files', 8, 8)
bss_alloc('hwnd_files_gutter', 8, 8)
# V8.6.1：每个面板 28px 标题栏 + 4px 分界线（标题栏可点击切换三态）。
bss_alloc('hwnd_files_header', 8, 8)
bss_alloc('hwnd_outline_header', 8, 8)
bss_alloc('hwnd_panel_divider', 8, 8)
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
bss_alloc('hbrush_scroll_thumb', 8, 8)
bss_alloc('hbrush_scroll_hot', 8, 8)
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
bss_alloc('outline_width', 4, 4)
# V8.6.1 双面板几何：文件列表高度、大纲列表的 y 与高度（像素）。
bss_alloc('files_list_h', 4, 4)
bss_alloc('outline_list_y', 4, 4)
bss_alloc('outline_list_h', 4, 4)
bss_alloc('files_list_y', 4, 4)
bss_alloc('divider_y', 4, 4)
# V8.6.1 面板三态：0 = maximized，1 = half，2 = minimized（默认 half）。
bss_alloc('files_state', 4, 4)
bss_alloc('outline_state', 4, 4)
bss_alloc('panel_split', 4, 4)   # 文件面板占可用高度的千分比（默认 500）
bss_alloc('splitter_drag', 4, 4)
bss_alloc('scrollbar_w', 4, 4)
bss_alloc('scroll_trim_w', 4, 4)
# OutlineController owns one contiguous state record. scroll_layout is its only
# geometry producer; hit testing, dragging and painting consume cached fields.
_scroll_fields = [('outline_scroll_top',4), ('outline_scroll_count',4),
    ('outline_visible_rows',4), ('outline_max_top',4), ('outline_scroll_visible',4),
    ('outline_scroll_drag',4), ('outline_scroll_drag_offset',4),
    ('outline_scroll_thumb_top',4), ('outline_scroll_thumb_h',4),
    ('outline_scroll_track_h',4), ('outline_scroll_travel',4),
    ('outline_track_rect',16), ('outline_thumb_rect',16)]
_scroll_base = bss_alloc('outline_scroll_state', sum(n for _,n in _scroll_fields), 8)
_scroll_offset = 0
for _name, _size in _scroll_fields:
    bsyms[_name] = _scroll_base + _scroll_offset
    bss_sizes[_name] = _size
    _scroll_offset += _size
bss_alloc('preview_visible_format_only', 4, 4)
bss_alloc('preview_theme_dirty', 4, 4)
bss_alloc('format_visible_end', 4, 4)
bss_alloc('preview_client_rect',16,4)
bss_alloc('preview_bottom_point',8,4)
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
# V8.4.25：heading_index 已删除——统一扫描器在识别点同步写 outline 表，
# 不再需要"outline 序号 ↔ 渲染序号"两套计数对齐。
bss_alloc('drawitem_ptr', 8, 8)
bss_alloc('draw_savedc', 4, 4)
bss_alloc('draw_old_font', 8, 8)
bss_alloc('draw_rect', 16, 8)
bss_alloc('menuinfo', 40, 8)
bss_alloc('paint_hdc', 8, 8)
bss_alloc('scroll_paint_hwnd', 8, 8)
bss_alloc('ps_scroll', 80, 16)
bss_alloc('defproc_result', 8, 8)
bss_alloc('nav_hwnd', 8, 8)
bss_alloc('style_count', 4, 4)
# V8.6 Phase E：三个样式表（start/end/type）合并为一个动态 arena 的三个区段。
bss_alloc('style_start', 8, 8)      # dynamic arena segment pointers
bss_alloc('style_end', 8, 8)
bss_alloc('style_type', 8, 8)
bss_alloc('style_capacity', 4, 4)   # arena entries currently owned
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
# V8.6 Phase E：document 文本不再固定预留物理内存，而是在政策上限内
# 保留地址空间并按 512 KiB 单元块提交。编辑器上限与规范化上限仍由
# WIDE_CHARS 决定，因此可见行为不变。
DOC_COMMIT_CHUNK = 262_144
MAX_FILE_BYTES = 4_194_304
# V8.6 Phase E：解码/编码 scratch 也改按需分配。
# Saving UTF-16 source as UTF-8 can take up to 4 bytes per code unit, so the
# byte arena ceiling stays 4 * WIDE_CHARS + 3; capacity is committed in
# 64 KiB blocks and never shrinks while the process lives.
BYTE_CAP = 4 * 8_500_000 + 3
WIDE_CHUNK = 65_536
BYTE_CHUNK = 65_536
bss_alloc('document_len', 4, 4)
bss_alloc('suppress_edit_change', 4, 4)
bss_alloc('render_len', 4, 4)
# For each visible Preview UTF-16 code unit, remember which source UTF-16 index produced it.
# This makes Source <-> Preview caret mapping independent of word-wrap and RichEdit line semantics.
# V8.6 Phase E：渲染侧派生缓冲区（位置映射 + 渲染文本）迁入动态 arena。
# 两者都是 update_preview 的派生结果，容量由规范化文档长度推导，分配失败只需
# 放弃本次渲染，不改变文档模型。
bss_alloc('render_srcmap', 8, 8)          # pointer to the position map
bss_alloc('previewbuf', 8, 8)             # pointer to the render text
bss_alloc('render_arena_capacity', 4, 4)  # units currently owned
bss_alloc('document_model', 8, 8)        # pointer into the reserved document arena
bss_alloc('document_capacity', 4, 4)     # committed units
bss_alloc('document_reserved', 4, 4)     # reserved units (policy bound)
bss_alloc('sync_text_len', 4, 4)         # editor length kept across the ensure call
# V8.6 切片 1：workspace 状态与目录枚举结果。条目表由自有 arena 提供。
# 每条 = 名称（260 单元）+ 原始属性 + 目录标志 + 大小 + 最后写入时间，
# stride 取 544 字节保持 8 字节对齐，且 64 位字段自然对齐。
WS_STRIDE = 544
WS_NAME_UNITS = 260
WS_OFF_NAME = 0                          # WCHAR[260]
WS_OFF_ATTRIBUTES = 520                  # u32 原始 dwFileAttributes
WS_OFF_KIND = 524                        # u32 bit0 = directory
WS_OFF_SIZE_LOW = 528                    # u32
WS_OFF_SIZE_HIGH = 532                   # u32
WS_OFF_WRITE_TIME = 536                  # u64 FILETIME
bss_alloc('ws_root_path', 512*2, 2)
bss_alloc('ws_current_path', 512*2, 2)
bss_alloc('ws_pattern', (512+4)*2, 2)
bss_alloc('ws_find_data', 592, 8)
bss_alloc('ws_find_handle', 8, 8)
bss_alloc('ws_entry_count', 4, 4)
bss_alloc('ws_error', 4, 4)
bss_alloc('ws_entries', 8, 8)            # arena pointer
bss_alloc('ws_capacity', 4, 4)           # entries currently owned
# V8.6 切片 2：侧边栏面板模式。0 = 大纲，1 = 文件。两个模式共用同一个
# ListBox 控件与同一套滚动条几何，只改变列表内容、行文本与行颜色。
bss_alloc('panel_mode', 4, 4)
# V8.6 切片 3：目录导航。ws_path_buf 只用于拼接/截断路径，避免与枚举
# 模式串 ws_pattern 混用；open_bypass_picker 记录"已确认的 Open 跳过选择器"。
bss_alloc('open_bypass_picker', 4, 4)
bss_alloc('ws_path_buf', 512*2, 16)
# BROWSEINFOW（x64 共 64 字节）：pszDisplayName 复用 ws_path_buf。
bss_alloc('browseinfo', 64, 8)
bss_alloc('widebuf', 8, 8)            # pointer into the decode/serialize arena
bss_alloc('wide_capacity', 4, 4)      # committed units
bss_alloc('bytebuf', 8, 8)            # pointer into the file-byte arena
bss_alloc('byte_capacity', 4, 4)      # committed bytes
# Append new state after the complete V8.5.1 layout. This preserves every
# historical symbol address while the candidate state layout is evaluated.
bss_alloc('document_revision', 8, 8)
bss_alloc('saved_revision', 8, 8)
bss_alloc('pending_destructive_action', 4, 4)  # 0 none, 1 New, 2 Open, 3 Close
bss_alloc('save_target_is_temp', 4, 4)         # Save As commits temp_path only after write
bss_alloc('inject_write_call_count', 4, 4)     # test builds only; zero in release
bss_alloc('inject_flush_call_count', 4, 4)
bss_alloc('inject_replace_call_count', 4, 4)
bss_alloc('save_stage_path', 512*2, 16)         # append-only candidate state
bss_alloc('inject_create_call_count', 4, 4)
bss_alloc('inject_close_call_count', 4, 4)
bss_alloc('eol_state', 4, 4)                 # 0 CRLF, 1 LF, 2 CR
bss_alloc('candidate_encoding_state', 4, 4)  # Open scratch; committed at open_commit
bss_alloc('candidate_eol_state', 4, 4)
bss_alloc('outline_srcpos', 8, 8)       # dynamic arena table pointers
bss_alloc('outline_renderpos', 8, 8)
bss_alloc('outline_level', 8, 8)
bss_alloc('outline_capacity', 4, 4)
if OUTLINE_ALLOC_INJECTED:
    bss_alloc('inject_outline_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if STYLE_ALLOC_INJECTED:
    bss_alloc('inject_style_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if RENDER_ALLOC_INJECTED:
    bss_alloc('inject_render_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if DOCUMENT_ALLOC_INJECTED:
    bss_alloc('inject_document_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if WIDE_ALLOC_INJECTED:
    bss_alloc('inject_wide_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if BYTE_ALLOC_INJECTED:
    bss_alloc('inject_byte_alloc_call_count', 4, 4)
    bss_alloc('open_alloc_error_count', 4, 4)
if OPEN_TEST_BUILD:
    bss_alloc('open_decode_error_count', 4, 4)
    bss_alloc('open_read_error_count', 4, 4)
    bss_alloc('inject_read_call_count', 4, 4)
    # 切片 2：把 ListBox 行文本导出到一块 owner-draw 不会触碰的缓冲。
    # 进程外直接 LB_GETTEXT 既有跨进程指针封送限制，也会与绘制共用缓冲。
    bss_alloc('list_probe_index', 4, 4)
    bss_alloc('list_probe_result', 4, 4)
    bss_alloc('list_probe_text', 512*2, 16)
BSS_VSIZE = align(bss_off, 0x1000)

# ---------------- IDATA ----------------
imports = {
    'KERNEL32.dll': [
        'ExitProcess','CreateFileW','ReadFile','WriteFile','FlushFileBuffers','CloseHandle','VirtualAlloc','VirtualFree',
        'MoveFileExW','DeleteFileW','GetLastError','GetFileSize',
        'MultiByteToWideChar','WideCharToMultiByte','lstrcpyW','lstrlenW','GetModuleHandleW','CompareStringOrdinal','LoadLibraryW','GetProcAddress','MulDiv'
        ,'FindFirstFileW','FindNextFileW','FindClose'
    ],
    'USER32.dll': [
        'CreateWindowExW','GetMessageW','TranslateMessage','DispatchMessageW','IsWindow',
        'GetFocus',
        'CreateMenu','CreatePopupMenu','AppendMenuW','GetWindowTextLengthW','GetWindowTextW',
        'SetWindowTextW','SendMessageW','MoveWindow','SetWindowPos','MessageBoxW','SetFocus',
        'RegisterClassExW','DefWindowProcW','PostQuitMessage','PostMessageW','LoadCursorW',
        'DestroyWindow','ShowWindow','CheckMenuItem','GetWindowRect','GetClientRect','wsprintfW','RegisterWindowMessageW','InvalidateRect','UpdateWindow','RedrawWindow',
        'GetCursorPos','ScreenToClient','SetCapture','ReleaseCapture','SetCursor','BeginPaint','EndPaint','SetScrollRange','SetScrollPos','ShowScrollBar','GetKeyState','GetSystemMetrics','SetTimer','KillTimer',
        'CreateAcceleratorTableW','TranslateAcceleratorW','DestroyAcceleratorTable','IsDialogMessageW','SetForegroundWindow','DrawMenuBar','DrawTextW','FillRect','GetMenuStringW','SetMenuInfo','GetWindowDC','ReleaseDC','GetMenuItemRect'
    ],
    'COMDLG32.dll': ['GetOpenFileNameW','GetSaveFileNameW','FindTextW','ReplaceTextW'],
    'SHELL32.dll': ['SHBrowseForFolderW','SHGetPathFromIDListW','ILFree'],
    'OLE32.dll': ['CoInitializeEx'],
    'SHLWAPI.dll': ['StrStrW','StrStrIW'],
    'COMCTL32.dll': ['InitCommonControlsEx'],
    'GDI32.dll': ['CreateFontW','DeleteObject','CreateSolidBrush','SetTextColor','SetBkColor','SetBkMode','GetClipBox','SelectObject','SaveDC','RestoreDC','IntersectClipRect'],
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
    def or_r32_imm(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x81,0xC8|(r&7),u32(imm))
    def add_r32_imm(self,reg,imm):
        r=REG[reg]; self.rex(b=(r>>3)&1); self.emit(0x81,0xC0|(r&7),u32(imm))
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
    def mov_r64_mrsp(self,reg,off):
        r=REG[reg]; self.rex(w=1,r=(r>>3)&1); self.emit(0x8B,0x44|((r&7)<<3),0x24,off&255)
    def mov_r32_mrsp(self,reg,off):
        r=REG[reg]; self.rex(r=(r>>3)&1); self.emit(0x8B,0x44|((r&7)<<3),0x24,off&255)
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
    # Displacement helpers: pick disp8 or disp32 automatically. Using disp8 for a
    # larger offset silently truncates it, which corrupted two slice-1 fields
    # before this was fixed.
    def _mreg_off(self, off):
        assert -2**31 <= off < 2**31, off
        return (0x40, off & 0xFF, b'') if -128 <= off <= 127 else (0x80, 0, u32(off))
    def _no_sib_base(self, base):
        assert (REG[base]&7) not in (4,5), \
            'base needs a SIB byte (rsp/rbp/r12/r13); use another register'
    def mov_mreg_imm32(self,base,off,imm):
        self._no_sib_base(base)
        b=REG[base]; mod,disp8,disp32=self._mreg_off(off)
        self.rex(b=(b>>3)&1)
        if disp32:
            self.emit(0xC7,mod|(b&7),*disp32,u32(imm))
        else:
            self.emit(0xC7,mod|(b&7),disp8,u32(imm))
    def mov_mreg_reg32(self,base,off,src):
        self._no_sib_base(base)
        b,s=REG[base],REG[src]; mod,disp8,disp32=self._mreg_off(off)
        self.rex(r=(s>>3)&1,b=(b>>3)&1)
        if disp32: self.emit(0x89,mod|((s&7)<<3)|(b&7),*disp32)
        else: self.emit(0x89,mod|((s&7)<<3)|(b&7),disp8)
    def mov_r32_mreg(self,dst,base,off):
        self._no_sib_base(base)
        d,b=REG[dst],REG[base]; mod,disp8,disp32=self._mreg_off(off)
        self.rex(r=(d>>3)&1,b=(b>>3)&1)
        if disp32: self.emit(0x8B,mod|((d&7)<<3)|(b&7),*disp32)
        else: self.emit(0x8B,mod|((d&7)<<3)|(b&7),disp8)
    def mov_r64_mreg(self,dst,base,off):
        self._no_sib_base(base)
        d,b=REG[dst],REG[base]; mod,disp8,disp32=self._mreg_off(off)
        self.rex(w=1,r=(d>>3)&1,b=(b>>3)&1)
        if disp32: self.emit(0x8B,mod|((d&7)<<3)|(b&7),*disp32)
        else: self.emit(0x8B,mod|((d&7)<<3)|(b&7),disp8)
    def mov_mreg_reg64(self,base,off,src):
        self._no_sib_base(base)
        b,s=REG[base],REG[src]; mod,disp8,disp32=self._mreg_off(off)
        self.rex(w=1,r=(s>>3)&1,b=(b>>3)&1)
        if disp32: self.emit(0x89,mod|((s&7)<<3)|(b&7),*disp32)
        else: self.emit(0x89,mod|((s&7)<<3)|(b&7),disp8)
    def mov_mreg_r64(self,base,off,src):
        self.mov_mreg_reg64(base,off,src)

em=E()
# PE entry point. Exit correctness is owned by the message-loop terminal branch;
# the probe experiment disproved the former loader-reentry hypothesis.
em.label('entry_first_run')
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
em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag_offset'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_top'],4)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_h'],32)
em.mov_ripmem_imm32(bsyms['outline_scroll_track_h'],100)
em.mov_ripmem_imm32(bsyms['outline_visible_rows'],1)
em.mov_ripmem_imm32(bsyms['outline_max_top'],0)
em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],0)
em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],0)
em.mov_ripmem_imm32(bsyms['theme_dark'],0)
em.mov_ripmem_imm32(bsyms['zoom_pct'],100)
em.mov_ripmem_imm32(bsyms['encoding_state'],0)
em.mov_ripmem_imm32(bsyms['eol_state'],0)
em.mov_ripmem_imm32(bsyms['find_flags'],1)
em.mov_ripmem_imm32(bsyms['search_wrap_flag'],1)
em.mov_ripmem_imm32(bsyms['client_w'],884)
em.mov_ripmem_imm32(bsyms['client_h'],590)
# V8.4.23: reserve a permanent scrollbar gutter whose width follows the current
# Windows vertical-scrollbar metric. The Outline ListBox itself has NO WS_VSCROLL.
em.mov_ripmem_imm32(bsyms['scrollbar_w'],17)
em.mov_r32_imm('rcx',2); em.call_iat('GetSystemMetrics'); em.test32('rax'); em.jcc(0x84,'scroll_metric_ready'); em.mov_ripmem_r32(bsyms['scrollbar_w'],'rax')
em.label('scroll_metric_ready')
# The gutter geometry never changes when its scrollbar is shown/hidden; only the
# child scrollbar visibility changes. This avoids ListBox client/non-client races.
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
# V8.4.23: register a dedicated scrollbar-surface child class.  Unlike an
# owner-drawn STATIC, it owns its WM_PAINT lifecycle directly, so theme changes
# and hover invalidations cannot fall back to a system COLOR_WINDOW background.
em.lea_rip('r12',bsyms['wc'])
em.mov_mr12_imm32(0,80)
em.mov_mr12_imm32(4,3)
em.lea_label('rax','scrollproc'); em.mov_mr12_reg64(8,'rax')
em.mov_mr12_reg64(24,'r15')
em.xor32('rcx'); em.mov_r32_imm('rdx',32512); em.call_iat('LoadCursorW')
em.mov_mr12_reg64(40,'rax')
em.mov_mr12_imm32(48,0)
em.mov_mr12_imm32(56,0)
em.lea_rip('rax',rsyms['class_scroll_surface']); em.mov_mr12_reg64(64,'rax')
em.mov_mr12_imm32(72,0)
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

append_imm('r12',0,1001,'m_new'); append_imm('r12',0,1002,'m_open'); append_imm('r12',0,1006,'m_openfolder'); append_sep('r12')
append_imm('r12',0,1003,'m_save'); append_imm('r12',0,1004,'m_saveas'); append_sep('r12'); append_imm('r12',0,1007,'m_close'); append_sep('r12'); append_imm('r12',0,1005,'m_exit')
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
append_sep('r14'); append_imm('r14',0,1308,'m_panel_files'); append_imm('r14',0x8,1309,'m_panel_outline')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x0404); em.mov_r32_imm('r8',7); em.lea_rip('r9',rsyms['status_parts']); em.call_iat('SendMessageW')
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
# Left Markdown outline. V8.4.23 intentionally omits WS_VSCROLL: the ListBox
# owns only the content rectangle, while a separate SCROLLBAR child lives in a
# permanently reserved gutter to its right.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_listbox']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x54010151)  # no WS_VSCROLL
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,210); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,4,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x01A0); em.xor32('r8'); em.mov_r32_imm('r9',30); em.call_iat('SendMessageW')
# SendMessageW returns an LRESULT in RAX; reload the ListBox HWND before WM_SETFONT.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont_outline']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Permanent scrollbar-gutter background. It remains visible with the Outline even
# when the actual scrollbar is hidden, so Outline width never changes on hover.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)  # owner-draw gutter
em.mov_mrsp_imm32(0x20,210); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,18); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,7,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline_gutter'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# V8.4.23 architecture preview: dedicated custom scrollbar surface.
# It lives permanently in the fixed gutter and paints itself via scrollproc/WM_PAINT.
# This removes the brittle owner-drawn STATIC -> parent WM_DRAWITEM dependency that
# caused the V8.4.20 white/black full-height gutter and invisible thumb.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_scroll_surface']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x44000000)  # WS_CHILD|CLIPSIBLINGS; shown only on hover/drag
em.mov_mrsp_imm32(0x20,210); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,18); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,8,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline_scroll'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# One-pixel visual divider; resize hit testing is logical and lives on the document side.
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,228); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,1); em.mov_mrsp_imm32(0x38,590)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,6,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_splitter'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# V8.6.1：文件面板的列表与 gutter（ID 14 / 15）。标题栏与分界线稍后加入。
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_listbox']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x54010151)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,210); em.mov_mrsp_imm32(0x38,250)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,14,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_files'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x01A0); em.xor32('r8'); em.mov_r32_imm('r9',30); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont_outline']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,210); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,18); em.mov_mrsp_imm32(0x38,250)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,15,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_files_gutter'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
# 文件标题栏（ID 16）、大纲标题栏（ID 17）、分界线（ID 18）。
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,228); em.mov_mrsp_imm32(0x38,28)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,16,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_files_header'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,300); em.mov_mrsp_imm32(0x30,228); em.mov_mrsp_imm32(0x38,28)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,17,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_outline_header'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_static']); em.lea_rip('r8',rsyms['empty']); em.mov_r32_imm('r9',0x5400000D)
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,296); em.mov_mrsp_imm32(0x30,228); em.mov_mrsp_imm32(0x38,4)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,18,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_ripmem_r64(bsyms['hwnd_panel_divider'],'rax'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_ripmem_imm32(bsyms['files_state'],1); em.mov_ripmem_imm32(bsyms['outline_state'],1)
em.mov_ripmem_imm32(bsyms['panel_split'],500)
em.call_label('apply_theme'); em.call_label('update_preview'); em.call_label('resize_children'); em.call_label('sync_outline_scrollbar'); em.call_label('sync_panel_menu'); em.call_label('update_status')

# Message pump
em.label('msg_loop')
em.lea_rip('r12',bsyms['msg']); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.call_iat('GetMessageW')
em.test32('rax'); em.jcc(0x8E,'exit') # jle
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x8001); em.jcc(0x84,'command')  # WM_APP+1 posted by wndproc
em.cmp_r32_imm('rax',0x8002); em.jcc(0x84,'resize_event') # legacy/private resize event
em.cmp_r32_imm('rax',0x8003); em.jcc(0x84,'findreplace_event')
em.cmp_r32_imm('rax',0x8004); em.jcc(0x84,'document_changed_event')
em.cmp_r32_imm('rax',0x8005); em.jcc(0x84,'outline_select_event')
em.cmp_r32_imm('rax',0x8006); em.jcc(0x84,'request_close')
em.cmp_r32_imm('rax',0x8007); em.jcc(0x84,'list_activate_event')
em.cmp_r32_imm('rax',0x0100); em.jcc(0x84,'keydown_event')  # WM_KEYDOWN: Backspace over the file list
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
# Architecture-preview event routing: scrollbar drag, splitter drag, then hover.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag']); em.test32('rax'); em.jcc(0x84,'mousemove_not_scroll_drag')
em.call_label('outline_scroll_drag_move'); em.jmp('msg_loop')
em.label('mousemove_not_scroll_drag')
em.mov_r32_ripmem('rax',bsyms['splitter_drag']); em.test32('rax'); em.jcc(0x84,'mousemove_hover_only')
em.call_label('splitter_drag_move'); em.jmp('msg_loop')
em.label('mousemove_hover_only'); em.call_label('update_outline_hover'); em.jmp('dispatch')

em.label('lbuttondown_event')
# Convert current pointer to main-client coordinates once.  The permanent scrollbar
# gutter and the divider resize hit-zone are geometrically disjoint.
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'dispatch')
# V8.4.24 二次修复（P0-002 时序根因）：命中测试必须使用消息入队时的指针位置
# （MSG.pt 屏幕坐标：pt.x@36 / pt.y@40），不得用 GetCursorPos 读“此刻”位置——
# 快速拖动时按下消息已在队列中滞后，GetCursorPos 读到的是终点坐标，本应命中
# thumb 的按下会被误判成轨道点击。r12 由 msg_loop 指向 MSG，此处尚未发生任何
# call，r12 必定有效；msg.pt 仍为屏幕坐标，ScreenToClient 语义不变。
em.mov_eax_mr12(36); em.mov_ripmem_r32(bsyms['cursor_pt'],'rax')
em.mov_eax_mr12(40); em.mov_ripmem_r32(bsyms['cursor_pt']+4,'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient'); em.test32('rax'); em.jcc(0x84,'dispatch')
# First test permanent scrollbar gutter: [outline_width-scrollbar_w, outline_width).
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.mov_r32_ripmem('rax',bsyms['scrollbar_w']); em.mov_r32_r32('r8','r11'); em.sub_r32_r32('r8','rax')
em.cmp_r32_r32('r10','r8'); em.jcc(0x8C,'lbd_test_splitter'); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'lbd_test_splitter')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.test32('r10'); em.jcc(0x88,'dispatch'); em.mov_r32_ripmem('r11',bsyms['content_h']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'dispatch')
# Reveal scrollbar immediately and refresh geometry before hit-testing the thumb.
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.call_label('sync_outline_scrollbar')
# Hit-test the exact cached rectangle used by the painter.
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.mov_r32_ripmem('r11',bsyms['outline_thumb_rect']+4); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'lbd_scroll_pageup')
em.mov_r32_ripmem('r11',bsyms['outline_thumb_rect']+12); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'lbd_scroll_pagedown')
# Convert the main-client x coordinate to scrollbar-local x.
em.mov_r32_ripmem('rax',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.sub_r32_r32('rax','r11'); em.mov_r32_ripmem('r11',bsyms['scrollbar_w']); em.add_r32_r32('rax','r11')
em.mov_r32_ripmem('r11',bsyms['outline_thumb_rect']); em.cmp_r32_r32('rax','r11'); em.jcc(0x8C,'dispatch')
em.mov_r32_ripmem('r11',bsyms['outline_thumb_rect']+8); em.cmp_r32_r32('rax','r11'); em.jcc(0x8D,'dispatch')
# Begin thumb drag and remember y-within-thumb.
em.mov_r32_ripmem('r11',bsyms['outline_scroll_thumb_top']); em.sub_r32_r32('r10','r11'); em.mov_ripmem_r32(bsyms['outline_scroll_drag_offset'],'r10'); em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.call_iat('SetCapture'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.jmp('msg_loop')
em.label('lbd_scroll_pageup')
em.mov_r32_ripmem('r10',bsyms['outline_scroll_top']); em.mov_r32_ripmem('rax',bsyms['outline_visible_rows']); em.cmp_r32_r32('r10','rax'); em.jcc(0x83,'lbd_scroll_pageup_sub'); em.xor32('r10'); em.jmp('lbd_scroll_apply')
em.label('lbd_scroll_pageup_sub'); em.sub_r32_r32('r10','rax'); em.jmp('lbd_scroll_apply')
em.label('lbd_scroll_pagedown')
em.mov_r32_ripmem('r10',bsyms['outline_scroll_top']); em.mov_r32_ripmem('rax',bsyms['outline_visible_rows']); em.add_r32_r32('r10','rax'); em.mov_r32_ripmem('r11',bsyms['outline_max_top']); em.cmp_r32_r32('r10','r11'); em.jcc(0x86,'lbd_scroll_apply'); em.mov_r32_r32('r10','r11')
em.label('lbd_scroll_apply'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'r10'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.mov_r32_r32('r8','r10'); em.xor32('r9'); em.call_iat('SendMessageW'); em.call_label('sync_outline_scrollbar'); em.jmp('msg_loop')
# Splitter logical hit-zone [outline_width, outline_width+8].
em.label('lbd_test_splitter')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'dispatch'); em.add_r32_imm8('r11',8); em.cmp_r32_r32('r10','r11'); em.jcc(0x8F,'dispatch')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.test32('r10'); em.jcc(0x88,'dispatch'); em.mov_r32_ripmem('r11',bsyms['content_h']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'dispatch')
em.mov_ripmem_imm32(bsyms['splitter_drag'],1); em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.call_iat('SetCapture')
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.xor32('r8'); em.mov_r32_imm('r9',0x105); em.call_iat('RedrawWindow')
em.call_label('splitter_drag_move'); em.jmp('msg_loop')

em.label('lbuttonup_event')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag']); em.test32('rax'); em.jcc(0x84,'lbu_not_scroll')
em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],0); em.call_iat('ReleaseCapture'); em.call_label('sync_outline_scrollbar'); em.call_label('update_outline_hover'); em.jmp('msg_loop')
em.label('lbu_not_scroll')
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

em.label('list_activate_event')
em.call_label('ws_open_or_enter'); em.jmp('msg_loop')

# V8.6 切片 3：只有当焦点在文件列表上时，Backspace 才是"返回上级"。
# 编辑区获得焦点时照常派发，删除字符的行为不变。
em.label('keydown_event')
em.mov_r32_ripmem('rax',bsyms['panel_mode']); em.test32('rax'); em.jcc(0x84,'dispatch')
em.mov_rax_mr12(16); em.cmp_r32_imm('rax',0x08); em.jcc(0x85,'dispatch')
em.call_iat('GetFocus'); em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.cmp_r64_r64('rax','rcx'); em.jcc(0x85,'dispatch')
em.call_label('ws_go_up'); em.jmp('msg_loop')

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
# V8.4.24（P0-002）：钳制到 max_top（count - visible_rows）而非 count-1，
# 使滚轮驱动的顶部索引永远不会超出拖动/轨道范围；滚轮滚到底时 thumb
# 与拖动到底时一样，恰好贴住轨道底部。
em.mov_r32_ripmem('r11',bsyms['outline_max_top']); em.cmp_r32_r32('r8','r11'); em.jcc(0x86,'outline_wheel_send'); em.mov_r32_r32('r8','r11')
em.label('outline_wheel_send')
em.mov_ripmem_r32(bsyms['outline_scroll_top'],'r8'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.xor32('r9'); em.call_iat('SendMessageW'); em.call_label('sync_outline_scrollbar'); em.jmp('msg_loop')
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
_command_routes = [(1001,'cmd_new'),(1002,'cmd_open'),(1003,'cmd_save'),(1004,'cmd_saveas'),(1005,'cmd_exit'),
                  (1101,'cmd_undo'),(1102,'cmd_cut'),(1103,'cmd_copy'),(1104,'cmd_paste'),(1105,'cmd_selectall'),(1106,'cmd_find'),(1107,'cmd_findnext'),(1108,'cmd_replace'),(1201,'cmd_about'),
                  (1301,'cmd_zoomin'),(1302,'cmd_zoomout'),(1303,'cmd_zoomreset'),(1304,'cmd_wrap'),(1305,'cmd_status'),(1306,'cmd_preview'),(1307,'cmd_outline'),(1310,'cmd_light'),(1311,'cmd_dark'),(1312,'cmd_theme_toggle'),
                  (1006,'cmd_open_folder'),(1308,'cmd_panel_files'),(1309,'cmd_panel_outline'),
                  (1007,'cmd_close_file'),
                  (1401,'cmd_md_h1'),(1402,'cmd_md_h2'),(1410,'cmd_md_h3'),(1411,'cmd_md_h4'),(1412,'cmd_md_h5'),(1413,'cmd_md_h6'),(1403,'cmd_md_bold'),(1404,'cmd_md_italic'),(1405,'cmd_md_inline'),(1406,'cmd_md_codeblock'),(1407,'cmd_md_quote'),(1408,'cmd_md_bullet'),(1409,'cmd_md_link')]
if OPEN_TEST_BUILD:
    _command_routes.append((1901, 'cmd_open_selected'))
    _command_routes.append((1902, 'cmd_workspace_probe'))
    _command_routes.append((1903, 'cmd_show_files'))
    _command_routes.append((1904, 'cmd_show_outline'))
    _command_routes.append((1905, 'cmd_dump_row'))
    _command_routes.append((1906, 'cmd_list_activate'))
    _command_routes.append((1907, 'cmd_go_up'))
    _command_routes.append((1908, 'cmd_open_folder_selected'))
for cid,label in _command_routes:
    em.cmp_r32_imm('rax',cid); em.jcc(0x84,label)
em.jmp('dispatch')

em.label('cmd_new'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],1); em.jmp('destructive_request')
# Close 与 New 在单文档模型下是同一个终态（空文档 + clean revision），因此复用
# 同一条破坏性保护路径，只是菜单与快捷键分开，和 Rabbit 一致。
em.label('cmd_close_file'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],1); em.jmp('destructive_request')
em.label('cmd_new_commit')
# V8.6：新建文档同样需要文档 arena；失败时不执行 New，保留当前文档。
em.xor32('rcx'); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('r8'); em.call_label('set_view_mode')
em.mov_r64_ripmem('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['document_len'],0); em.call_label('load_model_into_editor')
em.lea_rip('rax',bsyms['current_path']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['encoding_state'],0); em.mov_ripmem_imm32(bsyms['eol_state'],0); em.call_label('commit_clean_document'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

# Initialize OFN common fields macro
def emit_ofn(title_sym, flags):
    em.lea_rip('r12',bsyms['ofn']); em.mov_mr12_imm32(0,152); em.mov_mr12_reg64(8,'rbx')
    em.lea_rip('rax',rsyms['filter']); em.mov_mr12_reg64(24,'rax')
    em.mov_mr12_imm32(44,1)
    em.lea_rip('rax',bsyms['temp_path']); em.mov_mr12_reg64(48,'rax'); em.mov_mr12_imm32(56,512)
    em.lea_rip('rax',rsyms[title_sym]); em.mov_mr12_reg64(88,'rax'); em.mov_mr12_imm32(96,flags)
    em.lea_rip('rax',rsyms['defext']); em.mov_mr12_reg64(104,'rax')

em.label('cmd_open'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],2); em.jmp('destructive_request')
em.label('cmd_open_folder')
# 选择工作区目录：SHBrowseForFolderW -> 设为根目录 -> 切到文件面板。
# 新式浏览对话框使用 shell COM，先在调用线程初始化（失败也无妨）。
em.xor32('rcx'); em.mov_r32_imm('rdx',2); em.call_iat('CoInitializeEx')
em.lea_rip('rax',bsyms['temp_path']); em.mov_word_ptr_reg_zero('rax')
em.lea_rip('r15',bsyms['browseinfo'])                                        # r12/r13 need a SIB byte as a base
em.xor32('rax')
for _bi_off in (0,8,16,24,32,40,48,56):
    em.mov_mreg_reg64('r15',_bi_off,'rax')
em.mov_mreg_reg64('r15',0,'rbx')                                             # hwndOwner
em.lea_rip('rax',bsyms['ws_path_buf']); em.mov_mreg_reg64('r15',16,'rax')    # pszDisplayName
em.lea_rip('rax',rsyms['folder_title']); em.mov_mreg_reg64('r15',24,'rax')   # lpszTitle
em.mov_mreg_imm32('r15',32,0x51)                                             # BIF_RETURNONLYFSDIRS|BIF_EDITBOX|BIF_NEWDIALOGSTYLE
em.mov_r64_r64('rcx','r15'); em.call_iat('SHBrowseForFolderW')
em.test64('rax'); em.jcc(0x84,'msg_loop')
em.mov_r64_r64('r13','rax')
em.mov_r64_r64('rcx','rax'); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('SHGetPathFromIDListW'); em.mov_r32_r32('r14','rax')
em.mov_r64_r64('rcx','r13'); em.call_iat('ILFree')
em.test32('r14'); em.jcc(0x84,'msg_loop')
em.lea_rip('rcx',bsyms['temp_path']); em.call_label('workspace_set_root')
em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode'); em.call_label('update_status'); em.jmp('msg_loop')
em.label('cmd_open_dialog')
em.lea_rip('rax',bsyms['temp_path']); em.mov_word_ptr_reg_zero('rax')
em.emit(*[]) ; emit_ofn('open_title',0x00081804)
em.mov_r64_r64('rcx','r12'); em.call_iat('GetOpenFileNameW'); em.test32('rax'); em.jcc(0x84,'destructive_cancel')
em.label('cmd_open_selected')  # build-time-only command 1901 bypasses only the picker
# CreateFileW(temp, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, NORMAL, 0)
em.lea_rip('rcx',bsyms['temp_path']); em.mov_r32_imm('rdx',0x80000000); em.mov_r32_imm('r8',1); em.xor32('r9')
em.mov_mrsp_imm32(0x20,3); em.mov_mrsp_imm32(0x28,0x80); em.mov_mrsp_imm32(0x30,0,qword=True); em.call_iat('CreateFileW'); em.cmp_rax_neg1(); em.jcc(0x84,'err_open'); em.mov_r64_r64('r12','rax')
# GetFileSize with high dword
em.lea_rip('rax',bsyms['size_high']); em.mov_word_ptr_reg_zero('rax'); # zero low word enough, then dword zero explicitly
em.emit(0xC7,0x00,u32(0))
em.mov_r64_r64('rcx','r12'); em.lea_rip('rdx',bsyms['size_high']); em.call_iat('GetFileSize'); em.mov_r32_r32('r13','rax')
em.lea_rip('rax',bsyms['size_high']); em.mov_eax_ptr('rax'); em.test32('rax'); em.jcc(0x85,'too_large_close')
em.cmp_r32_imm('r13',MAX_FILE_BYTES); em.jcc(0x87,'too_large_close')
em.test32('r13'); em.jcc(0x85,'read_nonempty'); em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.jmp('decode_empty')
# Complete-read loop. The size snapshot in r13 remains authoritative; r14/r15
# own the next buffer position and remaining byte count.
em.label('read_nonempty')
# V8.6：解码与编码 scratch 现在是按需 arena；读取前必须保证两个缓冲区
# 都能容纳本次文件（字节数 + NUL，以及解码后最坏情况的单元数）。
em.mov_r32_r32('rcx','r13'); em.add_r32_imm8('rcx',2); em.call_label('ensure_byte_arena'); em.test32('rax'); em.jcc(0x84,'open_alloc_close')
em.mov_r32_r32('rcx','r13'); em.add_r32_imm8('rcx',1); em.call_label('ensure_wide_arena'); em.test32('rax'); em.jcc(0x84,'open_alloc_close')
em.mov_r64_ripmem('r14',bsyms['bytebuf']); em.mov_r32_r32('r15','r13')
em.label('open_read_loop'); em.test32('r15'); em.jcc(0x84,'open_read_complete')
em.mov_r64_r64('rcx','r12'); em.mov_r64_r64('rdx','r14'); em.mov_r32_r32('r8','r15'); em.lea_rip('r9',bsyms['io_count']); em.mov_mrsp_imm32(0x20,0,qword=True)
if OPEN_READ_INJECTION_MODE != 'release': em.call_label('injected_ReadFile')
else: em.call_iat('ReadFile')
em.test32('rax'); em.jcc(0x84,'read_fail_close'); em.mov_r32_ripmem('rax',bsyms['io_count']); em.test32('rax'); em.jcc(0x84,'read_fail_close'); em.cmp_r32_r32('rax','r15'); em.jcc(0x87,'read_fail_close')
em.add_r64_r64('r14','rax'); em.sub_r32_r32('r15','rax'); em.jmp('open_read_loop')
em.label('open_read_complete')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
# NUL terminate raw buffer at actual byte count returned by ReadFile
em.mov_r64_ripmem('rdx',bsyms['bytebuf']); em.mov_r32_r32('rax','r13'); em.add_r64_r64('rdx','rax'); em.mov_word_ptr_reg_zero('rdx')
# Empty file is valid text.
em.test32('r13'); em.jcc(0x84,'decode_empty')
# BOM detection
em.mov_r64_ripmem('r14',bsyms['bytebuf']); em.cmp_r32_imm('r13',2); em.jcc(0x82,'decode_8bit')
em.movzx_eax_word_ptr('r14'); em.cmp_r32_imm('rax',0xFEFF); em.jcc(0x84,'decode_utf16')
em.cmp_r32_imm('r13',3); em.jcc(0x82,'decode_8bit')
em.mov_eax_ptr('r14'); em.and_r32_imm('rax',0x00FFFFFF); em.cmp_r32_imm('rax',0x00BFBBEF); em.jcc(0x85,'decode_8bit')
em.add_r64_imm8('r14',3); em.mov_r32_r32('r15','r13'); em.sub_r32_imm8('r15',3); em.mov_ripmem_imm32(bsyms['candidate_encoding_state'],2); em.jmp('decode_utf8_call')

em.label('decode_8bit')
em.mov_r64_ripmem('r14',bsyms['bytebuf']); em.mov_r32_r32('r15','r13'); em.mov_ripmem_imm32(bsyms['candidate_encoding_state'],0)
em.label('decode_utf8_call')
# Strict UTF-8 only. MB_ERR_INVALID_CHARS rejects malformed byte sequences;
# legacy code-page fallback is deliberately outside the V8.6 contract.
em.test32('r15'); em.jcc(0x84,'decode_empty_utf8_bom')
em.mov_r32_imm('rcx',65001); em.mov_r32_imm('rdx',8); em.mov_r64_r64('r8','r14'); em.mov_r32_r32('r9','r15'); em.mov_r64_ripmem('rax',bsyms['widebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_r32_ripmem('rax',bsyms['wide_capacity']); em.mov_mrsp_reg32(0x28,'rax'); em.call_iat('MultiByteToWideChar'); em.test32('rax'); em.jcc(0x84,'err_decode')
em.label('decode_done')
em.mov_r32_r32('r15','rax'); em.mov_r64_ripmem('rdx',bsyms['widebuf']); em.mov_word_index2_zero('rdx','r15')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.mov_r32_r32('rdx','r15'); em.call_label('validate_wide_no_nul'); em.test32('rax'); em.jcc(0x84,'err_decode')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.mov_r32_r32('rdx','r15'); em.call_label('detect_preferred_eol'); em.mov_ripmem_r32(bsyms['candidate_eol_state'],'rax')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_outline_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_style_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_render_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.call_label('normalize_to_document_model'); em.call_label('load_model_into_editor')
em.jmp('open_commit')

em.label('decode_empty_utf8_bom')
em.mov_r64_ripmem('rax',bsyms['widebuf']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['candidate_eol_state'],0)
em.xor32('rcx'); em.call_label('ensure_outline_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_style_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_render_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['document_len'],0); em.call_label('load_model_into_editor'); em.jmp('open_commit')

em.label('decode_empty')
em.mov_ripmem_imm32(bsyms['candidate_encoding_state'],0); em.mov_ripmem_imm32(bsyms['candidate_eol_state'],0)
em.xor32('rcx'); em.call_label('ensure_outline_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_style_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_render_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.xor32('rcx'); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_ripmem('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax'); em.mov_ripmem_imm32(bsyms['document_len'],0); em.call_label('load_model_into_editor')
em.jmp('open_commit')

em.label('decode_utf16')
em.mov_r32_r32('r15','r13'); em.sub_r32_imm8('r15',2); em.mov_r32_r32('rax','r15'); em.and_r32_imm('rax',1); em.test32('rax'); em.jcc(0x85,'err_decode'); em.shr_r32_imm8('r15',1)
em.mov_r64_ripmem('rcx',bsyms['bytebuf']); em.add_r64_imm8('rcx',2); em.mov_r32_r32('rdx','r15'); em.call_label('validate_wide_no_nul'); em.test32('rax'); em.jcc(0x84,'err_decode')
em.mov_ripmem_imm32(bsyms['candidate_encoding_state'],1)
em.mov_r64_ripmem('rcx',bsyms['bytebuf']); em.add_r64_imm8('rcx',2); em.mov_r32_r32('rdx','r15'); em.call_label('detect_preferred_eol'); em.mov_ripmem_r32(bsyms['candidate_eol_state'],'rax')
em.mov_r64_ripmem('r14',bsyms['bytebuf']); em.add_r64_imm8('r14',2); em.mov_r64_r64('rcx','r14'); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_outline_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_r64('rcx','r14'); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_style_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_r64('rcx','r14'); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_render_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_r64('rcx','r14'); em.call_label('candidate_normalized_length'); em.mov_r32_r32('rcx','rax'); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'err_open_alloc')
em.mov_r64_r64('rcx','r14'); em.call_label('normalize_to_document_model'); em.call_label('load_model_into_editor')
em.label('open_commit')
# Only a fully read and validated candidate may change visible/document state.
em.mov_r32_ripmem('rax',bsyms['candidate_encoding_state']); em.mov_ripmem_r32(bsyms['encoding_state'],'rax'); em.mov_r32_ripmem('rax',bsyms['candidate_eol_state']); em.mov_ripmem_r32(bsyms['eol_state'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',0x4D); em.call_iat('KillTimer'); em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],0)
em.xor32('r8'); em.call_label('set_view_mode')
em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW'); em.call_label('commit_clean_document'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('msg_loop')

em.label('too_large_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle');
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_large']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('read_fail_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
if OPEN_TEST_BUILD:
    em.mov_r32_ripmem('rax',bsyms['open_read_error_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['open_read_error_count'],'rax'); em.jmp('msg_loop')
else:
    em.jmp('err_open')

em.label('open_alloc_close')
em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle'); em.jmp('err_open_alloc')

em.label('err_open')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_open']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('err_decode')
if OPEN_TEST_BUILD:
    em.mov_r32_ripmem('rax',bsyms['open_decode_error_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['open_decode_error_count'],'rax'); em.jmp('msg_loop')
else:
    em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_decode']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('err_open_alloc')
if ARENA_ALLOC_INJECTION_MODE != 'release':
    em.mov_r32_ripmem('rax',bsyms['open_alloc_error_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['open_alloc_error_count'],'rax'); em.jmp('msg_loop')
else:
    em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_alloc']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('cmd_save')
em.mov_ripmem_imm32(bsyms['save_target_is_temp'],0); em.lea_rip('rax',bsyms['current_path']); em.cmp_word_ptr_reg_zero('rax'); em.jcc(0x84,'cmd_saveas'); em.jmp('do_save')

em.label('cmd_saveas')
em.lea_rip('rcx',bsyms['temp_path']); em.lea_rip('rdx',bsyms['current_path']); em.call_iat('lstrcpyW')
em.emit(*[]); emit_ofn('save_title',0x00080802)
em.mov_r64_r64('rcx','r12'); em.call_iat('GetSaveFileNameW'); em.test32('rax'); em.jcc(0x84,'destructive_cancel')
em.mov_ripmem_imm32(bsyms['save_target_is_temp'],1)

em.label('do_save')
# Persist only the canonical Document Model. Synchronize once in case a queued EN_CHANGE is pending.
em.call_label('sync_model_from_editor')
# V8.6：serialize 写 widebuf、编码写 bytebuf，先保证两个 arena 都能容纳本次输出。
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.add_r32_imm8('rcx',1); em.call_label('ensure_wide_arena'); em.test32('rax'); em.jcc(0x84,'err_save')
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.shl_r32_imm8('rcx',2); em.add_r32_imm8('rcx',3); em.call_label('ensure_byte_arena'); em.test32('rax'); em.jcc(0x84,'err_save')
em.call_label('serialize_preferred_eol'); em.mov_r32_r32('r13','rax'); em.cmp_r32_imm('r13',WIDE_CHARS-1); em.jcc(0x87,'err_save')
# Encode the EOL-adjusted UTF-16 scratch according to committed document metadata.
em.mov_r32_ripmem('rax',bsyms['encoding_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'save_encode_utf16'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'save_encode_utf8_bom')
em.test32('r13'); em.jcc(0x84,'save_zero_bytes')
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.mov_r64_ripmem('r8',bsyms['widebuf']); em.mov_r32_r32('r9','r13'); em.mov_r64_ripmem('rax',bsyms['bytebuf']); em.mov_mrsp_reg64(0x20,'rax'); em.mov_r32_ripmem('rax',bsyms['byte_capacity']); em.mov_mrsp_reg32(0x28,'rax'); em.mov_mrsp_imm32(0x30,0,qword=True); em.mov_mrsp_imm32(0x38,0,qword=True); em.call_iat('WideCharToMultiByte'); em.test32('rax'); em.jcc(0x84,'err_save'); em.mov_r32_r32('r13','rax'); em.jmp('save_create')
em.label('save_encode_utf8_bom')
em.mov_r32_imm('rcx',65001); em.xor32('rdx'); em.mov_r64_ripmem('r8',bsyms['widebuf']); em.mov_r32_r32('r9','r13'); em.mov_r64_ripmem('rax',bsyms['bytebuf']); em.add_r64_imm8('rax',3); em.mov_mrsp_reg64(0x20,'rax'); em.mov_r32_ripmem('rax',bsyms['byte_capacity']); em.sub_r32_imm8('rax',3); em.mov_mrsp_reg32(0x28,'rax'); em.mov_mrsp_imm32(0x30,0,qword=True); em.mov_mrsp_imm32(0x38,0,qword=True); em.call_iat('WideCharToMultiByte'); em.test32('r13'); em.jcc(0x84,'save_utf8_bom_prefix'); em.test32('rax'); em.jcc(0x84,'err_save')
em.label('save_utf8_bom_prefix'); em.mov_r32_r32('r13','rax'); em.add_r32_imm8('r13',3); em.mov_r64_ripmem('rcx',bsyms['bytebuf']); em.mov_byte_ptr_imm8('rcx',0xEF); em.add_r64_imm8('rcx',1); em.mov_byte_ptr_imm8('rcx',0xBB); em.add_r64_imm8('rcx',1); em.mov_byte_ptr_imm8('rcx',0xBF); em.jmp('save_create')
em.label('save_encode_utf16')
em.mov_r64_ripmem('rcx',bsyms['bytebuf']); em.xor32('r8'); em.mov_word_index2_imm16('rcx','r8',0xFEFF); em.mov_r64_ripmem('rdx',bsyms['widebuf']); em.xor32('r8'); em.mov_r32_imm('r9',1)
em.label('save_utf16_copy'); em.cmp_r32_r32('r8','r13'); em.jcc(0x83,'save_utf16_done'); em.movzx_r32_word_index2('rax','rdx','r8'); em.mov_word_index2_reg('rcx','r9','rax'); em.add_r32_imm8('r8',1); em.add_r32_imm8('r9',1); em.jmp('save_utf16_copy')
em.label('save_utf16_done'); em.shl_r32_imm8('r13',1); em.add_r32_imm8('r13',2); em.jmp('save_create')
em.label('save_zero_bytes'); em.xor32('r13')
em.label('save_create')
# Freeze the destination for this transaction in nonvolatile r14. Save As keeps
# its selected path in temp_path until the atomic replacement commits.
em.mov_r32_ripmem('rax',bsyms['save_target_is_temp']); em.test32('rax'); em.jcc(0x84,'save_use_current_path'); em.lea_rip('r14',bsyms['temp_path']); em.jmp('save_target_ready')
em.label('save_use_current_path'); em.lea_rip('r14',bsyms['current_path'])
# Build a sibling staging path by appending ".pemark.tmp". A 500-character
# destination plus the 11-character suffix and NUL exactly fits PATH_CHARS=512.
em.label('save_target_ready'); em.mov_r64_r64('rcx','r14'); em.call_iat('lstrlenW'); em.cmp_r32_imm('rax',500); em.jcc(0x87,'err_save'); em.mov_r32_r32('r15','rax')
em.lea_rip('rcx',bsyms['save_stage_path']); em.mov_r64_r64('rdx','r14'); em.call_iat('lstrcpyW'); em.lea_rip('rcx',bsyms['save_stage_path'])
for _ch in '.pemark.tmp':
    em.mov_word_index2_imm16('rcx','r15',ord(_ch)); em.add_r32_imm8('r15',1)
em.mov_word_index2_zero('rcx','r15')
# Only the sibling staging file is truncated. The destination remains untouched
# until MoveFileExW is the single commit point.
em.lea_rip('rcx',bsyms['save_stage_path']); em.mov_r32_imm('rdx',0x40000000); em.xor32('r8'); em.xor32('r9'); em.mov_mrsp_imm32(0x20,1); em.mov_mrsp_imm32(0x28,0x80); em.mov_mrsp_imm32(0x30,0,qword=True)
if WRITE_INJECTION_MODE == 'create_failure': em.call_label('injected_CreateFileW')
else: em.call_iat('CreateFileW')
em.cmp_rax_neg1(); em.jcc(0x84,'save_create_failed'); em.mov_r64_r64('r12','rax')
# Complete-write loop. WriteFile success may legally report fewer bytes than
# requested. Advance by io_count until no bytes remain; zero progress or an
# impossible count above remaining is a hard failure.
em.mov_r64_ripmem('r14',bsyms['bytebuf']); em.mov_r32_r32('r15','r13')
em.label('save_write_loop'); em.test32('r15'); em.jcc(0x84,'save_write_complete')
em.mov_r64_r64('rcx','r12'); em.mov_r64_r64('rdx','r14'); em.mov_r32_r32('r8','r15'); em.lea_rip('r9',bsyms['io_count']); em.mov_mrsp_imm32(0x20,0,qword=True)
if WRITE_CALL_INJECTED: em.call_label('injected_WriteFile')
else: em.call_iat('WriteFile')
em.test32('rax'); em.jcc(0x84,'save_fail_close')
em.mov_r32_ripmem('rax',bsyms['io_count']); em.test32('rax'); em.jcc(0x84,'save_fail_close'); em.cmp_r32_r32('rax','r15'); em.jcc(0x87,'save_fail_close')
em.add_r64_r64('r14','rax'); em.sub_r32_r32('r15','rax'); em.jmp('save_write_loop')
em.label('save_write_complete')
em.mov_r64_r64('rcx','r12')
if WRITE_INJECTION_MODE == 'flush_failure': em.call_label('injected_FlushFileBuffers')
else: em.call_iat('FlushFileBuffers')
em.test32('rax'); em.jcc(0x84,'save_fail_close')
em.mov_r64_r64('rcx','r12')
if WRITE_INJECTION_MODE == 'close_failure': em.call_label('injected_CloseHandle')
else: em.call_iat('CloseHandle')
em.test32('rax'); em.jcc(0x84,'save_close_retry')
# Recover the frozen destination pointer after r14 was reused by the write loop.
em.mov_r32_ripmem('rax',bsyms['save_target_is_temp']); em.test32('rax'); em.jcc(0x84,'save_replace_current'); em.lea_rip('rdx',bsyms['temp_path']); em.jmp('save_replace_ready')
em.label('save_replace_current'); em.lea_rip('rdx',bsyms['current_path'])
em.label('save_replace_ready'); em.lea_rip('rcx',bsyms['save_stage_path']); em.mov_r32_imm('r8',9)
if WRITE_INJECTION_MODE == 'replace_failure': em.call_label('injected_MoveFileExW')
else: em.call_iat('MoveFileExW')
em.test32('rax'); em.jcc(0x84,'save_fail_delete')
em.mov_r32_ripmem('rax',bsyms['save_target_is_temp']); em.test32('rax'); em.jcc(0x84,'save_path_committed'); em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW')
em.label('save_path_committed'); em.mov_ripmem_imm32(bsyms['save_target_is_temp'],0); em.call_label('mark_document_saved'); em.call_label('update_preview'); em.call_label('update_status'); em.jmp('destructive_continue')

em.label('save_fail_close'); em.mov_r64_r64('rcx','r12'); em.call_iat('CloseHandle')
em.jmp('save_fail_delete')
em.label('save_close_retry'); em.mov_r64_r64('rcx','r12')
if WRITE_INJECTION_MODE == 'close_failure': em.call_label('injected_CloseHandle')
else: em.call_iat('CloseHandle')
em.label('save_fail_delete'); em.lea_rip('rcx',bsyms['save_stage_path']); em.call_iat('DeleteFileW')
em.label('err_save'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],0); em.mov_ripmem_imm32(bsyms['save_target_is_temp'],0); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_save']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x10); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

em.label('save_create_failed'); em.call_iat('GetLastError'); em.cmp_r32_imm('rax',80); em.jcc(0x84,'err_recovery_exists'); em.cmp_r32_imm('rax',183); em.jcc(0x85,'err_save')
em.label('err_recovery_exists'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],0); em.mov_ripmem_imm32(bsyms['save_target_is_temp'],0); em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['err_recovery_exists']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x30); em.call_iat('MessageBoxW'); em.jmp('msg_loop')

# All destructive document transitions enter here. pending action: 1 New,
# 2 Open, 3 Close. Dirty Save retains the action until a successful save commit;
# Discard continues immediately; Cancel and save failure clear it.
em.label('request_close'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],3); em.jmp('destructive_request')
em.label('destructive_request')
em.call_label('is_document_dirty'); em.test32('rax'); em.jcc(0x84,'destructive_continue')
em.mov_r64_r64('rcx','rbx'); em.lea_rip('rdx',rsyms['unsaved_prompt']); em.lea_rip('r8',rsyms['err_title']); em.mov_r32_imm('r9',0x33); em.call_iat('MessageBoxW')
em.cmp_r32_imm('rax',6); em.jcc(0x84,'cmd_save')       # IDYES: save then continue
em.cmp_r32_imm('rax',7); em.jcc(0x84,'destructive_continue') # IDNO: discard
em.label('destructive_cancel'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],0); em.mov_ripmem_imm32(bsyms['save_target_is_temp'],0); em.mov_ripmem_imm32(bsyms['open_bypass_picker'],0); em.jmp('msg_loop')
em.label('destructive_continue')
em.mov_r32_ripmem('r10',bsyms['pending_destructive_action']); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],0)
em.cmp_r32_imm('r10',1); em.jcc(0x84,'cmd_new_commit')
em.cmp_r32_imm('r10',2); em.jcc(0x84,'destructive_open')
em.cmp_r32_imm('r10',3); em.jcc(0x84,'destructive_close')
em.jmp('msg_loop')
# V8.6 切片 3：从文件列表发起并且已确认的 Open 跳过文件选择器，直接用列表里
# 已经定好的 temp_path 走 cmd_open_selected（同一套读取/解码/提交路径）。
em.label('destructive_open')
em.mov_r32_ripmem('rax',bsyms['open_bypass_picker']); em.mov_ripmem_imm32(bsyms['open_bypass_picker'],0); em.test32('rax'); em.jcc(0x84,'cmd_open_dialog')
em.jmp('cmd_open_selected')
em.label('destructive_close'); em.mov_r64_r64('rcx','rbx'); em.call_iat('DestroyWindow'); em.jmp('msg_loop')

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
em.xor32('rcx'); em.call_iat('GetModuleHandleW'); em.mov_r64_r64('r15','rax')
em.xor32('rcx'); em.lea_rip('rdx',rsyms['class_edit']); em.xor32('r8')
em.mov_r32_ripmem('rax',bsyms['wrap_flag']); em.test32('rax'); em.jcc(0x84,'wrap_style_off')
em.mov_r32_imm('r9',0x54211044)  # WS_CLIPSIBLINGS
em.jmp('wrap_style_ready')
em.label('wrap_style_off'); em.mov_r32_imm('r9',0x503110C4)
em.label('wrap_style_ready')
em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,100); em.mov_mrsp_imm32(0x38,100)
em.mov_mrsp_reg64(0x40,'rbx'); em.mov_mrsp_imm32(0x48,1,qword=True); em.mov_mrsp_reg64(0x50,'r15'); em.mov_mrsp_imm32(0x58,0,qword=True)
em.call_iat('CreateWindowExW'); em.mov_r64_r64('rsi','rax'); em.mov_ripmem_r64(bsyms['hwnd_edit'],'rsi'); em.test64('rax'); em.jcc(0x84,'exit')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00C5); em.mov_r32_imm('r8',WIDE_CHARS-1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x000C); em.xor32('r8'); em.mov_r64_ripmem('r9',bsyms['document_model']); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x0030); em.mov_r64_ripmem('r8',bsyms['hfont']); em.mov_r32_imm('r9',1); em.call_iat('SendMessageW')
# Apply the 10px Source text gutter after WM_SETFONT so it cannot be reset by the font change.
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00D3); em.mov_r32_imm('r8',3); em.mov_r32_imm('r9',0x000A000A); em.call_iat('SendMessageW')
em.mov_r64_r64('rcx','rsi'); em.mov_r32_imm('rdx',0x00B1); em.mov_r32_ripmem('r8',bsyms['sel_start']); em.mov_r32_ripmem('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
em.call_label('resize_children'); em.call_label('update_status')
# V8.5.0：重建后的 EDIT 以 WS_VISIBLE 样式出生，预览模式下必须重新隐藏。
# 表面一致性恢复统一经由 set_view_mode_commit(当前模式)，源码模式下全部
# 操作幂等。旧版在此对文档表面直接 ShowWindow，是 ViewState 收拢前的
# 最后一个散落写点。
em.mov_r32_ripmem('r8',bsyms['preview_flag']); em.call_label('set_view_mode_commit')
em.mov_r64_r64('rcx','rsi'); em.call_iat('SetFocus'); em.jmp('msg_loop')

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

# ---------------- V8.5.0 ViewState：视图模式唯一写者 ----------------
# 契约：r8d = 模式（0=SOURCE, 1=PREVIEW）。
#   set_view_mode          — 原子切换：写 preview_flag + 两文档表面
#                            ShowWindow + 菜单勾选（无编排的简单场景）。
#   set_view_mode_prepare  — 仅写 preview_flag（供 preview_show 编排的
#                            提前数据依赖：update_preview 读该标志决定
#                            是否把渲染文本装载进 RichEdit）。
#   set_view_mode_commit   — 仅做表面 ShowWindow + 菜单（编排的最后
#                            一步原子显示，避免未格式化中间帧；prepare
#                            与 commit 之间视图状态过渡期由编排持有）。
# 不变量（构建期架构断言强制）：除初始化区外，preview_flag 写点与对
# hwnd_edit/hwnd_preview 的 ShowWindow 只允许出现在本家族例程及
# load_model_into_editor 的防闪烁配对内。
# clobber：rax,rcx,rdx,r8,r9,r10,r11
# 帧纪律（AGENTS 规则 5）：commit 是唯一含嵌套调用的成员，入口建立
# 标准帧 sub rsp,0x28（进入时 RSP≡8 mod 16，减 40 后 call 前 ≡0 对齐，
# [rsp,rsp+0x20) 影子空间不覆盖返回地址）；set_view_mode 经尾调用 jmp
# 委托给 commit，帧纪律由 commit 独立维护；prepare 无嵌套调用无需帧。
# V8.5.0 首次构建曾遗漏本帧：ShowWindow 写影子空间覆盖返回地址，
# 打开文件即崩溃——教训已固化为构建期断言 (F)/(G)。
em.label('set_view_mode_prepare')
em.mov_ripmem_r32(bsyms['preview_flag'],'r8')
em.emit(0xC3)
em.label('set_view_mode')
em.mov_ripmem_r32(bsyms['preview_flag'],'r8')
em.jmp('set_view_mode_commit')
em.label('set_view_mode_commit')
em.emit(0x48,0x83,0xEC,0x28)  # sub rsp,0x28：对齐 + 影子空间
em.test32('r8'); em.jcc(0x84,'set_view_source')
# PREVIEW：隐藏源码表面，显示预览表面，勾选菜单。
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)
em.label('set_view_source')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1306); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('cmd_preview')
# V8.5.0：preview_flag 是唯一权威（set_view_mode 家族保证它与实际
# 可见性一致）。旧版在此用 IsWindowVisible 调和逻辑状态与表面状态——
# 双状态表示正是 P0-001 的病根，单一写者建立后调和逻辑不再需要。
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'preview_show')
em.label('preview_hide_active')
# Preview -> Source: capture selection AND the first visible paragraph anchor,
# map both back into source coordinates, then restore the same viewport after switching.
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('capture_surface_state')
em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_sel_start'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_sel_end']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_sel_end'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.call_label('map_render_to_source'); em.mov_ripmem_r32(bsyms['view_top_pos'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',0x4D); em.call_iat('KillTimer'); em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],0)
# V8.5.0：视图状态切换全部经由唯一写者。
em.xor32('r8'); em.call_label('set_view_mode')
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('SetFocus'); em.jmp('msg_loop')

em.label('preview_show')
# Source -> Preview: capture source viewport/caret, render once, map selection +
# top-visible anchor through render_srcmap, then restore them in RichEdit.
em.call_label('sync_model_from_editor')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_label('capture_surface_state')
# V8.5.0：prepare 只提前写 preview_flag——update_preview 依赖它决定
# 是否把渲染文本装载进 RichEdit 表面。表面切换推迟到 commit。
em.mov_r32_imm('r8',1); em.call_label('set_view_mode_prepare')
em.call_label('update_preview')
em.mov_r32_ripmem('r8',bsyms['view_sel_start']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_sel_start'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_sel_end']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_sel_end'],'rax')
em.mov_r32_ripmem('r8',bsyms['view_top_pos']); em.call_label('map_source_to_render'); em.mov_ripmem_r32(bsyms['view_top_pos'],'rax')
# Keep Preview hidden while restoring its mapped viewport and applying the first
# visible semantic spans, so the user never sees an unformatted intermediate frame.
# V8.5.0：commit 原子完成隐藏源码表面 + 显示预览表面 + 菜单勾选。
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.call_label('restore_surface_state')
em.call_label('refresh_preview_visible_theme')
em.mov_r32_imm('r8',1); em.call_label('set_view_mode_commit')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.call_iat('ShowWindow'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag_offset'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_top'],4)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_h'],32)
em.mov_ripmem_imm32(bsyms['outline_scroll_track_h'],100)
em.mov_ripmem_imm32(bsyms['outline_visible_rows'],1)
em.mov_ripmem_imm32(bsyms['outline_max_top'],0)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.xor32('r8'); em.call_iat('CheckMenuItem'); em.jmp('outline_layout')
em.label('outline_show')
em.mov_ripmem_imm32(bsyms['outline_flag'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
# V8.4.24（P0-002）：空闲时表面保持物理隐藏。若在此处 SW_SHOW 而可见标志
# 仍为 0，会先画出一条没有 thumb 的空条，直到 resize_children 再次隐藏它；
# 隐藏状态与可见标志、空闲契约保持一致。
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.call_iat('ShowWindow'); em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag_offset'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_top'],4)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_h'],32)
em.mov_ripmem_imm32(bsyms['outline_scroll_track_h'],100)
em.mov_ripmem_imm32(bsyms['outline_visible_rows'],1)
em.mov_ripmem_imm32(bsyms['outline_max_top'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1307); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.label('outline_layout')
em.call_label('resize_children')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.call_label('restore_surface_state')
em.mov_r64_ripmem('rcx',bsyms['view_hwnd']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.jmp('msg_loop')

# Theme changes reuse the already parsed render buffer/style table. They never
# rescan Markdown or replace the RichEdit text.  In Preview mode repaint is frozen
# while base colors + recorded spans are restyled, then viewport is restored.
em.label('cmd_light'); em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.jmp('theme_fast_apply')
em.label('cmd_dark'); em.mov_ripmem_imm32(bsyms['theme_dark'],1); em.jmp('theme_fast_apply')
em.label('cmd_theme_toggle')
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_toggle_dark')
em.mov_ripmem_imm32(bsyms['theme_dark'],0); em.jmp('theme_fast_apply')
em.label('theme_toggle_dark'); em.mov_ripmem_imm32(bsyms['theme_dark'],1)
em.label('theme_fast_apply')
# Theme changes supersede any pending lazy repaint from the previous theme.
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.mov_r32_imm('rdx',0x4D); em.call_iat('KillTimer')
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

em.label('cmd_exit'); em.jmp('request_close')

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
em.mov_eax_mr12(8); em.cmp_r32_imm('rax',0x0115); em.jcc(0x84,'dispatch_theme_schedule')  # WM_VSCROLL
em.cmp_r32_imm('rax',0x020A); em.jcc(0x84,'dispatch_theme_schedule')                       # WM_MOUSEWHEEL
# Lazy Preview styling must also follow keyboard viewport movement (arrows, PgUp/
# PgDn, Home/End). Scheduling on any Preview WM_KEYDOWN is cheap and avoids stale
# formatting after keyboard-only navigation.
em.cmp_r32_imm('rax',0x0100); em.jcc(0x85,'dispatch_theme_refresh_done')
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
# 退出崩溃根因修复（2026-09-14 定位）：主窗口在 DispatchMessageW 内部被
# DestroyWindow 销毁后，IsWindow=0 使 JNE 不跳转，执行流曾直落（fall
# through）进下方 sync_outline_scrollbar——一个以 ret 结尾、却从未被
# call 进入的子程序：栈上没有返回地址，ret 弹出消息循环栈残留数据当
# 返回地址 → 跳野地址 → 每次关窗 0xC0000005。dispatch 块必须以显式
# jmp 终结（构建期断言 (I) 强制）。
em.jmp('exit')

# ------------------------------------------------------------------
# 辅助例程：同步独立的大纲滚动条范围/位置。
# V8.4.24（P0-002）OutlineScrollState 归属说明：BSS 字段
# {outline_scroll_top, outline_scroll_count, outline_scroll_visible,
#  outline_scroll_drag, outline_scroll_drag_offset,
#  outline_scroll_thumb_top, outline_scroll_thumb_h,
#  outline_scroll_track_h, outline_visible_rows, outline_max_top}
# 构成唯一的滚动条状态记录。下方的 sync_outline_scrollbar 是唯一的
# 几何生产者；WM_PAINT（scrollproc）、thumb 命中测试（lbuttondown）
# 和拖动映射（outline_scroll_drag_move）都只是这些缓存字段的消费者，
# 绝不独立重算几何。
em.label('sync_outline_scrollbar')
em.emit(0x48,0x83,0xEC,0x38)
# count/top from ListBox
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'sync_os_ret')
em.mov_r32_imm('rdx',0x018B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['outline_scroll_count'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x018E); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'rax')
em.call_label('scroll_layout')
# Enforce the cached maximum after native ListBox keyboard/wheel navigation too.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.mov_r32_ripmem('r8',bsyms['outline_scroll_top']); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.xor32('r8'); em.mov_r32_imm('r9',0x105); em.call_iat('RedrawWindow')
em.label('sync_os_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Inputs: count/top, content_h, scrollbar_w. Outputs: cached track/thumb/travel/rects.
em.label('scroll_layout')
em.emit(0x48,0x83,0xEC,0x28)
# Use floor(outline_list_h/30): a partially visible row cannot increase the valid top index.
em.mov_r32_ripmem('rax',bsyms['outline_list_h']); em.test32('rax'); em.jcc(0x89,'scroll_height_ok'); em.xor32('rax')
em.label('scroll_height_ok'); em.xor32('rdx'); em.mov_r32_imm('rcx',30); em.emit(0xF7,0xF1)
em.test32('rax'); em.jcc(0x85,'sync_rows_ok'); em.mov_r32_imm('rax',1)
em.label('sync_rows_ok'); em.mov_ripmem_r32(bsyms['outline_visible_rows'],'rax')
# maxTop=max(0,count-visibleRows)
em.mov_r32_ripmem('r10',bsyms['outline_scroll_count']); em.mov_r32_ripmem('r11',bsyms['outline_visible_rows']); em.cmp_r32_r32('r10','r11'); em.jcc(0x87,'sync_have_maxtop'); em.xor32('r10'); em.jmp('sync_store_maxtop')
em.label('sync_have_maxtop'); em.sub_r32_r32('r10','r11')
em.label('sync_store_maxtop'); em.mov_ripmem_r32(bsyms['outline_max_top'],'r10')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_top']); em.test32('rax'); em.jcc(0x89,'scroll_top_nonnegative'); em.xor32('rax')
em.label('scroll_top_nonnegative'); em.cmp_r32_r32('rax','r10'); em.jcc(0x86,'scroll_top_clamped'); em.mov_r32_r32('rax','r10')
em.label('scroll_top_clamped'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'rax')
# track height uses 4px top/bottom margins.
em.mov_r32_ripmem('r10',bsyms['outline_list_h']); em.cmp_r32_imm('r10',8); em.jcc(0x8F,'sync_track_ok'); em.mov_r32_imm('r10',8)
em.label('sync_track_ok'); em.sub_r32_imm8('r10',8); em.mov_ripmem_r32(bsyms['outline_scroll_track_h'],'r10')
# thumb_h：所有行都放得下时等于轨道高，否则取 max(32, visibleRows*track/count)。
# V8.4.24 二次修复（P0-002 主根因）：V8.4.23 起此分支即写反——cmp 后用
# JAE(0x83)，导致“需要滚动”（visibleRows<count）时反而落入 sync_thumb_full，
# thumb 占满整条轨道，travel = track_h - thumb_h = 0，拖动行程归零，列表永远
# 滚不动。正确语义：visibleRows < count（需要滚动）才按比例计算（JB=0x82），
# visibleRows >= count（全部可见）才占满轨道。
em.mov_r32_ripmem('r11',bsyms['outline_scroll_count']); em.test32('r11'); em.jcc(0x84,'sync_thumb_full')
em.mov_r32_ripmem('rax',bsyms['outline_visible_rows']); em.cmp_r32_r32('rax','r11'); em.jcc(0x82,'sync_thumb_calc')
em.label('sync_thumb_full'); em.mov_r32_ripmem('rax',bsyms['outline_scroll_track_h']); em.jmp('sync_thumb_store')
em.label('sync_thumb_calc'); em.mov_r32_ripmem('rcx',bsyms['outline_visible_rows']); em.mov_r32_ripmem('rdx',bsyms['outline_scroll_track_h']); em.mov_r32_ripmem('r8',bsyms['outline_scroll_count']); em.call_iat('MulDiv'); em.cmp_r32_imm('rax',32); em.jcc(0x83,'sync_thumb_store'); em.mov_r32_imm('rax',32)
em.label('sync_thumb_store'); em.mov_r32_ripmem('r10',bsyms['outline_scroll_track_h']); em.cmp_r32_r32('rax','r10'); em.jcc(0x86,'sync_thumb_store2'); em.mov_r32_r32('rax','r10')
em.label('sync_thumb_store2'); em.mov_ripmem_r32(bsyms['outline_scroll_thumb_h'],'rax')
# thumbTop = 4 + top * (track-thumb) / maxTop
em.mov_r32_ripmem('r10',bsyms['outline_max_top']); em.test32('r10'); em.jcc(0x84,'sync_thumb_top_zero')
em.mov_r32_ripmem('r11',bsyms['outline_scroll_track_h']); em.mov_r32_ripmem('rax',bsyms['outline_scroll_thumb_h']); em.sub_r32_r32('r11','rax')
em.mov_r32_ripmem('rcx',bsyms['outline_scroll_top']); em.mov_r32_r32('rdx','r11'); em.mov_r32_r32('r8','r10'); em.call_iat('MulDiv'); em.add_r32_imm8('rax',4); em.jmp('sync_thumb_top_store')
em.label('sync_thumb_top_zero'); em.mov_r32_imm('rax',4)
em.label('sync_thumb_top_store'); em.mov_ripmem_r32(bsyms['outline_scroll_thumb_top'],'rax')
# Cache rectangles in scrollbar-local coordinates.
em.lea_rip('rcx',bsyms['outline_track_rect']); em.mov_mreg_imm32('rcx',0,0); em.mov_mreg_imm32('rcx',4,4)
em.mov_r32_ripmem('rax',bsyms['scrollbar_w']); em.mov_mreg_reg32('rcx',8,'rax')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_track_h']); em.add_r32_imm8('rax',4); em.mov_mreg_reg32('rcx',12,'rax')
em.mov_r32_ripmem('r10',bsyms['outline_scroll_track_h']); em.mov_r32_ripmem('rax',bsyms['outline_scroll_thumb_h']); em.sub_r32_r32('r10','rax'); em.mov_ripmem_r32(bsyms['outline_scroll_travel'],'r10')
em.mov_r32_ripmem('r11',bsyms['scrollbar_w']); em.mov_r32_r32('r10','r11'); em.shr_r32_imm8('r10',1)
em.cmp_r32_imm('r10',6); em.jcc(0x83,'scroll_width_min'); em.mov_r32_imm('r10',6)
em.label('scroll_width_min'); em.cmp_r32_imm('r10',9); em.jcc(0x86,'scroll_width_max'); em.mov_r32_imm('r10',9)
em.label('scroll_width_max'); em.cmp_r32_r32('r10','r11'); em.jcc(0x86,'scroll_width_ready'); em.mov_r32_r32('r10','r11')
em.label('scroll_width_ready'); em.sub_r32_r32('r11','r10'); em.shr_r32_imm8('r11',1)
em.lea_rip('rcx',bsyms['outline_thumb_rect']); em.mov_mreg_reg32('rcx',0,'r11'); em.add_r32_r32('r11','r10'); em.mov_mreg_reg32('rcx',8,'r11')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_thumb_top']); em.mov_mreg_reg32('rcx',4,'rax'); em.mov_r32_ripmem('r10',bsyms['outline_scroll_thumb_h']); em.add_r32_r32('rax','r10'); em.mov_mreg_reg32('rcx',12,'rax')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Owner-drawn overlay scrollbar visibility.  Geometry never changes on hover.
em.label('update_outline_hover')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('rax',bsyms['outline_max_top']); em.test32('rax'); em.jcc(0x84,'hover_hide_custom')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'hover_hide_custom')
em.mov_r32_ripmem('rax',bsyms['splitter_drag']); em.test32('rax'); em.jcc(0x85,'hover_hide_custom')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag']); em.test32('rax'); em.jcc(0x85,'hover_show_custom')
em.lea_rip('rcx',bsyms['cursor_pt']); em.call_iat('GetCursorPos'); em.test32('rax'); em.jcc(0x84,'hover_hide_custom')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient'); em.test32('rax'); em.jcc(0x84,'hover_hide_custom')
# V8.4.24（P0-002）：悬停显示区从槽道左缘 6px 前开始、到分隔条为止。
# 旧实现多出的 +4px 越界与 splitter 拖拽命中区 [outline_width,
# outline_width+8) 重叠：在那里悬停会显示 thumb，而一次点击却会变成
# splitter 拖动把 thumb 移走。悬停区 == 槽道区。
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.mov_r32_ripmem('rax',bsyms['scrollbar_w']); em.sub_r32_r32('r11','rax'); em.sub_r32_imm8('r11',6); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'hover_hide_custom')
em.mov_r32_ripmem('r11',bsyms['outline_width']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'hover_hide_custom')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.test32('r10'); em.jcc(0x88,'hover_hide_custom'); em.mov_r32_ripmem('r11',bsyms['content_h']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8D,'hover_hide_custom')
em.label('hover_show_custom')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x85,'hover_cursor_custom')
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],1)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.call_label('sync_outline_scrollbar'); em.jmp('hover_cursor_custom')
em.label('hover_hide_custom')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'hover_cursor_custom')
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.label('hover_cursor_custom')
# Resize cursor only on document-side hit zone.
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.mov_r32_ripmem('r11',bsyms['outline_width']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8C,'hover_done_custom'); em.add_r32_imm8('r11',8); em.cmp_r32_r32('r10','r11'); em.jcc(0x8F,'hover_done_custom')
em.xor32('rcx'); em.mov_r32_imm('rdx',32644); em.call_iat('LoadCursorW'); em.mov_r64_r64('rcx','rax'); em.call_iat('SetCursor')
em.label('hover_done_custom'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# MSG.pt preserves the pointer position that generated the queued event.
em.label('capture_message_point')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rax',bsyms['msg']+36); em.mov_ripmem_r32(bsyms['cursor_pt'],'rax')
em.mov_r32_ripmem('rax',bsyms['msg']+40); em.mov_ripmem_r32(bsyms['cursor_pt']+4,'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.lea_rip('rdx',bsyms['cursor_pt']); em.call_iat('ScreenToClient')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Drag the custom thumb without touching ListBox geometry.
em.label('outline_scroll_drag_move')
em.emit(0x48,0x83,0xEC,0x38)
em.call_label('capture_message_point'); em.test32('rax'); em.jcc(0x84,'os_drag_ret')
# desired thumb offset inside track = y - dragOffset - 4, clamped to [0, travel].
# V8.4.24 二次修复：钳制必须用有符号比较（JGE=0x8D / JLE=0x8E）。V8.4.23 用
# 无符号 JAE/JBE：鼠标拖到客户区上方时 y-dragOffset 为负，无符号下被当作巨大
# 正数，跳过下限钳制并直接命中上限，thumb 瞬间跳到最底部（实测“向窗口上方
# 拖动会跳到底部”）。
em.mov_r32_ripmem('r10',bsyms['cursor_pt']+4); em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag_offset']); em.sub_r32_r32('r10','rax'); em.cmp_r32_imm('r10',4); em.jcc(0x8D,'os_drag_after_top'); em.mov_r32_imm('r10',4)
em.label('os_drag_after_top'); em.sub_r32_imm8('r10',4)
em.mov_r32_ripmem('r11',bsyms['outline_scroll_travel']); em.cmp_r32_r32('r10','r11'); em.jcc(0x8E,'os_drag_pos_ok'); em.mov_r32_r32('r10','r11')
em.label('os_drag_pos_ok'); em.mov_r32_ripmem('r11',bsyms['outline_max_top']); em.test32('r11'); em.jcc(0x84,'os_drag_zero')
em.mov_r32_r32('rcx','r10'); em.mov_r32_r32('rdx','r11'); em.mov_r32_ripmem('r8',bsyms['outline_scroll_travel']); em.test32('r8'); em.jcc(0x84,'os_drag_zero'); em.call_iat('MulDiv'); em.mov_r32_r32('r10','rax'); em.jmp('os_drag_apply')
em.label('os_drag_zero'); em.xor32('r10')
em.label('os_drag_apply'); em.mov_ripmem_r32(bsyms['outline_scroll_top'],'r10'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0197); em.mov_r32_r32('r8','r10'); em.xor32('r9'); em.call_iat('SendMessageW'); em.call_label('sync_outline_scrollbar')
em.label('os_drag_ret'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: live splitter drag; clamp Outline to 140..500 px while preserving at least 240px document width.
em.label('splitter_drag_move')
em.emit(0x48,0x83,0xEC,0x28)
em.call_label('capture_message_point'); em.test32('rax'); em.jcc(0x84,'split_drag_ret')
em.mov_r32_ripmem('r10',bsyms['cursor_pt']); em.cmp_r32_imm('r10',140); em.jcc(0x83,'split_drag_min_ok'); em.mov_r32_imm('r10',140)
em.label('split_drag_min_ok'); em.mov_r32_ripmem('r11',bsyms['client_w']); em.mov_r32_imm('rax',240); em.sub_r32_r32('r11','rax'); em.cmp_r32_imm('r11',500); em.jcc(0x86,'split_drag_max_ready'); em.mov_r32_imm('r11',500)
em.label('split_drag_max_ready'); em.cmp_r32_imm('r11',140); em.jcc(0x83,'split_drag_have_max'); em.mov_r32_imm('r11',140)
em.label('split_drag_have_max'); em.cmp_r32_r32('r10','r11'); em.jcc(0x86,'split_drag_store'); em.mov_r32_r32('r10','r11')
em.label('split_drag_store'); em.mov_ripmem_r32(bsyms['outline_width'],'r10'); em.call_label('resize_children')
em.label('split_drag_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: compute the current theme-format window without touching RichEdit
# character metrics. Used by the fast theme path before apply_styles.
em.label('set_visible_format_window')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.lea_rip('rdx',bsyms['preview_client_rect']); em.call_iat('GetClientRect')
em.lea_rip('rcx',bsyms['preview_client_rect']); em.mov_r32_mreg('rax','rcx',8); em.sub_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['preview_bottom_point'],'rax')
em.mov_r32_mreg('rax','rcx',12); em.sub_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['preview_bottom_point']+4,'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x00D7); em.xor32('r8'); em.lea_rip('r9',bsyms['preview_bottom_point']); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'visible_window_fallback')
em.mov_r32_ripmem('r10',bsyms['view_top_pos']); em.cmp_r32_r32('rax','r10'); em.jcc(0x83,'visible_window_margin')
em.label('visible_window_fallback'); em.mov_r32_ripmem('rax',bsyms['view_top_pos'])
em.label('visible_window_margin'); em.mov_r32_imm('r11',2000); em.add_r32_r32('rax','r11')
em.mov_r32_ripmem('r9',bsyms['render_len']); em.cmp_r32_r32('rax','r9'); em.jcc(0x86,'visible_window_ok'); em.mov_r32_r32('rax','r9')
em.label('visible_window_ok'); em.mov_ripmem_r32(bsyms['format_visible_end'],'rax'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: lazily apply semantic Markdown styles in the current Preview viewport.
# Used both for theme maintenance and for first-time formatting of newly visited regions.
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

# Helper: resize Outline content + permanent scrollbar gutter + independent
# scrollbar + 1px divider + active document surface from one geometry source.
em.label('resize_children')
em.emit(0x48,0x83,0xEC,0x38)
em.xor32('rax'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.mov_r32_ripmem('rax',bsyms['status_flag']); em.test32('rax'); em.jcc(0x84,'resize_content')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.test64('rcx'); em.jcc(0x84,'resize_content')
em.mov_r32_imm('rdx',0x0005); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetWindowRect')
em.mov_r32_ripmem('rax',bsyms['rect']+12); em.mov_r32_ripmem('r10',bsyms['rect']+4); em.sub_r32_r32('rax','r10'); em.mov_ripmem_r32(bsyms['status_h'],'rax')
em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.test64('rcx'); em.jcc(0x84,'resize_content')
em.xor32('rdx'); em.mov_r32_ripmem('r8',bsyms['client_w']); em.sub_r32_imm8('r8',56)
em.mov_r32_ripmem('r9',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r9','rax')
em.mov_mrsp_imm32(0x20,56); em.mov_r32_ripmem('r11',bsyms['status_h']); em.mov_mrsp_reg32(0x28,'r11'); em.mov_mrsp_imm32(0x30,0x0040); em.call_iat('SetWindowPos')
em.label('resize_content')
em.mov_r32_ripmem('r11',bsyms['client_h']); em.mov_r32_ripmem('rax',bsyms['status_h']); em.sub_r32_r32('r11','rax'); em.mov_ripmem_r32(bsyms['content_h'],'r11')
em.mov_ripmem_imm32(bsyms['content_x'],0); em.mov_r32_ripmem('r10',bsyms['client_w']); em.mov_ripmem_r32(bsyms['content_w'],'r10')
em.mov_r32_ripmem('rax',bsyms['outline_flag']); em.test32('rax'); em.jcc(0x84,'resize_sidebar_hidden')
# Total sidebar width remains outline_width. Reserve scrollbar_w pixels inside it.
em.mov_r32_ripmem('r10',bsyms['outline_width']); em.mov_r32_ripmem('r11',bsyms['scrollbar_w']); em.mov_r32_r32('rax','r10'); em.sub_r32_r32('rax','r11')  # rax = content/listbox width
# document begins after total sidebar + 1px divider
em.mov_r32_r32('r11','r10'); em.add_r32_imm8('r11',1); em.mov_ripmem_r32(bsyms['content_x'],'r11'); em.mov_r32_ripmem('rcx',bsyms['client_w']); em.sub_r32_r32('rcx','r11'); em.mov_ripmem_r32(bsyms['content_w'],'rcx')
# V8.6.1 双面板：两个 28px 标题栏 + 4px 分界线，剩余高度按 panel_split 分配。
em.mov_r32_ripmem('r10',bsyms['content_h']); em.sub_r32_imm8('r10',60)
em.test32('r10'); em.jcc(0x89,'rc_usable_ok'); em.xor32('r10')
em.label('rc_usable_ok')
em.mov_r32_r32('rcx','r10'); em.mov_r32_ripmem('rdx',bsyms['panel_split']); em.mov_r32_imm('r8',1000); em.call_iat('MulDiv')
em.mov_ripmem_r32(bsyms['files_list_h'],'rax')
# MulDiv 是 API 调用，会破坏 volatile 寄存器：可用高度必须重新推导，
# 不能沿用调用前的 r10（否则大纲高度会变成 content_h - 文件高度的错值）。
em.mov_r32_ripmem('r11',bsyms['content_h']); em.sub_r32_imm8('r11',60); em.sub_r32_r32('r11','rax')
em.mov_ripmem_r32(bsyms['outline_list_h'],'r11')
em.mov_ripmem_imm32(bsyms['files_list_y'],28)
em.add_r32_imm8('rax',28); em.mov_ripmem_r32(bsyms['divider_y'],'rax')
em.mov_r32_ripmem('r11',bsyms['divider_y']); em.add_r32_imm8('r11',32); em.mov_ripmem_r32(bsyms['outline_list_y'],'r11')
# 文件标题栏
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_header']); em.xor32('rdx'); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_mrsp_imm32(0x20,28); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 文件列表
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.xor32('rdx'); em.mov_r32_imm('r8',28)
em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_r32_ripmem('r10',bsyms['scrollbar_w']); em.sub_r32_r32('r9','r10')
em.mov_r32_ripmem('r11',bsyms['files_list_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 文件 gutter
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_gutter']); em.mov_r32_ripmem('r10',bsyms['scrollbar_w'])
em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.sub_r32_r32('rdx','r10'); em.mov_r32_imm('r8',28); em.mov_r32_r32('r9','r10')
em.mov_r32_ripmem('r11',bsyms['files_list_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 分界线
em.mov_r64_ripmem('rcx',bsyms['hwnd_panel_divider']); em.xor32('rdx'); em.mov_r32_ripmem('r8',bsyms['divider_y']); em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_mrsp_imm32(0x20,4); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 大纲标题栏
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_header']); em.xor32('rdx'); em.mov_r32_ripmem('r8',bsyms['divider_y']); em.add_r32_imm8('r8',4); em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_mrsp_imm32(0x20,28); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 大纲列表
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_ripmem('r8',bsyms['outline_list_y'])
em.mov_r32_ripmem('r9',bsyms['outline_width']); em.mov_r32_ripmem('r10',bsyms['scrollbar_w']); em.sub_r32_r32('r9','r10')
em.mov_r32_ripmem('r11',bsyms['outline_list_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 大纲 gutter
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.mov_r32_ripmem('r10',bsyms['scrollbar_w'])
em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.sub_r32_r32('rdx','r10'); em.mov_r32_ripmem('r8',bsyms['outline_list_y']); em.mov_r32_r32('r9','r10')
em.mov_r32_ripmem('r11',bsyms['outline_list_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# 滚动条 overlay（暂与大纲 gutter 同矩形）
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_ripmem('r10',bsyms['scrollbar_w'])
em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.sub_r32_r32('rdx','r10'); em.mov_r32_ripmem('r8',bsyms['outline_list_y']); em.mov_r32_r32('r9','r10')
em.mov_r32_ripmem('r11',bsyms['outline_list_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# Keep the custom surface above the fallback gutter STATIC without changing geometry.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.xor32('r8'); em.xor32('r9'); em.mov_mrsp_imm32(0x20,0); em.mov_mrsp_imm32(0x28,0); em.mov_mrsp_imm32(0x30,0x0013); em.call_iat('SetWindowPos')
# One-pixel visual divider after the gutter.
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.mov_r32_ripmem('rdx',bsyms['outline_width']); em.xor32('r8'); em.mov_r32_imm('r9',1); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
# Ensure stable visibility without changing any geometry.
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_header']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_panel_divider']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_header']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_gutter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
# The custom surface is physically hidden while idle. The permanent gutter keeps
# geometry stable, and showing the surface never changes ListBox width.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'resize_scroll_hidden')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow'); em.jmp('resize_doc')
em.label('resize_scroll_hidden'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.call_iat('ShowWindow'); em.jmp('resize_doc')
em.label('resize_sidebar_hidden')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_header']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_panel_divider']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_header']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files_gutter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.call_iat('ShowWindow')
em.mov_ripmem_imm32(bsyms['outline_scroll_visible'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_drag_offset'],0)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_top'],4)
em.mov_ripmem_imm32(bsyms['outline_scroll_thumb_h'],32)
em.mov_ripmem_imm32(bsyms['outline_scroll_track_h'],100)
em.mov_ripmem_imm32(bsyms['outline_visible_rows'],1)
em.mov_ripmem_imm32(bsyms['outline_max_top'],0)
em.label('resize_doc')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'resize_preview_surface'); em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_preview_surface')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'resize_ret'); em.mov_r32_ripmem('rdx',bsyms['content_x']); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['content_w']); em.mov_r32_ripmem('r11',bsyms['content_h']); em.mov_mrsp_reg32(0x20,'r11'); em.mov_mrsp_imm32(0x28,1,qword=True); em.call_iat('MoveWindow')
em.label('resize_ret'); em.call_label('sync_outline_scrollbar'); em.call_label('repaint_splitter_surface'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

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
em.mov_r32_r32('rdx','rax'); em.add_r32_r32('rdx','rdx'); em.add_r32_r32('rdx','rdx'); em.mov_r64_ripmem('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','rdx'); em.mov_r32_ptr('rdx','rcx')
em.cmp_r32_r32('rdx','r8'); em.jcc(0x82,'msr_move_lo'); em.mov_r32_r32('r11','rax'); em.jmp('msr_loop')
em.label('msr_move_lo'); em.mov_r32_r32('r10','rax'); em.add_r32_imm8('r10',1); em.jmp('msr_loop')
em.label('msr_done'); em.mov_r32_r32('rax','r10'); em.emit(0xC3)

# Map a Preview UTF-16 index (r8d) back to its exact source-producing index.
# A caret at Preview EOF maps to Document EOF.
em.label('map_render_to_source')
em.mov_r32_ripmem('r9',bsyms['render_len']); em.test32('r9'); em.jcc(0x85,'mrs_nonempty'); em.xor32('rax'); em.emit(0xC3)
em.label('mrs_nonempty'); em.cmp_r32_r32('r8','r9'); em.jcc(0x82,'mrs_inrange'); em.mov_r32_ripmem('rax',bsyms['document_len']); em.emit(0xC3)
em.label('mrs_inrange'); em.mov_r32_r32('rax','r8'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.mov_r64_ripmem('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('rax','rcx'); em.emit(0xC3)

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
# Revision ownership helpers are leaf routines. Revision zero is reserved for
# process initialization; wrap skips zero so equality remains unambiguous.
em.label('advance_document_revision')
em.mov_r64_ripmem('rax',bsyms['document_revision']); em.add_r64_imm8('rax',1); em.test64('rax'); em.jcc(0x85,'advance_document_revision_store'); em.add_r64_imm8('rax',1)
em.label('advance_document_revision_store'); em.mov_ripmem_r64(bsyms['document_revision'],'rax'); em.emit(0xC3)

em.label('mark_document_saved')
em.mov_r64_ripmem('rax',bsyms['document_revision']); em.mov_ripmem_r64(bsyms['saved_revision'],'rax'); em.emit(0xC3)

em.label('is_document_dirty')
em.mov_r64_ripmem('rax',bsyms['document_revision']); em.mov_r64_ripmem('r10',bsyms['saved_revision']); em.cmp_r64_r64('rax','r10'); em.jcc(0x85,'is_document_dirty_true'); em.xor32('rax'); em.emit(0xC3)
em.label('is_document_dirty_true'); em.xor32('rax'); em.add_r32_imm8('rax',1); em.emit(0xC3)

# validate_wide_no_nul(rcx=buffer, edx=count) -> eax 1 valid, 0 embedded NUL.
# The terminating NUL is outside count and is therefore accepted.
em.label('validate_wide_no_nul'); em.xor32('r8')
em.label('validate_wide_loop'); em.cmp_r32_r32('r8','rdx'); em.jcc(0x83,'validate_wide_ok'); em.movzx_r32_word_index2('rax','rcx','r8'); em.test32('rax'); em.jcc(0x84,'validate_wide_bad'); em.add_r32_imm8('r8',1); em.jmp('validate_wide_loop')
em.label('validate_wide_ok'); em.mov_r32_imm('rax',1); em.emit(0xC3)
em.label('validate_wide_bad'); em.xor32('rax'); em.emit(0xC3)

if OPEN_READ_INJECTION_MODE != 'release':
    em.label('injected_ReadFile')
    em.mov_r32_ripmem('rax',bsyms['inject_read_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_read_call_count'],'rax')
    if OPEN_READ_INJECTION_MODE == 'zero_success':
        em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.add_r32_imm8('rax',1); em.emit(0xC3)
    elif OPEN_READ_INJECTION_MODE == 'fail_first':
        em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.emit(0xC3)
    elif OPEN_READ_INJECTION_MODE == 'late_failure':
        em.cmp_r32_imm('rax',1); em.jcc(0x84,'injected_read_short'); em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.emit(0xC3)
    if OPEN_READ_INJECTION_MODE in {'short_then_complete', 'late_failure'}:
        em.label('injected_read_short'); em.cmp_r32_imm('r8',7); em.jcc(0x86,'injected_read_real'); em.mov_r32_imm('r8',7)
        em.label('injected_read_real'); em.emit(0x48,0x83,0xEC,0x28); em.mov_mrsp_imm32(0x20,0,qword=True); em.call_iat('ReadFile'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if OUTLINE_ALLOC_INJECTED:
    em.label('injected_OutlineVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_outline_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_outline_alloc_call_count'],'rax')
    _outline_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'fail_first' else 2
    em.cmp_r32_imm('rax',_outline_fail_ordinal); em.jcc(0x85,'injected_outline_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_outline_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if STYLE_ALLOC_INJECTED:
    em.label('injected_StyleVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_style_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_style_alloc_call_count'],'rax')
    _style_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'style_fail_first' else 2
    em.cmp_r32_imm('rax',_style_fail_ordinal); em.jcc(0x85,'injected_style_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_style_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if RENDER_ALLOC_INJECTED:
    em.label('injected_RenderVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_render_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_render_alloc_call_count'],'rax')
    _render_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'render_fail_first' else 2
    em.cmp_r32_imm('rax',_render_fail_ordinal); em.jcc(0x85,'injected_render_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_render_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if DOCUMENT_ALLOC_INJECTED:
    em.label('injected_DocumentVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_document_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_document_alloc_call_count'],'rax')
    _document_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'document_fail_first' else 2
    em.cmp_r32_imm('rax',_document_fail_ordinal); em.jcc(0x85,'injected_document_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_document_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if WIDE_ALLOC_INJECTED:
    em.label('injected_WideVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_wide_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_wide_alloc_call_count'],'rax')
    _wide_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'wide_fail_first' else 2
    em.cmp_r32_imm('rax',_wide_fail_ordinal); em.jcc(0x85,'injected_wide_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_wide_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if BYTE_ALLOC_INJECTED:
    em.label('injected_ByteVirtualAlloc')
    em.mov_r32_ripmem('rax',bsyms['inject_byte_alloc_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_byte_alloc_call_count'],'rax')
    _byte_fail_ordinal = 1 if ARENA_ALLOC_INJECTION_MODE == 'byte_fail_first' else 2
    em.cmp_r32_imm('rax',_byte_fail_ordinal); em.jcc(0x85,'injected_byte_alloc_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_byte_alloc_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('VirtualAlloc'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if WRITE_CALL_INJECTED:
    em.label('injected_WriteFile')
    em.mov_r32_ripmem('rax',bsyms['inject_write_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_write_call_count'],'rax')
    if WRITE_INJECTION_MODE == 'zero_success':
        em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.add_r32_imm8('rax',1); em.emit(0xC3)
    elif WRITE_INJECTION_MODE == 'fail_first':
        em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.emit(0xC3)
    elif WRITE_INJECTION_MODE == 'late_failure':
        em.cmp_r32_imm('rax',1); em.jcc(0x84,'injected_write_short'); em.xor32('rax'); em.mov_ptr_r32('r9','rax'); em.emit(0xC3)
    if WRITE_INJECTION_MODE in {'short_then_complete', 'late_failure'}:
        em.label('injected_write_short'); em.cmp_r32_imm('r8',7); em.jcc(0x86,'injected_write_real'); em.mov_r32_imm('r8',7)
        em.label('injected_write_real'); em.emit(0x48,0x83,0xEC,0x28); em.mov_mrsp_imm32(0x20,0,qword=True); em.call_iat('WriteFile'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

if WRITE_INJECTION_MODE == 'flush_failure':
    em.label('injected_FlushFileBuffers')
    em.mov_r32_ripmem('rax',bsyms['inject_flush_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_flush_call_count'],'rax'); em.xor32('rax'); em.emit(0xC3)

if WRITE_INJECTION_MODE == 'replace_failure':
    em.label('injected_MoveFileExW')
    em.mov_r32_ripmem('rax',bsyms['inject_replace_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_replace_call_count'],'rax'); em.xor32('rax'); em.emit(0xC3)

if WRITE_INJECTION_MODE == 'create_failure':
    em.label('injected_CreateFileW')
    em.mov_r32_ripmem('rax',bsyms['inject_create_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_create_call_count'],'rax'); em.mov_r32_imm('rax',0xFFFFFFFF); em.emit(0x48,0x98); em.emit(0xC3)

if WRITE_INJECTION_MODE == 'close_failure':
    em.label('injected_CloseHandle')
    em.mov_r32_ripmem('rax',bsyms['inject_close_call_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['inject_close_call_count'],'rax'); em.cmp_r32_imm('rax',1); em.jcc(0x85,'injected_close_real'); em.xor32('rax'); em.emit(0xC3)
    em.label('injected_close_real'); em.emit(0x48,0x83,0xEC,0x28); em.call_iat('CloseHandle'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('commit_clean_document')
em.emit(0x48,0x83,0xEC,0x28)
em.call_label('advance_document_revision'); em.call_label('mark_document_saved')
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# detect_preferred_eol(rcx=UTF-16 text, edx=length): first terminator wins;
# documents without a terminator use the new-document CRLF default.
em.label('detect_preferred_eol')
em.xor32('r8')
em.label('detect_eol_loop')
em.cmp_r32_r32('r8','rdx'); em.jcc(0x83,'detect_eol_crlf')
em.movzx_r32_word_index2('r9','rcx','r8'); em.cmp_r32_imm('r9',0x0A); em.jcc(0x84,'detect_eol_lf')
em.cmp_r32_imm('r9',0x0D); em.jcc(0x85,'detect_eol_next')
em.mov_r32_r32('r10','r8'); em.add_r32_imm8('r10',1); em.cmp_r32_r32('r10','rdx'); em.jcc(0x83,'detect_eol_cr')
em.movzx_r32_word_index2('r9','rcx','r10'); em.cmp_r32_imm('r9',0x0A); em.jcc(0x84,'detect_eol_crlf'); em.jmp('detect_eol_cr')
em.label('detect_eol_next'); em.add_r32_imm8('r8',1); em.jmp('detect_eol_loop')
em.label('detect_eol_lf'); em.mov_r32_imm('rax',1); em.emit(0xC3)
em.label('detect_eol_cr'); em.mov_r32_imm('rax',2); em.emit(0xC3)
em.label('detect_eol_crlf'); em.xor32('rax'); em.emit(0xC3)

# Return the exact normalized UTF-16 length without touching active document state.
em.label('candidate_normalized_length')
em.xor32('rax'); em.xor32('rdx')
em.label('candidate_len_loop')
em.movzx_r32_word_index2('r8','rcx','rdx'); em.test32('r8'); em.jcc(0x84,'candidate_len_done')
em.add_r32_imm8('rdx',1); em.add_r32_imm8('rax',1); em.cmp_r32_imm('r8',0x0D); em.jcc(0x84,'candidate_len_cr'); em.cmp_r32_imm('r8',0x0A); em.jcc(0x85,'candidate_len_loop'); em.add_r32_imm8('rax',1); em.jmp('candidate_len_loop')
em.label('candidate_len_cr'); em.movzx_r32_word_index2('r8','rcx','rdx'); em.cmp_r32_imm('r8',0x0A); em.jcc(0x85,'candidate_len_cr_add'); em.add_r32_imm8('rdx',1)
em.label('candidate_len_cr_add'); em.add_r32_imm8('rax',1); em.jmp('candidate_len_loop')
em.label('candidate_len_done'); em.emit(0xC3)

# normalize_to_document_model(rcx = NUL-terminated UTF-16 source): normalize CRLF/LF/CR -> CRLF.
em.label('normalize_to_document_model')
em.emit(0x56); em.emit(0x57); em.emit(0x41,0x54); em.emit(0x41,0x55)
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('rsi','rcx'); em.mov_r64_ripmem('rdi',bsyms['document_model']); em.xor32('r12'); em.xor32('r13')
em.label('doc_norm_loop')
em.movzx_r32_word_index2('rax','rsi','r12'); em.test32('rax'); em.jcc(0x84,'doc_norm_done')
# 越界检查不得破坏 rax：它保存着刚从源读出的字符。
em.mov_r32_ripmem('rdx',bsyms['document_capacity']); em.sub_r32_imm8('rdx',3); em.cmp_r32_r32('r13','rdx'); em.jcc(0x83,'doc_norm_done')
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

# DocumentModel is canonical CRLF. Produce UTF-16 scratch using preferred_eol:
# 0 keeps CRLF, 1 writes LF, 2 writes CR. Returns output UTF-16 length in eax.
em.label('serialize_preferred_eol')
em.mov_r64_ripmem('rcx',bsyms['document_model']); em.mov_r64_ripmem('rdx',bsyms['widebuf']); em.mov_r32_ripmem('r11',bsyms['eol_state']); em.mov_r32_ripmem('r10',bsyms['document_len']); em.xor32('r8'); em.xor32('r9')
em.label('serialize_eol_loop'); em.cmp_r32_r32('r8','r10'); em.jcc(0x83,'serialize_eol_done'); em.movzx_r32_word_index2('rax','rcx','r8')
em.test32('r11'); em.jcc(0x84,'serialize_eol_copy'); em.cmp_r32_imm('rax',0x0D); em.jcc(0x85,'serialize_eol_copy')
em.cmp_r32_imm('r11',1); em.jcc(0x84,'serialize_eol_emit_lf'); em.mov_r32_imm('rax',0x0D); em.jmp('serialize_eol_emit')
em.label('serialize_eol_emit_lf'); em.mov_r32_imm('rax',0x0A)
em.label('serialize_eol_emit'); em.mov_word_index2_reg('rdx','r9','rax'); em.add_r32_imm8('r9',1); em.add_r32_imm8('r8',2); em.jmp('serialize_eol_loop')
em.label('serialize_eol_copy'); em.mov_word_index2_reg('rdx','r9','rax'); em.add_r32_imm8('r9',1); em.add_r32_imm8('r8',1); em.jmp('serialize_eol_loop')
em.label('serialize_eol_done'); em.mov_word_index2_zero('rdx','r9'); em.mov_r32_r32('rax','r9'); em.emit(0xC3)

# Source Editor -> Document Model. Standard multiline EDIT returns canonical CRLF.
em.label('sync_model_from_editor')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.test64('rcx'); em.jcc(0x84,'sync_model_ret')
em.call_iat('GetWindowTextLengthW'); em.cmp_r32_imm('rax',WIDE_CHARS-1); em.jcc(0x87,'sync_model_ret')
# V8.6：先把文档 arena 提交到本次编辑器长度的容量，再读取文本。分配失败时
# 不能只更新一半状态，因此恢复编辑器显示并保留旧模型。
em.mov_ripmem_r32(bsyms['sync_text_len'],'rax')
em.mov_r32_r32('rcx','rax'); em.add_r32_imm8('rcx',1); em.call_label('ensure_document_arena')
em.test32('rax'); em.jcc(0x84,'sync_model_rollback')
em.mov_r32_ripmem('r8',bsyms['sync_text_len']); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r64_ripmem('rdx',bsyms['document_model']); em.call_iat('GetWindowTextW')
em.mov_ripmem_r32(bsyms['document_len'],'rax')
em.label('sync_model_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)
em.label('sync_model_rollback'); em.call_label('load_model_into_editor'); em.jmp('sync_model_ret')

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
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r64_ripmem('rdx',bsyms['document_model']); em.call_iat('SetWindowTextW')
# A newly opened document starts at its true beginning.
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B1); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
# V8.5.0：无条件显示源码表面。契约：调用方（cmd_new/cmd_open）必须先经
# set_view_mode(0) 进入 Source 模式——视图状态由唯一写者管理，装载例程
# 不再读 preview_flag 自行决定可见性（调用点均为打开/新建，恒为 Source）。
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',5); em.call_iat('ShowWindow')
em.label('load_model_invalidate'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.label('load_model_unsuppress'); em.mov_ripmem_imm32(bsyms['suppress_edit_change'],0)
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# Helper: append a rich-format span. Inputs: r8d=start, r9d=end, r10d=style.
# V8.6 Phase E：三张样式表由动态 arena 提供，写入一律经 arena 指针。
# 没有容量（未分配或注入失败）时静默跳过：不会越界，也不会破坏文档状态。
em.label('add_style')
em.mov_r32_ripmem('r11',bsyms['style_count']); em.mov_r32_ripmem('rax',bsyms['style_capacity']); em.cmp_r32_r32('r11','rax'); em.jcc(0x83,'add_style_ret')
em.mov_r32_r32('rax','r11'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.mov_r64_ripmem('rcx',bsyms['style_start']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r8')
em.mov_r64_ripmem('rcx',bsyms['style_end']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r9')
em.mov_r64_ripmem('rcx',bsyms['style_type']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r10')
em.add_r32_imm8('r11',1); em.mov_ripmem_r32(bsyms['style_count'],'r11')
em.label('add_style_ret'); em.emit(0xC3)

# Ensure one contiguous style-span arena: [start][end][type] dwords per entry.
# Capacity is derived from the requested canonical document length in ecx
# (every recorded span consumes at least two source characters) and never
# shrinks during the process lifetime. Returns 1 on success, 0 on failure.
em.label('ensure_style_arena')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_r32('r13','rcx'); em.shr_r32_imm8('r13',STYLE_SPAN_DIVISOR); em.add_r32_imm8('r13',16); em.cmp_r32_imm('r13',STYLE_MIN_ENTRIES); em.jcc(0x83,'style_need_ready'); em.mov_r32_imm('r13',STYLE_MIN_ENTRIES)
em.label('style_need_ready'); em.mov_r32_ripmem('rax',bsyms['style_capacity']); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,'style_arena_ok')
em.mov_r32_r32('r14','r13'); em.shl_r32_imm8('r14',2); em.mov_r32_r32('rdx','r14'); em.mov_r32_r32('rax','r14'); em.add_r32_r32('rdx','rax'); em.add_r32_r32('rdx','rax')
em.xor32('rcx'); em.mov_r32_imm('r8',0x3000); em.mov_r32_imm('r9',4)
if STYLE_ALLOC_INJECTED: em.call_label('injected_StyleVirtualAlloc')
else: em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'style_arena_fail'); em.mov_r64_r64('r15','rax')
em.mov_r64_ripmem('r12',bsyms['style_start']); em.test64('r12'); em.jcc(0x84,'style_arena_commit'); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.mov_r32_imm('r8',0x8000); em.call_iat('VirtualFree')
em.label('style_arena_commit'); em.mov_ripmem_r64(bsyms['style_start'],'r15'); em.mov_r64_r64('rax','r15'); em.add_r64_r64('rax','r14'); em.mov_ripmem_r64(bsyms['style_end'],'rax'); em.add_r64_r64('rax','r14'); em.mov_ripmem_r64(bsyms['style_type'],'rax'); em.mov_ripmem_r32(bsyms['style_capacity'],'r13')
em.label('style_arena_ok'); em.mov_r32_imm('rax',1); em.jmp('style_arena_ret')
em.label('style_arena_fail'); em.xor32('rax')
em.label('style_arena_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Ensure one contiguous Outline arena: [srcpos][renderpos][level]. Capacity is
# derived from the requested canonical document length in ecx (minimum heading representation is four
# UTF-16 units) and never shrinks during the process lifetime.
em.label('ensure_outline_arena')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_r32('r13','rcx'); em.shr_r32_imm8('r13',2); em.add_r32_imm8('r13',1); em.cmp_r32_imm('r13',4096); em.jcc(0x83,'outline_need_ready'); em.mov_r32_imm('r13',4096)
em.label('outline_need_ready'); em.mov_r32_ripmem('rax',bsyms['outline_capacity']); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,'outline_arena_ok')
em.mov_r32_r32('r14','r13'); em.shl_r32_imm8('r14',2); em.mov_r32_r32('rdx','r14'); em.mov_r32_r32('rax','r14'); em.add_r32_r32('rdx','rax'); em.add_r32_r32('rdx','rax')
em.xor32('rcx'); em.mov_r32_imm('r8',0x3000); em.mov_r32_imm('r9',4)
if OUTLINE_ALLOC_INJECTED: em.call_label('injected_OutlineVirtualAlloc')
else: em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'outline_arena_fail'); em.mov_r64_r64('r15','rax')
em.mov_r64_ripmem('r12',bsyms['outline_srcpos']); em.test64('r12'); em.jcc(0x84,'outline_arena_commit'); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.mov_r32_imm('r8',0x8000); em.call_iat('VirtualFree')
em.label('outline_arena_commit'); em.mov_ripmem_r64(bsyms['outline_srcpos'],'r15'); em.mov_r64_r64('rax','r15'); em.add_r64_r64('rax','r14'); em.mov_ripmem_r64(bsyms['outline_renderpos'],'rax'); em.add_r64_r64('rax','r14'); em.mov_ripmem_r64(bsyms['outline_level'],'rax'); em.mov_ripmem_r32(bsyms['outline_capacity'],'r13')
em.label('outline_arena_ok'); em.mov_r32_imm('rax',1); em.jmp('outline_arena_ret')
em.label('outline_arena_fail'); em.xor32('rax')
em.label('outline_arena_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Ensure one contiguous render arena: [position map 4 bytes/unit][render text 2 bytes/unit].
# The renderer never emits more units than the canonical document contains, so the
# requested capacity is max(4096, canonical_length + 1) and never shrinks during the
# process lifetime. Returns 1 on success, 0 on failure; the previous arena stays
# published until the new one is complete.
em.label('ensure_render_arena')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_r32('r13','rcx'); em.add_r32_imm8('r13',1); em.cmp_r32_imm('r13',4096); em.jcc(0x83,'render_need_ready'); em.mov_r32_imm('r13',4096)
em.label('render_need_ready'); em.mov_r32_ripmem('rax',bsyms['render_arena_capacity']); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,'render_arena_ok')
em.mov_r32_r32('r14','r13'); em.shl_r32_imm8('r14',2); em.mov_r32_r32('rdx','r14'); em.mov_r32_r32('rax','r13'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rdx','rax')
em.xor32('rcx'); em.mov_r32_imm('r8',0x3000); em.mov_r32_imm('r9',4)
if RENDER_ALLOC_INJECTED: em.call_label('injected_RenderVirtualAlloc')
else: em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'render_arena_fail'); em.mov_r64_r64('r15','rax')
em.mov_r64_ripmem('r12',bsyms['render_srcmap']); em.test64('r12'); em.jcc(0x84,'render_arena_commit'); em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.mov_r32_imm('r8',0x8000); em.call_iat('VirtualFree')
em.label('render_arena_commit'); em.mov_ripmem_r64(bsyms['render_srcmap'],'r15'); em.mov_r64_r64('rax','r15'); em.add_r64_r64('rax','r14'); em.mov_ripmem_r64(bsyms['previewbuf'],'rax'); em.mov_ripmem_r32(bsyms['render_arena_capacity'],'r13')
em.label('render_arena_ok'); em.mov_r32_imm('rax',1); em.jmp('render_arena_ret')
em.label('render_arena_fail'); em.xor32('rax')
em.label('render_arena_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Ensure the document arena can hold ecx units (including the terminator).
# The policy bound WIDE_CHARS is reserved once as address space; physical pages
# are committed in 512 KiB unit blocks and only as content actually grows, so a
# small document does not reserve megabytes of committed memory. The editor text
# limit and the normalization bound keep using WIDE_CHARS, so visible behaviour
# is unchanged. Returns 1 on success, 0 on failure with no state change.
em.label('ensure_document_arena')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_r32('r13','rcx'); em.add_r32_imm8('r13',1)
em.mov_r32_imm('rax',DOC_COMMIT_CHUNK-1); em.add_r32_r32('r13','rax'); em.and_r32_imm('r13',~(DOC_COMMIT_CHUNK-1) & 0xFFFFFFFF)
em.cmp_r32_imm('r13',DOC_COMMIT_CHUNK); em.jcc(0x83,'doc_need_ready'); em.mov_r32_imm('r13',DOC_COMMIT_CHUNK)
em.label('doc_need_ready'); em.cmp_r32_imm('r13',WIDE_CHARS); em.jcc(0x87,'doc_arena_fail')
em.mov_r32_ripmem('rax',bsyms['document_capacity']); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,'doc_arena_ok')
em.mov_r64_ripmem('r15',bsyms['document_model']); em.test64('r15'); em.jcc(0x85,'doc_arena_commit')
em.xor32('rcx'); em.mov_r32_imm('rdx',WIDE_CHARS*2); em.mov_r32_imm('r8',0x2000); em.mov_r32_imm('r9',4); em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'doc_arena_fail'); em.mov_r64_r64('r15','rax'); em.mov_ripmem_r64(bsyms['document_model'],'r15'); em.mov_ripmem_imm32(bsyms['document_reserved'],WIDE_CHARS)
em.label('doc_arena_commit')
em.mov_r32_ripmem('r12',bsyms['document_capacity']); em.mov_r32_r32('r14','r13')
em.shl_r32_imm8('r12',1); em.shl_r32_imm8('r14',1)
em.mov_r32_r32('rdx','r14'); em.sub_r32_r32('rdx','r12')
em.mov_r64_r64('rcx','r15'); em.add_r64_r64('rcx','r12'); em.mov_r32_imm('r8',0x1000); em.mov_r32_imm('r9',4)
if DOCUMENT_ALLOC_INJECTED: em.call_label('injected_DocumentVirtualAlloc')
else: em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'doc_arena_fail'); em.mov_ripmem_r32(bsyms['document_capacity'],'r13')
em.label('doc_arena_ok'); em.mov_r32_imm('rax',1); em.jmp('doc_arena_ret')
em.label('doc_arena_fail'); em.xor32('rax')
em.label('doc_arena_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# V8.6 Phase E：解码/编码 scratch arena。两者结构相同——容量按 64 KiB 块向上
# 取整、只增不减、失败时不发布新指针——所以由同一个模板生成。
def emit_ensure_scratch_arena(entry, ptr_sym, cap_sym, chunk, unit_scale,
                              inject_label=None):
    em.label(entry)
    em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
    em.mov_r32_r32('r13','rcx'); em.add_r32_imm8('r13',1)
    em.mov_r32_imm('rax',chunk-1); em.add_r32_r32('r13','rax'); em.and_r32_imm('r13',~(chunk-1) & 0xFFFFFFFF)
    em.cmp_r32_imm('r13',chunk); em.jcc(0x83,entry+'_ready'); em.mov_r32_imm('r13',chunk)
    em.label(entry+'_ready')
    em.mov_r32_ripmem('rax',bsyms[cap_sym]); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,entry+'_ok')
    em.mov_r32_r32('r14','r13')
    if unit_scale == 2: em.shl_r32_imm8('r14',1)
    em.xor32('rcx'); em.mov_r32_r32('rdx','r14'); em.mov_r32_imm('r8',0x3000); em.mov_r32_imm('r9',4)
    if inject_label: em.call_label(inject_label)
    else: em.call_iat('VirtualAlloc')
    em.test64('rax'); em.jcc(0x84,entry+'_fail'); em.mov_r64_r64('r15','rax')
    em.mov_r64_ripmem('r12',bsyms[ptr_sym]); em.test64('r12'); em.jcc(0x84,entry+'_commit')
    em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.mov_r32_imm('r8',0x8000); em.call_iat('VirtualFree')
    em.label(entry+'_commit'); em.mov_ripmem_r64(bsyms[ptr_sym],'r15'); em.mov_ripmem_r32(bsyms[cap_sym],'r13')
    em.label(entry+'_ok'); em.mov_r32_imm('rax',1); em.jmp(entry+'_ret')
    em.label(entry+'_fail'); em.xor32('rax')
    em.label(entry+'_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

emit_ensure_scratch_arena('ensure_wide_arena','widebuf','wide_capacity',WIDE_CHUNK,2,
                          'injected_WideVirtualAlloc' if WIDE_ALLOC_INJECTED else None)
emit_ensure_scratch_arena('ensure_byte_arena','bytebuf','byte_capacity',BYTE_CHUNK,1,
                          'injected_ByteVirtualAlloc' if BYTE_ALLOC_INJECTED else None)

# ---------------- V8.6 切片 1：workspace 目录枚举 ----------------
# Ensure the workspace entry arena can hold ecx entries (stride WS_STRIDE).
# Same shape as the other arenas: 64-entry blocks, never shrinks, publishes the
# pointer only after a successful allocation.
em.label('ensure_workspace_arena')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_r32('r13','rcx'); em.add_r32_imm8('r13',1)                    # headroom for the insert
em.add_r32_imm8('r13',63); em.and_r32_imm('r13',~63 & 0xFFFFFFFF)
em.cmp_r32_imm('r13',64); em.jcc(0x83,'ws_need_ready'); em.mov_r32_imm('r13',64)
em.label('ws_need_ready'); em.mov_r32_ripmem('rax',bsyms['ws_capacity']); em.cmp_r32_r32('rax','r13'); em.jcc(0x83,'ws_arena_ok')
em.mov_r32_r32('r14','r13'); em.shl_r32_imm8('r14',5)                    # r14 = need * 32
em.mov_r32_r32('rax','r13'); em.shl_r32_imm8('rax',9)                    # rax = need * 512
em.add_r32_r32('r14','rax')                                             # need * 544
em.xor32('rcx'); em.mov_r32_r32('rdx','r14'); em.mov_r32_imm('r8',0x3000); em.mov_r32_imm('r9',4)
em.call_iat('VirtualAlloc')
em.test64('rax'); em.jcc(0x84,'ws_arena_fail'); em.mov_r64_r64('r15','rax')
em.mov_r64_ripmem('r12',bsyms['ws_entries']); em.test64('r12'); em.jcc(0x84,'ws_arena_commit')
# Growing the table must keep the entries already published: copy count * 68
# eight-byte blocks (count * WS_STRIDE bytes) before releasing the old block.
em.mov_r32_ripmem('r14',bsyms['ws_entry_count'])
em.mov_r32_r32('rax','r14'); em.shl_r32_imm8('rax',6)                    # count * 64
em.mov_r32_r32('r8','r14'); em.shl_r32_imm8('r8',2)                      # count * 4
em.add_r32_r32('rax','r8')                                              # count * 68
em.mov_r64_r64('r8','r12'); em.mov_r64_r64('r9','r15')
em.label('ws_arena_copy')
em.test32('rax'); em.jcc(0x84,'ws_arena_copy_done')
em.mov_r64_mreg('r10','r8',0); em.mov_mreg_reg64('r9',0,'r10')
em.add_r64_imm8('r8',8); em.add_r64_imm8('r9',8); em.sub_r32_imm8('rax',1)
em.jmp('ws_arena_copy')
em.label('ws_arena_copy_done')
em.mov_r64_r64('rcx','r12'); em.xor32('rdx'); em.mov_r32_imm('r8',0x8000); em.call_iat('VirtualFree')
em.label('ws_arena_commit'); em.mov_ripmem_r64(bsyms['ws_entries'],'r15'); em.mov_ripmem_r32(bsyms['ws_capacity'],'r13')
em.label('ws_arena_ok'); em.mov_r32_imm('rax',1); em.jmp('ws_arena_ret')
em.label('ws_arena_fail'); em.xor32('rax')
em.label('ws_arena_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# edx = entry index -> rax = entry pointer. Leaf: only rax/rdx/rcx scratch.
def emit_ws_entry_ptr():
    em.mov_r32_r32('rax','rdx')
    em.mov_r32_r32('rcx','rax'); em.shl_r32_imm8('rcx',9)                # index * 512
    em.shl_r32_imm8('rax',5)                                             # index * 32
    em.add_r64_r64('rax','rcx')                                          # index * 544
    em.mov_r64_ripmem('rcx',bsyms['ws_entries']); em.add_r64_r64('rax','rcx')

# rcx = name -> eax = 1 when it ends in .md / .markdown / .txt (ASCII, case-insensitive)
em.label('ws_suffix_match')
em.xor32('rdx')                                                          # length
em.label('ws_len_loop'); em.movzx_r32_word_index2('r8','rcx','rdx'); em.test32('r8'); em.jcc(0x84,'ws_len_done')
em.add_r32_imm8('rdx',1); em.cmp_r32_imm('rdx',WS_NAME_UNITS); em.jcc(0x82,'ws_len_loop')
em.xor32('rax'); em.emit(0xC3)
em.label('ws_len_done')
def suffix_case(chars, fail_label):
    """Compare the tail of the name (length in edx) against an ASCII suffix."""
    n = len(chars)
    em.cmp_r32_imm('rdx',n); em.jcc(0x82,fail_label)
    for i, ch in enumerate(chars):
        em.mov_r32_r32('r9','rdx'); em.sub_r32_imm8('r9',n - i)
        em.movzx_r32_word_index2('r8','rcx','r9')
        em.or_r32_imm('r8',0x20)
        em.cmp_r32_imm('r8',ord(ch)); em.jcc(0x85,fail_label)
for _index, _suffix in enumerate(('.md', '.txt', '.markdown')):
    _fail = 'ws_suf_next_%d' % _index
    suffix_case(_suffix, _fail)
    em.mov_r32_imm('rax',1); em.emit(0xC3)
    em.label(_fail)
em.xor32('rax'); em.emit(0xC3)

# rcx = nameA, rdx = nameB -> eax = -1 / 0 / +1 (case-insensitive ordinal).
em.label('ws_name_cmp')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('r8','rdx'); em.mov_r32_imm('rdx',0xFFFFFFFF); em.mov_r32_imm('r9',0xFFFFFFFF)
em.mov_mrsp_imm32(0x20,1)
em.call_iat('CompareStringOrdinal')
em.sub_r32_imm8('rax',2)                     # 1/2/3 -> -1/0/+1
em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# rcx = destination entry, rdx = source entry: copy one WS_STRIDE entry.
em.label('ws_copy_entry')
em.mov_r32_imm('rax',WS_STRIDE // 8)
em.label('ws_copy_loop')
em.mov_r64_mreg('r8','rdx',0); em.mov_mreg_r64('rcx',0,'r8')
em.add_r64_imm8('rdx',8); em.add_r64_imm8('rcx',8)
em.sub_r32_imm8('rax',1); em.jcc(0x85,'ws_copy_loop')
em.emit(0xC3)

# rcx = new name, edx = new dwFileAttributes -> eax = insertion index.
# Directories come first, then names in case-insensitive ordinal order.
em.label('ws_find_insert_index')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('r12','rcx')
em.mov_r32_r32('r13','rdx'); em.and_r32_imm('r13',0x10); em.shr_r32_imm8('r13',4)
em.mov_r32_ripmem('r14',bsyms['ws_entry_count']); em.xor32('r15')
em.label('ws_fii_scan'); em.cmp_r32_r32('r15','r14'); em.jcc(0x83,'ws_fii_done')
em.mov_r32_r32('rdx','r15'); emit_ws_entry_ptr()
em.mov_r32_mreg('r10','rax',WS_OFF_ATTRIBUTES)
em.and_r32_imm('r10',0x10); em.shr_r32_imm8('r10',4)
em.cmp_r32_r32('r13','r10'); em.jcc(0x84,'ws_fii_same_kind')
em.test32('r13'); em.jcc(0x85,'ws_fii_done')          # new entry is a directory
em.jmp('ws_fii_next')
em.label('ws_fii_same_kind')
em.mov_r32_r32('rdx','r15'); emit_ws_entry_ptr(); em.mov_r64_r64('rdx','rax')
em.mov_r64_r64('rcx','r12')          # after the pointer computation: it clobbers rcx
em.call_label('ws_name_cmp'); em.test32('rax'); em.jcc(0x88,'ws_fii_done')
em.label('ws_fii_next'); em.add_r32_imm8('r15',1); em.jmp('ws_fii_scan')
em.label('ws_fii_done'); em.mov_r32_r32('rax','r15')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# ecx = first index to move: shift entries [ecx, count) one slot to the right.
em.label('ws_shift_right')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_r32('r12','rcx'); em.mov_r32_ripmem('r13',bsyms['ws_entry_count'])
em.label('ws_shift_loop'); em.cmp_r32_r32('r13','r12'); em.jcc(0x86,'ws_shift_done')
em.mov_r32_r32('rdx','r13'); emit_ws_entry_ptr(); em.mov_mrsp_reg64(0x20,'rax')
em.mov_r32_r32('rdx','r13'); em.sub_r32_imm8('rdx',1); emit_ws_entry_ptr(); em.mov_r64_r64('rdx','rax')
em.mov_r64_mrsp('rcx',0x20)
em.call_label('ws_copy_entry'); em.sub_r32_imm8('r13',1); em.jmp('ws_shift_loop')
em.label('ws_shift_done'); em.add_r64_imm8('rsp',0x38); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# rcx = WIN32_FIND_DATAW pointer -> eax = 1 when the entry was added, 0 when the
# arena could not grow (the caller reports the failure; the document is
# untouched). The entry copies name, attributes, directory flag, size and last
# write time so the model owns its data instead of the loader's scratch buffer.
em.label('workspace_insert')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('r15','rcx')                                     # FIND_DATA (SIB-free base)
em.mov_r32_ripmem('r14',bsyms['ws_entry_count']); em.mov_r32_r32('rcx','r14'); em.add_r32_imm8('rcx',1)
em.call_label('ensure_workspace_arena'); em.test32('rax'); em.jcc(0x84,'ws_ins_fail')
em.mov_r64_r64('rcx','r15'); em.add_r64_imm8('rcx',44)          # cFileName
em.mov_r32_mreg('rdx','r15',0)                                  # dwFileAttributes
em.call_label('ws_find_insert_index')
em.mov_r32_r32('r14','rax'); em.mov_r32_r32('rcx','r14'); em.call_label('ws_shift_right')
em.mov_r32_r32('rdx','r14'); emit_ws_entry_ptr(); em.mov_r64_r64('r14','rax')   # r14 = new entry
em.mov_r64_r64('rcx','r14'); em.mov_r64_r64('rdx','r15'); em.add_r64_imm8('rdx',44); em.call_iat('lstrcpyW')
em.mov_r32_mreg('r8','r15',0); em.mov_mreg_reg32('r14',WS_OFF_ATTRIBUTES,'r8')
em.mov_r32_r32('r9','r8'); em.and_r32_imm('r9',0x10); em.shr_r32_imm8('r9',4)
em.mov_mreg_reg32('r14',WS_OFF_KIND,'r9')
em.mov_r32_mreg('r10','r15',32); em.mov_mreg_reg32('r14',WS_OFF_SIZE_LOW,'r10')    # nFileSizeLow
em.mov_r32_mreg('r10','r15',28); em.mov_mreg_reg32('r14',WS_OFF_SIZE_HIGH,'r10')   # nFileSizeHigh
em.mov_r64_mreg('r11','r15',20); em.mov_mreg_reg64('r14',WS_OFF_WRITE_TIME,'r11')
em.mov_r32_ripmem('rax',bsyms['ws_entry_count']); em.add_r32_imm8('rax',1); em.mov_ripmem_r32(bsyms['ws_entry_count'],'rax')
em.mov_r32_imm('rax',1); em.jmp('ws_ins_ret')
em.label('ws_ins_fail'); em.xor32('rax')
em.label('ws_ins_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Enumerate ws_current_path into the entry arena. Sets ws_error on failure and
# leaves the previous entries replaced by whatever was enumerated.
em.label('workspace_refresh')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_imm32(bsyms['ws_entry_count'],0); em.mov_ripmem_imm32(bsyms['ws_error'],0)
em.lea_rip('rcx',bsyms['ws_pattern']); em.lea_rip('rdx',bsyms['ws_current_path']); em.call_iat('lstrcpyW')
# ws_pattern currently holds the directory; append a separator when missing and
# then the wildcard so FindFirstFileW lists the directory's children.
em.lea_rip('rcx',bsyms['ws_pattern']); em.call_iat('lstrlenW'); em.mov_r32_r32('r12','rax')
em.lea_rip('rcx',bsyms['ws_pattern'])
em.test32('r12'); em.jcc(0x84,'ws_pat_star')                 # empty path: just "*"
em.mov_r32_r32('rax','r12'); em.sub_r32_imm8('rax',1)
em.movzx_r32_word_index2('rdx','rcx','rax'); em.cmp_r32_imm('rdx',0x5C); em.jcc(0x84,'ws_pat_star')
em.mov_word_index2_imm16('rcx','r12',0x5C); em.add_r32_imm8('r12',1)
em.label('ws_pat_star'); em.mov_word_index2_imm16('rcx','r12',0x2A); em.add_r32_imm8('r12',1); em.mov_word_index2_zero('rcx','r12')
em.lea_rip('rcx',bsyms['ws_pattern']); em.lea_rip('rdx',bsyms['ws_find_data']); em.call_iat('FindFirstFileW')
em.cmp_rax_neg1(); em.jcc(0x84,'ws_refresh_error')
em.mov_ripmem_r64(bsyms['ws_find_handle'],'rax')
em.label('ws_enum_loop')
# Entry name lives at FIND_DATA + 44 (cFileName). Skip "." and ".." outright.
em.lea_rip('r13',bsyms['ws_find_data']); em.add_r64_imm8('r13',44)
em.mov_r64_r64('rcx','r13'); em.movzx_eax_word_ptr('rcx'); em.cmp_r32_imm('rax',0x2E); em.jcc(0x85,'ws_enum_kind')
em.add_r64_imm8('rcx',2); em.movzx_eax_word_ptr('rcx')
em.test32('rax'); em.jcc(0x84,'ws_enum_next')
em.cmp_r32_imm('rax',0x2E); em.jcc(0x85,'ws_enum_kind')
em.add_r64_imm8('rcx',2); em.movzx_eax_word_ptr('rcx'); em.test32('rax'); em.jcc(0x84,'ws_enum_next')
em.label('ws_enum_kind')
em.mov_r32_ripmem('r14',bsyms['ws_find_data']); em.and_r32_imm('r14',0x10)   # FILE_ATTRIBUTE_DIRECTORY
em.test32('r14'); em.jcc(0x85,'ws_enum_add')
em.mov_r64_r64('rcx','r13'); em.call_label('ws_suffix_match'); em.test32('rax'); em.jcc(0x84,'ws_enum_next')
em.label('ws_enum_add')
em.lea_rip('rcx',bsyms['ws_find_data']); em.call_label('workspace_insert')
em.test32('rax'); em.jcc(0x84,'ws_refresh_nomem')
em.label('ws_enum_next')
em.mov_r64_ripmem('rcx',bsyms['ws_find_handle']); em.lea_rip('rdx',bsyms['ws_find_data']); em.call_iat('FindNextFileW')
em.test32('rax'); em.jcc(0x85,'ws_enum_loop')
em.jmp('ws_refresh_close')
em.label('ws_refresh_nomem')                                                 # ERROR_NOT_ENOUGH_MEMORY:
em.mov_ripmem_imm32(bsyms['ws_entry_count'],0)                               # report an empty list, not a
em.mov_ripmem_imm32(bsyms['ws_error'],8)                                     # half-enumerated one
em.jmp('ws_refresh_close')
em.label('ws_refresh_error'); em.call_iat('GetLastError'); em.mov_ripmem_r32(bsyms['ws_error'],'rax'); em.jmp('ws_refresh_ret')
em.label('ws_refresh_close')
em.mov_r64_ripmem('rcx',bsyms['ws_find_handle']); em.call_iat('FindClose')
em.label('ws_refresh_ret')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# rcx = directory path: remember it as the root and the current directory, then
# enumerate it. No UI involvement yet - slice 1 is model only.
em.label('workspace_set_root')
em.emit(0x41,0x54); em.emit(0x48,0x83,0xEC,0x30)
em.mov_r64_r64('r12','rcx')
em.lea_rip('rcx',bsyms['ws_root_path']); em.mov_r64_r64('rdx','r12'); em.call_iat('lstrcpyW')
em.lea_rip('rcx',bsyms['ws_current_path']); em.mov_r64_r64('rdx','r12'); em.call_iat('lstrcpyW')
em.call_label('workspace_refresh')
# V8.6.1：文件面板始终存在，新的根目录枚举完成后立即刷新文件列表与状态栏。
em.call_label('rebuild_file_list')
em.call_label('update_status')
em.label('wsr_ret'); em.add_r64_imm8('rsp',0x30); em.emit(0x41,0x5C); em.emit(0xC3)

# V8.6 切片 2：用 workspace 条目重建 ListBox（文件模式）。复用同一个控件、
# 同一套滚动条几何、同一套主题刷子：布局、命中测试、滚轮、hover 与
# sync_outline_scrollbar 都不需要第二套实现。目录行追加反斜杠，配合
# owner-draw 的颜色分支提供不依赖新资源的行类型区分。
em.label('rebuild_file_list')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.test64('rcx'); em.jcc(0x84,'rfl_ret')
em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.mov_r32_imm('rdx',0x0184); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
# V8.6.1：文件列表有自己的 ListBox，不再借用大纲控件，因此大纲计数不受影响。
em.mov_r32_ripmem('r13',bsyms['ws_entry_count'])
em.mov_r64_ripmem('r14',bsyms['ws_entries'])
em.xor32('r12')
em.label('rfl_loop')
em.cmp_r32_r32('r12','r13'); em.jcc(0x83,'rfl_done')
em.test64('r14'); em.jcc(0x84,'rfl_done')
em.mov_r32_r32('rax','r12'); em.mov_r32_r32('rcx','r12')
em.shl_r32_imm8('rcx',9); em.shl_r32_imm8('rax',5); em.add_r32_r32('rax','rcx')
em.mov_r64_r64('r15','r14'); em.add_r64_r64('r15','rax')
em.lea_rip('rcx',bsyms['outline_titlebuf']); em.mov_r64_r64('rdx','r15'); em.call_iat('lstrcpyW')
em.mov_r32_mreg('r10','r15',WS_OFF_KIND); em.test32('r10'); em.jcc(0x84,'rfl_add')
em.lea_rip('rcx',bsyms['outline_titlebuf']); em.call_iat('lstrlenW')
em.lea_rip('rcx',bsyms['outline_titlebuf'])
em.mov_word_index2_imm16('rcx','rax',0x5C); em.add_r32_imm8('rax',1); em.mov_word_index2_zero('rcx','rax')
em.label('rfl_add')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.mov_r32_imm('rdx',0x0180); em.xor32('r8'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
em.add_r32_imm8('r12',1); em.jmp('rfl_loop')
em.label('rfl_done')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.call_label('sync_outline_scrollbar')
em.label('rfl_ret')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# V8.6.1：两个面板同时存在，因此"切换模式"退化为"刷新两个列表"；参数只是
# 记录最近聚焦的面板（供状态栏与后续的滚动路由使用）。
em.label('set_panel_mode')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_ripmem_r32(bsyms['panel_mode'],'rcx')
em.add_r64_imm8('rsp',0x28); em.jmp('refresh_panel_list')
em.label('spm_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# 重建两个列表：大纲来自文档，文件来自当前 workspace。
em.label('refresh_panel_list')
em.emit(0x48,0x83,0xEC,0x28)
em.call_label('update_preview')
em.call_label('rebuild_file_list')
em.label('rpl_ret'); em.call_label('sync_panel_menu'); em.call_label('update_status'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# View 菜单的勾选与 panel_mode 的唯一同步点。
em.label('sync_panel_menu')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.test64('rcx'); em.jcc(0x84,'spmm_ret')
em.mov_r32_ripmem('rax',bsyms['panel_mode']); em.test32('rax'); em.jcc(0x84,'spmm_outline')
em.mov_r32_imm('rdx',1308); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1309); em.xor32('r8'); em.call_iat('CheckMenuItem'); em.jmp('spmm_ret')
em.label('spmm_outline')
em.mov_r32_imm('rdx',1308); em.xor32('r8'); em.call_iat('CheckMenuItem')
em.mov_r64_ripmem('rcx',bsyms['hmenu_view']); em.mov_r32_imm('rdx',1309); em.mov_r32_imm('r8',0x8); em.call_iat('CheckMenuItem')
em.label('spmm_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('cmd_panel_files'); em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode'); em.jmp('msg_loop')
em.label('cmd_panel_outline'); em.xor32('rcx'); em.call_label('set_panel_mode'); em.jmp('msg_loop')

# ---------------- V8.6 切片 3：目录导航与从列表打开 ----------------
# rcx = 基路径, rdx = 条目名 -> rax = ws_path_buf 中的拼接结果。
# 分隔符只在缺失时补一个，空基路径不补。
em.label('ws_join_path')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_r64('r12','rcx'); em.mov_r64_r64('r13','rdx')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.mov_r64_r64('rdx','r12'); em.call_iat('lstrcpyW')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.call_iat('lstrlenW'); em.mov_r32_r32('r11','rax')
em.test32('r11'); em.jcc(0x84,'wjp_copy')
em.lea_rip('rcx',bsyms['ws_path_buf'])
em.mov_r32_r32('rax','r11'); em.sub_r32_imm8('rax',1)
em.movzx_r32_word_index2('r10','rcx','rax'); em.cmp_r32_imm('r10',0x5C); em.jcc(0x84,'wjp_copy')
em.mov_word_index2_imm16('rcx','r11',0x5C); em.add_r32_imm8('r11',1); em.mov_word_index2_zero('rcx','r11')
em.label('wjp_copy')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.mov_r32_r32('rdx','r11'); em.add_r32_r32('rdx','rdx'); em.add_r64_r64('rcx','rdx')
em.mov_r64_r64('rdx','r13'); em.call_iat('lstrcpyW')
em.lea_rip('rax',bsyms['ws_path_buf'])
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# 返回上级：截断 ws_current_path 的最后一段后重新枚举。"C:\" 形式保留分隔符；
# 没有任何分隔符（相对路径）时不动作。
em.label('ws_go_up')
em.emit(0x48,0x83,0xEC,0x28)
em.lea_rip('rcx',bsyms['ws_path_buf']); em.lea_rip('rdx',bsyms['ws_current_path']); em.call_iat('lstrcpyW')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.call_iat('lstrlenW'); em.mov_r32_r32('r10','rax')
em.test32('r10'); em.jcc(0x84,'wgu_ret')
em.mov_r32_r32('r11','r10'); em.sub_r32_imm8('r11',1)
em.lea_rip('rcx',bsyms['ws_path_buf'])
em.label('wgu_scan')
em.movzx_r32_word_index2('rax','rcx','r11'); em.cmp_r32_imm('rax',0x5C); em.jcc(0x84,'wgu_found')
em.test32('r11'); em.jcc(0x84,'wgu_ret')
em.sub_r32_imm8('r11',1); em.jmp('wgu_scan')
em.label('wgu_found')
em.cmp_r32_imm('r11',2); em.jcc(0x85,'wgu_cut')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.add_r64_imm8('rcx',2); em.movzx_eax_word_ptr('rcx')
em.cmp_r32_imm('rax',0x3A); em.jcc(0x85,'wgu_cut'); em.add_r32_imm8('r11',1)
em.label('wgu_cut')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.mov_word_index2_zero('rcx','r11')
em.lea_rip('rcx',bsyms['ws_path_buf']); em.call_label('workspace_set_root'); em.call_label('update_status')
em.label('wgu_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

# 双击（或在列表上回车）：目录进入，文件走现有 Open 事务——只设置临时路径与
# pending action，让 destructive_request 复用未保存保护与 cmd_open_selected 的
# 读取/解码/提交路径，不新增第二条打开逻辑。
em.label('ws_open_or_enter')
em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57); em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.test64('rcx'); em.jcc(0x84,'woe_ret')
em.mov_r32_imm('rdx',0x0188); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'woe_ret')
em.mov_r32_r32('r12','rax')
em.mov_r64_ripmem('r13',bsyms['ws_entries']); em.test64('r13'); em.jcc(0x84,'woe_ret')
em.mov_r32_ripmem('r14',bsyms['ws_entry_count']); em.cmp_r32_r32('r12','r14'); em.jcc(0x83,'woe_ret')
em.mov_r32_r32('rax','r12'); em.mov_r32_r32('rcx','r12')
em.shl_r32_imm8('rcx',9); em.shl_r32_imm8('rax',5); em.add_r32_r32('rax','rcx')
em.mov_r64_r64('r15','r13'); em.add_r64_r64('r15','rax')
em.lea_rip('rcx',bsyms['ws_current_path']); em.mov_r64_r64('rdx','r15'); em.call_label('ws_join_path')
em.mov_r32_mreg('r10','r15',WS_OFF_KIND); em.test32('r10'); em.jcc(0x84,'woe_file')
em.mov_r64_r64('rcx','rax'); em.call_label('workspace_set_root'); em.call_label('update_status')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.call_iat('SetFocus'); em.jmp('woe_ret')
em.label('woe_file')
em.lea_rip('rcx',bsyms['temp_path']); em.mov_r64_r64('rdx','rax'); em.call_iat('lstrcpyW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.call_iat('SetFocus')
em.mov_ripmem_imm32(bsyms['open_bypass_picker'],1)
em.mov_ripmem_imm32(bsyms['pending_destructive_action'],2)
# destructive_request 的每条出口都以 jmp msg_loop 结束，永不返回，所以这里
# 必须同时丢弃调用者的返回地址；否则栈会永久错位 8 字节并破坏对齐。
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.add_r64_imm8('rsp',8)
em.jmp('destructive_request')
em.label('woe_ret')
em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0xC3)

# Build-time-only probe (command 1902): enumerate whatever temp_path points at
# and leave the entries in BSS for the Windows harness to read back.
if OPEN_TEST_BUILD:
    em.label('cmd_workspace_probe')
    em.lea_rip('rcx',bsyms['temp_path']); em.call_label('workspace_set_root'); em.jmp('msg_loop')
    # 切片 2：非交互面板切换，供 Windows 测试脚本驱动模式、绘制与滚动。
    em.label('cmd_show_files'); em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode'); em.jmp('msg_loop')
    em.label('cmd_show_outline'); em.xor32('rcx'); em.call_label('set_panel_mode'); em.jmp('msg_loop')
    # 切片 2：把 list_probe_index 指向的行文本导出到 list_probe_text。
    em.label('cmd_dump_row')
    em.mov_r32_imm('rax',0xFFFFFFFF)
    em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.test64('rcx'); em.jcc(0x84,'cdr_store')
    em.mov_r32_imm('rdx',0x0189); em.mov_r32_ripmem('r8',bsyms['list_probe_index']); em.lea_rip('r9',bsyms['list_probe_text']); em.call_iat('SendMessageW')
    em.label('cdr_store'); em.mov_ripmem_r32(bsyms['list_probe_result'],'rax'); em.jmp('msg_loop')
    # 切片 3：非交互地驱动"激活选中项"与"返回上级"。
    em.label('cmd_list_activate'); em.call_label('ws_open_or_enter'); em.jmp('msg_loop')
    em.label('cmd_go_up'); em.call_label('ws_go_up'); em.jmp('msg_loop')
    # 切片 4：跳过文件夹浏览对话框，直接采用 temp_path 作为工作区。
    em.label('cmd_open_folder_selected')
    em.lea_rip('rcx',bsyms['temp_path']); em.call_label('workspace_set_root')
    em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode'); em.call_label('update_status'); em.jmp('msg_loop')


# ---------------- V8.4.25 统一扫描：大纲条目推送例程 ----------------
# 契约：统一扫描器（update_preview 的 pv8 循环）在围栏代码块之外识别出
# ATX 标题行时调用，当场完成该大纲行的文本构建、ListBox 登记与三表写入。
# 旧版独立的 rebuild_outline 扫描器已删除：它不跟踪围栏状态，围栏内的
# 伪 '#' 行会进入大纲并与渲染侧序号错位（V8.4.25 消除的双解析分歧）。
# 输入（volatile，进入后立即转存栈槽）：
#   r8d  = '#' 序列的源字符偏移（outline_srcpos 语义：前导空格之后）
#   r9d  = 该标题行的渲染缓冲偏移（outline_renderpos 语义）
#   r10d = 标题级别 1..6
#   r12d = 标题文本源起始偏移（'#' 后空格之后；r12 非 volatile，
#          跨 SendMessageW 存活，本例程不保存也不破坏）
# clobber：rax, rcx, rdx, r8, r9, r10, r11
em.label('outline_push')
em.emit(0x48,0x83,0xEC,0x48)  # sub rsp,0x48：栈对齐 + 32 字节影子空间 + 三个参数槽
em.mov_mrsp_reg32(0x30,'r8'); em.mov_mrsp_reg32(0x38,'r9'); em.mov_mrsp_reg32(0x40,'r10')
# 大纲窗口不存在或动态 arena 已满：跳过登记。
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'outline_push_ret')
em.mov_r32_ripmem('r11',bsyms['outline_count']); em.mov_r32_ripmem('rax',bsyms['outline_capacity']); em.cmp_r32_r32('r11','rax'); em.jcc(0x83,'outline_push_ret')
# 可见标题文本：每低一级缩进两个空格（与旧版一致），随后拷贝源标题至行尾。
em.lea_rip('rcx',bsyms['outline_titlebuf']); em.xor32('rdx')
em.label('outline_push_indent'); em.cmp_r32_imm('r10',1); em.jcc(0x8E,'outline_push_copy')
em.mov_word_index2_imm16('rcx','rdx',0x20); em.add_r32_imm8('rdx',1)
em.mov_word_index2_imm16('rcx','rdx',0x20); em.add_r32_imm8('rdx',1)
em.sub_r32_imm8('r10',1); em.jmp('outline_push_indent')
em.label('outline_push_copy'); em.mov_r64_ripmem('rax',bsyms['document_model']); em.mov_r32_r32('r11','r12')
em.label('outline_push_copy_loop'); em.movzx_r32_word_index2('r10','rax','r11'); em.test32('r10'); em.jcc(0x84,'outline_push_copy_done')
em.cmp_r32_imm('r10',0x0D); em.jcc(0x84,'outline_push_copy_done'); em.cmp_r32_imm('r10',0x0A); em.jcc(0x84,'outline_push_copy_done')
em.cmp_r32_imm('rdx',500); em.jcc(0x83,'outline_push_copy_done')
em.mov_word_index2_reg('rcx','rdx','r10'); em.add_r32_imm8('rdx',1); em.add_r32_imm8('r11',1); em.jmp('outline_push_copy_loop')
em.label('outline_push_copy_done'); em.mov_word_index2_zero('rcx','rdx')
# 登记到 ListBox，按返回索引写三张大纲表（与旧版语义一致）。
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0180); em.xor32('r8'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'outline_push_ret'); em.mov_r32_ripmem('r10',bsyms['outline_capacity']); em.cmp_r32_r32('rax','r10'); em.jcc(0x83,'outline_push_ret')
em.mov_r32_r32('r11','rax'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.emit(0x44,0x8B,0x44,0x24,0x30); em.mov_r64_ripmem('rcx',bsyms['outline_srcpos']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r8')
em.emit(0x44,0x8B,0x44,0x24,0x38); em.mov_r64_ripmem('rcx',bsyms['outline_renderpos']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r8')
em.emit(0x44,0x8B,0x44,0x24,0x40); em.mov_r64_ripmem('rcx',bsyms['outline_level']); em.add_r64_r64('rcx','rax'); em.mov_ptr_r32('rcx','r8')
em.mov_r32_ripmem('r11',bsyms['outline_count']); em.add_r32_imm8('r11',1); em.mov_ripmem_r32(bsyms['outline_count'],'r11')
em.label('outline_push_ret'); em.emit(0x48,0x83,0xC4,0x48); em.emit(0xC3)

# Helper: establish Preview default character format BEFORE SetWindowTextW.
# RichEdit applies SCF_DEFAULT (wParam=0) to subsequently inserted text, so a huge
# document gets the correct base font/size/color in one load operation without an
# expensive SCF_ALL pass over every character. Semantic Markdown spans are then
# applied only to the visible viewport and lazily as new regions are visited.
em.label('prepare_preview_default')
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.test64('rax'); em.jcc(0x84,'preview_default_ret')
# Page background.
em.mov_r64_r64('rcx','rax'); em.mov_r32_imm('rdx',0x0443); em.xor32('r8'); em.mov_r32_ripmem('r9',bsyms['theme_dark']); em.test32('r9'); em.jcc(0x84,'preview_default_bg_light'); em.mov_r32_imm('r9',0x001E1E1E); em.jmp('preview_default_bg_send')
em.label('preview_default_bg_light'); em.mov_r32_imm('r9',0x00FFFFFF)
em.label('preview_default_bg_send'); em.call_iat('SendMessageW')
# CHARFORMATW default: face + size + color. SCF_DEFAULT is wParam=0.
em.lea_rip('r11',bsyms['charfmt']); em.mov_mreg_imm32('r11',0,116); em.mov_mreg_imm32('r11',4,0xE0000000); em.mov_mreg_imm32('r11',8,0); em.mov_mreg_imm32('r11',12,220)
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'preview_default_text_light'); em.mov_mreg_imm32('r11',20,0x00D4D4D4); em.jmp('preview_default_text_ready')
em.label('preview_default_text_light'); em.mov_mreg_imm32('r11',20,0x00202020)
em.label('preview_default_text_ready'); em.lea_rip('rcx',bsyms['charfmt']+26); em.lea_rip('rdx',rsyms['font_face']); em.call_iat('lstrcpyW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r32_imm('rdx',0x0444); em.xor32('r8'); em.lea_rip('r9',bsyms['charfmt']); em.call_iat('SendMessageW')
em.label('preview_default_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

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
# V8.6 Phase E：arena 未建立（分配失败或尚未预留）时不得解引用样式指针。
em.mov_r64_ripmem('rcx',bsyms['style_start']); em.test64('rcx'); em.jcc(0x84,'styles_done')
em.xor32('r12')
em.label('style_loop')
em.mov_r32_ripmem('rax',bsyms['style_count']); em.cmp_r32_r32('r12','rax'); em.jcc(0x83,'styles_done')
em.mov_r32_r32('rax','r12'); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.mov_r64_ripmem('rcx',bsyms['style_start']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r8','rcx')
em.mov_r64_ripmem('rcx',bsyms['style_end']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r9','rcx')
em.mov_r64_ripmem('rcx',bsyms['style_type']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r13','rcx')
# During a theme-only viewport refresh, skip spans completely outside the current
# visible formatting window. The style array scan is cheap; expensive RichEdit
# range formatting is limited to what can actually be seen.
em.mov_r32_ripmem('rax',bsyms['preview_visible_format_only']); em.test32('rax'); em.jcc(0x84,'style_range_send')
em.mov_r32_ripmem('rax',bsyms['view_top_pos']); em.cmp_r32_r32('r9','rax'); em.jcc(0x86,'style_next')
em.mov_r32_ripmem('rax',bsyms['format_visible_end']); em.cmp_r32_r32('r8','rax'); em.jcc(0x83,'style_next')
em.cmp_r32_r32('r9','rax'); em.jcc(0x86,'style_clip_end'); em.mov_r32_r32('r9','rax')
em.label('style_clip_end'); em.mov_r32_ripmem('rax',bsyms['view_top_pos']); em.cmp_r32_r32('r8','rax'); em.jcc(0x83,'style_range_send'); em.mov_r32_r32('r8','rax')
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
    em.mov_r64_ripmem('rcx',bsyms['render_srcmap']); em.add_r64_r64('rcx','r10'); em.mov_ptr_r32('rcx','r12')

# Helper: rebuild Markdown render buffer, formatting spans and outline from source text.
em.label('update_preview')
em.emit(0x56); em.emit(0x57); em.emit(0x41,0x54); em.emit(0x41,0x55); em.emit(0x41,0x56); em.emit(0x41,0x57)
em.emit(0x48,0x83,0xEC,0x28)
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.call_label('ensure_outline_arena'); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
# V8.6 Phase E：样式表同样在扫描前按文档长度预留；分配失败放弃本次渲染，
# 文档模型与编辑器内容保持不变（下一次编辑/切换会重试）。
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.call_label('ensure_style_arena'); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.call_label('ensure_render_arena'); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
em.mov_r32_ripmem('rcx',bsyms['document_len']); em.call_label('ensure_document_arena'); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
# A full Preview rebuild is authoritative. Cancel any delayed viewport-theme timer
# left over from a previous Light/Dark scroll cycle; otherwise that stale timer can
# fire after the new render and re-apply ranges using old viewport state, producing
# intermittent wrong code backgrounds/colors until Preview is toggled again.
em.mov_r64_ripmem('rcx',bsyms['hwnd_main']); em.test64('rcx'); em.jcc(0x84,'pv_timer_reset_done'); em.mov_r32_imm('rdx',0x4D); em.call_iat('KillTimer')
em.label('pv_timer_reset_done'); em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],0); em.mov_ripmem_imm32(bsyms['preview_visible_format_only'],0)
# ---------------- V8.4.25 统一扫描（one scan, three tables）----------------
# 单一扫描器一次遍历文档模型，同时产出：大纲三表（outline_srcpos/
# outline_renderpos/outline_level）、渲染样式表（style_*）、位置映射
# （render_srcmap/render_len）。旧版独立的 rebuild_outline 扫描器已删除。
#
# 大纲准备（吸收自旧 rebuild_outline）：计数清零、冻结重绘、清空列表。
em.mov_ripmem_imm32(bsyms['outline_count'],0)
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'pv_scan_prep_done')
em.mov_r32_imm('rdx',0x000B); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.mov_r32_imm('rdx',0x0184); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.label('pv_scan_prep_done')
# 源码模式下同样执行完整扫描（V8.4.25 行为变化）：大纲保持正确，且
# 切回预览前的渲染数据与位置映射始终新鲜，消除旧版"源码模式下
# render_srcmap 陈旧"的隐患。隐藏的 RichEdit 表面不被触碰，文本装载
# 仅在预览模式进行（见 pv8_finish 之后）。
em.mov_ripmem_imm32(bsyms['style_count'],0); em.mov_ripmem_imm32(bsyms['heading_level'],0); em.mov_ripmem_imm32(bsyms['line_flags'],0); em.mov_ripmem_imm32(bsyms['render_len'],0)
em.mov_ripmem_imm32(bsyms['bold_flag'],0); em.mov_ripmem_imm32(bsyms['italic_flag'],0); em.mov_ripmem_imm32(bsyms['inlinecode_flag'],0); em.mov_ripmem_imm32(bsyms['link_flag'],0)
em.mov_r64_ripmem('rsi',bsyms['document_model']); em.mov_r64_ripmem('rdi',bsyms['previewbuf']); em.xor32('r12'); em.xor32('r13'); em.mov_r32_imm('r14',1); em.xor32('r15')

em.label('pv8_loop')
# Never let malformed input or a future renderer rule overrun Preview Buffer.
em.mov_r32_ripmem('rax',bsyms['render_arena_capacity']); em.sub_r32_imm8('rax',8); em.cmp_r32_r32('r13','rax'); em.jcc(0x83,'pv8_eof')
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
em.test32('r15'); em.jcc(0x84,'pv8_line_heading_check')
# The fence probe advanced past up to three leading spaces. Restore the original
# source offset before copying code so indentation and internal spacing are byte-exact.
em.mov_r32_ripmem('r12',bsyms['line_src_start']); em.jmp('pv8_codeblock_copy')
em.label('pv8_line_heading_check')
# ATX heading: one to six #'s followed by a space.
em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'pv8_line_quote')
em.xor32('r10'); em.mov_r32_r32('r11','r12')
em.label('pv8_hash_count'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x23); em.jcc(0x85,'pv8_hash_done'); em.cmp_r32_imm('r10',6); em.jcc(0x83,'pv8_hash_done'); em.add_r32_imm8('r10',1); em.add_r32_imm8('r11',1); em.jmp('pv8_hash_count')
em.label('pv8_hash_done'); em.test32('r10'); em.jcc(0x84,'pv8_line_quote'); em.movzx_r32_word_index2('rax','rsi','r11'); em.cmp_r32_imm('rax',0x20); em.jcc(0x85,'pv8_line_quote')
# V8.4.25 统一扫描：标题识别点同步登记大纲条目。到达此处即意味着该行
# 在围栏代码块之外（fence 检查在 pv8_line_after_fence_check 前置完成），
# 大纲与渲染从此共享同一套块级状态，不再有第二套解析器。
# 调用前安置跨调用信息：'#' 源偏移 = r11-r10（r11 指向 '#' 序列之后）；
# 级别先落盘（r10 是 volatile，outline_push 会破坏）；标题文本源起点
# 写入非 volatile r12，调用后 pv8 循环从该处继续逐字拷贝。
em.mov_ripmem_r32(bsyms['heading_level'],'r10'); em.mov_ripmem_r32(bsyms['heading_out_start'],'r13')
em.mov_r32_r32('r8','r11'); em.sub_r32_r32('r8','r10'); em.mov_r32_r32('r9','r13')
em.mov_r32_r32('r12','r11'); em.add_r32_imm8('r12',1)
em.call_label('outline_push')
em.xor32('r14'); em.jmp('pv8_loop')

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
# 大纲收尾（吸收自旧 rebuild_outline 尾部）：恢复重绘、整体失效、同步
# 滚动条几何。源码模式与预览模式统一走此路径。
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'pv_outline_done')
em.mov_r32_imm('rdx',0x000B); em.mov_r32_imm('r8',1); em.xor32('r9'); em.call_iat('SendMessageW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_gutter']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect')
em.call_label('sync_outline_scrollbar')
em.label('pv_outline_done')
# 仅预览模式把渲染文本装载进 RichEdit 表面。源码模式下渲染数据在后台
# 保持新鲜，切换命令（cmd_preview）会重新扫描装载，无需触碰隐藏控件。
# Populate the RichEdit surface, but do NOT synchronously format every recorded
# Markdown span. On very large documents the old apply_styles() pass issued tens
# of thousands of EM_SETCHARFORMAT calls and dominated Preview entry time. Set the
# base format as RichEdit's default before loading text, then lazily style only the
# viewport after its mapped position has been restored.
em.mov_r32_ripmem('rax',bsyms['preview_flag']); em.test32('rax'); em.jcc(0x84,'pv_render_ret')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.test64('rcx'); em.jcc(0x84,'pv_render_ret')
em.call_label('prepare_preview_default')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.mov_r64_ripmem('rdx',bsyms['previewbuf']); em.call_iat('SetWindowTextW')
em.call_label('apply_preview_zoom')
# Keep this flag set: it now means offscreen semantic spans are still lazy. Scroll,
# keyboard paging, theme changes and outline jumps format only newly visible ranges.
em.mov_ripmem_imm32(bsyms['preview_theme_dirty'],1)
em.label('pv_render_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0x41,0x5F); em.emit(0x41,0x5E); em.emit(0x41,0x5D); em.emit(0x41,0x5C); em.emit(0x5F); em.emit(0x5E); em.emit(0xC3)

# 辅助例程：点击大纲标题后，在源码模式或渲染模式之间导航。
# V8.4.24 修复（P0-001）：V8.4.23 的代码把 index*4 的数组字节偏移
# 保存在 volatile RAX 中跨越了 IsWindowVisible 调用，偏移随即被
# BOOL 返回值覆盖。结果 Preview 跳转读到错位的 outline_srcpos 表项，
# Source 跳转则永远落在第一个标题上。下面的重排先确定目标表面，
# 再发 LB_GETCURSEL 并立即消费 RAX，中间没有任何 API 调用。
em.label('navigate_outline')
em.emit(0x48,0x83,0xEC,0x28)
# 1）V8.5.0：选定导航目标表面。preview_flag 由 set_view_mode 家族唯一
#    写入并保证与实际可见性一致，不再需要 IsWindowVisible 二次确认——
#    旧版正是让 volatile 数组偏移跨越该调用才引发 P0-001。
em.mov_r32_ripmem('r11',bsyms['preview_flag']); em.test32('r11'); em.jcc(0x84,'navigate_pick_source')
em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.jmp('navigate_have_surface')
em.label('navigate_pick_source'); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit'])
em.label('navigate_have_surface'); em.mov_ripmem_r64(bsyms['nav_hwnd'],'rcx')
# 2）选中索引：先做边界检查，再缩放并立即消费，中间没有任何
#    API 调用，因此不会有 volatile 寄存器携带该偏移存活。
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.test64('rcx'); em.jcc(0x84,'navigate_ret'); em.mov_r32_imm('rdx',0x0188); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW')
em.cmp_r32_imm('rax',0xFFFFFFFF); em.jcc(0x84,'navigate_ret'); em.mov_r32_ripmem('r10',bsyms['outline_count']); em.cmp_r32_r32('rax','r10'); em.jcc(0x83,'navigate_ret')
em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax')
em.mov_r64_ripmem('rcx',bsyms['outline_srcpos']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r8','rcx')
# Preview 导航的目标位置由规范的源码标题偏移推导而来。
# outline_renderpos 在大文件首次加载期间可能暂时过期/为零；
# Preview 一旦存在，当前的 render_srcmap 才是权威。
# V8.4.24：仅当跳转确实指向 Preview 时才映射为渲染偏移；
# 若在此处检查 preview_flag，过期标志把跳转路由到 Source 时会错误映射。
em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.cmp_r64_r64('rcx','rax'); em.jcc(0x85,'navigate_target_ready')
em.call_label('map_source_to_render'); em.mov_r32_r32('r8','rax')
em.label('navigate_target_ready'); em.mov_r32_r32('r9','r8'); em.mov_r64_ripmem('rcx',bsyms['nav_hwnd'])
em.mov_r32_imm('rdx',0x00B1); em.call_iat('SendMessageW'); em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.mov_r32_imm('rdx',0x00B7); em.xor32('r8'); em.xor32('r9'); em.call_iat('SendMessageW'); em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.call_iat('SetFocus')
# 程序化的大纲跳转可能落在 Preview 从未格式化过的懒加载区域。
# 同步格式化该视口，使标题/代码/链接颜色在第一帧就正确，
# 而不是等到用户滚动后才变正确。
em.mov_r64_ripmem('rcx',bsyms['nav_hwnd']); em.mov_r64_ripmem('rax',bsyms['hwnd_preview']); em.cmp_r64_r64('rcx','rax'); em.jcc(0x85,'navigate_ret'); em.call_label('refresh_preview_visible_theme')
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
em.label('theme_del_menu'); em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'theme_del_scroll_thumb'); em.call_iat('DeleteObject')
em.label('theme_del_scroll_thumb'); em.mov_r64_ripmem('rcx',bsyms['hbrush_scroll_thumb']); em.test64('rcx'); em.jcc(0x84,'theme_del_scroll_hot'); em.call_iat('DeleteObject')
em.label('theme_del_scroll_hot'); em.mov_r64_ripmem('rcx',bsyms['hbrush_scroll_hot']); em.test64('rcx'); em.jcc(0x84,'theme_make'); em.call_iat('DeleteObject')
em.label('theme_make'); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'theme_make_light')
em.mov_r32_imm('rcx',0x001A1A1A); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x001F1F1F); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x001D1D1D); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_splitter'],'rax'); em.mov_r32_imm('rcx',0x00202020); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_status'],'rax'); em.mov_r32_imm('rcx',0x00202020); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax'); em.mov_r32_imm('rcx',0x007A7A7A); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_scroll_thumb'],'rax'); em.mov_r32_imm('rcx',0x00A8A8A8); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_scroll_hot'],'rax'); em.jmp('theme_controls')
em.label('theme_make_light'); em.mov_r32_imm('rcx',0x00FFFFFF); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_edit'],'rax'); em.mov_r32_imm('rcx',0x00F3F3F3); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_outline'],'rax'); em.mov_r32_imm('rcx',0x00E8EAED); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_splitter'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_status'],'rax'); em.mov_r32_imm('rcx',0x00F5F5F5); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_menu'],'rax'); em.mov_r32_imm('rcx',0x00B8B8B8); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_scroll_thumb'],'rax'); em.mov_r32_imm('rcx',0x008A8A8A); em.call_iat('CreateSolidBrush'); em.mov_ripmem_r64(bsyms['hbrush_scroll_hot'],'rax')
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
# Independent scrollbar is permanently created and themed above; no ListBox frame recreation is required.
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_splitter']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_outline_scroll']); em.xor32('rdx'); em.xor32('r8'); em.mov_r32_imm('r9',0x105); em.call_iat('RedrawWindow'); em.mov_r64_ripmem('rcx',bsyms['hwnd_preview']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_files']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_files_gutter']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_ripmem('rcx',bsyms['hwnd_corner']); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.xor32('rdx'); em.mov_r32_imm('r8',1); em.call_iat('InvalidateRect'); em.mov_r64_r64('rcx','rbx'); em.call_iat('UpdateWindow'); em.call_label('paint_menu_gaps')
em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Helper: find next occurrence using SHLWAPI StrStrW/StrStrIW, select it, and scroll caret.
# Uses the current selection end as the search start and optionally wraps once.
em.label('find_next_select')
em.emit(0x48,0x83,0xEC,0x38)
em.lea_rip('rcx',bsyms['findbuf']); em.call_iat('lstrlenW'); em.mov_ripmem_r32(bsyms['find_len'],'rax'); em.test32('rax'); em.jcc(0x84,'find_none')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
# V8.6：搜索快照写入 widebuf，先保证 arena 有容量；失败即视为未找到。
em.mov_r32_ripmem('rcx',bsyms['total_chars']); em.add_r32_imm8('rcx',1); em.call_label('ensure_wide_arena'); em.test32('rax'); em.jcc(0x84,'find_none')
em.mov_r32_r32('r8','rax'); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r64_ripmem('rdx',bsyms['widebuf']); em.call_iat('GetWindowTextW')
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r32_imm('rdx',0x00B0); em.lea_rip('r8',bsyms['sel_start']); em.lea_rip('r9',bsyms['sel_end']); em.call_iat('SendMessageW')
# pointer = widebuf + 2*sel_end
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.mov_r32_ripmem('rax',bsyms['sel_end']); em.add_r64_r64('rax','rax'); em.add_r64_r64('rcx','rax'); em.lea_rip('rdx',bsyms['findbuf'])
em.mov_r32_ripmem('rax',bsyms['find_flags']); em.and_r32_imm('rax',4); em.test32('rax'); em.jcc(0x85,'find_case_first')
em.call_iat('StrStrIW'); em.jmp('find_first_done')
em.label('find_case_first'); em.call_iat('StrStrW')
em.label('find_first_done'); em.test64('rax'); em.jcc(0x85,'find_got')
# Wrap only for ordinary Find Next; Replace All disables this.
em.mov_r32_ripmem('r10',bsyms['search_wrap_flag']); em.test32('r10'); em.jcc(0x84,'find_none')
em.mov_r32_ripmem('r10',bsyms['sel_end']); em.test32('r10'); em.jcc(0x84,'find_none')
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.lea_rip('rdx',bsyms['findbuf']); em.mov_r32_ripmem('r10',bsyms['find_flags']); em.and_r32_imm('r10',4); em.test32('r10'); em.jcc(0x85,'find_case_wrap')
em.call_iat('StrStrIW'); em.jmp('find_wrap_done')
em.label('find_case_wrap'); em.call_iat('StrStrW')
em.label('find_wrap_done'); em.test64('rax'); em.jcc(0x84,'find_none')
em.label('find_got')
em.mov_r64_ripmem('r10',bsyms['widebuf']); em.sub_r64_r64('rax','r10'); em.shr_r64_imm8('rax',1); em.mov_ripmem_r32(bsyms['match_start'],'rax')
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
em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.call_iat('GetWindowTextLengthW'); em.mov_ripmem_r32(bsyms['total_chars'],'rax')
em.mov_r32_r32('rcx','rax'); em.add_r32_imm8('rcx',1); em.call_label('ensure_wide_arena'); em.test32('rax'); em.jcc(0x84,'replace_no')
em.mov_r32_ripmem('r8',bsyms['total_chars']); em.add_r32_imm8('r8',1); em.mov_r64_ripmem('rcx',bsyms['hwnd_edit']); em.mov_r64_ripmem('rdx',bsyms['widebuf']); em.call_iat('GetWindowTextW')
# CompareStringOrdinal(selected, find_len, findbuf, find_len, ignoreCase)
em.mov_r64_ripmem('rcx',bsyms['widebuf']); em.mov_r32_ripmem('rax',bsyms['sel_start']); em.add_r64_r64('rax','rax'); em.add_r64_r64('rcx','rax')
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
em.mov_r32_ripmem('rax',bsyms['eol_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'eol_lf'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'eol_cr'); em.lea_rip('r9',rsyms['status_crlf']); em.jmp('eol_send')
em.label('eol_lf'); em.lea_rip('r9',rsyms['status_lf']); em.jmp('eol_send')
em.label('eol_cr'); em.lea_rip('r9',rsyms['status_cr'])
em.label('eol_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1104); em.call_iat('SendMessageW')
# encoding
em.mov_r32_ripmem('rax',bsyms['encoding_state']); em.cmp_r32_imm('rax',1); em.jcc(0x84,'enc_utf16'); em.cmp_r32_imm('rax',2); em.jcc(0x84,'enc_utf8_bom'); em.lea_rip('r9',rsyms['status_utf8']); em.jmp('enc_send')
em.label('enc_utf16'); em.lea_rip('r9',rsyms['status_utf16']); em.jmp('enc_send')
em.label('enc_utf8_bom'); em.lea_rip('r9',rsyms['status_utf8_bom'])
em.label('enc_send'); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1105); em.call_iat('SendMessageW')
# V8.6 切片 3：第七段显示当前工作区目录（只有文件面板有意义）。
em.lea_rip('r9',bsyms['ws_current_path']); em.mov_r64_ripmem('rcx',bsyms['hwnd_status']); em.mov_r32_imm('rdx',0x040B); em.mov_r32_imm('r8',0x1106); em.call_iat('SendMessageW')
em.label('status_ret'); em.add_r64_imm8('rsp',0x28); em.emit(0xC3)

em.label('exit')
# 正常退出路径：直接 ExitProcess。进程退出时 OS 回收全部 GDI/窗口资源，
# 清理链（exit_skip…exit_now）仅为纵深防御保留。注：V8.5.0 初期曾误以为
# 退出崩溃与清理链或加载器 DETACH 重入有关（均已被实验否定）；真正根因
# 是 dispatch 块 fall through（2026-09-14 修复，构建期断言 (I) 防回退）。
em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)
em.label('exit_skip')
em.mov_r64_ripmem('rcx',bsyms['hfont']); em.test64('rcx'); em.jcc(0x84,'exit_font_outline'); em.call_iat('DeleteObject')
em.label('exit_font_outline'); em.mov_r64_ripmem('rcx',bsyms['hfont_outline']); em.test64('rcx'); em.jcc(0x84,'exit_font_status'); em.call_iat('DeleteObject')
em.label('exit_font_status'); em.mov_r64_ripmem('rcx',bsyms['hfont_status']); em.test64('rcx'); em.jcc(0x84,'exit_brush_menu'); em.call_iat('DeleteObject')
em.label('exit_brush_menu'); em.mov_r64_ripmem('rcx',bsyms['hbrush_menu']); em.test64('rcx'); em.jcc(0x84,'exit_brush_scroll'); em.call_iat('DeleteObject')
em.label('exit_brush_scroll'); em.mov_r64_ripmem('rcx',bsyms['hbrush_scroll_thumb']); em.test64('rcx'); em.jcc(0x84,'exit_brush_scroll_hot'); em.call_iat('DeleteObject')
em.label('exit_brush_scroll_hot'); em.mov_r64_ripmem('rcx',bsyms['hbrush_scroll_hot']); em.test64('rcx'); em.jcc(0x84,'exit_accel'); em.call_iat('DeleteObject')
em.label('exit_accel'); em.mov_r64_ripmem('rcx',bsyms['haccel']); em.test64('rcx'); em.jcc(0x84,'exit_now'); em.call_iat('DestroyAcceleratorTable')
em.label('exit_now'); em.xor32('rcx'); em.call_iat('ExitProcess'); em.emit(0xCC)
# ------------------------------------------------------------------
# Dedicated Outline overlay-scrollbar surface WndProc.
# V8.4.20 used SS_OWNERDRAW STATIC and depended on the parent WM_DRAWITEM path.
# On real Windows that path could miss/reorder paints, leaving a full-height
# COLOR_WINDOW stripe and no thumb.  This class owns paint/erase deterministically.
em.label('scrollproc')
em.emit(0x48,0x83,0xEC,0x38)
em.cmp_r32_imm('rdx',0x000F); em.jcc(0x84,'sp_paint')      # WM_PAINT
em.cmp_r32_imm('rdx',0x0014); em.jcc(0x84,'sp_erase')      # WM_ERASEBKGND
em.call_iat('DefWindowProcW'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('sp_erase')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('sp_paint')
em.mov_ripmem_r64(bsyms['scroll_paint_hwnd'],'rcx')
em.lea_rip('rdx',bsyms['ps_scroll']); em.call_iat('BeginPaint'); em.test64('rax'); em.jcc(0x84,'sp_paint_end')
em.mov_ripmem_r64(bsyms['paint_hdc'],'rax')
# Fill the ENTIRE gutter with the current Outline palette every paint; no stale
# light/dark stripe survives a theme transition.
em.mov_r64_ripmem('rcx',bsyms['scroll_paint_hwnd']); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('GetClientRect')
em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.lea_rip('rdx',bsyms['draw_rect']); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
# Draw the thumb only while hover/drag state says it is visible.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'sp_endpaint')
# Visual thumb width = clamp(clientWidth/2, 6..9), centered in the permanent gutter.
em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_mreg('rax','rcx',8); em.cmp_r32_imm('rax',1); em.jcc(0x83,'sp_width_have'); em.mov_r32_imm('rax',1)
em.label('sp_width_have'); em.mov_r32_r32('rcx','rax'); em.mov_r32_imm('rdx',1); em.mov_r32_imm('r8',2); em.call_iat('MulDiv')
em.cmp_r32_imm('rax',6); em.jcc(0x83,'sp_w_min_ok'); em.mov_r32_imm('rax',6)
em.label('sp_w_min_ok'); em.cmp_r32_imm('rax',9); em.jcc(0x86,'sp_w_ok'); em.mov_r32_imm('rax',9)
em.label('sp_w_ok'); em.mov_r32_r32('r10','rax')
# Build thumb rectangle in draw_rect using the client rect already fetched above.
# Do NOT call another Win32 API after placing thumb width in volatile r10d.
em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_mreg('rax','rcx',8); em.sub_r32_r32('rax','r10'); em.shr_r32_imm8('rax',1); em.mov_ptr_r32('rcx','rax')
em.mov_r32_ripmem('r11',bsyms['outline_scroll_thumb_top']); em.mov_mreg_reg32('rcx',4,'r11'); em.add_r32_r32('rax','r10'); em.mov_mreg_reg32('rcx',8,'rax')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_thumb_h']); em.add_r32_r32('r11','rax'); em.mov_mreg_reg32('rcx',12,'r11')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag']); em.test32('rax'); em.jcc(0x84,'sp_brush_normal'); em.mov_r64_ripmem('r8',bsyms['hbrush_scroll_hot']); em.jmp('sp_fill_thumb')
em.label('sp_brush_normal'); em.mov_r64_ripmem('r8',bsyms['hbrush_scroll_thumb'])
em.label('sp_fill_thumb'); em.mov_r64_ripmem('rcx',bsyms['paint_hdc']); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('FillRect')
em.label('sp_endpaint'); em.mov_r64_ripmem('rcx',bsyms['scroll_paint_hwnd']); em.lea_rip('rdx',bsyms['ps_scroll']); em.call_iat('EndPaint')
em.label('sp_paint_end'); em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# ------------------------------------------------------------------
# Real application WndProc. Windows delivers menu, child notifications,
# live sizing and control-color messages synchronously to this callback.
em.label('wndproc')
em.emit(0x48,0x83,0xEC,0x38)
em.mov_r32_ripmem('r10',bsyms['findmsg_id']); em.cmp_r32_r32('rdx','r10'); em.jcc(0x84,'wp_findreplace')
em.cmp_r32_imm('rdx',0x0111); em.jcc(0x84,'wp_command')      # WM_COMMAND
em.cmp_r32_imm('rdx',0x0005); em.jcc(0x84,'wp_size')         # WM_SIZE
em.cmp_r32_imm('rdx',0x0010); em.jcc(0x84,'wp_close')        # WM_CLOSE -> shared unsaved controller
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

em.label('wp_close')
em.mov_r32_imm('rdx',0x8006); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW')
em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_vscroll')
# Handle only our independent Outline scrollbar; other controls keep default behavior.
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
em.call_label('advance_document_revision'); em.mov_r32_imm('rdx',0x8004); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('wp_child_return')
# Outline selection notification.
# V8.6.1：两个面板各自的通知分流。文件面板的双击才是"激活/打开"，
# 大纲面板的单选才触发文档跳转。
em.label('wp_cmd_outline_check'); em.mov_r64_ripmem('rax',bsyms['hwnd_files']); em.cmp_r64_r64('r9','rax'); em.jcc(0x84,'wp_cmd_files_child')
em.mov_r64_ripmem('rax',bsyms['hwnd_outline']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_cmd_other_child')
em.mov_r32_r32('r10','r8'); em.shr_r32_imm8('r10',16); em.cmp_r32_imm('r10',1); em.jcc(0x85,'wp_child_return')
em.mov_r32_imm('rdx',0x8005); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('wp_child_return')
em.label('wp_cmd_files_child')
em.mov_r32_r32('r10','r8'); em.shr_r32_imm8('r10',16); em.cmp_r32_imm('r10',2); em.jcc(0x85,'wp_child_return')
em.label('wp_cmd_outline_activate'); em.mov_r32_imm('rdx',0x8007); em.xor32('r8'); em.xor32('r9'); em.call_iat('PostMessageW'); em.jmp('wp_child_return')
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
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',4); em.jcc(0x84,'wp_measure_set'); em.cmp_r32_imm('rax',14); em.jcc(0x85,'wp_default')
em.label('wp_measure_set'); em.mov_mreg_imm32('r9',16,30); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Owner-draw status bar and outline rows.
em.label('wp_drawitem')
em.mov_ripmem_r64(bsyms['drawitem_ptr'],'r9')
em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',2); em.jcc(0x84,'wp_draw_status'); em.cmp_r32_imm('rax',4); em.jcc(0x84,'wp_draw_outline'); em.cmp_r32_imm('rax',14); em.jcc(0x84,'wp_draw_outline'); em.cmp_r32_imm('rax',5); em.jcc(0x84,'wp_draw_corner'); em.cmp_r32_imm('rax',6); em.jcc(0x84,'wp_draw_splitter'); em.cmp_r32_imm('rax',7); em.jcc(0x84,'wp_draw_gutter'); em.cmp_r32_imm('rax',15); em.jcc(0x84,'wp_draw_gutter'); em.cmp_r32_imm('rax',16); em.jcc(0x84,'wp_draw_files_header'); em.cmp_r32_imm('rax',17); em.jcc(0x84,'wp_draw_outline_header'); em.cmp_r32_imm('rax',18); em.jcc(0x84,'wp_draw_panel_divider'); em.jmp('wp_default')

# V8.6.1：当前 owner-draw 行属于哪个 ListBox（ID 14 = 文件面板，其余 = 大纲）。
# 行文本与"行类型表"必须来自同一个控件。
em.label('wp_row_hwnd')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',14); em.jcc(0x84,'wp_row_hwnd_files')
em.mov_r64_ripmem('rax',bsyms['hwnd_outline']); em.emit(0xC3)
em.label('wp_row_hwnd_files'); em.mov_r64_ripmem('rax',bsyms['hwnd_files']); em.emit(0xC3)

# V8.6.1 面板框架：分界线背景 + 两个标题栏（背景与左对齐小标题）。
em.label('wp_draw_panel_divider')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_splitter']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

def emit_panel_header(title_sym, tag):
    em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_status']); em.call_iat('FillRect')
    em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_hdr_light_' + tag)
    em.mov_r32_imm('rdx',0x00E6E6E6); em.jmp('wp_hdr_color_' + tag)
    em.label('wp_hdr_light_' + tag); em.mov_r32_imm('rdx',0x00202020)
    em.label('wp_hdr_color_' + tag); em.call_iat('SetTextColor')
    em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r32_imm('rdx',1); em.call_iat('SetBkMode')
    # SetBkMode 会破坏 volatile 的 R9：重新加载 drawitem 指针再读矩形。
    em.mov_r64_ripmem('r9',bsyms['drawitem_ptr'])
    em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_mreg('rax','r9',40); em.mov_ptr_r32('rcx','rax')
    em.mov_r32_mreg('rax','r9',44); em.mov_mreg_reg32('rcx',4,'rax')
    em.mov_r32_mreg('rax','r9',48); em.mov_mreg_reg32('rcx',8,'rax')
    em.mov_r32_mreg('rax','r9',52); em.mov_mreg_reg32('rcx',12,'rax')
    em.mov_r32_mreg('rax','rcx',0); em.add_r32_imm8('rax',10); em.mov_ptr_r32('rcx','rax')
    em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.lea_rip('rdx',rsyms[title_sym]); em.mov_r32_imm('r8',0xFFFFFFFF); em.lea_rip('r9',bsyms['draw_rect']); em.mov_mrsp_imm32(0x20,0x0824); em.call_iat('DrawTextW')
    em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_draw_files_header'); emit_panel_header('panel_files', 'files')
em.label('wp_draw_outline_header'); emit_panel_header('panel_outline', 'outline')

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

# Permanent Outline scrollbar gutter background.
em.label('wp_draw_gutter')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Palette-driven overlay scrollbar.  The full gutter is always painted with the
# Outline surface; only the thumb appears on hover/drag, so theme behavior is deterministic.
em.label('wp_draw_scrollbar')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.mov_r32_ripmem('rax',bsyms['outline_scroll_visible']); em.test32('rax'); em.jcc(0x84,'wp_draw_scrollbar_done')
# Copy the cached thumb RECT; painting never derives independent geometry.
em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_ripmem('rax',bsyms['outline_thumb_rect']); em.mov_ptr_r32('rcx','rax')
em.mov_r32_ripmem('rax',bsyms['outline_thumb_rect']+4); em.mov_mreg_reg32('rcx',4,'rax')
em.mov_r32_ripmem('rax',bsyms['outline_thumb_rect']+8); em.mov_mreg_reg32('rcx',8,'rax')
em.mov_r32_ripmem('rax',bsyms['outline_thumb_rect']+12); em.mov_mreg_reg32('rcx',12,'rax')
# Dragging uses the hot brush; hover uses normal thumb brush.
em.mov_r32_ripmem('rax',bsyms['outline_scroll_drag']); em.test32('rax'); em.jcc(0x84,'wp_scroll_normal_brush'); em.mov_r64_ripmem('r8',bsyms['hbrush_scroll_hot']); em.jmp('wp_scroll_fill')
em.label('wp_scroll_normal_brush'); em.mov_r64_ripmem('r8',bsyms['hbrush_scroll_thumb'])
em.label('wp_scroll_fill'); em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.lea_rip('rdx',bsyms['draw_rect']); em.call_iat('FillRect')
em.label('wp_draw_scrollbar_done'); em.mov_r32_imm('rax',1); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

# Outline: 30px rows, per-level accent colors, selection surface, more breathing room.
em.label('wp_draw_outline')
em.mov_ripmem_imm32(bsyms['draw_old_font'],0)
em.mov_ripmem_imm32(bsyms['draw_savedc'],0)
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('r10','r9',8); em.cmp_r32_imm('r10',0xFFFFFFFF); em.jcc(0x84,'wp_draw_outline_done')
# Explicitly select the current ClearType font into the owner-draw HDC. This
# removes the jagged/default-font first paint that previously disappeared only after zoom.
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_ripmem('rdx',bsyms['hfont_outline']); em.call_iat('SelectObject'); em.mov_ripmem_r64(bsyms['draw_old_font'],'rax')
# SelectObject follows the Windows x64 ABI and may clobber volatile R9.
# V8.4.4 accidentally dereferenced that stale R9 here, crashing as soon as an
# outline item was owner-drawn (normally immediately after opening any file).
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr'])
# V8.4.23: hard-isolate owner-drawn Outline rows from the native scrollbar gutter.
# Clamping DrawText alone was insufficient because FillRect/selection painting could still
# cover an overlay-style themed scrollbar. Save the supplied HDC state, intersect its clip
# with the item content area to the LEFT of the scrollbar gutter, and keep that clip active
# for ALL row painting (background + text). Nothing in this owner-draw path can physically
# reach the scrollbar strip after this point.
# Start with a copy of the item's RECT in draw_rect.
em.mov_r32_mreg('rax','r9',40); em.lea_rip('rcx',bsyms['draw_rect']); em.mov_ptr_r32('rcx','rax')
em.mov_r32_mreg('rax','r9',44); em.mov_mreg_reg32('rcx',4,'rax')
em.mov_r32_mreg('rax','r9',48); em.mov_mreg_reg32('rcx',8,'rax')
em.mov_r32_mreg('rax','r9',52); em.mov_mreg_reg32('rcx',12,'rax')
# The ListBox physically ends before the permanent gutter, so its full client
# width is safe. Keep only a 4px internal breathing margin.
em.mov_r64_ripmem('rcx',bsyms['hwnd_outline']); em.lea_rip('rdx',bsyms['rect']); em.call_iat('GetClientRect')
em.mov_r32_ripmem('r10',bsyms['rect']+8); em.sub_r32_imm8('r10',4)
# Never let the clip right exceed the actual item right.
em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_mreg('r11','rcx',8); em.cmp_r32_r32('r11','r10'); em.jcc(0x86,'outline_clip_right_ready'); em.mov_mreg_reg32('rcx',8,'r10')
em.label('outline_clip_right_ready')
# Save HDC and intersect clip to [item.left,item.top,safeRight,item.bottom].
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.call_iat('SaveDC'); em.mov_ripmem_r32(bsyms['draw_savedc'],'rax')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32)
em.lea_rip('rax',bsyms['draw_rect']); em.mov_r32_mreg('rdx','rax',0); em.mov_r32_mreg('r8','rax',4); em.mov_r32_mreg('r9','rax',8); em.mov_r32_mreg('r10','rax',12); em.mov_mrsp_reg32(0x20,'r10'); em.call_iat('IntersectClipRect')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr'])
# selected state chooses a slightly lighter surface, otherwise regular outline brush.
em.mov_r32_mreg('rax','r9',16); em.and_r32_imm('rax',1); em.test32('rax'); em.jcc(0x84,'wp_outline_fill_normal')
em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_outline_fill_sel_light'); em.mov_r64_ripmem('r8',bsyms['hbrush_edit']); em.call_iat('FillRect'); em.jmp('wp_outline_text')
em.label('wp_outline_fill_sel_light'); em.mov_r64_ripmem('r8',bsyms['hbrush_edit']); em.call_iat('FillRect'); em.jmp('wp_outline_text')
em.label('wp_outline_fill_normal'); em.mov_r64_mreg('rcx','r9',32); em.mov_r64_r64('rdx','r9'); em.add_r64_imm8('rdx',40); em.mov_r64_ripmem('r8',bsyms['hbrush_outline']); em.call_iat('FillRect')
em.label('wp_outline_text')
# Fetch item text from the ListBox this row belongs to (ID decides).
em.call_label('wp_row_hwnd'); em.mov_r64_r64('rcx','rax')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('r10','r9',8); em.mov_r32_imm('rdx',0x0189); em.mov_r32_r32('r8','r10'); em.lea_rip('r9',bsyms['outline_titlebuf']); em.call_iat('SendMessageW')
# V8.6.1：文件面板（ID 14）的行按 workspace 条目表着色，绝不读 outline_level
# ——那是一套不同的索引空间。目录用强调色，文件用正文色。
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',4); em.cmp_r32_imm('rax',14); em.jcc(0x84,'wp_file_row_branch')
em.jmp('wp_outline_level_row')
em.label('wp_file_row_branch')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',8)
em.mov_r32_r32('rcx','rax'); em.shl_r32_imm8('rcx',9); em.shl_r32_imm8('rax',5); em.add_r32_r32('rax','rcx')
em.mov_r64_ripmem('rcx',bsyms['ws_entries']); em.test64('rcx'); em.jcc(0x84,'wp_draw_outline_done')
em.add_r64_r64('rax','rcx'); em.mov_r32_mreg('r10','rax',WS_OFF_KIND)
em.mov_r32_ripmem('rax',bsyms['theme_dark']); em.test32('rax'); em.jcc(0x84,'wp_outline_file_light')
em.test32('r10'); em.jcc(0x84,'wp_outline_dark_file')
em.mov_r32_imm('rdx',0x00F4C843); em.jmp('wp_outline_color_send')
em.label('wp_outline_dark_file'); em.mov_r32_imm('rdx',0x00D4D4D4); em.jmp('wp_outline_color_send')
em.label('wp_outline_file_light')
em.test32('r10'); em.jcc(0x84,'wp_outline_light_file')
em.mov_r32_imm('rdx',0x00D78F0B); em.jmp('wp_outline_color_send')
em.label('wp_outline_light_file'); em.mov_r32_imm('rdx',0x00202020); em.jmp('wp_outline_color_send')
# level = outline_level[itemID]
em.label('wp_outline_level_row')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r32_mreg('rax','r9',8); em.add_r32_r32('rax','rax'); em.add_r32_r32('rax','rax'); em.mov_r64_ripmem('rcx',bsyms['outline_level']); em.add_r64_r64('rcx','rax'); em.mov_r32_ptr('r10','rcx')
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
# draw_rect is already clipped to the permanent scrollbar-safe content area;
# add only the 8px left text inset before DrawTextW.
em.lea_rip('rcx',bsyms['draw_rect']); em.mov_r32_mreg('rax','rcx',0); em.add_r32_imm8('rax',8); em.mov_ptr_r32('rcx','rax')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.lea_rip('rdx',bsyms['outline_titlebuf']); em.mov_r32_imm('r8',0xFFFFFFFF); em.lea_rip('r9',bsyms['draw_rect']); em.mov_mrsp_imm32(0x20,0x0824); em.call_iat('DrawTextW')
em.label('wp_draw_outline_done')
# Restore the caller's HDC clip/state if this row established a scrollbar-safe clip.
em.mov_r32_ripmem('rdx',bsyms['draw_savedc']); em.test32('rdx'); em.jcc(0x84,'wp_draw_outline_clip_restored')
em.mov_r64_ripmem('r9',bsyms['drawitem_ptr']); em.mov_r64_mreg('rcx','r9',32); em.call_iat('RestoreDC')
em.label('wp_draw_outline_clip_restored')
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
# Splitter, permanent Outline gutter and lower-right corner each own a palette surface.
em.mov_r64_ripmem('rax',bsyms['hwnd_splitter']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_static_gutter_check')
em.mov_r64_ripmem('rax',bsyms['hbrush_splitter']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_static_gutter_check'); em.mov_r64_ripmem('rax',bsyms['hwnd_outline_gutter']); em.cmp_r64_r64('r9','rax'); em.jcc(0x85,'wp_static_corner')
em.mov_r64_ripmem('rax',bsyms['hbrush_outline']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)
em.label('wp_static_corner'); em.mov_r64_ripmem('rax',bsyms['hbrush_status']); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.label('wp_destroy')
em.xor32('rcx'); em.call_iat('PostQuitMessage'); em.xor32('rax'); em.add_r64_imm8('rsp',0x38); em.emit(0xC3)

em.patch()
text=em.b
if len(text) >= (RDATA_RVA-TEXT_RVA):
    raise RuntimeError(f'text too large: {len(text):x}')

# ---------------------------------------------------------------------------
# V8.4.24 稳定化回归自检（构建期确定性门禁，AGENTS 规则 12）：
# 任一断言失败即中止构建、不产出 EXE，防止已修复缺陷随后续编辑静默回退。
_code = bytes(em.b)

def _jcc_ccs(label):
    # 返回所有跳往 label 的近跳转 jcc 的条件码（0F cc rel32 中的 cc）。
    return [_code[p-1] for (p, l) in em.fix if l == label and _code[p-2] == 0x0F]

# (a) thumb 比例分支：需要滚动（visibleRows<count）必须以 JB(0x82) 进入比例
#     计算。回退为 JAE(0x83) 会让 thumb 占满轨道、travel=0、列表永远拖不动
#     （P0-002 主根因）。
assert _jcc_ccs('sync_thumb_calc') == [0x82], 'sync_thumb_calc 必须为 JB(0x82)'
# (b) 拖动钳制必须用有符号比较：JGE(0x8D) 下限 / JLE(0x8E) 上限。无符号
#     JAE/JBE 会把负偏移当巨大正数，鼠标拖到客户区上方时 thumb 会瞬跳到底部。
assert _jcc_ccs('os_drag_after_top') == [0x8D], 'os_drag_after_top 必须为 JGE(0x8D)'
assert _jcc_ccs('os_drag_pos_ok') == [0x8E], 'os_drag_pos_ok 必须为 JLE(0x8E)'
# (c) LBUTTONDOWN 命中测试必须消费 MSG.pt（消息入队坐标）：mov eax,[r12+36]
#     与 mov eax,[r12+40] 必须出现在 lbuttondown_event..lbuttonup_event 区间，
#     不得回退为 GetCursorPos 的“此刻”坐标（快速拖动时命中判错）。
_lb = em.labels['lbuttondown_event']; _lu = em.labels['lbuttonup_event']
_seg = _code[_lb:_lu]
assert b'\x41\x8b\x44\x24\x24' in _seg and b'\x41\x8b\x44\x24\x28' in _seg, \
    'LBUTTONDOWN 必须读取 MSG.pt 而非 GetCursorPos'
# (d) thumb 最小高度统一 32：全部 4 处 imm 直写 outline_scroll_thumb_h 的
#     指令（C7 05 disp32 imm32）必须写 32；出现 24 即一致性回退。
_th = bsyms['outline_scroll_thumb_h']; _n = 0
for _p in range(len(_code) - 10):
    if _code[_p:_p+2] == b'\xc7\x05':
        _d = int.from_bytes(_code[_p+2:_p+6], 'little', signed=True)
        if TEXT_RVA + _p + 10 + _d == _th:
            assert int.from_bytes(_code[_p+6:_p+10], 'little') == 32, \
                'thumb 最小高度必须统一 32'
            _n += 1
assert _n == 4, 'outline_scroll_thumb_h 的 imm 直写应恰好 4 处，实际 %d' % _n
print('stabilization regression assertions passed: '
      'thumb-ratio=JB, drag-clamp=JGE/JLE, LBUTTONDOWN=MSG.pt, thumb-min=32x4')

# ---------------------------------------------------------------------------
# V8.4.25 统一扫描回归自检（构建期确定性门禁，AGENTS 规则 12）：
# (e) 结构断言：outline_push 存在且恰好由 pv8 循环调用一次；旧的双解析
#     例程与 heading_index BSS 已彻底移除；update_preview 准备段保留
#     "冻结重绘 + LB_RESETCONTENT" 语义。
assert 'outline_push' in em.labels, 'outline_push 例程必须存在'
_pv0 = em.labels['pv8_loop']; _pv1 = em.labels['pv8_eof']
_calls = 0
for (_p, _l) in em.fix:
    if _l == 'outline_push' and _code[_p-1] == 0xE8:
        assert _pv0 <= _p - 1 < _pv1, 'outline_push 必须在 pv8_loop..pv8_eof 区间内被调用'
        _calls += 1
assert _calls == 1, f'pv8 循环应恰好调用 outline_push 一次，实际 {_calls}'
for _dead in ('rebuild_outline', 'add_outline_heading', 'outline_scan_loop',
              'pv8_heading_map_done', 'outline_rebuild_ret'):
    assert _dead not in em.labels, f'旧双解析例程 {_dead} 不应再存在'
assert 'heading_index' not in bsyms, 'heading_index BSS 应已删除'
_up0 = em.labels['update_preview']; _up1 = em.labels['pv_scan_prep_done']
assert b'\xba\x84\x01\x00\x00' in _code[_up0:_up1], \
    'update_preview 准备段必须发送 LB_RESETCONTENT(0x0184)'
print('unified-scan structure assertions passed: '
      'outline_push called once inside pv8 loop, legacy scanners removed')

# (f) 双写对照（Python 语义仿真）：精确复刻旧 rebuild_outline 的标题识别
#     （不跟踪围栏）与新统一扫描的标题识别（跟踪围栏），对 tests/ 全部
#     语料与合成边界用例断言：旧结果剔除围栏内伪标题后 == 新结果。
#     证明统一扫描除"围栏内伪标题不再进入大纲"这一修复点外，与旧行为
#     逐条目一致（含 <=3 前导空格、1-6 个 # 加空格、CR/LF/CRLF 混合
#     换行语义）。容量上限不参与对照：旧扫描器让围栏内伪标题占用 2048
#     名额、挤出真标题，统一扫描不占——这是修复点的一部分而非分歧，
#     因此两侧仿真均收集全部条目后再截断，只对照解析规则本身。
def _old_outline_scan(text):
    out = []; pos = 0; line_start = True; n = len(text)
    while pos < n:
        c = text[pos]
        if c == '\n':
            pos += 1; line_start = True; continue
        if not line_start:
            pos += 1; continue
        lead = 0
        while pos < n and text[pos] == ' ' and lead < 3:
            pos += 1; lead += 1
        if pos >= n or text[pos] != '#':
            line_start = False; pos += 1; continue
        hashes = 0; p = pos
        while p < n and text[p] == '#' and hashes < 6:
            hashes += 1; p += 1
        if hashes == 0 or p >= n or text[p] != ' ':
            line_start = False; pos += 1; continue
        out.append((pos, hashes))
        while pos < n and text[pos] not in ('\r', '\n'):
            pos += 1
        line_start = False
    return out

def _unified_scan(text):
    heads = []; spans = []; pos = 0; line_start = True; fence = False; n = len(text)
    while pos < n:
        if line_start:
            lead = 0; p = pos
            while p < n and text[p] == ' ' and lead < 3:
                p += 1; lead += 1
            if p + 2 < n and text[p] == '`' and text[p+1] == '`' and text[p+2] == '`':
                fence = not fence
                if fence: spans.append([p, n])
                else: spans[-1][1] = p
                pos = p
                while pos < n and text[pos] != '\n':
                    pos += 1
                if pos < n:
                    pos += 1
                line_start = True; continue
            if not fence and p < n and text[p] == '#':
                hashes = 0; q = p
                while q < n and text[q] == '#' and hashes < 6:
                    hashes += 1; q += 1
                if hashes > 0 and q < n and text[q] == ' ':
                    heads.append((p, hashes))
                    pos = q + 1; line_start = False; continue
            # 普通行：与 pv8_normal_line 一致，pos 保持在行首原位（不消费
            # 任何字符），由下方统一路径逐字符推进——空行的 LF 因此正确
            # 开启下一行的行首状态。
            line_start = False; continue
        if text[pos] == '\n':
            pos += 1; line_start = True; continue
        pos += 1
    return heads, spans

def _in_fences(pos, spans):
    return any(a <= pos < b for (a, b) in spans)

_cases = {}
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for _f in sorted(glob.glob(os.path.join(_project_root, 'tests', '*.md'))):
    with open(_f, 'r', encoding='utf-8-sig', newline='') as _fh:
        _cases[os.path.basename(_f)] = _fh.read()
_cases['synthetic_fence_heading.md'] = (
    '# A\n## B\n```\n# fence pseudo\nstill fence\n```\n## C\n'
    '```py\n# another pseudo\n```\n# D\n')
_cases['synthetic_edges.md'] = (
    '####### seven not heading\n#nospace not heading\n'
    '   # three-space indent is heading\n    # four-space indent not heading\n'
    '# CR heading\r\n## LF heading\n### CRLF heading\r\n#### tail no newline')

for _name, _text in _cases.items():
    _old = _old_outline_scan(_text)
    _new, _spans = _unified_scan(_text)
    _old_filtered = [(p, lv) for (p, lv) in _old if not _in_fences(p, _spans)]
    assert _old_filtered == _new, (
        f'语料 {_name} 双写对照失败：旧扫描剔除围栏内伪标题后应与统一扫描一致')
print(f'unified-scan parity assertions passed: {len(_cases)} corpora agree')

# ---------------------------------------------------------------------------
# V8.5.0 架构不变量断言（AGENTS 规则 1/2/6，构建期确定性门禁）：
# 生成器是机器码的唯一真理源（发射确定性），因此对其自身源码做归属
# 静态检查等价于对最终字节做检查。三条不变量：
#   (A) preview_flag 写点只允许出现在初始化区与 set_view_mode 家族；
#   (B) 对 hwnd_edit/hwnd_preview 的 ShowWindow 只允许出现在
#       set_view_mode_commit/set_view_source 与 load_model_into_editor
#       的防闪烁配对内；
#   (C) 文档/大纲子窗口的 MoveWindow/SetWindowPos 只允许出现在
#       resize_children 家族与 repaint_splitter_surface（Z 序维护）。
#   (D) 视图状态调和彻底退役：机器码不再调用 IsWindowVisible。
_this_src_lines = open(os.path.abspath(__file__), encoding='utf-8').read().split('\n')
# 截断到本断言块之前：断言源码自身含 'call_iat(...)' 等字符串字面量，
# 若不截断会被扫描逻辑自噬（最后一个 em.label 段延伸到文件尾）。
_ab_start = next(_i for _i, _ln in enumerate(_this_src_lines)
                 if 'V8.5.0 架构不变量断言' in _ln)
_scan_lines = _this_src_lines[:_ab_start]
_re = __import__('re')
_seg = []  # (例程名, 起始行 idx)
for _i, _ln in enumerate(_this_src_lines):
    _m = _re.search(r"em\.label\('(\w+)'\)", _ln)
    if _m:
        _seg.append((_m.group(1), _i))
def _owner(line_idx):
    """返回行所属例程；初始化区返回 '<INIT>'。"""
    _cur = '<INIT>'
    for _name, _start in _seg:
        if _start <= line_idx:
            _cur = _name
        else:
            break
    return _cur

# (A) preview_flag 唯一写者
_flag_writers = set()
for _i, _ln in enumerate(_scan_lines):
    if _re.search(r"mov_ripmem_imm32\(bsyms\['preview_flag'\]|mov_ripmem_r32\(bsyms\['preview_flag'\]", _ln):
        _flag_writers.add(_owner(_i))
assert _flag_writers <= {'<INIT>', 'entry_first_run', 'set_view_mode', 'set_view_mode_prepare'}, \
    f'架构违规：preview_flag 出现家族外写点 {_flag_writers - {"<INIT>", "entry_first_run", "set_view_mode", "set_view_mode_prepare"}}'

# (B) 文档表面 ShowWindow 唯一写者：call_iat('ShowWindow') 前两行内装载
#     hwnd_edit/hwnd_preview 到 rcx 的调用点必须在白名单例程内。
_surf_owners = set()
for _i, _ln in enumerate(_scan_lines):
    if "call_iat('ShowWindow')" in _ln:
        _ctx = '\n'.join(_scan_lines[max(0, _i - 2):_i + 1])
        if "hwnd_edit" in _ctx or "hwnd_preview" in _ctx:
            _surf_owners.add(_owner(_i))
assert _surf_owners <= {'set_view_mode_commit', 'set_view_source', 'load_model_into_editor'}, \
    f'架构违规：文档表面 ShowWindow 出现在家族外例程 {_surf_owners - {"set_view_mode_commit", "set_view_source", "load_model_into_editor"}}'

# (C) 布局唯一几何：文档/大纲子窗口的 MoveWindow/SetWindowPos 必须在
#     resize_children 家族或 repaint_splitter_surface 内。
_geo_owners = set()
_geo_targets = ('hwnd_edit', 'hwnd_preview', 'hwnd_outline', 'hwnd_splitter',
                'hwnd_outline_gutter', 'hwnd_outline_scroll', 'hwnd_status', 'hwnd_corner')
for _i, _ln in enumerate(_scan_lines):
    if ("call_iat('MoveWindow')" in _ln or "call_iat('SetWindowPos')" in _ln):
        _ctx = '\n'.join(_scan_lines[max(0, _i - 3):_i + 1])
        if any(_t in _ctx for _t in _geo_targets):
            _geo_owners.add(_owner(_i))
_layout_family = {'resize_children', 'resize_content', 'resize_doc',
                  'resize_preview_surface', 'repaint_splitter_surface',
                  'rc_usable_ok', 'rc_files_min', 'rc_files_max',
                  'rc_outline_min', 'rc_outline_max'}
assert _geo_owners <= _layout_family, \
    f'架构违规：布局几何出现在 LayoutManager 外的例程 {_geo_owners - _layout_family}'

# (D) 调和逻辑退役：机器码不再调用 IsWindowVisible（导入表亦无此槽）。
assert 'IsWindowVisible' not in imports, 'IsWindowVisible 应已从导入表移除'
for _i, _ln in enumerate(_scan_lines):
    assert "call_iat('IsWindowVisible')" not in _ln, \
        f'架构违规：第 {_i+1} 行仍调用 IsWindowVisible 调和视图状态'
# (E) set_view_mode 家族调用计数（字节级：em.fix 的 E8 patch 点即真实
#     机器码 call 指令）。调用者清单：cmd_new/cmd_open/preview_hide_active
#     → set_view_mode；preview_show → prepare + commit；
#     wrap_style_ready → commit（EDIT 重建后的表面一致性恢复）。
_call_counts = {}
for _p, _l in em.fix:
    if _code[_p - 1] == 0xE8:
        _call_counts[_l] = _call_counts.get(_l, 0) + 1
assert _call_counts.get('set_view_mode', 0) == 3, \
    f"set_view_mode 应有 3 个调用点，实际 {_call_counts.get('set_view_mode', 0)}"
assert _call_counts.get('set_view_mode_prepare', 0) == 1, \
    f"set_view_mode_prepare 应有 1 个调用点，实际 {_call_counts.get('set_view_mode_prepare', 0)}"
assert _call_counts.get('set_view_mode_commit', 0) == 2, \
    f"set_view_mode_commit 应有 2 个调用点，实际 {_call_counts.get('set_view_mode_commit', 0)}"

# (F) Win64 帧纪律弱断言（AGENTS 规则 5 的机械化）：被 call_label 调用
#     的例程，其源码段内第一个嵌套调用（call_iat/call_label/call_r64）
#     之前必须已建立栈帧（sub rsp 或 push）。无嵌套调用的例程天然豁免
#     （如 set_view_mode_prepare）。V8.5.0 首次构建的"打开即崩溃"
#     （set_view_mode 无帧调 ShowWindow，影子空间覆盖返回地址）正是
#     本断言要永久拦截的错误模式。
_routine_targets = set()
for _ln in _scan_lines:
    for _m in _re.finditer(r"call_label\('(\w+)'\)", _ln):
        _routine_targets.add(_m.group(1))
_label_order = list(_seg)
_label_ranges = {}
for _idx, (_name, _start) in enumerate(_label_order):
    _end = _label_order[_idx + 1][1] if _idx + 1 < len(_label_order) else len(_scan_lines)
    _label_ranges[_name] = (_start, _end)
for _name in sorted(_routine_targets):
    if _name not in _label_ranges:
        continue
    _s, _e = _label_ranges[_name]
    _seg_lines = _scan_lines[_s:_e]
    _first_call = None
    for _j, _ln in enumerate(_seg_lines):
        if ('call_iat(' in _ln or 'call_label(' in _ln or 'call_r64(' in _ln):
            _first_call = _j
            break
    if _first_call is None:
        continue
    _before = '\n'.join(_seg_lines[:_first_call])
    assert ('0x48,0x83,0xEC' in _before or '0x48,0x81,0xEC' in _before
            or _re.search(r"emit\(0x5[0-7]\)|emit\(0x41,0x5[0-7]\)", _before)), \
        f'Win64 帧纪律违规：例程 {_name} 的第一个嵌套调用之前没有 sub rsp / push 栈帧建立'

# (G) set_view_mode 家族字节级帧验证：commit 入口必须是 sub rsp,0x28；
#     家族区间内必须恰有两条 add rsp,0x28; ret 出口路径。
_c0 = em.labels['set_view_mode_prepare']; _c1 = em.labels['set_view_source']
_fam = _code[_c0:_c1 + 64]
assert _fam.startswith(bytes.fromhex('4883ec28')) or \
       _code[em.labels['set_view_mode_commit']:em.labels['set_view_mode_commit'] + 4] == bytes.fromhex('4883ec28'), \
    'set_view_mode_commit 入口必须是 sub rsp,0x28（48 83 EC 28）'
_src_exit = _code[em.labels['set_view_source']:]
_addret = bytes.fromhex('4883c428c3')
# set_view_source 段内（到下一个 label 或 64 字节）应有 add rsp,0x28; ret
assert _addret in _src_exit[:64], \
    'set_view_source 出口必须配对 add rsp,0x28; ret（48 83 C4 28 C3）'
_commit_exit = _code[em.labels['set_view_mode_commit']:em.labels['set_view_source']]
assert _addret in _commit_exit, \
    'commit PREVIEW 分支出口必须配对 add rsp,0x28; ret（48 83 C4 28 C3）'
# (H) Document revision ownership: only the two leaf helpers write revision
# fields. User EN_CHANGE advances the document revision; New and each successful
# Open branch commit a fresh clean revision; successful Save marks it saved.
_doc_rev_writers = set()
_saved_rev_writers = set()
for _i, _ln in enumerate(_scan_lines):
    if "mov_ripmem_r64(bsyms['document_revision']" in _ln:
        _doc_rev_writers.add(_owner(_i))
    if "mov_ripmem_r64(bsyms['saved_revision']" in _ln:
        _saved_rev_writers.add(_owner(_i))
assert _doc_rev_writers == {'advance_document_revision_store'}, \
    f'document_revision 唯一写者违规：{_doc_rev_writers}'
assert _saved_rev_writers == {'mark_document_saved'}, \
    f'saved_revision 唯一写者违规：{_saved_rev_writers}'
assert _call_counts.get('commit_clean_document', 0) == 2, \
    f"New + Open 统一提交点应各提交一次 clean revision，实际 {_call_counts.get('commit_clean_document', 0)}"
assert _call_counts.get('advance_document_revision', 0) == 2, \
    f"用户 EN_CHANGE 与 clean helper 应各调用一次 revision advance，实际 {_call_counts.get('advance_document_revision', 0)}"
assert _call_counts.get('mark_document_saved', 0) == 2, \
    f"clean helper 与 Save 成功应调用 mark saved，实际 {_call_counts.get('mark_document_saved', 0)}"
# (I) Dirty state is derived only from the two 64-bit revisions. The leaf helper
# returns normalized 0/1 and cannot write either revision field.
assert bss_sizes['document_revision'] == 8 and bss_sizes['saved_revision'] == 8, \
    'document/saved revision 必须保持 64-bit'
_dirty0 = em.labels['is_document_dirty']
_dirty1 = em.labels['validate_wide_no_nul']
_dirty_code = bytes(_code[_dirty0:_dirty1])
# 按指令模式检查两个叶出口（0x31C0C3 = xor eax,eax; ret，0x31C083C001C3 = 返回 1）。
# 不要用裸 ret 字节计数：RIP 相对 displacement 里可能出现 0xC3。
assert bytes.fromhex('4c39d0') in _dirty_code and \
       bytes.fromhex('31c0c3') in _dirty_code and \
       bytes.fromhex('31c083c001c3') in _dirty_code, \
    'is_document_dirty 必须比较完整 64-bit revision 并保留 clean/dirty 两个叶出口'
assert bytes.fromhex('488905') not in _dirty_code and bytes.fromhex('4c8905') not in _dirty_code, \
    'is_document_dirty 必须是只读推导，禁止写入 revision state'
# (J) New/Open/Close must enter one destructive controller. WM_CLOSE is consumed
# by WndProc and posted to the main loop; only the controller commits Close.
assert _call_counts.get('is_document_dirty', 0) == 1, \
    f"dirty 判定必须只由 destructive controller 调用一次，实际 {_call_counts.get('is_document_dirty', 0)}"
_production_source = '\n'.join(_scan_lines)
assert "em.label('cmd_new'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],1); em.jmp('destructive_request')" in _production_source
assert "em.label('cmd_open'); em.mov_ripmem_imm32(bsyms['pending_destructive_action'],2); em.jmp('destructive_request')" in _production_source
assert "em.label('cmd_exit'); em.jmp('request_close')" in _production_source
assert "em.cmp_r32_imm('rdx',0x0010); em.jcc(0x84,'wp_close')" in _production_source
assert "em.label('destructive_close'); em.mov_r64_r64('rcx','rbx'); em.call_iat('DestroyWindow')" in _production_source
# (K) Save As path transaction: selection remains in temp_path; current_path is
# copied only after the sibling staging file atomically replaces the target.
_saveas_src = _production_source[_production_source.index("em.label('cmd_saveas')"):
                                 _production_source.index("em.label('do_save')")]
assert "mov_ripmem_imm32(bsyms['save_target_is_temp'],1)" in _saveas_src
assert "lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW')" not in _saveas_src, \
    'Save As 禁止在磁盘提交前覆盖 current_path'
_save_commit_src = _production_source[_production_source.index("em.label('save_create')"):
                                      _production_source.index("em.label('save_fail_close')")]
_close_pos = _save_commit_src.rindex("call_iat('CloseHandle')")
_replace_pos = _save_commit_src.index("call_iat('MoveFileExW')")
_path_pos = _save_commit_src.index("em.lea_rip('rcx',bsyms['current_path']); em.lea_rip('rdx',bsyms['temp_path']); em.call_iat('lstrcpyW')")
_saved_pos = _save_commit_src.index("call_label('mark_document_saved')")
assert _close_pos < _replace_pos < _path_pos < _saved_pos, \
    'Save As 必须按 close -> atomic replace -> commit path -> mark saved 的顺序提交'
assert "lea_rip('rcx',bsyms['save_stage_path'])" in _save_commit_src
assert "call_iat('FlushFileBuffers')" in _save_commit_src
assert "em.mov_mrsp_imm32(0x20,1)" in _save_commit_src, \
    'staging file 必须使用 CREATE_NEW，禁止覆盖已有恢复文件'
assert "em.mov_r32_imm('r8',9)" in _save_commit_src, \
    'atomic commit 必须请求 REPLACE_EXISTING | WRITE_THROUGH'
_save_failure_src = _production_source[_production_source.index("em.label('save_fail_close')"):
                                       _production_source.index("em.label('err_save')")]
assert "call_iat('CloseHandle')" in _save_failure_src and \
       "call_iat('DeleteFileW')" in _save_failure_src, \
    '写入/刷新/替换失败必须关闭句柄并清理自有 staging file'
# (L) Complete-write ownership: exactly one WriteFile call lives in a back-edge
# loop, and io_count==0 / io_count>remaining both reach the failure cleanup.
_write_src = _production_source[_production_source.index("em.label('save_write_loop')"):
                                _production_source.index("em.label('save_write_complete')")]
assert _write_src.count("call_iat('WriteFile')") == 1
assert "mov_r32_ripmem('rax',bsyms['io_count']); em.test32('rax'); em.jcc(0x84,'save_fail_close')" in _write_src
assert "em.cmp_r32_r32('rax','r15'); em.jcc(0x87,'save_fail_close')" in _write_src
assert "em.add_r64_r64('r14','rax'); em.sub_r32_r32('r15','rax'); em.jmp('save_write_loop')" in _write_src
assert ('injected_WriteFile' in em.labels) == WRITE_CALL_INJECTED
assert ('injected_FlushFileBuffers' in em.labels) == (WRITE_INJECTION_MODE == 'flush_failure')
assert ('injected_MoveFileExW' in em.labels) == (WRITE_INJECTION_MODE == 'replace_failure')
assert ('injected_CreateFileW' in em.labels) == (WRITE_INJECTION_MODE == 'create_failure')
assert ('injected_CloseHandle' in em.labels) == (WRITE_INJECTION_MODE == 'close_failure')
_recovery_src = _production_source[_production_source.index("em.label('save_create_failed')"):
                                   _production_source.index("em.label('destructive_request')")]
assert "em.label('save_create_failed'); em.call_iat('GetLastError')" in _recovery_src
assert "em.cmp_r32_imm('rax',80)" in _recovery_src and "em.cmp_r32_imm('rax',183)" in _recovery_src
assert "lea_rip('rdx',rsyms['err_recovery_exists'])" in _recovery_src, \
    'staging collision 必须保留恢复文件并显示专用可行动提示'
_open_src = _production_source[_production_source.index("em.label('cmd_open_dialog')"):
                               _production_source.index("em.label('cmd_save')")]
assert "em.mov_r32_imm('rcx',65001); em.mov_r32_imm('rdx',8)" in _open_src
assert "fallback CP_ACP" not in _open_src and "em.xor32('rcx'); em.xor32('rdx')" not in _open_src
assert _open_src.count("em.label('open_commit')") == 1 and \
       _open_src.count("call_label('commit_clean_document')") == 1
assert "candidate_encoding_state" in _open_src and "candidate_eol_state" in _open_src
_open_commit_src = _open_src[_open_src.index("em.label('open_commit')"):]
assert "mov_ripmem_r32(bsyms['encoding_state'],'rax')" in _open_commit_src and \
       "mov_ripmem_r32(bsyms['eol_state'],'rax')" in _open_commit_src, \
    'Open must commit encoding and EOL metadata only at open_commit'
assert "call_label('validate_wide_no_nul')" in _open_src
assert ((1901, 'cmd_open_selected') in _command_routes) == OPEN_TEST_BUILD, \
    'Open picker bypass command must exist only in the explicit test build'
_read_src = _open_src[_open_src.index("em.label('open_read_loop')"):
                      _open_src.index("em.label('open_read_complete')")]
assert "mov_r32_ripmem('rax',bsyms['io_count']); em.test32('rax'); em.jcc(0x84,'read_fail_close')" in _read_src
assert "em.cmp_r32_r32('rax','r15'); em.jcc(0x87,'read_fail_close')" in _read_src
assert "em.add_r64_r64('r14','rax'); em.sub_r32_r32('r15','rax'); em.jmp('open_read_loop')" in _read_src
assert ('injected_ReadFile' in em.labels) == (OPEN_READ_INJECTION_MODE != 'release')
assert ('injected_OutlineVirtualAlloc' in em.labels) == \
       OUTLINE_ALLOC_INJECTED
assert ('injected_StyleVirtualAlloc' in em.labels) == STYLE_ALLOC_INJECTED
assert "call_label('candidate_normalized_length')" in _open_src and \
       "call_label('ensure_outline_arena')" in _open_src
_first_model_write = min(_open_src.index("call_label('normalize_to_document_model')"),
                         _open_src.index("em.mov_r64_ripmem('rax',bsyms['document_model']); em.mov_word_ptr_reg_zero('rax')"))
assert _open_src.index("call_label('ensure_outline_arena')") < _first_model_write, \
    'Open must reserve Outline capacity before mutating active DocumentModel'
assert all(bss_sizes[name] == 8 for name in
           ('outline_srcpos','outline_renderpos','outline_level'))
assert 'VirtualAlloc' in IAT and 'VirtualFree' in IAT
_outline_dynamic_src = _production_source[
    _production_source.index("em.label('ensure_outline_arena')"):
    _production_source.index("em.label('prepare_preview_default')")]
assert "call_iat('VirtualAlloc')" in _outline_dynamic_src and \
       "call_iat('VirtualFree')" in _outline_dynamic_src
for _outline_table in ('outline_srcpos','outline_renderpos','outline_level'):
    assert "lea_rip('rcx',bsyms['%s'])" % _outline_table not in _production_source, \
        '%s must be accessed through its dynamic pointer' % _outline_table
# V8.6 Phase E：固定 131072 项样式表已删除，三个表必须经动态 arena 指针访问。
assert all(bss_sizes[name] == 8 for name in
           ('style_start','style_end','style_type')), \
    'style tables must be dynamic arena pointers'
assert bss_sizes['style_capacity'] == 4
assert 'STYLE_CAP' not in _production_source and 'STYLE_CAP' not in globals()
_style_arena_src = _production_source[
    _production_source.index("em.label('ensure_style_arena')"):
    _production_source.index("em.label('ensure_outline_arena')")]
assert "call_iat('VirtualAlloc')" in _style_arena_src or STYLE_ALLOC_INJECTED, \
    'style arena growth must allocate through VirtualAlloc'
assert "call_iat('VirtualFree')" in _style_arena_src, \
    'style arena growth must release the previous arena'
_add_style_src = _production_source[
    _production_source.index("em.label('add_style')"):
    _production_source.index("em.label('ensure_style_arena')")]
for _style_table in ('style_start','style_end','style_type'):
    assert "lea_rip('rcx',bsyms['%s'])" % _style_table not in _production_source, \
        '%s must be accessed through its dynamic pointer' % _style_table
    assert "mov_r64_ripmem('rcx',bsyms['%s'])" % _style_table in _add_style_src or \
           "mov_r64_ripmem('rcx',bsyms['%s'])" % _style_table in _production_source, \
        '%s pointer must be loaded before each span write' % _style_table
assert "mov_r32_ripmem('rax',bsyms['style_capacity'])" in _add_style_src, \
    'add_style must bound writes by the dynamic arena capacity'
_apply_styles_src = _production_source[
    _production_source.index("em.label('apply_styles')"):
    _production_source.index("em.label('styles_done')")]
assert all("mov_r64_ripmem('rcx',bsyms['%s'])" % _style_table
           in _apply_styles_src for _style_table in
           ('style_start','style_end','style_type')), \
    'apply_styles must read the dynamic style arena pointers'
assert "call_label('ensure_style_arena')" in _open_src, \
    'Open must reserve style capacity before mutating active DocumentModel'
assert _open_src.index("call_label('ensure_style_arena')") < _first_model_write, \
    'Open must reserve style capacity before mutating active DocumentModel'
_preview_ensure_src = _production_source[
    _production_source.index("em.label('update_preview')"):
    _production_source.index("em.label('pv_timer_reset_done')")]
assert "call_label('ensure_outline_arena')" in _preview_ensure_src and \
       "call_label('ensure_style_arena')" in _preview_ensure_src, \
    'update_preview must reserve both dynamic arenas before scanning'
# V8.6 Phase E：渲染侧缓冲区（位置映射 + 渲染文本）必须经动态 arena 指针访问。
assert all(bss_sizes[name] == 8 for name in ('render_srcmap','previewbuf')), \
    'render map and preview text must be dynamic arena pointers'
assert bss_sizes['render_arena_capacity'] == 4
for _render_symbol in ('render_srcmap','previewbuf'):
    assert ("lea_rip('rcx',bsyms['%s'])" % _render_symbol) not in _production_source and \
           ("lea_rip('rdi',bsyms['%s'])" % _render_symbol) not in _production_source and \
           ("lea_rip('rdx',bsyms['%s'])" % _render_symbol) not in _production_source, \
        '%s must be accessed through its dynamic pointer' % _render_symbol
_render_arena_src = _production_source[
    _production_source.index("em.label('ensure_render_arena')"):
    _production_source.index("em.label('outline_push')")]
assert "call_iat('VirtualAlloc')" in _render_arena_src or RENDER_ALLOC_INJECTED, \
    'render arena growth must allocate through VirtualAlloc'
assert "call_iat('VirtualFree')" in _render_arena_src, \
    'render arena growth must release the previous arena'
assert "mov_r64_ripmem('rcx',bsyms['render_srcmap'])" in _production_source, \
    'position-map readers must load the arena pointer'
assert "call_label('ensure_render_arena')" in _open_src and \
       _open_src.index("call_label('ensure_render_arena')") < _first_model_write, \
    'Open must reserve render capacity before mutating active DocumentModel'
assert "call_label('ensure_render_arena')" in _preview_ensure_src, \
    'update_preview must reserve the render arena before scanning'
# V8.6 Phase E：document 文本必须经保留区 + 分块提交访问。
assert bss_sizes['document_model'] == 8, \
    'document_model must be a pointer into the reserved arena'
assert all(bss_sizes[name] == 4 for name in
           ('document_capacity','document_reserved','sync_text_len'))
assert "lea_rip('rdi',bsyms['document_model'])" not in _production_source and \
       "lea_rip('rsi',bsyms['document_model'])" not in _production_source, \
    'document readers must load the arena pointer'
_doc_arena_src = _production_source[
    _production_source.index("em.label('ensure_document_arena')"):
    _production_source.index("em.label('outline_push')")]
assert "em.mov_r32_imm('r8',0x2000)" in _doc_arena_src, \
    'document arena must reserve the policy bound once'
assert "em.mov_r32_imm('r8',0x1000)" in _doc_arena_src, \
    'document arena must commit pages in blocks'
assert DOC_COMMIT_CHUNK > 0 and DOC_COMMIT_CHUNK & (DOC_COMMIT_CHUNK-1) == 0, \
    'document commit chunk must be a power of two for masking to be correct'
assert "em.and_r32_imm('r13',~(DOC_COMMIT_CHUNK-1) & 0xFFFFFFFF)" in _doc_arena_src, \
    'document arena must round the request up to a whole commit block'
assert "call_label('ensure_document_arena')" in _open_src and \
       _open_src.index("call_label('ensure_document_arena')") < _first_model_write, \
    'Open must reserve document capacity before mutating active DocumentModel'
assert "call_label('ensure_document_arena')" in _preview_ensure_src, \
    'update_preview must reserve the document arena before scanning'
_sync_src = _production_source[
    _production_source.index("em.label('sync_model_from_editor')"):
    _production_source.index("em.label('load_model_into_editor')")]
assert "call_label('ensure_document_arena')" in _sync_src and \
       "em.label('sync_model_rollback')" in _sync_src, \
    'editor sync must reserve document capacity and roll back on failure'
assert "em.mov_r32_imm('r8',WIDE_CHARS-1)" in _production_source, \
    'editor text limit must keep using the WIDE_CHARS policy bound'
# V8.6 Phase E：解码/编码 scratch 也必须经按需 arena 访问。
assert all(bss_sizes[name] == 8 for name in ('widebuf','bytebuf')), \
    'decode and file-byte buffers must be arena pointers'
assert all(bss_sizes[name] == 4 for name in ('wide_capacity','byte_capacity'))
for _scratch in ('widebuf','bytebuf'):
    assert "lea_rip(" not in "".join(
        "lea_rip('%s',bsyms['%s'])" % (_reg,_scratch)
        for _reg in ('rax','rcx','rdx','r8','r9','r10','r14')
        if "lea_rip('%s',bsyms['%s'])" % (_reg,_scratch) in _production_source), \
        '%s must be accessed through its dynamic pointer' % _scratch
# 这两个例程由 emit_ensure_scratch_arena 模板生成，因此检查生成的标签集合。
for _arena in ('ensure_wide_arena','ensure_byte_arena'):
    assert _arena in em.labels, '%s must be emitted' % _arena
    for _suffix in ('_ready','_ok','_fail','_ret'):
        assert _arena + _suffix in em.labels, \
            '%s must keep its checked growth structure' % _arena
assert "call_label('ensure_byte_arena')" in _production_source and \
       "call_label('ensure_wide_arena')" in _production_source
_read_alloc_src = _production_source[
    _production_source.index("em.label('read_nonempty')"):
    _production_source.index("em.label('open_read_loop')")]
assert "call_label('ensure_byte_arena')" in _read_alloc_src and \
       "call_label('ensure_wide_arena')" in _read_alloc_src and \
       "'open_alloc_close'" in _read_alloc_src, \
    'Open must reserve both scratch arenas before reading and close on failure'
_save_alloc_src = _production_source[
    _production_source.index("em.label('do_save')"):
    _production_source.index("call_label('serialize_preferred_eol')")]
assert "call_label('ensure_wide_arena')" in _save_alloc_src and \
       "call_label('ensure_byte_arena')" in _save_alloc_src, \
    'Save must reserve both scratch arenas before encoding'
assert "mov_mrsp_reg32(0x28,'rax')" in _production_source and \
       "mov_mrsp_imm32(0x28,WIDE_CHARS)" not in _production_source and \
       "BYTE_CAP)" not in _production_source, \
    'encoding APIs must use the published capacities, not compile-time bounds'
assert _production_source.count("call_label('ensure_wide_arena')") >= 4, \
    'decode, save and both search paths must reserve the wide arena'
_save_encode_src = _production_source[_production_source.index("em.label('do_save')"):
                                      _production_source.index("em.label('save_create')")]
assert "call_label('serialize_preferred_eol')" in _save_encode_src
assert "em.label('save_encode_utf8_bom')" in _save_encode_src and \
       "em.label('save_encode_utf16')" in _save_encode_src
assert "mov_ripmem_imm32(bsyms['encoding_state'],0)" not in _save_commit_src, \
    'Save commit must preserve the document encoding metadata'
# (M) Entry point begins with the fixed Win64 stack frame used by the main flow.
_e0 = em.labels['entry_first_run']
assert _e0 == 0 and _code.startswith(bytes.fromhex('4881ec88000000')), \
    'entry point must begin with sub rsp,0x88'

# (N) dispatch 终结断言（退出崩溃根因的防回退门禁）：dispatch_status_done
#     块检查 IsWindow 后必须以 JNE msg_loop + 无条件 jmp exit 终结，绝不
#     允许执行流直落进下一个 label。本断言要永久拦截的错误模式：dispatch
#     尾部 fall through 进 ret 结尾的子程序（无压栈返回地址的 ret = 野返回
#     地址）——v4→V8.5.0 每次关窗 0xC0000005 的真正根因（2026-09-14 由
#     v4 单点修复实验确诊：仅补 jmp exit 即 3/3 干净退出）。
_d0 = em.labels['dispatch_status_done']
_d1 = em.labels['sync_outline_scrollbar']
_dblk = bytes(_code[_d0:_d1])
assert len(_dblk) > 5 and _dblk[-5] == 0xE9, \
    'dispatch_status_done 必须以无条件 jmp（E9）终结：禁止 fall through 进子程序'
assert bytes.fromhex('0f85') in _dblk and bytes.fromhex('85c0') in _dblk, \
    'dispatch_status_done 必须保留 IsWindow 检查（test + JNE msg_loop）'
print('viewstate/layout ownership assertions passed: '
      'preview_flag & doc-surface ShowWindow owned by set_view_mode family, '
      'geometry owned by resize_children family, IsWindowVisible retired, '
      'call-site counts verified (set_view_mode=3, prepare=1, commit=2), '
      'win64 frame discipline enforced (routine prologue + commit byte pattern)')

# ---------------- PE writer ----------------
# ---------------- PE writer (v8: one loader-simple section) ----------------
# Keep the exact RVAs used by the machine-code emitter, but put code, strings,
# import table, and the zero-filled runtime buffers into ONE PE section.
# This mirrors the layout style of the earlier 1.5 KiB build that was confirmed
# to load on Windows, while still leaving the big work buffers as virtual-only
# zero-filled memory rather than storing megabytes of zeros in the file.

# V8.6：文件头需要容纳多个节头，因此头区扩大到 0x400（仍是 FileAlignment 的倍数）。
headers_size = 0x400

# Preserve the existing absolute RVA plan：
#   code  @ 0x1000  （预算 0xF000 = 60KB）
#   rdata @ 0x10000
#   idata @ 0x13000
#   bss   @ 0x14000 (virtual-only tail)
# V8.6：同一份文件布局现在用四个独立节描述，权限按内容分离，
# 而不是把它们并进一个可读可写可执行节。
code_raw = align(len(text), FILE_ALIGN)
rdata_raw = align(len(rdata), FILE_ALIGN)
idata_raw = align(len(idata), FILE_ALIGN)
if len(text) > RDATA_RVA - TEXT_RVA:
    raise RuntimeError('text overlaps rdata')
if len(rdata) > IDATA_RVA - RDATA_RVA:
    raise RuntimeError('rdata overlaps idata')
if len(idata) > BSS_RVA - IDATA_RVA:
    raise RuntimeError('idata overlaps bss')

# V8.6：base relocation 与 ASLR。发射的代码本身只用 RIP 相对寻址（数据经
# lea_rip、外部函数经 IAT），因此没有任何位置需要修正。为了让加载器可以自由
# 选择基址，仍然需要一张有效的重定位表：每个 4 KiB 页一个块，块内条目为
# IMAGE_REL_BASED_ABSOLUTE（0），语义是"该页无需修正"。表在下面与 .pdata 的
# 布局一起生成，因为它必须覆盖到 .reloc 之前的最后一个映像页。
RELOC_RVA = BSS_RVA + BSS_VSIZE

# V8.6：x64 栈回溯元数据（.pdata）。只有非叶子例程需要条目——规范规定找不到
# 函数表项的地址按叶子处理，返回地址就位于 [RSP]。下面从已生成的机器码里解析
# 每个被调用例程的 prologue（push 非易失寄存器序列 + sub rsp,imm），据此生成
# RUNTIME_FUNCTION 与 UNWIND_INFO。无法识别的入口按叶子处理，不产生条目。
_UWOP_PUSH_NONVOL = 0
_UWOP_ALLOC_LARGE = 1
_UWOP_ALLOC_SMALL = 2
# A REX-prefixed 0x54..0x57 is R12..R15; without the prefix the same bytes mean
# RSP/RBP/RSI/RDI. Conflating them produced unwind codes naming the wrong
# registers, which made a debugger find our entries but fail to walk past them.
_PUSH_REG = {0x50: 0, 0x51: 1, 0x52: 2, 0x53: 3,
             0x54: 4, 0x55: 5, 0x56: 6, 0x57: 7}
_PUSH_REG_REX = {0x54: 12, 0x55: 13, 0x56: 14, 0x57: 15}


def _parse_prologue(offset):
    """Return (pushes, alloc, prolog_size) for a non-leaf entry, else None."""
    i = offset
    pushes = []
    while i < len(text):
        byte = text[i]
        if byte in _PUSH_REG:
            pushes.append(_PUSH_REG[byte]); i += 1; continue
        if byte == 0x41 and i + 1 < len(text) and text[i + 1] in _PUSH_REG_REX:
            pushes.append(_PUSH_REG_REX[text[i + 1]]); i += 2; continue
        break
    alloc = None
    if i + 3 < len(text) and text[i] == 0x48 and text[i + 1] == 0x83 and text[i + 2] == 0xEC:
        alloc = text[i + 3]; i += 4
    elif i + 6 < len(text) and text[i] == 0x48 and text[i + 1] == 0x81 and text[i + 2] == 0xEC:
        alloc = struct.unpack_from('<I', text, i + 3)[0]; i += 7
    if alloc is None and not pushes:
        return None
    return pushes, alloc, i - offset


_call_targets = set(re.findall(r"call_label\('([^']+)'\)",
                               open(__file__, encoding='utf-8').read()))
_entries = sorted({em.labels[_name] for _name in _call_targets if _name in em.labels} |
                  {0})
_runtime_functions = []
_unwind_blobs = []
for _offset in _entries:
    _parsed = _parse_prologue(_offset)
    if _parsed is None:
        continue                      # leaf routine: no entry required
    _pushes, _alloc, _prolog = _parsed
    _codes = []
    if _alloc:
        if _alloc <= 128 and _alloc % 8 == 0:
            _codes.append((_prolog, (_alloc // 8 - 1) << 4 | _UWOP_ALLOC_SMALL))
        else:
            _codes.append((_prolog, (_UWOP_ALLOC_LARGE)))
    _cursor = _offset
    for _reg in reversed(_pushes):
        _cursor += 2 if text[_cursor] == 0x41 else 1
        _codes.append((_cursor - _offset, (_reg << 4) | _UWOP_PUSH_NONVOL))
    _unwind = bytearray()
    _unwind.append(1)                 # Version 1
    _unwind.append(0)                 # Flags: no handler, no chain
    _unwind.append(_prolog)
    # CountOfCodes counts 2-byte slots, so UWOP_ALLOC_LARGE contributes one extra
    # slot for its trailing size field (two when the field itself is 4 bytes).
    _large = bool(_alloc) and not (_alloc <= 128 and _alloc % 8 == 0)
    _unwind.append(len(_codes) + (1 if _large else 0))
    _unwind.append(0)                 # FrameRegister/FrameOffset: none
    for _code_off, _code in _codes:
        _unwind.extend(struct.pack('<BB', _code_off, _code))
        if _code == _UWOP_ALLOC_LARGE:
            # The extra data of a large allocation follows its own code entry.
            _unwind.extend(struct.pack('<H', _alloc // 8))
    while len(_unwind) % 4:
        _unwind.append(0)
    _runtime_functions.append((_offset, _unwind))
# UNWIND_INFO lives in .rdata (as linkers do — notepad.exe keeps every unwind
# blob there) and the exception directory size covers only the array, so the
# loader/debugger can binary-search the entries by Size/12.
if len(rdata) % 4:
    rdata.extend(b'\0' * (4 - len(rdata) % 4))
_unwind_rvas = []
for _offset, _blob in _runtime_functions:
    _unwind_rvas.append(RDATA_RVA + len(rdata))
    rdata.extend(_blob)
_pdata_entries = len(_runtime_functions) * 12
pdata_payload = _pdata_entries
pdata_raw = align(pdata_payload, FILE_ALIGN)
PDATA_RVA = RELOC_RVA + 0x1000
_reloc_pages = (PDATA_RVA - TEXT_RVA) // SECT_ALIGN
reloc = bytearray()
for _page_index in range(_reloc_pages):
    reloc.extend(struct.pack('<IIHH', TEXT_RVA + _page_index * SECT_ALIGN, 12, 0, 0))
reloc_size = len(reloc)
reloc_raw = align(reloc_size, FILE_ALIGN)

# Raw layout stays aligned with the RVA plan: a byte at RVA r lives at file
# offset headers_size + (r - TEXT_RVA). Each section then only has to point at
# its own window inside that buffer. Packing the sections tightly instead made
# the loader reject the image (ERROR_BAD_EXE_FORMAT).
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
if len(raw) > BSS_RVA - TEXT_RVA:
    raise RuntimeError('idata overlaps bss')
raw.extend(b'\0' * ((BSS_RVA - TEXT_RVA) - len(raw)))
if len(raw) > RELOC_RVA - TEXT_RVA:
    raise RuntimeError('bss reservation overlaps reloc')
raw.extend(b'\0' * ((RELOC_RVA - TEXT_RVA) - len(raw)))
raw.extend(reloc)
raw.extend(b'\0' * (reloc_raw - reloc_size))

# RUNTIME_FUNCTION 数组按 BeginAddress 升序排列。
_pdata = bytearray()
_bounds = [entry[0] for entry in _runtime_functions]
for _index, (_offset, _blob) in enumerate(_runtime_functions):
    _end = _bounds[_index + 1] if _index + 1 < len(_bounds) else len(text)
    if _end <= _offset:
        raise RuntimeError('runtime function ranges must increase')
    _pdata.extend(struct.pack('<III', TEXT_RVA + _offset, TEXT_RVA + _end,
                              _unwind_rvas[_index]))
assert len(_pdata) == pdata_payload, (len(_pdata), pdata_payload)
raw.extend(b'\0' * ((PDATA_RVA - TEXT_RVA) - len(raw)))
raw.extend(_pdata)
raw.extend(b'\0' * (pdata_raw - pdata_payload))
raw_size = len(raw)

# name, VirtualSize, VirtualAddress, PointerToRawData, SizeOfRawData, Characteristics
# Each section spans the whole gap to the next RVA. A compact layout with
# SizeOfRawData equal to the actual payload made Windows reject the image with
# ERROR_BAD_EXE_FORMAT; the covering form below is the one verified to load.
sections = [
    (b'.text\0\0\0', RDATA_RVA - TEXT_RVA, TEXT_RVA,
     headers_size, RDATA_RVA - TEXT_RVA, 0x60000020),
    (b'.rdata\0\0', IDATA_RVA - RDATA_RVA, RDATA_RVA,
     headers_size + (RDATA_RVA - TEXT_RVA), IDATA_RVA - RDATA_RVA, 0x40000040),
    (b'.idata\0\0', BSS_RVA - IDATA_RVA, IDATA_RVA,
     headers_size + (IDATA_RVA - TEXT_RVA), BSS_RVA - IDATA_RVA, 0xC0000040),
    (b'.bss\0\0\0\0', BSS_VSIZE, BSS_RVA, 0, 0, 0xC0000080),
    (b'.reloc\0\0', reloc_raw, RELOC_RVA,
     headers_size + (RELOC_RVA - TEXT_RVA), reloc_raw, 0x42000040),
    (b'.pdata\0\0', pdata_raw, PDATA_RVA,
     headers_size + (PDATA_RVA - TEXT_RVA), pdata_raw, 0x40000040),
]
size_image = align(PDATA_RVA + pdata_raw, SECT_ALIGN)

hdr = bytearray(b'\0' * headers_size)
hdr[0:2] = b'MZ'
struct.pack_into('<I', hdr, 0x3c, 0x80)
dosmsg = b'This program cannot be run in DOS mode.\r\r\n$'
hdr[0x40:0x40+len(dosmsg)] = dosmsg
p = 0x80
hdr[p:p+4] = b'PE\0\0'; p += 4

# COFF header: AMD64, one section per region, executable + large-address-aware.
struct.pack_into('<HHIIIHH', hdr, p, 0x8664, len(sections), 0, 0, 0, 0xF0, 0x0022); p += 20

opt = bytearray(b'\0' * 0xF0)
init_data = rdata_raw + idata_raw
struct.pack_into('<HBBIII', opt, 0, 0x20B, 14, 0, code_raw, init_data, BSS_VSIZE)
struct.pack_into('<II', opt, 16, TEXT_RVA, TEXT_RVA)
struct.pack_into('<Q', opt, 24, IMAGE_BASE)
struct.pack_into('<II', opt, 32, SECT_ALIGN, FILE_ALIGN)
struct.pack_into('<HHHHHH', opt, 40, 6, 0, 0, 0, 6, 0)
struct.pack_into('<I', opt, 52, 0)
struct.pack_into('<II', opt, 56, size_image, headers_size)
struct.pack_into('<I', opt, 64, 0)
struct.pack_into('<HH', opt, 68, 2, DLL_CHARACTERISTICS)  # GUI, NX_COMPAT | DYNAMIC_BASE
struct.pack_into('<QQQQ', opt, 72, 0x100000, 0x1000, 0x100000, 0x1000)
struct.pack_into('<II', opt, 104, 0, 16)
struct.pack_into('<II', opt, 112 + 8*1, IDATA_RVA, IMPORT_DESC_SIZE)
struct.pack_into('<II', opt, 112 + 8*3, PDATA_RVA, pdata_payload)
struct.pack_into('<II', opt, 112 + 8*5, RELOC_RVA, reloc_size)
struct.pack_into('<II', opt, 112 + 8*12, IAT_RVA, IAT_SIZE)
hdr[p:p+0xF0] = opt; p += 0xF0

# V8.6：可执行代码与数据分离。.text 只读可执行，.rdata 只读，.idata 读写
# （导入表与 IAT 由加载器写入），.bss 读写且不占文件空间。可写数据不再可执行。
for _name, _vsize, _va, _ptr, _rsize, _chars in sections:
    shdr = _name + struct.pack('<IIIIIIHHI', _vsize, _va, _rsize, _ptr, 0, 0, 0, 0, _chars)
    hdr[p:p+40] = shdr; p += 40

if p > headers_size:
    raise RuntimeError('section table overlaps first section data')

# (P) V8.6 节权限分离断言（防回退门禁）。本断言要永久拦截的错误模式：
#     把代码与数据重新并回一个可读可写可执行节，或让节区间互相重叠。
_EXPECTED_SECTIONS = {
    b'.text': 0x60000020,    # CODE | EXECUTE | READ
    b'.rdata': 0x40000040,   # INITIALIZED_DATA | READ
    b'.idata': 0xC0000040,   # INITIALIZED_DATA | READ | WRITE
    b'.bss': 0xC0000080,     # UNINITIALIZED_DATA | READ | WRITE
    b'.reloc': 0x42000040,   # INITIALIZED_DATA | DISCARDABLE | READ
    b'.pdata': 0x40000040,   # INITIALIZED_DATA | READ
}
assert len(sections) == 6, 'the image must declare exactly six sections'
_prev_va_end = 0
_prev_raw_end = 0
for _name, _vsize, _va, _ptr, _rsize, _chars in sections:
    _key = _name.split(b'\0', 1)[0]
    assert _key in _EXPECTED_SECTIONS, 'unexpected section %r' % _key
    assert _chars == _EXPECTED_SECTIONS[_key], \
        '%s characteristics 0x%08X do not match the declared permissions' % (
            _key.decode(), _chars)
    if _key != b'.text':
        assert not (_chars & 0x20000000), \
            '%s must not be executable' % _key.decode()
    assert _va % SECT_ALIGN == 0, '%s RVA must be section aligned' % _key.decode()
    assert _va >= _prev_va_end, '%s RVA overlaps the previous section' % _key.decode()
    if _rsize:
        assert _ptr % FILE_ALIGN == 0, \
            '%s raw pointer must be file aligned' % _key.decode()
        assert _ptr >= _prev_raw_end, '%s raw data overlaps' % _key.decode()
        assert _ptr + _rsize <= headers_size + raw_size, \
            '%s raw data exceeds the file image' % _key.decode()
    else:
        assert _key == b'.bss', 'only .bss may omit raw data'
    _prev_va_end = align(_va + max(_vsize, _rsize), SECT_ALIGN)
    _prev_raw_end = _ptr + _rsize
assert sections[0][5] & 0x20000000, '.text must stay executable'
assert size_image >= _prev_va_end, 'SizeOfImage must cover every section'
assert not any(chars & 0x20000000 and chars & 0x80000000 for _, _, _, _, _, chars in sections), \
    'no section may be both writable and executable'
# (Q) ASLR / 重定位断言：无绝对地址的映像仍必须提供合法的重定位表，
#     否则加载器无法在非首选基址加载，DYNAMIC_BASE 等于失效或被拒。
# (R) 栈回溯表断言：条目有序、范围不重叠、UNWIND_INFO 版本与 prologue 一致。
assert _runtime_functions, 'at least the entry routine needs unwind metadata'
assert len(_runtime_functions) * 12 == _pdata_entries
assert all(RDATA_RVA <= rva < RDATA_RVA + len(rdata) for rva in _unwind_rvas), \
    'unwind blobs must live inside .rdata'
assert len(rdata) <= IDATA_RVA - RDATA_RVA, 'unwind blobs must fit in .rdata'
_prev_end = 0
for _index, (_offset, _blob) in enumerate(_runtime_functions):
    _begin = TEXT_RVA + _offset
    _end = (TEXT_RVA + _bounds[_index + 1]) if _index + 1 < len(_bounds) else TEXT_RVA + len(text)
    assert _begin >= _prev_end, 'RUNTIME_FUNCTION entries must be ordered'
    assert _end > _begin, 'RUNTIME_FUNCTION ranges must be non-empty'
    _prev_end = _end
    assert _blob[0] == 1, 'UNWIND_INFO version must be 1'
    assert _blob[2] >= 1, 'SizeOfProlog must cover the analysed prologue'
    assert _blob[3] >= 1, 'at least one unwind code is required'
assert _reloc_pages * SECT_ALIGN == PDATA_RVA - TEXT_RVA

assert reloc_size >= 12 and reloc_size % 4 == 0, \
    'the relocation table must contain whole blocks'
_reloc_blocks = 0
_reloc_cursor = 0
while _reloc_cursor < reloc_size:
    _page, _block_size = struct.unpack_from('<II', reloc, _reloc_cursor)
    assert _block_size >= 12 and _block_size % 4 == 0, \
        'relocation block size must cover at least one entry and stay aligned'
    assert _page % SECT_ALIGN == 0, 'relocation blocks must start on a page'
    for _entry in range((_block_size - 8) // 2):
        _value = struct.unpack_from('<H', reloc, _reloc_cursor + 8 + _entry * 2)[0]
        assert (_value >> 12) == 0, \
            'this image has no absolute addresses, so every entry must be ABSOLUTE'
    _reloc_cursor += _block_size
    _reloc_blocks += 1
assert _reloc_cursor == reloc_size, 'relocation blocks must tile the table exactly'
assert _reloc_blocks == (PDATA_RVA - TEXT_RVA) // SECT_ALIGN, \
    'every image page must be declared relocation-clean'
assert DLL_CHARACTERISTICS & 0x0040, 'DYNAMIC_BASE must stay enabled'
# (S) V8.6 切片 1：workspace 枚举的所有权与接口断言。要拦截的错误模式：
#     绕过自有 arena 直接写固定表、忘记归一化目录标志、把测试命令带进正式构建。
assert all(name in IAT for name in ('FindFirstFileW','FindNextFileW','FindClose')), \
    'directory enumeration must go through the Find*FileW imports'
for _ws_symbol in ('ws_root_path','ws_current_path','ws_pattern','ws_find_data',
                   'ws_find_handle','ws_entry_count','ws_error','ws_capacity'):
    assert _ws_symbol in bsyms, '%s must exist' % _ws_symbol
assert bss_sizes['ws_entries'] == 8, 'the entry table must be an arena pointer'
assert bss_sizes['ws_find_data'] == 592, 'WIN32_FIND_DATAW must be 592 bytes'
assert WS_STRIDE % 8 == 0 and WS_STRIDE == WS_OFF_WRITE_TIME + 8, \
    'workspace entries must be 8-byte aligned and end exactly at the stride'
assert WS_STRIDE == 512 + 32, \
    'entry addressing is emitted as index*512 + index*32; update both the ' \
    'arena sizing and emit_ws_entry_ptr together with WS_STRIDE'
assert (WS_OFF_NAME, WS_OFF_ATTRIBUTES, WS_OFF_KIND, WS_OFF_SIZE_LOW,
        WS_OFF_SIZE_HIGH, WS_OFF_WRITE_TIME) == \
       (0, WS_NAME_UNITS * 2, WS_NAME_UNITS * 2 + 4, WS_NAME_UNITS * 2 + 8,
        WS_NAME_UNITS * 2 + 12, WS_NAME_UNITS * 2 + 16), \
    'workspace entry name, attributes, kind, size and time must tile the stride'
assert bss_sizes['ws_pattern'] >= bss_sizes['ws_root_path'] + 4, \
    'the pattern buffer must fit the longest accepted path plus the wildcard'
assert bss_sizes['ws_root_path'] == bss_sizes['ws_current_path'], \
    'root and current directory must have the same capacity'
_ws_ensure_src = _production_source[
    _production_source.index("em.label('ensure_workspace_arena')"):
    _production_source.index("em.label('ws_suffix_match')")]
assert "em.label('ws_arena_copy')" in _ws_ensure_src and \
       _ws_ensure_src.index("em.label('ws_arena_copy_done')") < \
       _ws_ensure_src.index("call_iat('VirtualFree')"), \
    'growing the workspace arena must copy the published entries before freeing the old block'
for _ws_routine in ('ensure_workspace_arena','ws_suffix_match','ws_name_cmp',
                    'ws_copy_entry','ws_find_insert_index','ws_shift_right',
                    'workspace_insert','workspace_refresh','workspace_set_root'):
    assert _ws_routine in em.labels, '%s must be emitted' % _ws_routine
assert ('cmd_workspace_probe' in em.labels) == OPEN_TEST_BUILD, \
    'the workspace probe command must exist only in the explicit test build'
assert ((1902, 'cmd_workspace_probe') in _command_routes) == OPEN_TEST_BUILD
_ws_src = _production_source[
    _production_source.index("em.label('workspace_refresh')"):
    _production_source.index("em.label('workspace_set_root')")]
_ws_insert_src = _production_source[
    _production_source.index("em.label('workspace_insert')"):
    _production_source.index("em.label('workspace_refresh')")]
_ws_index_src = _production_source[
    _production_source.index("em.label('ws_find_insert_index')"):
    _production_source.index("em.label('ws_shift_right')")]
assert "call_iat('FindFirstFileW')" in _ws_src and \
       "call_iat('FindNextFileW')" in _ws_src and \
       "call_iat('FindClose')" in _ws_src, \
    'workspace_refresh must enumerate with Find*FileW and always close the handle'
assert "mov_ripmem_imm32(bsyms['ws_entry_count'],0)" in _ws_src, \
    'a refresh must publish an empty list on failure instead of a partial one'
assert "shr_r32_imm8('r13',4)" in _ws_index_src and \
       "shr_r32_imm8('r10',4)" in _ws_index_src and \
       "shr_r32_imm8('r9',4)" in _ws_insert_src, \
    'FILE_ATTRIBUTE_DIRECTORY must reach the arena normalised to kind bit 0'
for _ws_field in ("mov_mreg_reg32('r14',WS_OFF_ATTRIBUTES,'r8')",
                  "mov_mreg_reg32('r14',WS_OFF_KIND,'r9')",
                  "mov_mreg_reg32('r14',WS_OFF_SIZE_LOW,'r10')",
                  "mov_mreg_reg32('r14',WS_OFF_SIZE_HIGH,'r10')",
                  "mov_mreg_reg64('r14',WS_OFF_WRITE_TIME,'r11')"):
    assert _ws_field in _ws_insert_src, \
        'workspace entries must own attributes, kind, size and write time: %s' % _ws_field

# (T) V8.6 切片 2：侧边栏面板模式的所有权断言。要拦截的错误模式：
#     目录条目被当成大纲行走 outline_level、切回大纲时不重建列表、
#     文件模式下选中项触发文档跳转、测试切换命令进入正式构建。
assert bss_sizes['panel_mode'] == 4, 'panel_mode must be a 4-byte state field'
assert WS_OFF_KIND == WS_NAME_UNITS * 2 + 4, \
    'the owner-draw file row reads the kind field through WS_OFF_KIND'
for _panel_routine in ('rebuild_file_list', 'set_panel_mode', 'refresh_panel_list',
                       'outline_push', 'navigate_outline', 'wp_outline_level_row'):
    assert _panel_routine in em.labels, '%s must be emitted' % _panel_routine
# V8.6.1：大纲与文件各自拥有 ListBox，因此"扫描不得触碰对方列表"的旧约束换成
# 控件归属断言（见下方 _dual_panel_src）。
_panel_draw_src = _production_source[
    _production_source.index("em.label('wp_outline_text')"):
    _production_source.index("em.label('wp_outline_level_row')")]
assert "WS_OFF_KIND" in _panel_draw_src and "bsyms['outline_level']" not in _panel_draw_src, \
    'the file row branch must colour from the workspace table, never outline_level'
_panel_list_src = _production_source[
    _production_source.index("em.label('rebuild_file_list')"):
    _production_source.index("em.label('set_panel_mode')")]
assert "call_iat('lstrcpyW')" in _panel_list_src and \
       "bsyms['hwnd_files']" in _panel_list_src and \
       "call_label('sync_outline_scrollbar')" in _panel_list_src, \
    'rebuild_file_list must own the row text and fill its own ListBox'
_panel_switch_src = _production_source[
    _production_source.index("em.label('set_panel_mode')"):
    _production_source.index("em.label('refresh_panel_list')")]
assert "em.jmp('refresh_panel_list')" in _panel_switch_src, \
    'a mode change must rebuild the list through the shared refresh path'
_panel_refresh_src = _production_source[
    _production_source.index("em.label('refresh_panel_list')"):
    _production_source.index("em.label('cmd_workspace_probe')")] if OPEN_TEST_BUILD else \
    _production_source[_production_source.index("em.label('refresh_panel_list')"):]
assert "call_label('rebuild_file_list')" in _panel_refresh_src and \
       "call_label('update_preview')" in _panel_refresh_src, \
    'set_panel_mode must own both panel contents, rebuilding the outline on the way back'
_panel_root_src = _production_source[
    _production_source.index("em.label('workspace_set_root')"):
    _production_source.index("em.label('rebuild_file_list')")]
assert "call_label('workspace_refresh')" in _panel_root_src and \
       "call_label('rebuild_file_list')" in _panel_root_src, \
    'a new workspace root must refresh an active file list'
for _panel_symbol in ('cmd_show_files', 'cmd_show_outline'):
    assert (_panel_symbol in em.labels) == OPEN_TEST_BUILD, \
        'the panel switch probe must exist only in the explicit test build'
assert ((1903, 'cmd_show_files') in _command_routes) == OPEN_TEST_BUILD and \
       ((1904, 'cmd_show_outline') in _command_routes) == OPEN_TEST_BUILD
assert ('cmd_dump_row' in em.labels) == OPEN_TEST_BUILD and \
       ((1905, 'cmd_dump_row') in _command_routes) == OPEN_TEST_BUILD, \
    'the row-export probe must exist only in the explicit test build'
if OPEN_TEST_BUILD:
    assert bss_sizes['list_probe_text'] == 1024 and \
           bss_sizes['list_probe_result'] == 4, \
        'the row-export probe owns its own buffer, away from owner-draw scratch'

# (U) V8.6 切片 3：目录导航与从列表打开的所有权断言。要拦截的错误模式：
#     绕过未保存保护的第二条打开路径、双击与单选混淆、Backspace 抢走编辑区
#     的删除键、状态栏丢失路径段。
for _nav_routine in ('ws_join_path', 'ws_go_up', 'ws_open_or_enter',
                     'list_activate_event', 'keydown_event', 'destructive_open'):
    assert _nav_routine in em.labels, '%s must be emitted' % _nav_routine
_nav_open_src = _production_source[
    _production_source.index("em.label('ws_open_or_enter')"):
    _production_source.index("em.label('woe_ret')")]
assert "mov_ripmem_imm32(bsyms['pending_destructive_action'],2)" in _nav_open_src and \
       "em.jmp('destructive_request')" in _nav_open_src and \
       "call_label('workspace_set_root')" in _nav_open_src, \
    'the list must enter directories and route files through the shared Open transaction'
_nav_dispatch_src = _production_source[
    _production_source.index("em.label('destructive_open')"):
    _production_source.index("em.label('destructive_close')")]
assert "open_bypass_picker" in _nav_dispatch_src and \
       "em.jmp('cmd_open_selected')" in _nav_dispatch_src and \
       "em.jcc(0x84,'cmd_open_dialog')" in _nav_dispatch_src, \
    'only a confirmed list Open may skip the picker, and the default stays the picker'
assert "mov_ripmem_imm32(bsyms['open_bypass_picker'],0)" in _production_source, \
    'the bypass flag must be cleared when it is consumed or cancelled'
_nav_list_src = _production_source[
    _production_source.index("em.label('wp_cmd_outline_check')"):
    _production_source.index("em.label('wp_cmd_other_child')")]
assert "cmp_r32_imm('r10',2)" in _nav_list_src and "0x8007" in _nav_list_src, \
    'LBN_DBLCLK must be routed to the activation event, not the selection event'
_nav_pump_src = _production_source[
    _production_source.index("em.label('msg_loop')"):
    _production_source.index("em.label('mousemove_event')")]
assert "0x8007" in _nav_pump_src and "0x0100" in _nav_pump_src, \
    'the pump must dispatch the activation event and WM_KEYDOWN'
_nav_key_src = _production_source[
    _production_source.index("em.label('keydown_event')"):
    _production_source.index("em.label('mousewheel_event')")]
assert "call_iat('GetFocus')" in _nav_key_src and \
       "bsyms['hwnd_files']" in _nav_key_src and \
       "em.jcc(0x85,'dispatch')" in _nav_key_src, \
    'Backspace must only go up while the file list owns the focus'
_nav_status_src = _production_source[
    _production_source.index("em.label('update_status')"):
    _production_source.index("em.label('status_ret')")]
assert "0x1106" in _nav_status_src and "bsyms['ws_current_path']" in _nav_status_src, \
    'the status bar must show the workspace directory'
assert "em.mov_r32_imm('r8',7); em.lea_rip('r9',rsyms['status_parts'])" in _production_source, \
    'the status bar must publish seven parts'
for _nav_symbol in ('cmd_list_activate', 'cmd_go_up'):
    assert (_nav_symbol in em.labels) == OPEN_TEST_BUILD, \
        'the navigation probes must exist only in the explicit test build'
assert ((1906, 'cmd_list_activate') in _command_routes) == OPEN_TEST_BUILD and \
       ((1907, 'cmd_go_up') in _command_routes) == OPEN_TEST_BUILD

# (V) V8.6 切片 4：菜单入口的所有权断言。要拦截的错误模式：切片 2/3 的机制在
#     正式构建里没有可达入口、菜单勾选与 panel_mode 脱钩、选择文件夹后未切换面板。
for _menu_routine in ('cmd_open_folder', 'cmd_panel_files', 'cmd_panel_outline',
                      'sync_panel_menu'):
    assert _menu_routine in em.labels, '%s must be emitted' % _menu_routine
assert "append_imm('r12',0,1006,'m_openfolder')" in _production_source, \
    'File must expose Open Folder...'
assert "append_imm('r14',0,1308,'m_panel_files')" in _production_source and \
       "append_imm('r14',0x8,1309,'m_panel_outline')" in _production_source, \
    'View must expose the two panel switches with the outline checked by default'
for _panel_cmd in ((1006, 'cmd_open_folder'), (1308, 'cmd_panel_files'),
                   (1309, 'cmd_panel_outline')):
    assert _panel_cmd in _command_routes, '%r must be routed' % (_panel_cmd,)
assert "call_label('sync_panel_menu')" in _production_source and \
       "em.label('spmm_outline')" in _production_source, \
    'the menu check state must follow panel_mode'
assert "em.label('cmd_panel_files'); em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode')" in _production_source and \
       "em.label('cmd_panel_outline'); em.xor32('rcx'); em.call_label('set_panel_mode')" in _production_source, \
    'both menu items must drive the shared panel switch'
_menu_folder_src = _production_source[
    _production_source.index("em.label('cmd_open_folder')"):
    _production_source.index("em.label('cmd_open_dialog')")]
assert "call_iat('SHBrowseForFolderW')" in _menu_folder_src and \
       "call_iat('SHGetPathFromIDListW')" in _menu_folder_src and \
       "call_iat('ILFree')" in _menu_folder_src and \
       "call_label('workspace_set_root')" in _menu_folder_src and \
       "em.mov_r32_imm('rcx',1); em.call_label('set_panel_mode')" in _menu_folder_src, \
    'Open Folder must browse, adopt the directory and switch to the file panel'
assert ('cmd_open_folder_selected' in em.labels) == OPEN_TEST_BUILD and \
       ((1908, 'cmd_open_folder_selected') in _command_routes) == OPEN_TEST_BUILD, \
    'the picker bypass must exist only in the explicit test build'

# (W) 快捷键方案：与 Rabbit 对齐的键位必须唯一且指向正确命令，菜单里的提示必须与
#     加速键表一致，为后续功能预留的键位不得被占用。
_accel_by_key = {}
for _accel_flags, _accel_vk, _accel_cmd in _accels:
    _accel_by_key[(_accel_flags, _accel_vk)] = _accel_cmd
assert len(_accel_by_key) == len(_accels), 'accelerator keys must be unique'
assert _accel_by_key[(FVIRTKEY|FCONTROL|FSHIFT, 0x53)] == 1004, \
    'Ctrl+Shift+S must be Save As, matching Rabbit'
assert _accel_by_key[(FVIRTKEY|FCONTROL|FALT, 0x53)] == 1305, \
    'the status bar keeps the freed Ctrl+Alt+S'
assert _accel_by_key[(FVIRTKEY|FCONTROL|FSHIFT, 0x4F)] == 1006, \
    'Ctrl+Shift+O must open a folder, matching Rabbit'
assert _accel_by_key[(FVIRTKEY|FCONTROL, 0x57)] == 1007, \
    'Ctrl+W must close the document, matching Rabbit'
assert _accel_by_key[(FVIRTKEY|FCONTROL, 0x42)] == 1307, \
    'Ctrl+B must keep toggling the left sidebar'
assert _accel_by_key[(FVIRTKEY|FCONTROL|FALT, 0x4B)] == 1406 and \
       _accel_by_key[(FVIRTKEY|FCONTROL|FALT, 0x4C)] == 1409, \
    'the Markdown modifiers move to the Ctrl+Alt family'
assert (FVIRTKEY|FCONTROL, 0x4B) not in _accel_by_key, \
    'Ctrl+K is reserved for the V9 AI quick edit (Rabbit parity)'
assert (FVIRTKEY|FCONTROL|FSHIFT, 0x4B) not in _accel_by_key, \
    'Ctrl+Shift+K is reserved for Delete Line (Rabbit parity)'
assert (FVIRTKEY|FCONTROL, 0x4C) not in _accel_by_key and \
       (FVIRTKEY|FCONTROL|FSHIFT, 0x4C) not in _accel_by_key, \
    'Ctrl+L is reserved for quoting to the AI (Rabbit parity)'
for _menu_hint in (r'Save &As...\tCtrl+Shift+S', r'&Status Bar\tCtrl+Alt+S',
                   r'Code Bloc&k\tCtrl+Alt+K', r'&Link\tCtrl+Alt+L',
                   r'Left &Sidebar\tCtrl+B', r'Open &Folder...\tCtrl+Shift+O',
                   r'&Close\tCtrl+W'):
    assert _menu_hint in _production_source, \
        'the menu hint must match the accelerator table: %s' % _menu_hint
assert 'cmd_close_file' in em.labels and (1007, 'cmd_close_file') in _command_routes, \
    'Close must exist as its own command next to New'
assert "append_imm('r12',0,1007,'m_close')" in _production_source, \
    'the File menu must expose Close'

_output_channel = 'test' if INJECTED_BUILD else _BUILD_CHANNEL
_output_name = (('pemark_x64_v8_6_outline_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if OUTLINE_ALLOC_INJECTED else
                ('pemark_x64_v8_6_style_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if STYLE_ALLOC_INJECTED else
                ('pemark_x64_v8_6_render_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if RENDER_ALLOC_INJECTED else
                ('pemark_x64_v8_6_document_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if DOCUMENT_ALLOC_INJECTED else
                ('pemark_x64_v8_6_wide_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if WIDE_ALLOC_INJECTED else
                ('pemark_x64_v8_6_byte_alloc_%s.exe' % ARENA_ALLOC_INJECTION_MODE)
                if BYTE_ALLOC_INJECTED else
                ('pemark_x64_v8_6_open_read_%s.exe' % OPEN_READ_INJECTION_MODE)
                if OPEN_READ_INJECTION_MODE != 'release' else
                'pemark_x64_v8_6_open_transaction_test.exe' if OPEN_TEST_BUILD
                else ('pemark_x64_v8_6_write_%s.exe' % WRITE_INJECTION_MODE
                      if INJECTED_BUILD else
                      'pemark_x64_v8_6.exe' if _RELEASE_CHANNEL else
                      'pemark_x64_v8_6_candidate.exe'))
out = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'bin',
                                   _output_channel, _output_name))
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'wb') as f:
    f.write(hdr)
    f.write(raw)

sha = hashlib.sha256(open(out,'rb').read()).hexdigest()
print(out)
print('size', os.path.getsize(out), 'text', len(text), 'raw', raw_size,
      'sections', len(sections), 'image_size', size_image, 'bss_vsize', BSS_VSIZE)
print('sha256', sha)

# ---------------- PE_MEMORY_MAP.md 自动导出 ----------------
# AGENTS 布局纪律：“If changing PE layout, regenerate docs/PE_MEMORY_MAP.md”。
# 本文档自 V8.5.0-pre 起由生成器在每次构建时自动重写，符号表永远与
# 实际 BSS 分配一致；人工只需维护头部说明文字的变化（布局数字本身
# 也由下方 f-string 注入，无手写数字）。
_map_name = 'PE_MEMORY_MAP_V8_6.md' if _RELEASE_CHANNEL else 'PE_MEMORY_MAP_V8_6_CANDIDATE.md'
_map_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'docs', _map_name))
if not INJECTED_BUILD:
 with open(_map_path, 'w', encoding='utf-8') as _mf:
    _mf.write('# PE / BSS 内存映射 — 由生成器自动导出\n\n')
    _mf.write('节布局（V8.6 权限分离）：\n\n')
    _mf.write('| Section | RVA | VirtualSize | RawSize | Permissions |\n')
    _mf.write('|---|---:|---:|---:|---|\n')
    for _sname, _svs, _sva, _sptr, _srs, _schars in sections:
        _mf.write('| `%s` | `0x%X` | %d | %d | `0x%08X` |\n'
                  % (_sname.split(b'\0', 1)[0].decode(), _sva, _svs, _srs, _schars))
    _mf.write('\ntext 实际代码 %d 字节（预算 %d），rdata %d 字节，idata %d 字节，'
              'BSS 虚拟 %d 字节。\n\n'
              % (len(text), RDATA_RVA - TEXT_RVA, len(rdata), len(idata), BSS_VSIZE))
    _mf.write('本次构建：text 实际 %d 字节（余量 %d 字节）；BSS 符号 %d 个，'
              '最终虚拟 BSS %d 字节。\n\n'
              % (len(text), (RDATA_RVA - TEXT_RVA) - len(text),
                 len(bsyms), BSS_VSIZE))
    _mf.write('SHA-256：`%s`\n\n' % sha)
    _mf.write('| Symbol | RVA | Size |\n|---|---:|---:|\n')
    for _name in sorted(bsyms, key=lambda n: bsyms[n]):
        _mf.write('| `%s` | `0x%X` | %d |\n'
                  % (_name, bsyms[_name], bss_sizes[_name]))
 if not INJECTED_BUILD:
    print('PE_MEMORY_MAP.md regenerated:', _map_path)
