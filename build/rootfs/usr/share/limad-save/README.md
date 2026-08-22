# LiSave 1.0.2

LiSave erstellt verschlüsselte Wiederherstellungsbackups als einzelne portable `*.lisavebackup.zip`-Datei. Preview5 ergänzt eine vollständige Live-Fortschrittsanzeige für Sicherung, Öffnen vorhandener Archive, ZIP-Erstellung und ZIP-Prüfung.

Während des Restic-Backups werden die offiziellen JSON-Statusdaten für Prozent, verarbeitete Bytes, Dateien und Restzeit ausgewertet. Beim Schreiben und Prüfen des ZIP-Containers misst LiSave den tatsächlichen Datenstrom und zeigt Quelle, Ziel, aktuellen Eintrag, Geschwindigkeit, Restzeit und voraussichtliche Endzeit. Phasen ohne verlässliche Prozentdaten bleiben bewusst indeterminiert.
