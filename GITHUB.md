# APK prin GitHub Actions

Workflow pregătit, încă NEEXECUTAT pe GitHub. Nu există încă un APK rezultat.

1. Creează un repository privat și încarcă întregul conținut al proiectului la rădăcină, inclusiv `.github/workflows/android.yml`. Nu încărca doar arhiva ZIP: GitHub nu o extrage automat. Fișierul `project.godot` trebuie să fie în rădăcina repository-ului.
2. Deschide **Actions → Build Android APK → Run workflow**. Un push pe main/master pornește de asemenea compilarea.
3. După succes, descarcă artifactul **GrimObserver-Android-APK**. Extrage ZIP-ul și deschide fișierul `.apk` pe telefon. Android poate cere să permiți instalarea din aplicația cu care îl deschizi.

Pachetul nou este `ro.grimobserver.standalone20261015`; originalul `ro.w40k.sim` nu este înlocuit. Workflow-ul validează semnătura și alinierea APK-ului, identificatorul și arhitectura ARM64. Instalarea și performanța pe telefon rămân de verificat efectiv.

## Semnarea

Prima compilare poate funcționa fără configurarea secretelor: workflow-ul creează o cheie temporară pentru un APK de probă semnat. Cheia nu este publicată și este eliminată la sfârșit. O nouă compilare cu altă cheie nu poate actualiza aplicația de probă instalată: aceasta trebuie dezinstalată, pierzând setările ei. Aplicația originală rămâne separată.

Pentru actualizări fără dezinstalare, configurează înainte de prima versiune stabilă secretele repository-ului:

- `ANDROID_KEYSTORE_BASE64`: keystore propriu codificat base64.
- `ANDROID_KEY_ALIAS`: aliasul cheii.
- `ANDROID_KEY_PASSWORD`: parola comună pentru keystore și cheie.

Nu pune cheile sau parolele în cod și nu le trimite în conversație. Păstrează o copie sigură a cheii permanente.

Workflow-ul folosește Godot 4.6.3, Java 17, SDK Android și verificări headless. Rezultatul rămâne prototipul descris în README, cu modele procedurale; compilarea nu îmbunătățește automat grafica.
