from __future__ import annotations
import json, re, subprocess, sys, threading, webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
from gui.logbox import LogBox


def _run(app, frame, log, args, done=None):
    def worker():
        ok=False
        try:
            cmd=([sys.executable,"--multisource-cli",*args] if getattr(sys,"frozen",False)
                 else [sys.executable,str(app.project_root/"main.py"),"--multisource-cli",*args])
            p=subprocess.Popen(cmd,cwd=str(app.data_root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
            for line in p.stdout or []:
                frame.after(0,lambda m=line.rstrip(): log.append(m,"info"))
            ok=p.wait()==0
        except Exception as e:
            frame.after(0,lambda: log.append(f"Error: {e}","error"))
        frame.after(0,lambda: (app.refresh_status(), done(ok) if done else None))
    threading.Thread(target=worker,daemon=True).start()

class CrunchyrollTab:
    def __init__(self,frame,app): self.frame=frame; self.app=app; self._build()
    def _build(self):
        f=self.frame; f.columnconfigure(0,weight=1); f.rowconfigure(1,weight=1)
        card=ctk.CTkFrame(f); card.grid(row=0,column=0,sticky="ew",padx=14,pady=12); card.columnconfigure(1,weight=1)
        ctk.CTkLabel(card,text="Crunchyroll",font=ctk.CTkFont(size=20,weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=14,pady=(12,4))
        ctk.CTkLabel(card,text="1  Open Crunchyroll and sign in.\n2  F12 → Application → Storage → Cookies → crunchyroll.com.\n3  Copy the value of the etp_rt cookie and paste it below.",justify="left",anchor="w").grid(row=1,column=0,columnspan=2,sticky="w",padx=14,pady=8)
        ctk.CTkButton(card,text="Open Watch History ↗",command=lambda:webbrowser.open("https://www.crunchyroll.com/history")).grid(row=1,column=2,padx=14)
        ctk.CTkLabel(card,text="FIRST-TIME SETUP: After pasting the cookie, click Configure Crunchyroll. This is required before your first sync and normally only needs to be done once, unless the cookie expires or changes.",justify="left",anchor="w",wraplength=720,font=ctk.CTkFont(size=11,weight="bold"),text_color=("#8a5a00","#f0b44c")).grid(row=2,column=0,columnspan=3,sticky="ew",padx=14,pady=(2,6))
        self.cookie=ctk.StringVar(value=self.app.cfg.get("crunchyroll",{}).get("etp_rt",""))
        e=ctk.CTkEntry(card,textvariable=self.cookie,show="*"); e.grid(row=3,column=0,columnspan=2,sticky="ew",padx=14,pady=(4,12))
        ctk.CTkButton(card,text="Configure Crunchyroll",command=self.save).grid(row=3,column=2,padx=14,pady=(4,12))
        bottom=ctk.CTkFrame(f,fg_color="transparent"); bottom.grid(row=1,column=0,sticky="nsew",padx=14); bottom.columnconfigure(0,weight=1); bottom.rowconfigure(1,weight=1)
        ctk.CTkButton(bottom,text="Refresh Crunchyroll History",command=self.refresh).grid(row=0,column=0,sticky="w",pady=6)
        self.log=LogBox(bottom,height=220); self.log.grid(row=1,column=0,sticky="nsew")
    def save(self):
        self.app.cfg.setdefault("crunchyroll",{})["etp_rt"]=self.cookie.get().strip(); self.app.save_config(); messagebox.showinfo("Crunchyroll","Crunchyroll configured successfully. It is ready for sync.")
    def refresh(self): self.save(); self.log.clear(); _run(self.app,self.frame,self.log,["fetch"])

class HidiveTab:
    def __init__(self,frame,app): self.frame=frame; self.app=app; self._build()
    @staticmethod
    def parse(text):
        a=re.search(r'(?is)["\']?authorization["\']?\s*[=:]\s*["\']?Bearer\s+([^"\'\r\n; }]+)',text)
        k=re.search(r'(?is)["\']?x-api-key["\']?\s*[=:]\s*["\']?([^"\'\r\n; }]+)',text)
        v=re.search(r'(?is)["\']?x-app-var["\']?\s*[=:]\s*["\']?([^"\'\r\n; }]+)',text)
        return (a.group(1).strip() if a else "",k.group(1).strip() if k else "",v.group(1).strip() if v else "")
    def _build(self):
        f=self.frame; f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        card=ctk.CTkFrame(f); card.grid(row=0,column=0,sticky="ew",padx=14,pady=12); card.columnconfigure(0,weight=1)
        ctk.CTkLabel(card,text="HIDIVE",font=ctk.CTkFont(size=20,weight="bold")).grid(row=0,column=0,sticky="w",padx=14,pady=(12,4))
        guide="1  HIDIVE → Watch History.\n2  F12 → Network → Fetch/XHR → Refresh.\n3  Find vod?p=1&rpp=10.\n4  Right-click → Copy → Copy as PowerShell.\n5  Paste the copied request below and click Configure HIDIVE."
        ctk.CTkLabel(card,text=guide,justify="left",anchor="w").grid(row=1,column=0,sticky="w",padx=14,pady=6)
        ctk.CTkButton(card,text="Open Watch History ↗",command=lambda:webbrowser.open("https://www.hidive.com/history")).grid(row=1,column=1,sticky="e",padx=14,pady=6)
        ctk.CTkLabel(card,text="FIRST-TIME SETUP: After pasting the copied request, click Configure HIDIVE. This is required before your first sync and normally only needs to be repeated when HIDIVE authentication expires or changes.",justify="left",anchor="w",wraplength=720,font=ctk.CTkFont(size=11,weight="bold"),text_color=("#8a5a00","#f0b44c")).grid(row=2,column=0,columnspan=2,sticky="ew",padx=14,pady=(2,6))
        self.box=ctk.CTkTextbox(card,height=115); self.box.grid(row=3,column=0,columnspan=2,sticky="ew",padx=14,pady=6)
        self.state=ctk.CTkLabel(card,text="HIDIVE not configured",anchor="w"); self.state.grid(row=4,column=0,columnspan=2,sticky="w",padx=14,pady=(2,8))
        ctk.CTkButton(card,text="Configure HIDIVE",command=self.configure).grid(row=5,column=0,sticky="w",padx=14,pady=(0,12))
        bottom=ctk.CTkFrame(f,fg_color="transparent"); bottom.grid(row=1,column=0,sticky="ew",padx=14); ctk.CTkButton(bottom,text="Refresh HIDIVE History",command=self.refresh).pack(side="left",pady=4)
        self.log=LogBox(f,height=210); self.log.grid(row=2,column=0,sticky="nsew",padx=14,pady=(6,10)); self._status()
    def _status(self):
        ok=bool(self.app.cfg.get("hidive",{}).get("bearer_token","")); self.state.configure(text="● HIDIVE configured" if ok else "○ HIDIVE not configured",text_color="#4caf50" if ok else "#777777")
    def configure(self):
        token,key,ver=self.parse(self.box.get("1.0","end").strip())
        if not token: messagebox.showerror("HIDIVE","Could not find a HIDIVE Authorization Bearer token in the pasted request."); return
        h=self.app.cfg.setdefault("hidive",{}); h["bearer_token"]=token
        if key: h["api_key"]=key
        if ver: h["app_version"]=ver
        self.app.save_config(); self.box.delete("1.0","end"); self._status(); messagebox.showinfo("HIDIVE","HIDIVE configured successfully.")
    def refresh(self):
        h=self.app.cfg.get("hidive",{}); token=h.get("bearer_token","")
        if not token: messagebox.showerror("HIDIVE","Configure HIDIVE first."); return
        self.log.clear(); _run(self.app,self.frame,self.log,["fetch-hidive"])

class NetflixTab:
    def __init__(self,frame,app): self.frame=frame; self.app=app; self.path=ctk.StringVar(); self._build()
    def _build(self):
        f=self.frame; f.columnconfigure(0,weight=1)
        card=ctk.CTkFrame(f); card.grid(row=0,column=0,sticky="ew",padx=14,pady=12); card.columnconfigure(0,weight=1)
        ctk.CTkLabel(card,text="Netflix",font=ctk.CTkFont(size=20,weight="bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=14,pady=(12,4))
        ctk.CTkLabel(card,text="Import your Netflix Viewing Activity CSV. Selecting a file does not replace existing data until you click Import.",anchor="w").grid(row=1,column=0,columnspan=2,sticky="w",padx=14,pady=6)
        ctk.CTkButton(card,text="Open Netflix Profile Management ↗",command=lambda:webbrowser.open("https://www.netflix.com/ProfilesGate")).grid(row=2,column=0,sticky="w",padx=14,pady=(4,2))
        ctk.CTkLabel(card,text="Manage Profile → Select Profile needed for watch history → Viewing Activity → 'Download All' at bottom of the page",anchor="w",justify="left",wraplength=720,font=ctk.CTkFont(size=11)).grid(row=3,column=0,columnspan=2,sticky="w",padx=14,pady=(0,8))
        ctk.CTkEntry(card,textvariable=self.path).grid(row=4,column=0,sticky="ew",padx=(14,6),pady=6); ctk.CTkButton(card,text="Choose CSV…",command=self.choose).grid(row=4,column=1,padx=(0,14))
        self.preview=ctk.CTkLabel(card,text="No CSV selected.",anchor="w"); self.preview.grid(row=5,column=0,columnspan=2,sticky="w",padx=14,pady=4)
        ctk.CTkButton(card,text="Import Netflix History",command=self.import_csv).grid(row=6,column=0,sticky="w",padx=14,pady=(4,12))
        self.log=LogBox(f,height=220); self.log.grid(row=1,column=0,sticky="nsew",padx=14,pady=8)
    def choose(self):
        p=filedialog.askopenfilename(filetypes=[("CSV files","*.csv")]);
        if p:
            self.path.set(p)
            try:
                import csv
                with open(p,encoding="utf-8-sig",newline="") as fh: n=sum(1 for _ in csv.DictReader(fh))
                self.preview.configure(text=f"{Path(p).name}  •  {n} viewing records ready to import")
            except Exception as e: self.preview.configure(text=f"Could not validate CSV: {e}")
    def import_csv(self):
        p=self.path.get().strip()
        if not p: messagebox.showerror("Netflix","Choose a CSV first."); return
        self.log.clear(); _run(self.app,self.frame,self.log,["import-netflix",p])

class ManualEntryTab:
    def __init__(self,frame,app): self.frame=frame; self.app=app; self.quick_on=ctk.BooleanVar(value=True); self.structured_on=ctk.BooleanVar(value=False); self._build(); self.refresh_list()
    def _build(self):
        f=self.frame; f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        top=ctk.CTkFrame(f); top.grid(row=0,column=0,sticky="ew",padx=14,pady=(12,6)); top.columnconfigure(0,weight=1); top.columnconfigure(1,weight=1)
        q=ctk.CTkFrame(top,fg_color="transparent"); q.grid(row=0,column=0,sticky="nsew",padx=10,pady=10)
        ctk.CTkCheckBox(q,text="Include Quick Entry",variable=self.quick_on).pack(anchor="w"); ctk.CTkLabel(q,text="Quick Entry",font=ctk.CTkFont(size=15,weight="bold")).pack(anchor="w",pady=(8,2)); ctk.CTkLabel(q,text="One title per line. Examples: Title - Season 2 - Episode 6\nTitle Season 2, watched 8",justify="left").pack(anchor="w")
        self.quick=ctk.CTkTextbox(q,height=135); self.quick.pack(fill="both",expand=True,pady=6)
        s=ctk.CTkFrame(top,fg_color="transparent"); s.grid(row=0,column=1,sticky="nsew",padx=10,pady=10); ctk.CTkCheckBox(s,text="Include Structured Entry",variable=self.structured_on).pack(anchor="w"); ctk.CTkLabel(s,text="Structured Entry",font=ctk.CTkFont(size=15,weight="bold")).pack(anchor="w",pady=(8,2))
        self.title=ctk.CTkEntry(s,placeholder_text="Title"); self.title.pack(fill="x",pady=3); self.season=ctk.CTkEntry(s,placeholder_text="Season (default 1)"); self.season.pack(fill="x",pady=3); self.progress=ctk.CTkEntry(s,placeholder_text="Episodes watched"); self.progress.pack(fill="x",pady=3); self.source=ctk.CTkOptionMenu(s,values=["amazon","other"]); self.source.pack(anchor="w",pady=3)
        ctk.CTkButton(f,text="Preview & Append Selected Entries",command=self.save).grid(row=1,column=0,sticky="w",padx=14,pady=6)
        self.listbox=ctk.CTkTextbox(f,height=190); self.listbox.grid(row=2,column=0,sticky="nsew",padx=14,pady=(4,10))
    @staticmethod
    def parse_line(line):
        line=line.strip(); season=1; progress=None
        m=re.search(r'(?i)season\s*(\d+)',line); season=int(m.group(1)) if m else 1
        p=re.search(r'(?i)(?:episode|watched)\s*(\d+)',line); progress=int(p.group(1)) if p else None
        title=re.sub(r'(?i)\s*[-,]?\s*season\s*\d+','',line); title=re.sub(r'(?i)\s*[-,]?\s*(?:episode|watched)\s*\d+','',title).strip(' ,-')
        return title,season,progress
    def save(self):
        from src.importers.manual import add_manual
        entries=[]
        if self.quick_on.get():
            for line in self.quick.get("1.0","end").splitlines():
                if line.strip(): entries.append((*self.parse_line(line),"amazon"))
        if self.structured_on.get():
            t=self.title.get().strip()
            if t: entries.append((t,int(self.season.get() or 1),int(self.progress.get()) if self.progress.get().strip() else None,self.source.get()))
        if not entries: messagebox.showerror("Manual Entry","No selected entries were provided."); return
        preview="\n".join(f"• {t} | S{s} | progress {p if p is not None else '?'} | {src}" for t,s,p,src in entries)
        if not messagebox.askyesno("Confirm manual entries",f"Append/merge these entries?\n\n{preview}"): return
        path=self.app.data_root/"data"/"manual_history.json"
        for t,s,p,src in entries: add_manual(path,t,s,p,src)
        self.quick.delete("1.0","end"); self.refresh_list(); self.app.refresh_status()
    def refresh_list(self):
        p=self.app.data_root/"data"/"manual_history.json"; rows=[]
        if p.exists():
            try: rows=json.loads(p.read_text(encoding="utf-8")).get("entries",[])
            except: pass
        self.listbox.configure(state="normal"); self.listbox.delete("1.0","end")
        self.listbox.insert("1.0","Saved manual entries\n\n"+"\n".join(f"{x.get('title')}  •  S{x.get('season',1)}  •  {x.get('progress','?')} watched  •  {x.get('source','manual')}" for x in rows)); self.listbox.configure(state="disabled")
