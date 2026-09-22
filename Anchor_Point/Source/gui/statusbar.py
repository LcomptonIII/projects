"""MultiSource readiness strip: provider sources plus AniList destination."""
import json
import hashlib
from pathlib import Path
import customtkinter as ctk
from gui.paths import storage_data_dir
_GREEN="#4caf50"; _GRAY="#777777"; _AMBER="#d99a2b"
class StatusBar(ctk.CTkFrame):
    def __init__(self,master,app,**kwargs):
        kwargs.setdefault("height",34); kwargs.setdefault("corner_radius",0); kwargs.setdefault("fg_color",("gray78","gray15")); super().__init__(master,**kwargs); self.app=app; self.pack_propagate(False)
        row=ctk.CTkFrame(self,fg_color="transparent"); row.pack(expand=True); self._labels={}
        for k in ("crunchyroll","hidive","netflix","manual","anilist"):
            l=ctk.CTkLabel(row,text="",font=ctk.CTkFont(size=11),padx=12,cursor="hand2"); l.pack(side="left"); self._labels[k]=l
            l.bind("<Button-1>",lambda e,key=k:self._jump(key))
        self.refresh()
    def _jump(self,key): self.app._nav.set({"crunchyroll":"Crunchyroll","hidive":"HIDIVE","netflix":"Netflix","manual":"Manual Entry","anilist":"Export & Sync Settings"}[key]); self.app._show("settings" if key=="anilist" else key)
    def _set(self,k,ok,text,attention=False): self._labels[k].configure(text=f"{'●' if ok else '○'}  {text}",text_color=_AMBER if attention else (_GREEN if ok else _GRAY))
    def refresh(self):
        cfg=self.app.cfg; root=self.app.data_root
        # Crunchyroll is ready when configured and history exists.
        hp=Path(cfg.get("storage",{}).get("path","data/history.json")); hp=hp if hp.is_absolute() else root/hp
        cr_n=hi_n=0
        if hp.exists():
            try:
                eps=json.loads(hp.read_text(encoding="utf-8")).get("episodes",[]); cr_n=sum((x.get("source") or "crunchyroll")=="crunchyroll" for x in eps); hi_n=sum(x.get("source")=="hidive" for x in eps)
            except: pass
        cr_cfg=bool(cfg.get("crunchyroll",{}).get("etp_rt","")); hi_cfg=bool(cfg.get("hidive",{}).get("bearer_token",""))
        self._set("crunchyroll",cr_cfg and cr_n>0,f"Crunchyroll ({cr_n})" if cr_n else "Crunchyroll",attention=cr_cfg and not cr_n)
        self._set("hidive",hi_cfg and hi_n>0,f"HIDIVE ({hi_n})" if hi_n else "HIDIVE",attention=hi_cfg and not hi_n)
        data_dir=storage_data_dir(cfg, root)
        np=data_dir/"netflix_history.json"; nn=0
        if np.exists():
            try: nn=len(json.loads(np.read_text(encoding="utf-8")).get("views",[]))
            except: pass
        self._set("netflix",nn>0,f"Netflix ({nn})" if nn else "Netflix")
        mp=data_dir/"manual_history.json"; mn=0
        if mp.exists():
            try: mn=len(json.loads(mp.read_text(encoding="utf-8")).get("entries",[]))
            except: pass
        self._set("manual",mn>0,f"Manual ({mn})" if mn else "Manual")
        al_cfg=cfg.get("exporters",{}).get("anilist",{})
        token=al_cfg.get("access_token","")
        fp=hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""
        al_ok=bool(token and al_cfg.get("validated_token_fingerprint")==fp and al_cfg.get("validated_user_id") and al_cfg.get("validated_username"))
        al_attention=bool(token and not al_ok)
        al_text=f"AniList — {al_cfg.get('validated_username')}" if al_ok else ("AniList — configure required" if al_attention else "AniList")
        self._set("anilist",al_ok,al_text,attention=al_attention)
