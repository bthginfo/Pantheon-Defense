# Pantheon Defense

Ein 3D-Tower-Defense in Rust und Bevy für Solo und privaten Zweier-Koop.
Verteidige einen gemeinsamen Rundkurs und meistere acht Herausforderungen mit
16 bis 48 Wellen. Drei Fraktionen aus Griechenland, Rom und Japan bringen
36 Truppen, 24 Helden und neun Gebäude aufs Brett.

## Spielen

1. Erstelle ein Konto mit einem eindeutigen Rufnamen. Wähle eine Karte und
   Herausforderung. Bei **Zu zweit** gibst du den Rufnamen des registrierten
   Mitspielers ein. Kopiere den Einladungslink im Spielraum und teile ihn mit
   der eingeladenen Person.
2. Der Gastgeber startet. **Truppe ziehen** legt einen Rekruten in die Reserve.
   Wähle selbst eines der markierten Felder. Auf einem Feld kannst du bis zu
   drei Exemplare derselben Truppe und Seltenheit sammeln.
3. Tippe einen Dreierstapel an und wähle **Verschmelzen**, um auf demselben Feld
   eine Truppe der nächsten Seltenheit zu bekommen. Die Stufen sind Common,
   Uncommon, Rare, Epic und Legendary.
4. Ziehe bewegliche Figuren auf ein anderes Feld oder nutze **Umstellen**.
   Gebäude bleiben auf dem gewählten Bauplatz. Helden rufst du aus drei
   Truppen nach ihrem Rezept. Im Kampf setzt du ihre Fähigkeiten ein.
5. Wellen wechseln nach Zeit. Gegner bleiben auf dem Rundkurs, bis sie besiegt
   sind. Der gemeinsame Gegnerzähler und die Bossfristen entscheiden über den
   Ausgang. Gold, Essenz, Orakel und Schmiede helfen dir beim Ausbau.
6. Erfahrung und Siegel öffnen neue Karten, Herausforderungen und Figuren.
   In der Sammlung trainierst du freigeschaltete Figuren bis Meisterschaft 3.

Die Partie nutzt das Handy im Hochformat. Im Browser öffnet das Symbol neben dem
Verbindungsstatus den Vollbildmodus. Auf dem iPhone wähle in Safari **Teilen ›
Zum Home-Bildschirm** und starte Pantheon über den Home-Bildschirm.

Tastaturkürzel sind R zum Ziehen, M zum Umstellen, U zum Ausbauen, F für die
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
