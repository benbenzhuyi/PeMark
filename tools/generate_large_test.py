#!/usr/bin/env python3
from pathlib import Path
import argparse
p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--paragraphs',type=int,default=8000); a=p.parse_args()
out=Path(a.output)
with out.open('w',encoding='utf-8',newline='\n') as f:
    for i in range(1,a.paragraphs+1):
        if i%50==1: f.write(f'# Chapter {(i-1)//50+1}\n')
        if i%10==1: f.write(f'## Section {i}\n')
        f.write(f'Paragraph {i}: **bold** *italic* `inline code` and a [link](https://example.com/{i}). 中文测试段落。\n\n')
print(out, out.stat().st_size)
