# Drittanbieter-Hinweise – LiMusic 0.3.23

LiMusic 0.3.23 enthält **keinen kopierten Quellcode** aus uBlock Origin oder AdGuard Scriptlets.

Die neue LiMusic-Scriptlet-Engine ist eine eigenständige Implementierung eines kleinen, für YouTube benötigten Teilumfangs. Die Architektur und die deklarativen Regeltypen orientieren sich an öffentlich dokumentierten Konzepten wie Response-Replacement, JSON-Pruning und Scriptlet-Regeln.

Referenzprojekte:

- AdGuard Scriptlets – GPL-3.0 – https://github.com/AdguardTeam/Scriptlets
- AdGuard tsurlfilter – GPL-3.0 – https://github.com/AdguardTeam/tsurlfilter
- uBlock Origin / Resources Library – GPL-3.0 – https://github.com/gorhill/uBlock
- uBlock Origin uAssets – GPL-3.0 – https://github.com/uBlockOrigin/uAssets

Die in `data/adblock-scriptlet-rules.json` enthaltenen LiMusic-Regeln sind für LiMusic neu formulierte, deklarative Regeln und keine eingebettete Kopie einer Drittanbieter-Engine.
