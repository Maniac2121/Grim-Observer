# Verificări efectuate — 15 octombrie 2026

Motor: Godot 4.6.3.stable.official.7d41c59c4, Linux headless.

## Teste de simulare

- Cadia, 24 unități, 2 echipe: 22 eliminări, 16 blocaje, 11 contraatacuri, 98 atacuri la distanță; rezultat final detectat.
- Macragge, 36 unități, 3 echipe: 35 eliminări, 34 blocaje, 26 contraatacuri, 141 atacuri la distanță; rezultat final detectat.
- Warp, 48 unități, 4 echipe: 47 eliminări, 34 blocaje, 27 contraatacuri, 194 atacuri la distanță; rezultat final detectat.
- Test cu 320 unități, 4 echipe: 319 eliminări, 156 blocaje, 96 contraatacuri, 1283 atacuri la distanță; rezultat final detectat.
- Verificări prin assertions pentru pauză, selectarea țintei cinematice, lipsa țintelor aliate și existența eliminărilor.
- `bash -n build_android.sh`: fără erori de sintaxă.

## Export Android — EȘUAT

Mesajele Godot indică lipsa android_debug.apk și android_release.apk din șabloanele 4.6.3, lipsa SDK-ului Android/platform-tools/build-tools/apksigner și a căii Java SDK valide. Nu există un APK generat; nu s-a verificat nicio semnătură de APK nou.

Manifestul binar al referinței indică pachetul `ro.w40k.sim`. Presetul nou folosește `ro.grimobserver.standalone20261015`. Diferența este verificată la nivel de configurare, nu într-un APK nou compilat.

## Neverificat

Randarea vizuală (serverul grafic local nu a putut porni din cauza restricțiilor de socket), instalarea pe dispozitiv, performanța Android, inputul multitouch real, semnătura finală, alinierea finală, comportamentul la suspendarea și reluarea aplicației.

Testele headless nu demonstrează fidelitate artistică, fluiditate pe S22 Ultra sau absența problemelor grafice. Modelele, animațiile și ragdoll-urile sunt procedurale și simplificate.
