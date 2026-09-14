"""Execute real emitted x64 routines under Unicorn; Win32 calls deliberately clobber volatile registers.

Test dependency only: pip install unicorn. No compiler/assembler is used.
Usage: python tools/test_stabilization.py [generator.py]
"""
from pathlib import Path
import struct, sys, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn import x86_const as x

ROOT = Path(__file__).resolve().parents[1]

def load_generator(path):
    source = Path(path).read_text(encoding='utf-8')
    ns = {'__file__': str(Path(path).resolve())}
    # Build all image bytes and symbols without executing the output writer.
    exec(compile(source.split('\nout = ')[0], str(path), 'exec'), ns)
    return ns

class Machine:
    def __init__(self, ns):
        self.ns = ns
        self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        self.base = ns['IMAGE_BASE']
        self.u.mem_map(self.base, ns['size_image'])
        self.u.mem_write(self.base + ns['TEXT_RVA'], bytes(ns['raw']))
        self.u.mem_map(0x100000, 0x20000)
        self.u.mem_map(0x200000, 0x10000)
        self.api = {}
        for i, (name, rva) in enumerate(ns['IAT'].items()):
            addr = 0x200000 + i * 16
            self.api[addr] = name
            self.u.mem_write(self.base+rva, struct.pack('<Q', addr))
            self.u.mem_write(addr, b'\xc3')
        self.calls = []; self.create_instances=[]; self.selection = 2; self.count = 1800; self.top = 0
        self.cursor = (210, 100); self.visible = {1: True, 2: False}
        self.u.hook_add(UC_HOOK_CODE, self.hook)
        for key, value in {'hwnd_edit':1, 'hwnd_preview':2, 'hwnd_outline':3,
                           'hwnd_main':4, 'hwnd_outline_scroll':5, 'hmenu_view':6}.items():
            self.put(key, value, 8)
        self.put('content_h', 570); self.put('scrollbar_w',17)
        self.put('outline_width',230); self.put('outline_flag',1)

    def put(self, name, value, size=4):
        self.u.mem_write(self.base+self.ns['bsyms'][name], int(value).to_bytes(size,'little',signed=value<0))

    def get(self, name):
        return int.from_bytes(self.u.mem_read(self.base+self.ns['bsyms'][name],4),'little')

    def hook(self, u, addr, size, _):
        if addr not in self.api: return
        name = self.api[addr]
        a = [u.reg_read(getattr(x,'UC_X86_REG_'+r)) for r in ['RCX','RDX','R8','R9']]
        assert u.reg_read(x.UC_X86_REG_RSP)%16 == 8, f'ABI alignment at {name}'
        self.calls.append((name,a)); result = 1
        if name == 'CreateWindowExW':
            self.create_instances.append(int.from_bytes(u.mem_read(u.reg_read(x.UC_X86_REG_RSP)+0x58,8),'little'))
        if name == 'ExitProcess':
            u.emu_stop(); return
        if name == 'IsWindow': result = 0
        if name == 'SendMessageW':
            result = {0x188:self.selection,0x18b:self.count,0x18e:self.top,0xd7:1500}.get(a[1],0)
            if a[1] == 0x197: self.top = min(a[2],max(0,self.count-self.get('outline_visible_rows')))
        elif name == 'MulDiv':
            n,d,k = [v if v<0x80000000 else v-0x100000000 for v in a[:3]]
            result = (n*d+k//2)//k if k else -1
        elif name == 'IsWindowVisible': result = int(self.visible.get(a[0],False))
        elif name == 'ShowWindow': self.visible[a[0]]=bool(a[1])
        elif name == 'GetCursorPos': u.mem_write(a[0],struct.pack('<ii',*self.cursor))
        elif name == 'GetClientRect': u.mem_write(a[1],struct.pack('<4i',0,0,800,570))
        # Poison both volatile registers AND the callee-owned shadow space.
        for r in ['RCX','RDX','R8','R9','R10','R11']:
            u.reg_write(getattr(x,'UC_X86_REG_'+r),0xBAD00000)
        rsp=u.reg_read(x.UC_X86_REG_RSP)
        u.mem_write(rsp+8,b'\xcc'*32)
        u.reg_write(x.UC_X86_REG_RAX,result & 0xffffffffffffffff)

    def run(self, label, **regs):
        self.calls=[]
        self.u.mem_write(self.base+self.ns['bsyms']['msg']+36,struct.pack('<ii',*self.cursor))
        rsp=0x11ff08; end=0x20fff0
        self.u.mem_write(rsp,struct.pack('<Q',end))
        self.u.reg_write(x.UC_X86_REG_RSP,rsp)
        for r,v in regs.items(): self.u.reg_write(getattr(x,'UC_X86_REG_'+r.upper()),v)
        self.u.emu_start(self.base+self.ns['TEXT_RVA']+self.ns['em'].labels[label],end,count=2000000)
        assert self.u.reg_read(x.UC_X86_REG_RIP)==end, f'{label} did not return'

def checks(ns):
    failures=[]; passed=[]
    def check(name, fn):
        try: fn(); passed.append(name)
        except Exception as e: failures.append({'test':name,'error':str(e)})
    def navigate():
        m=Machine(ns)
        mode='view_mode' if 'view_mode' in ns['bsyms'] else 'preview_flag'
        m.put(mode,1); m.visible[2]=True; m.put('document_len',1000); m.put('render_len',1000)
        start=m.base+ns['bsyms']['outline_srcpos']
        m.u.mem_write(start,struct.pack('<III',0,100,200))
        m.u.mem_write(m.base+ns['bsyms']['render_srcmap'],struct.pack('<1000I',*range(1000)))
        m.run('navigate_outline')
        sels=[a for n,a in m.calls if n=='SendMessageW' and a[1]==0xb1]
        assert sels and sels[0][0]==2 and sels[0][2:]==[200,200], sels
    check('preview navigation survives volatile API clobbers',navigate)
    if 'detect_preferred_eol' in ns['em'].labels:
        def document_metadata_helpers():
            m=Machine(ns)
            scratch=m.base+ns['bsyms']['widebuf']
            for text, expected in [('plain',0), ('a\r\nb\n',0),
                                   ('a\nb\r\n',1), ('a\rb\n',2)]:
                encoded=text.encode('utf-16le')
                m.u.mem_write(scratch,encoded+b'\0\0')
                m.run('detect_preferred_eol',rcx=scratch,rdx=len(text))
                actual=m.u.reg_read(x.UC_X86_REG_RAX)&0xffffffff
                assert actual==expected,(repr(text),expected,actual)
            model=m.base+ns['bsyms']['document_model']
            canonical='a\r\nb\r\n'
            m.u.mem_write(model,canonical.encode('utf-16le')+b'\0\0')
            m.put('document_len',len(canonical))
            for state, expected in [(0,canonical),(1,'a\nb\n'),(2,'a\rb\r')]:
                m.put('eol_state',state)
                m.run('serialize_preferred_eol')
                length=m.u.reg_read(x.UC_X86_REG_RAX)&0xffffffff
                raw=bytes(m.u.mem_read(scratch,length*2))
                assert raw.decode('utf-16le')==expected,(state,raw)
            m.u.mem_write(m.base+ns['bsyms']['document_revision'],
                          struct.pack('<Q',0xffffffffffffffff))
            m.run('advance_document_revision')
            wrapped=int.from_bytes(m.u.mem_read(
                m.base+ns['bsyms']['document_revision'],8),'little')
            assert wrapped==1,wrapped
        check('document metadata helpers execute emitted x64 correctly',
              document_metadata_helpers)
    def scrollbar():
        m=Machine(ns); m.run('sync_outline_scrollbar')
        h=m.get('outline_scroll_thumb_h'); track=m.get('outline_scroll_track_h')
        assert 0<h<track, (h,track)
        m.top=890; m.run('sync_outline_scrollbar')
        assert 4<m.get('outline_scroll_thumb_top')<track-h+4
    check('long outline has positive thumb travel',scrollbar)
    def drag_above():
        m=Machine(ns); m.run('sync_outline_scrollbar'); m.put('outline_scroll_drag_offset',10)
        m.cursor=(220,-100); m.run('outline_scroll_drag_move')
        assert m.top==0, m.top
    check('drag above window clamps to start',drag_above)
    if 'set_view_mode' in ns['em'].labels:
        def view():
            m=Machine(ns)
            for i in range(20):
                mode=i%2; m.run('set_view_mode',r8=mode)
                assert m.get('preview_flag')==mode
                assert m.visible[1]==(mode==0) and m.visible[2]==(mode==1)
        check('20 view transitions keep HWND visibility coherent',view)
    if 'scroll_layout' in ns['em'].labels:
        def wrap_preview():
            m=Machine(ns); m.put('preview_flag',1); m.put('render_len',123)
            m.put('wrap_flag',0); m.visible={1:False,2:True}
            stop=m.base+ns['TEXT_RVA']+ns['em'].labels['msg_loop']
            m.u.reg_write(x.UC_X86_REG_RSP,0x11ff00)
            m.u.reg_write(x.UC_X86_REG_RSI,1); m.u.reg_write(x.UC_X86_REG_RBX,4)
            m.u.reg_write(x.UC_X86_REG_R15,1217000) # File-open byte count, not HINSTANCE.
            m.u.emu_start(m.base+ns['TEXT_RVA']+ns['em'].labels['cmd_wrap'],stop,count=2000000)
            assert m.u.reg_read(x.UC_X86_REG_RIP)==stop
            assert m.get('render_len')==123,'wrap rebuilt unchanged RenderModel'
            assert m.visible[2] and not m.visible[1]
            assert not any(n=='SetWindowTextW' and a[0]==2 for n,a in m.calls)
            creates=[a for n,a in m.calls if n=='CreateWindowExW']
            assert creates and creates[0][3]==0x54211044,creates
            assert creates[0][2]==0,'large text passed during EDIT creation'
            assert m.create_instances==[1],m.create_instances
            limit=next(i for i,(n,a) in enumerate(m.calls) if n=='SendMessageW' and a[1]==0xc5)
            textload=next(i for i,(n,a) in enumerate(m.calls) if n=='SendMessageW' and a[0]==1 and a[1]==0x000C)
            assert limit<textload,'load large text only after raising EDIT limit'
        check('wrap recreation preserves Preview model and creates wrapped Source',wrap_preview)
        def fenced_spaces():
            m=Machine(ns); m.put('hwnd_preview',0,8)
            source="```python\ndef hello():\n    return '# not heading'\n```\n"
            m.u.mem_write(m.base+ns['bsyms']['document_model'],(source+'\0').encode('utf-16le'))
            m.run('update_preview')
            rendered=bytes(m.u.mem_read(m.base+ns['bsyms']['previewbuf'],m.get('render_len')*2)).decode('utf-16le')
            assert "def hello():\r    return '# not heading'\r" in rendered,repr(rendered)
        check('fenced code preserves indentation and internal spaces',fenced_spaces)
        def short_hover():
            m=Machine(ns); m.count=6; m.run('sync_outline_scrollbar'); m.cursor=(220,100)
            m.run('update_outline_hover')
            assert m.get('outline_scroll_visible')==0
        check('short outline does not show a full-height hover thumb',short_hover)
        def shutdown():
            m=Machine(ns)
            m.u.reg_write(x.UC_X86_REG_RSP,0x11ff00)
            m.u.emu_start(m.base+ns['TEXT_RVA']+ns['em'].labels['dispatch_status_done'],0x20fff0,count=10000)
            assert any(n=='ExitProcess' for n,a in m.calls),m.calls
        check('destroyed main window reaches ExitProcess without helper fallthrough',shutdown)
        def event_point():
            m=Machine(ns); m.cursor=(220,14)
            m.run('capture_message_point')
            point=struct.unpack('<ii',m.u.mem_read(m.base+ns['bsyms']['cursor_pt'],8))
            assert point==(220,14),point
            assert not any(n=='GetCursorPos' for n,a in m.calls)
        check('queued mouse handlers consume message position',event_point)
        def viewport():
            m=Machine(ns); m.put('preview_flag',1); m.put('view_top_pos',1000); m.put('render_len',100000)
            m.run('set_visible_format_window')
            assert m.get('format_visible_end')==3500,m.get('format_visible_end')
            m.put('preview_visible_format_only',1); m.put('style_count',1)
            m.put('style_start',0); m.put('style_end',100000); m.put('style_type',15)
            m.run('apply_styles')
            sels=[a[2:] for n,a in m.calls if n=='SendMessageW' and a[1]==0xb1]
            # apply_styles also restores the saved empty selection at completion.
            assert sels==[[1000,3500],[0,0]],sels
        check('viewport formatting clips huge code spans to visible range',viewport)
        def geometry():
            m=Machine(ns)
            for count in [0,1,18,19,20,1800,2048]:
                for height in [0,8,20,29,30,31,565,570,599,1200]:
                    for top in [0,count//2,count+100]:
                        m.put('outline_scroll_count',count); m.put('outline_scroll_top',top)
                        m.put('content_h',height); m.run('scroll_layout')
                        rows=max(1,height//30); maximum=max(0,count-rows)
                        assert m.get('outline_visible_rows')==rows
                        assert m.get('outline_max_top')==maximum
                        assert m.get('outline_scroll_top')==min(top,maximum)
                        thumb=m.get('outline_scroll_thumb_h'); track=max(0,height-8)
                        assert 0<=thumb<=track
                        assert m.get('outline_scroll_travel')==track-thumb
                        rect=struct.unpack('<4i',m.u.mem_read(m.base+ns['bsyms']['outline_thumb_rect'],16))
                        assert rect[1]==m.get('outline_scroll_thumb_top') and rect[3]-rect[1]==thumb
                        assert 4<=rect[1]<=rect[3]<=track+4
        check('210 scrollbar capacity/height/top boundary combinations',geometry)
        def drag_positions():
            m=Machine(ns); m.run('sync_outline_scrollbar'); m.put('outline_scroll_drag_offset',10)
            for y,expected in [(-100,0),(14,0),(10000,1781),(14,0)]:
                m.cursor=(220,y); m.run('outline_scroll_drag_move')
                assert m.top==expected,(y,m.top,expected)
        check('drag clamps both extremes and returns to start',drag_positions)
    return {'passed':passed,'failures':failures}

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'src/stabilization/generate_markdown_editor_v8_5_1.py'
    report=checks(load_generator(path)); print(json.dumps(report,indent=2))
    sys.exit(bool(report['failures']))
