import json,zipfile,shutil,hashlib,csv,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'out';D=R/'delivery';D.mkdir(exist_ok=True)
m=json.loads((O/'audio_manifest.json').read_text());inv=json.loads((R/'apk_inventory.json').read_text())
ids={a['id'] for a in m['sound_effects']}
weapons={k:{'name':v['name'],'sfx_id':v['legacy_sfx']} for k,v in inv['weapons'].items()}
assert all(v['sfx_id'] in ids for v in weapons.values())
melee={k:v for k,v in [('fist','hit'),('chainsword','chain'),('powersword','power'),('chainaxe','chain'),('choppa','clang'),('klaw','power'),('scythe','power'),('spear','power'),('talons','stab'),('claws','stab'),('hellblade','power'),('monster','hammer'),('hammer','hammer'),('blade','clang'),('axe','power')]}
profiles=sorted(a['id'][:-5] for a in m['sound_effects'] if a['id'].endswith('_pain') and a['variant']==1)
mapdata={'ranged_weapons':weapons,'melee_contact':melee,'melee_note':'Use clang/parry only for metal/weapon contact; use hit/stab for body contact. Existing M.fx may need extra context in hit/block callbacks.','voice_profiles':{k:{'pain':k+'_pain','death':k+'_death'} for k in profiles},'vehicles':{'transport':['dropship_approach','dropship_loop','dropship_land','dropship_ramp','dropship_depart'],'drop_pod':['dropship_pod'],'tank':['tank_start','tank_loop','tank_stop','cannon','hbolt'],'dreadnought':['dread_start','dread_loop','dread_step','dread_stop','hbolt','rocket'],'titan':['titan_start','titan_loop','titan_step','titan_horn','titan_stop','bigboom'],'hover':['hover_loop'],'warp':['warp_loop']},'legacy_sfx_aliases':{'bolter':'bolt'},'all_audio_is_original_synthesis':True}
assert set(inv['literal_sfx_calls'])<=ids
(O/'integration_map.json').write_text(json.dumps(mapdata,indent=2,ensure_ascii=False))
for p in ['CLAUDE_INTEGRATION_RO.md','apk_inventory.json','web_audio_loader.js']:shutil.copy(R/p,O/p)
(O/'README_RO.md').write_text('''# Grim Observer — pachet audio original 1.0\n\n303 efecte/reacții WAV mono și șapte piese de luptă stereo. Pentru versiunea WebView/Three.js a W40K-TotalWar încărcată la 16 octombrie 2026.\n\n- SFX și reacțiile sunt în sfx/.\n- Muzica pentru joc este în music/ (OGG); MP3-urile sunt pentru ascultare.\n- Masterele muzicale WAV sunt într-o arhivă separată.\n- audio_manifest.json conține variații, durate, loop points și hash-uri.\n- CLAUDE_INTEGRATION_RO.md explică maparea în jocul actual.\n\nToate sunetele și piesele au fost sintetizate și compuse pentru acest pachet. Fără replici vorbite, fără înregistrări de actori, fără sample-uri extrase din APK sau melodii comerciale. Sunetul este stilizat/electronic; nu este audio oficial Warhammer. Poți folosi, modifica și redistribui fișierele generate în proiect, fără atribuire obligatorie; asta nu acordă drepturi asupra mărcilor sau personajelor terților.\n\nAcesta este un pachet de resurse, nu un APK. Nu modifica și nu înlocui versiunea actuală a jocului cu vechiul prototip Godot. Testarea pe dispozitiv și mixajul în joc rămân de făcut.\n''')
mp=O/'music_mp3';mp.mkdir(exist_ok=True)
for a in m['music']:
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(O/a['wav_master']),'-c:a','libmp3lame','-b:a','192k','-metadata','title='+a['title'],str(mp/(a['id']+'.mp3'))],check=True)
with (O/'catalog.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['id','category','variant','path','seconds','loop'])
 for a in m['sound_effects']:w.writerow([a['id'],a['category'],a['variant'],a['path'],a['duration_seconds'],a['loop']])
 for a in m['music']:w.writerow([a['id'],'music','',a['path'],a['duration_seconds'],True])
common=['README_RO.md','CLAUDE_INTEGRATION_RO.md','audio_manifest.json','integration_map.json','apk_inventory.json','web_audio_loader.js','catalog.csv','validation.json']
sets={
 'GrimObserver_Audio_COMPLETE.zip':['sfx','music','music_mp3','previews'],
 'GrimObserver_SFX_303.zip':['sfx'],
 'GrimObserver_BattleMusic_7.zip':['music','music_mp3'],
 'GrimObserver_Music_WAV_Masters.zip':['music_wav']}
for name,folders in sets.items():
 with zipfile.ZipFile(D/name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for f in common:z.write(O/f,f)
  for folder in folders:
   for f in sorted((O/folder).rglob('*')):
    if f.is_file():z.write(f,str(f.relative_to(O)))
 with zipfile.ZipFile(D/name) as z:assert z.testzip() is None
for p in (O/'previews').glob('*.mp3'):shutil.copy(p,D/p.name)
shutil.copy(O/'CLAUDE_INTEGRATION_RO.md',D/'CLAUDE_INTEGRATION_RO.md')
(D/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name for f in sorted(D.iterdir()) if f.is_file() and f.name!='SHA256SUMS.txt')+'\n')
print(json.dumps({'sfx':len(m['sound_effects']),'music':len(m['music']),'files':[{ 'name':f.name,'MB':round(f.stat().st_size/1e6,2)} for f in D.iterdir()]},indent=2))
