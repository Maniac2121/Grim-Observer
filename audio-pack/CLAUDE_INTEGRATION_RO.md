# Pachet audio pentru APK-ul W40K-TotalWar din 16 octombrie 2026

## Ce livrează acest pachet

303 WAV-uri mono de efecte și reacții, 7 compoziții originale stereo, manifest JSON, inventarul static al APK-ului și un loader Web Audio de referință. Muzica este livrată în OGG pentru bucle și MP3 pentru ascultare; masterele WAV sunt într-o arhivă separată. Toate fișierele audio sunt generate de la zero prin sinteză. Nu sunt extrase înregistrări din APK sau din jocuri comerciale. Vocalizările și corurile sunt sintetizate, nu înregistrări de actori/cor. Nu promit realism de studio sau fidelitate audio oficială Warhammer.

## Cerința utilizatorului

Integrează arme, melee, lovituri/moarte fără vorbire, nave care debarcă trupe, tancuri, dreadnoughts și titani; păstrează versiunea actualizată a jocului. Acest pachet NU este un APK și NU trebuie înlocuit proiectul nou cu vechiul prototip Godot.

## Ce am identificat prin inspecție statică

- APK-ul conține `assets/index.html` și `assets/three.min.js`: joc WebView/Three.js, nu proiect Godot.
- 46 intrări în tabelul W, plus vhb, pcannon, dcannon și dmissile = 50 definiții de arme la distanță. 15 tipuri în M.
- `sfx(name, pos)`, `AU.buf`, `LIM`, `LOUD`, `renderBank()` și suprascrieri ulterioare ale `RECIPES`.
- Ultimul `painSound(u, death)` este apelat prin wrapper-ele `damage` și `onKill`; are profilele din `PAIN_V`/`voiceOf`.
- `musicStart`, `musicStop`, `musicNext` și `MUS2` sunt redefinite spre finalul fișierului. Modifică definițiile efectiv active, nu doar prima versiune.
- Nava de transport, drop pod, nave hover, walker și titan au stări/animații care trebuie legate de evenimente audio; nu toate au deja hook audio separat.
- Unele nume SW apar în codul comun de modelare; nu le-am tratat ca dovadă că există facțiuni Star Wars selectabile în această versiune.

## Integrarea simplă în motorul actual

1. Copiază `sfx/`, `music/` și `audio_manifest.json` în `assets/audio/`. Nu împacheta `music_wav/` sau mostrele de prezentare în APK.
2. Încarcă manifestul și decodează numai familiile necesare pentru facțiunile selectate. WAV-urile decodate în float ocupă mai mult RAM decât fișierele. Nu încărca toate cele 303 la pornire.
3. Pentru familiile existente, umple `AU.buf[id]` cu variantele din manifest. `id` corespunde direct cu `bolt`, `hbolt`, `las`, `clang` etc. Oprește generarea vechilor variante pentru familiile înlocuite; altfel `renderBank()` asincron poate suprascrie noul buffer sau poate dubla sunetul.
4. Păstrează atenuarea după distanță și panoramarea din `sfx`. Folosește alegere aleatoare fără repetarea imediată a aceleiași variante, pitch între 0.96 și 1.04 pentru arme, 0.98–1.02 pentru reacții. Nu modifica pitch-ul muzicii.
5. 24 one-shot-uri simultane sunt un punct de pornire, nu o limită măsurată pe telefon. Prioritizează sursele apropiate/camera cinematică. Maxim 4 vocalizări simultane și cooldown per unitate de 0.4–0.8 s. Pentru hoarde, nu reda fiecare lovitură/împușcătură a fiecărei unități.
6. Reacții: alege `<voiceOf(u)>_pain` sau `<voiceOf(u)>_death`. Există toate cele 23 de profile din PAIN_V. Pentru profil necunoscut folosește guard. `necron`/`necronLord` sunt reacții mecanice, nu strigăte umane.
7. Utilizatorul NU dorește replici vorbite: dezactivează ruta `cry` către Android TTS/Web Speech pentru această integrare. Păstrează texte/subtitrări dacă sunt utile. Vocalizările au intenționat zero cuvinte, inclusiv `waaagh`, care este doar un răget nonverbal.
8. Nu dubla reacția de moarte cu pain sau cu vechea sinteză din `painSound`. Respectă probabilitățile și distanțele existente sau ajustează-le prin testare.
9. `web_audio_loader.js` este un exemplu opțional, verificat sintactic; nu este un patch testat în APK. Alege fie integrarea AU.buf, fie noul player. Nu le rula simultan pentru același eveniment.

## Mapări

`integration_map.json` acoperă cele 50 de chei W, cele 15 chei M, profilele vocale și vehiculele. Armele care folosesc aceeași familie acustică partajează variantele în mod intenționat; pachetul nu pretinde 50 de mecanisme de armă complet distincte.

- bolt/bpistol/infernobolt/plaguebolt/spearbolt → bolt; hbolter/assault/vhb/dcannon → hbolt.
- Bolterul de aici este un sunet SF original: atac metalic, corp grav, jet scurt și rezonanță. Dacă adaugi și impactul separat, evită încă o explozie artificială prea puternică la fiecare foc.
- clang/parry = contactul armelor/blocaj; sword_swing = aerul tăiat; hit/stab = corp; power = contact energetic; chain = contactul dinților, chain_loop = motorul ținut activ.
- Nu folosi clang pentru lovitura în carne și nu porni un loop de chainsword la fiecare cadru.

## Vehicule și nave

- dropship_approach la intrarea în scenă; dropship_loop în staționare; dropship_land la contactul cu solul; dropship_ramp la deschiderea rampei; armor_step pentru soldații care ies; dropship_depart la plecare.
- dropship_pod pentru coborârea + impactul capsulei; calibrarea întârzierii impactului din fișier este aproximativ 1.2 s.
- tank_start/tank_loop/tank_stop pentru motor; cannon sau hbolt pentru armă. Bucla include motor și mecanică, nu este un model fizic separat al șenilelor.
- dread_start/dread_loop/dread_stop + dread_step sincronizat cu contactul piciorului; hbolt/rocket pentru arme.
- titan_start/titan_loop/titan_stop + titan_step + titan_horn; bigboom pentru distrugere, cu limită de suprapunere.
- hover_loop pentru vehicule hover; warp_loop pentru efecte/portaluri Warp. Shield folosește `shield`.
- Limitează buclele apropiate la 4–8. Un emitter are un singur source în loop, cu fade de 100–300 ms la pornire/oprire; curăță emitter-ele la moarte, ieșire din hartă și întoarcerea la meniu.

## Muzică

Șapte piese distincte, fiecare 32 măsuri în 4/4, cu secțiuni de intensitate. OGG-urile au LOOPSTART/LOOPEND; la Web Audio setează `source.loop=true`, `loopStart=0`, `loopEnd=frames/sample_rate` din manifest. Cozile sunt integrate circular. Nu presupune că playerul citește automat tag-urile Vorbis.

MP3-urile sunt pentru ascultare/previzualizare: nu le folosi pentru bucle precise din cauza întârzierii codec-ului. Pentru schimbarea pieselor folosește crossfade egal în putere de 2–4 s și decodează doar piesa curentă și următoarea. Pe telefon se recomandă streaming pentru muzică, dacă implementarea asigură un loop acceptabil; AudioBuffer oferă limite precise, dar folosește RAM.

Gain inițial recomandat: muzică 0.12–0.2, arme 0.25–0.45, reacții 0.15–0.3, motoare 0.08–0.15. Acestea sunt puncte de pornire și depind de mixul existent. Păstrează headroom și compresor pe master; scade muzica cu 3–5 dB pentru explozii apropiate/finisher. Nu transforma fiecare sunet normalizat într-o sursă la volum maxim.

## Android/WebView

Pornește/resume AudioContext numai după gestul utilizatorului, prin ruta existentă de START BATTLE. Nu crea câte un AudioContext pentru fiecare unitate. Suspendă la background și curăță resursele la ieșire.

Pentru fișiere locale, preferă AndroidX WebViewAssetLoader și originea https://appassets.androidplatform.net/assets/audio/. Nu presupune că fetch din file:///android_asset funcționează fără ajustări. Nu dezactiva global securitatea WebView ca soluție.

## Validare necesară în joc

S-au verificat fișierele, lipsa clipping-ului digital, structura WAV/OGG, limitele buclelor și integritatea arhivelor. Nu s-a efectuat audiție umană, testare a mixului în APK sau benchmark pe S22 Ultra. Claude trebuie să testeze: pornirea audio pe mobil, mute, pauză, fundal/relansare, load fail cu fallback, memorie, hoarde de 300+ unități, buclele motoarelor și sincronizarea pașilor/aterizării. Stilul vocal sintetizat este o alegere de prototip, nu înlocuitor garantat pentru actori.
