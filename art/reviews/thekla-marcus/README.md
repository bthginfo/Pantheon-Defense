# Thekla und Marcus zur Abnahme

Thekla und Marcus sind für diese Runde mit größeren Polygonflächen modelliert. Helm, Rüstung und Stoff setzen dadurch auch in der Ganzkörperansicht klare Kanten. Die gemalten Farbverläufe und Gebrauchsspuren sind in den exportierten Spielmodellen enthalten.

![Blender-Renderings der neuen Fassung mit Thekla links und Marcus rechts](paar.webp)

## Abgleich mit dem Zielbild

- **Thekla** greift den offenen Bronzehelm mit flachem jadengrünem Kamm, das gekreuzte Leder über Leinen und das Rundschild des Zielbilds auf. Die Sonnenstrahlen haben ungleich lange Spitzen und gefaltete Metallflächen. Bronzeplatten und Leinenfalten zeichnen ihre Silhouette nach.
- **Marcus** greift den roten Querkamm, die überlappenden Eisenplatten, den dunklen Lederrock und den hohen roten Schild des Zielbilds auf. Die Adlerflügel bestehen aus einzeln modellierten Federn. Die Schildrückseite zeigt gebogene Holzleisten mit einem Griff auf einem Querholz.

Der direkte Vergleich mit der letzten bemalten Fassung nutzt dieselbe Pose, Kamera und Beleuchtung. [Vorher und neue Polygonflächen](poly-vergleich.webp)

| Ansicht | Was sich daran prüfen lässt |
| --- | --- |
| [Gesichter und Helme](nahaufnahmen.webp) | Helmschalen, Wangenschutz, Haaransätze und Stoffabschlüsse |
| [Schilde und Rüstung](oberflaechen.webp) | Sonnenstrahlen, Adlerfedern, Schulterplatten und Riemen |
| [Rückseite](bemalte-umhaenge.webp) | Umhänge, Schildgurte und Schildgriff |
| [Angriffsposen](aktion.webp) | Theklas Speerstoß und Marcus’ Signal mit gestütztem Schild |

In den Blender-Szenen sind die Bauteile und die Animationen editierbar. [Thekla](../../blend/thekla.blend) · [Marcus](../../blend/marcus.blend)

Die Grundanatomie stammt aus MakeHuman unter CC0. Posen, Ausrüstung, Kostümschnitte und Materialoberflächen sind für diese Figuren ausgearbeitet. [CC0-Lizenztext](../../reference-data/MakeHuman-CC0.md)

Neue Aufnahmen aus den Blender-Dateien lassen sich mit folgendem Befehl erzeugen.

```sh
blender -b --python-exit-code 1 --python art/render_commander_review.py -- --output /tmp/figuren-abnahme
```

## Frühere Abnahmen

[Erste Spielprobe am Desktop](spielansicht.webp) · [Erste Seiten- und Rückenansichten](seite-und-ruecken.webp) · [Übergang zur bemalten Fassung](vorher-nachher.webp)

In der emulierten Handy-Ansicht dieser früheren Spielprobe blieb der Boden der Ägäis-Karte leer.
