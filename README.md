# Pantheon Defense

Ein 3D-Tower-Defense in Rust und Bevy für Solo und privaten Zweier-Koop.
Verteidige einen gemeinsamen Rundkurs in fünf Schwierigkeitsstufen. Der Feldzug
hat 30 Wellen. Acht Spielvarianten reichen von 16 bis 48 Wellen. Griechenland,
Rom und Japan bringen 36 Truppen, 24 Helden und neun Gebäude aufs Brett.

## Spielen

1. Erstelle ein Konto mit einem eindeutigen Rufnamen. Wähle Karte, Schwierigkeit
   und Spielvariante. Bei **Zu zweit** gibst du den Rufnamen des registrierten
   Mitspielers ein. Kopiere den Einladungslink im Spielraum und teile ihn mit
   der eingeladenen Person.
2. Der Gastgeber startet. **Rekrutieren** setzt die Einheit auf ein zufälliges
   freies Feld und markiert sie kurz. Gleiche Einheiten derselben Seltenheit
   füllen zuerst ihren Trupp bis drei. Ist kein passendes Feld frei, wartet die
   Einheit in der Reserve. Im Koop rekrutierst du auf deiner eigenen Hälfte.
3. Tippe einen Trupp aus drei Einheiten an und wähle **Verschmelzen**, um auf
   demselben Feld eine Einheit der nächsten Seltenheit zu bekommen. Die Stufen sind Common,
   Uncommon, Rare, Epic und Legendary.
4. Ziehe bewegliche Figuren auf ein hervorgehobenes Feld oder nutze **Verschieben**.
   Zwei bewegliche Trupps können die Plätze tauschen. Gebäude bleiben auf dem
   gewählten Bauplatz. Unter **Helden** siehst du, wer beschwörbar ist und
   welche Einheiten noch fehlen. Eine Beschwörung kostet Gold und verbraucht
   die Einheiten des Rezepts. Im Kampf setzt du die Fähigkeiten deiner Helden ein.
5. Wellen wechseln nach Zeit. Gegner bleiben auf dem Rundkurs, bis sie besiegt
   sind. Der gemeinsame Gegnerzähler und die Bossfristen entscheiden über den
   Ausgang. Gold, Essenz, Orakel und Schmiede helfen dir beim Ausbau.
6. Nach jeder überstandenen Welle bekommst du Gold und Wellenbeute. Essenz fällt
   in bestimmten Wellen an. In der Sammlung steigern Trainingsmarken Truppen,
   Baupläne Gebäude und Heldensplitter Helden bis Meisterschaft 3. Siegel lassen
   sich für alle drei Arten einsetzen.

## Feldzug und Beute

| Schwierigkeit | Voraussetzung für jedes beteiligte Profil |
| --- | --- |
| Normal | Ab dem ersten Spiel verfügbar |
| Schwer | 2 Feldzugssiege auf Normal und 3 Meisterschaftsränge insgesamt |
| Hölle | 2 Feldzugssiege auf Schwer und 7 Meisterschaftsränge insgesamt |
| Göttlich | 2 Feldzugssiege auf Hölle und 12 Meisterschaftsränge insgesamt |
| Primal | 2 Feldzugssiege auf Göttlich und 18 Meisterschaftsränge insgesamt |

Auch verlorene Partien geben Erfahrung für die erreichte Welle. Im Feldzug auf
Normal sind es 20 EP je erreichter Welle. Schwierigkeit und Herausforderung
erhöhen die Ausbeute. Gutgeschriebene Wellenbeute bleibt nach einer Niederlage.

Ab Schwer bringen überstandene Meilensteinwellen Runenstaub. Mit ihm schmiedest
du in der Sammlung Feldzeichen für Startgold, Startessenz oder zusätzlichen
Schaden gegen Bosse. Ab Hölle lassen sich Feldzeichen mit Urkernen erwecken.
Das ausgerüstete Feldzeichen wirkt ab dem nächsten Spielraum.

Das Aussehen und die Zusammensetzung der Formationen entwickeln sich in
Fünf-Wellen-Abschnitten. Jede Karte hat auf jeder Schwierigkeitsstufe einen eigenen
Endboss. Höhere Stufen erhöhen den Druck durch schnellere Gegner, höhere
Lebenspunkte und kürzere Bossfristen.

Die Partie nutzt das Handy im Hochformat. Im Browser öffnet das Symbol neben dem
Verbindungsstatus den Vollbildmodus. Auf dem iPhone wähle in Safari **Teilen ›
Zum Home-Bildschirm** und starte Pantheon über den Home-Bildschirm.

Tastaturkürzel sind R zum Rekrutieren, M zum Verschieben, U zum Aufwerten, F für die
Heldenfähigkeit und Leertaste für den Wellenstart. Escape bricht eine Zielauswahl ab.

## Entwicklung

Node.js 22 oder neuer, Rust stable und ein Browser mit WebGL2 werden benötigt.
Der Build installiert bei Bedarf das Rust-WebAssembly-Target und die passende
`wasm-bindgen`-CLI. Die Blender-Quelldateien, GLB-Exporte, Landschaften und Tonspuren
liegen im Repository.

```sh
npm ci
npm run build
npm run dev
cargo test -p pantheon-simulation
npm run test:e2e
```

`PANTHEON_URL` wählt die URL der Browser-Tests. `npm test` prüft nach dem Build
Modellclips, vollständige deterministische Partien und Fortschritt. Eine bereitgestellte
Fassung lässt sich mit mehreren isolierten Testkonten prüfen.

```sh
node scripts/smoke-live.mjs https://pantheon-defense.vercel.app
```

Lokal speichert der Server
Konten und Partien in `.cache/pantheon.sqlite`. Auf Vercel verwendet er
`DATABASE_URL` für PostgreSQL oder einen privaten, mit dem Projekt
verbundenen Vercel-Blob-Speicher. Alle Zugriffe auf Spielstände laufen serverseitig.
Der Server bleibt maßgeblich. Der Browser rechnet dieselbe Rust-Simulation zwischen
den Serverständen mit 20 Takten pro Sekunde voraus und wendet eigene Befehle sofort an.
Er schickt sie gebündelt mit dem Takt, an dem sie gelten, und der Server bestätigt sie.
Derselbe Zustand lässt sich nach einer unterbrochenen Verbindung wieder laden.

## Grafik und Blender-Quellen

Die Renderings des vollständigen Kaders, der Regionalgegner und der Schlachtfelder
liegen in der [Blender-Abnahme](art/reviews/feldzug/README.md). Die editierbaren Blender-Szenen liegen in
[`art/blend`](art/blend). Jede Arena wird mit berechneten Licht- und
Kontaktschatten in ein Mesh exportiert. Truppen, Helden, Gegner und Gebäude
verwenden Armaturen. Studiolichter und Kameras gehören zu den Blender-Szenen
und werden für die Porträts verwendet.

Die Handyansicht lädt die Arenen in voller Auflösung und vereinfachte Figuren aus
denselben Blender-Exporten. Gleiche Figuren teilen sich Mesh, Bemalung und
vorberechnete Gelenkposen. Truppen tragen ihre Katalogfarbe als Stofffarbe und
haben kompakte Proportionen, damit sie auf dem Handy auf einen Blick lesbar sind.
`npm run art:mobile` aktualisiert die vereinfachten GLB-Dateien und die
Bevy-Pakete mit diesen Posen. `npm run art:poses` baut nur die Bevy-Pakete.

Mit Blender 4.3 und FFmpeg lassen sich die Assets erneut erzeugen.

```sh
npm run art
python3 art/sound.py
```

## Referenzen

- [Nililane mit Spielansichten der drei Regionen](https://github.com/bthginfo/Nililane)
- [Bevy WebGL2 und glTF](https://bevy.org/examples/)
- [Blender glTF und Animationsexport](https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html)
- [Vercel WebSockets und Wiederverbindung](https://vercel.com/docs/functions/websockets)
- [Browser-Audio für Spiele](https://developer.mozilla.org/en-US/docs/Games/Techniques/Audio_for_Web_Games)
- [Playwright Browser-Kontexte](https://playwright.dev/docs/browser-contexts)
