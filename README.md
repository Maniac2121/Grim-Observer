# Grim Observer 40K — prototip 0.1.0

Proiect independent creat de la zero în Godot 4.6.3. Nu conține cod, modele sau alte fișiere copiate din APK-ul de referință. Prototip fan neoficial; denumirile Warhammer și ale personajelor aparțin titularilor lor.

## Starea reală a livrării

**Nu există un APK compilat sau semnat în această arhivă.** Exportul a fost încercat și a eșuat deoarece mediul nu are Android SDK, JDK complet configurat sau șabloanele Android Godot. Conexiunea proxy necesară descărcării instrumentelor a eșuat. Nu a fost verificată instalarea pe Samsung Galaxy S22 Ultra și nici performanța pe Android. Testele sunt headless, fără verificare vizuală.

## Implementat în surse

- Meniu cu hărți, 2–4 echipe, patru facțiuni în fiecare echipă, 0–40 soldați per facțiune/echipă și plafon de 320 de unități.
- Ultramarines, Cadian Imperial Guard, Chaos Daemons și Black Legion. Primul soldat al fiecărui contingent poate deveni eroul facțiunii; este inclus în efectiv, nu adăugat peste acesta.
- Marneus Calgar, Ursula Creed, Skarbrand și Abaddon the Despoiler, cu nume afișate și reprezentări procedurale stilizate. Nu sunt modele oficiale, sculpturi detaliate sau reproduceri fidele de producție.
- Trei variante de teren: Cadia, Macragge, Warp, cu geometrii și palete diferite. Decorul exterior nu oferă navigație tactică sau acoperire.
- Simulare automată: selectarea inamicului, deplasare, foc la distanță pentru Cadian, atacuri corp la corp, blocaj probabilistic și contraatac. Animații procedurale ale membrelor, fără motion capture sau coregrafii avansate.
- Sânge dezactivabil, trasoare și explozii vizuale. Ragdoll simplificat: șase corpuri rigide articulate, maxim 20 de cadavre păstrate.
- Cameră Observer cu orbită, zoom și panoramare; cameră cinematică cu trei încadrări alternante și urmărirea eroilor.
- Pauză, viteze 0.25×–4×, statistici, jurnal de evenimente și rezultat final; configurația se salvează local.

Nu sunt încă implementate sunetul, modele artistice avansate, animații scheletale elaborate, comportamente tactice de tip Total War sau optimizarea măsurată pe telefon. Proiectul este un prototip de bază, nu îndeplinirea integrală a calității cerute.

## Rulare locală

Deschide `project.godot` în Godot 4.6.3 și apasă F6/F5. Nu sunt necesare resurse descărcate separat.

Desktop: mouse stânga pentru orbită, dreapta pentru panoramare, rotiță pentru zoom; Space pentru pauză, C pentru cinematică, Escape pentru configurare.

Android, după export: un deget pentru orbită, două degete pentru panoramare/zoom; comenzile principale sunt și pe ecran.

## Export Android

Presetul `Android` este pentru ARM64, compatibil ca arhitectură cu S22 Ultra, cu identificatorul `ro.grimobserver.standalone20261015`. Identificatorul APK-ului de referință este `ro.w40k.sim`; aplicațiile sunt distincte.

Instalează Godot 4.6.3, șabloanele de export pentru aceeași versiune, JDK 17+ și Android SDK (platform-tools, build-tools și platforma cerută de Godot). Configurează căile în Godot. Folosește un keystore release propriu, păstrat pentru actualizări. Nu folosi cheia aplicației originale.

`build_android.sh` acceptă `ANDROID_HOME`, `JAVA_HOME`, `OBSERVER_KEYSTORE`, `OBSERVER_KEY_ALIAS`, `OBSERVER_KEY_PASSWORD`. Scriptul încearcă exportul release și verifică semnătura, alinierea, identificatorul, arhitectura și SHA-256. Scriptul a fost verificat sintactic, dar fluxul complet nu a putut fi executat în acest mediu. Nu există o cheie privată inclusă.

Instalarea efectivă și verificarea interacțiunii tactile, performanței, randării și ciclului de viață trebuie făcute pe dispozitiv după compilare. Nu distribui ca versiune validată înainte de aceste verificări.

## Teste

`godot --headless --path . -- --smoke` rulează bătălii pe cele trei hărți, cu 2, 3 și 4 echipe, verifică pauza, selectarea cinematică, absența atacurilor asupra propriei echipe și înregistrarea eliminărilor.

`godot --headless --path . -- --stress` rulează o bătălie cu 320 de unități și 4 echipe. Acest test nu este un benchmark Android.

Vezi `VALIDATION.md` și jurnalele alăturate pentru rezultatele efective.

## Compilare în GitHub Actions

Workflow-ul este în `.github/workflows/android.yml`. Vezi `GITHUB.md`. Fișierele sunt pregătite, dar nu există încă o rulare GitHub verificată sau un APK rezultat.
