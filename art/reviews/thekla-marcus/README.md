# Thekla und Marcus zur Abnahme

Thekla und Marcus setzen die freigegebene Stilreferenz mit klaren Polygonflächen und handgemalten Oberflächen in Blender um. Die Farbtextur enthält unterschiedlich gerichtete Pinselstriche für Bronze, Eisen, Leinen, Leder und Schildlack. Bevy verwendet diese Textur aus den exportierten Spielmodellen.

![Blender-Renderings von Thekla links und Marcus rechts](paar.webp)

## Abgleich mit der Stilreferenz

- **Thekla** trägt einen Bronzehelm mit zurückgeschwungenem Jadekamm, gestufte Schulterplatten und diagonal überlappende Leinenbahnen. Der Umhang fällt mit einem Terrakottamäander zur Speerseite. Das gewölbte Schild trägt dunkelgrünen Lack und geschmiedete Sonnenstrahlen.
- **Marcus** überträgt die breiten Facetten und die gemalten Abriebspuren auf eine römische Silhouette mit roten Wollfalten, getriebenen Eisenplatten und einem Adlerrelief auf dem geschwungenen Scutum.

[Freigegebene Stilreferenz](../../references/thekla-handpainted-poly-referenz.png) · [Stilreferenz neben dem Blender-Modell](stilabgleich-thekla.webp)

Die Aufnahmen vor und nach der Umsetzung verwenden dieselbe Kamera und Beleuchtung. [Vorige und aktuelle Blender-Fassung](poly-vergleich.webp)

| Ansicht | Was sich daran prüfen lässt |
| --- | --- |
| [Gesichter und Helme](nahaufnahmen.webp) | Wangenschutz, Locken, Helmzier und Pinselspuren auf Metall |
| [Schilde und Rüstung](oberflaechen.webp) | Schildlack, Sonnenstrahlen, Adlerfedern und die Kanten der Platten |
| [Rückseite](bemalte-umhaenge.webp) | Gemusterte Umhänge, Schildgurte und Schildgriff |
| [Angriffsposen](aktion.webp) | Speerstoß, bewegliche Leinenbahnen und Marcus’ Signal |

In der lokalen Spielprobe erscheinen beide Figuren nach ihrem Heldenrezept auf dem Spielfeld. Die Aufnahmen zeigen Thekla in der Ägäis und Marcus in Rom. [Bevy-Spielprobe](spielprobe.webp)

In den Blender-Szenen sind die Bauteile und die Animationen editierbar. [Thekla](../../blend/thekla.blend) · [Marcus](../../blend/marcus.blend)

Die Grundanatomie stammt aus MakeHuman unter CC0. Posen, Ausrüstung, Kostümschnitte und Materialoberflächen sind für diese Figuren ausgearbeitet. [CC0-Lizenztext](../../reference-data/MakeHuman-CC0.md)

Neue Aufnahmen aus den Blender-Dateien lassen sich mit folgendem Befehl erzeugen.

```sh
blender -b --python-exit-code 1 --python art/render_commander_review.py -- --output /tmp/figuren-abnahme
```

## Frühere Abnahmen

[Erste Spielprobe am Desktop](spielansicht.webp) · [Erste Seiten- und Rückenansichten](seite-und-ruecken.webp) · [Übergang zur bemalten Fassung](vorher-nachher.webp)

In der emulierten Handy-Ansicht dieser früheren Spielprobe blieb der Boden der Ägäis-Karte leer.
