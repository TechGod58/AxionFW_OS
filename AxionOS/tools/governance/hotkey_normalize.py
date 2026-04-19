#!/usr/bin/env python3
import re

MOD_ORDER=["Ctrl","Alt","Shift"]
VALID_KEYS=set(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")+[str(i) for i in range(10)]+[f"F{i}" for i in range(1,25)]+["Esc","Tab","Enter","Space","Backspace","Delete","Insert","Home","End","PageUp","PageDown","Up","Down","Left","Right"])
MOD_ALIAS={"ctrl":"Ctrl","control":"Ctrl","alt":"Alt","shift":"Shift"}
KEY_ALIAS={"escape":"Esc","esc":"Esc","space":"Space","enter":"Enter","return":"Enter","backspace":"Backspace","del":"Delete","delete":"Delete","ins":"Insert","insert":"Insert","home":"Home","end":"End","pageup":"PageUp","pagedown":"PageDown","up":"Up","down":"Down","left":"Left","right":"Right","tab":"Tab"}

def parse_chord(ch):
    if not isinstance(ch,str) or not ch.strip():
        raise ValueError("empty chord")
    parts=[p.strip() for p in ch.replace('-', '+').split('+') if p.strip()]
    if not parts:
        raise ValueError("invalid chord")
    mods={"ctrl":False,"alt":False,"shift":False}
    key=None
    for i,p in enumerate(parts):
        pl=p.lower()
        if i < len(parts)-1:
            if pl not in MOD_ALIAS:
                raise ValueError(f"invalid modifier: {p}")
            m=MOD_ALIAS[pl].lower(); mods[m]=True
        else:
            if pl in KEY_ALIAS:
                key=KEY_ALIAS[pl]
            elif re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])",pl):
                key=pl.upper()
            elif re.fullmatch(r"[a-z]",pl):
                key=pl.upper()
            elif re.fullmatch(r"[0-9]",pl):
                key=pl
            else:
                key=p
            if key not in VALID_KEYS:
                raise ValueError(f"invalid key: {p}")
    return {"ctrl":mods["ctrl"],"alt":mods["alt"],"shift":mods["shift"],"key":key}

def normalize_chord(ch):
    o=parse_chord(ch)
    out=[]
    if o["ctrl"]: out.append("Ctrl")
    if o["alt"]: out.append("Alt")
    if o["shift"]: out.append("Shift")
    out.append(o["key"])
    return "+".join(out)
