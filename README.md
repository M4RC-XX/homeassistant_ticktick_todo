# TickTick To-Do Integration für Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Eine inoffizielle, aber voll funktionsfähige Home Assistant Integration für [TickTick](https://ticktick.com/). Diese Integration nutzt die offizielle `todo`-Plattform von Home Assistant, um deine Aufgabenlisten nahtlos in dein Smart Home zu integrieren.

## ✨ Funktionen

* **Alle Listen:** Lädt automatisch alle deine TickTick-Projekte (inklusive Posteingang) als separate To-Do-Entitäten.
* **Aufgaben verwalten:** Erstellen, Abhaken, Wiederherstellen und endgültiges Löschen von Aufgaben direkt aus Home Assistant.
* **Fälligkeitsdaten:** Volle Unterstützung für Fälligkeitsdaten (mit und ohne Uhrzeit).
* **Abgeschlossene Aufgaben:** Abgehakte Aufgaben können in der Home Assistant Ansicht eingeblendet werden.
* **Geräte-Gruppierung:** Alle Listen werden übersichtlich unter einem virtuellen "TickTick Account"-Gerät gruppiert.

---

## 🛠️ Voraussetzungen (WICHTIG!)

Da diese Integration über die offizielle TickTick-API läuft, benötigst du eigene Entwickler-Zugangsdaten. Keine Sorge, das ist kostenlos und dauert nur zwei Minuten:

1. Gehe zum [TickTick Developer Center](https://developer.ticktick.com/) und logge dich mit deinem normalen Account ein.
2. Klicke auf **Manage Apps** und erstelle eine neue App (Typ: Web App).
3. Gib der App einen Namen (z.B. "Mein Home Assistant").
4. Trage unter **OAuth redirect URL** zwingend exakt folgende Adresse ein:
   `https://my.home-assistant.io/redirect/oauth`
5. Speichere die Einstellungen. Du siehst nun eine **Client ID** und ein **Client Secret**. Halte diese für die Einrichtung bereit.

---

## 📦 Installation (über HACS)

1. Öffne Home Assistant und navigiere zu **HACS**.
2. Klicke oben rechts auf das Drei-Punkte-Menü und wähle **Benutzerdefinierte Repositories**.
3. Füge die URL dieses GitHub-Repositories ein und wähle als Kategorie **Integration**.
4. Suche nun in HACS nach "TickTick To-Do" und klicke auf **Herunterladen**.
5. Starte Home Assistant neu.

---

## ⚙️ Einrichtung in Home Assistant

Damit deine Zugangsdaten sicher gespeichert werden, nutzt diese Integration die Standard-Sicherheitsfunktionen von Home Assistant:

1. Gehe in Home Assistant zu **Einstellungen -> Geräte & Dienste**.
2. Klicke oben rechts auf das Drei-Punkte-Menü und wähle **Anmeldedaten für Anwendungen** (Application Credentials).
3. Klicke unten rechts auf **Anmeldedaten hinzufügen**.
4. Wähle als Integration **TickTick To-Do**.
5. Vergib einen beliebigen Namen (z.B. "TickTick API").
6. Kopiere deine **Client ID** und dein **Client Secret** aus dem TickTick Developer Dashboard in die entsprechenden Felder und klicke auf Hinzufügen.
7. Gehe zurück zu *Geräte & Dienste* und klicke auf **Integration hinzufügen**.
8. Suche nach "TickTick To-Do" und folge den Anweisungen. Du wirst zu TickTick weitergeleitet, um den Zugriff zu erlauben.

Fertig! Deine Listen tauchen nun unter dem Menüpunkt "Zu erledigen" auf.

---

## 🐛 Fehlerbehebung

* **Fehler: "invalid_grant" beim Login:** Stelle sicher, dass du bei TickTick exakt `https://my.home-assistant.io/redirect/oauth` als Redirect-URL eingetragen hast. Manchmal dauert es ein paar Minuten, bis TickTick Änderungen an der URL speichert.
* **Listen ausblenden:** Wenn du nicht alle TickTick-Projekte in Home Assistant sehen möchtest, gehe zu *Einstellungen -> Geräte & Dienste -> TickTick To-Do*, klicke auf "Entitäten" und deaktiviere die Listen, die du nicht benötigst.

---
*Hinweis: Dies ist ein Community-Projekt und steht in keiner offiziellen Verbindung zu TickTick.*