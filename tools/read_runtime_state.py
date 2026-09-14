"""Read-only debugger snapshot of a running Direct-PE instance; never sends UI messages.
Usage: python tools/read_runtime_state.py PID generator.py [output.json]
"""
import ctypes as c
from ctypes import wintypes as w
import json, sys, platform
from pathlib import Path
from test_stabilization import load_generator

def snapshot(pid, generator):
    ns=load_generator(generator)
    k=c.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
    k.ReadProcessMemory.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)]
    k.ReadProcessMemory.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE]
    h=k.OpenProcess(0x1010,False,pid)
    if not h: raise c.WinError(c.get_last_error())
    def read(name,size=4):
        b=c.create_string_buffer(size); n=c.c_size_t()
        if not k.ReadProcessMemory(h,ns['IMAGE_BASE']+ns['bsyms'][name],b,size,c.byref(n)):
            raise c.WinError(c.get_last_error())
        return b.raw
    try:
        names=['view_mode','preview_flag','document_len','render_len','outline_count',
               'nav_source_offset','view_sel_start','view_top_pos','outline_scroll_count',
               'outline_scroll_top','outline_visible_rows','outline_max_top','outline_scroll_visible',
               'outline_scroll_drag','outline_scroll_thumb_top','outline_scroll_thumb_h',
               'outline_scroll_track_h','outline_scroll_travel','theme_dark','zoom_pct',
               'content_h','outline_width','style_count']
        result={'pid':pid,'windows':platform.platform(), 'generator':str(generator),
                'state':{name:int.from_bytes(read(name),'little') for name in names if name in ns['bsyms']}}
        import struct
        for name in ['outline_thumb_rect','outline_track_rect']:
            if name in ns['bsyms']: result['state'][name]=struct.unpack('<4i',read(name,16))
        return result
    finally: k.CloseHandle(h)

if __name__=='__main__':
    result=snapshot(int(sys.argv[1]),sys.argv[2]); value=json.dumps(result,indent=2)
    if len(sys.argv)>3: Path(sys.argv[3]).write_text(value,encoding='utf-8')
    print(value)
