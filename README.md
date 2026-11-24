# Pantheon Defense

Ein 3D-Tower-Defense in Rust und Bevy für Solo und privaten Zweier-Koop. Ihr haltet ein
gemeinsames Tor, zieht Truppen aus der aktiven Fraktion, verschmelzt jeweils drei gleiche
Truppen eines Rangs und baut Verteidigungen auf festen Bauplätzen. Im Laufe der Partien
schaltet das Konto neue Karten, Herausforderungen, Gebäude und Helden frei. Siege und erreichte Meilensteine bringen Siegel, die deine Figuren dauerhaft trainieren.

## Spielen

1. Erstelle ein Konto mit einem eindeutigen Rufnamen.
2. Wähle in der Bastion eine Karte und Herausforderung. Für Koop wählst du **Zu zweit**
   und gibst den Rufnamen des registrierten Mitspielers ein.
3. Kopiere den Link im Spielraum. Das eingeladene Konto öffnet den Link und tritt bei.
4. Der Gastgeber startet. Ziehe Truppen oder wähle ein Gebäude und anschließend dessen
   Bauplatz. Klicke eine aufgestellte Figur an, um sie auszubauen, zu verschmelzen oder
   zu versetzen. Ein Held kann in der Welle seine Spezialfähigkeit einsetzen.
5. Nach der Partie siehst du Erfahrungspunkte und Freischaltungen in **Chronik** und **Sammlung**. In der Sammlung kannst du mit Siegeln die Meisterschaft einer freigeschalteten Figur bis Stufe 3 erhöhen.

Tastaturkürzel auf dem Spielfeld sind R zum Ziehen, M zum Umstellen, U zum Ausbauen,
F für die Heldenfähigkeit und Leertaste für den Wellenstart. Escape bricht eine Zielauswahl ab.

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
Der Browser sendet Eingaben und rendert die vom Rust-Kern berechneten
Spielstände. Derselbe Zustand lässt sich nach einer unterbrochenen Verbindung wieder laden.

Mit Blender 4.3 und FFmpeg lassen sich die Assets erneut erzeugen.

```sh
npm run art
blender -b -t 4 --python art/mural.py
python3 art/sound.py
```

## Referenzen

- [Bevy WebGL2 und glTF](https://bevy.org/examples/)
- [Blender glTF und Animationsexport](https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html)
- [Vercel WebSockets und Wiederverbindung](https://vercel.com/docs/functions/websockets)
- [Browser-Audio für Spiele](https://developer.mozilla.org/en-US/docs/Games/Techniques/Audio_for_Web_Games)
- [Playwright Browser-Kontexte](https://playwright.dev/docs/browser-contexts)
