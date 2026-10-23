![Version](https://img.shields.io/github/v/release/M4RC-XX/homeassistant_ticktick_todo?style=for-the-badge)
![Downloads](https://img.shields.io/github/downloads/M4RC-XX/homeassistant_ticktick_todo/total?style=for-the-badge)
![Contributors](https://img.shields.io/github/contributors/M4RC-XX/homeassistant_ticktick_todo/graphs/contributors?style=for-the-badge)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
<br>
<p align="center">
  <img src="images/logo.jpg" width="100" height="100" alt="TickTick Logo">
</p>

# TickTick To-Do & Habits Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [!TIP]
> **Deutschsprachige Anleitung:** Eine deutsche Version dieser Dokumentation findest du [weiter unten](#-deutsche-anleitung).

An unofficial but powerful Home Assistant integration for [TickTick](https://ticktick.com/). This integration uses Home Assistant's native `todo`, `switch`, `number`, and `button` platforms to bring your **To-Do lists** and **Habits** directly into your smart home dashboard and automations.

## ✨ Features

* **Live Auto-Discovery:** Automatically finds and adds all your TickTick projects (including a localized Inbox) and active Habits — even when new lists or habits are created at runtime without restarting Home Assistant.
* **Full Task Management:** Create, complete, uncomplete, rename, and permanently delete tasks while preserving existing TickTick metadata (such as task priority and sort order).
* **Task Descriptions / Notes:** View, create, edit, and clear task descriptions directly from Home Assistant.
* **Timezone-Aware Due Dates:** Full support for all-day due dates, specific due times, and clearing existing due dates.
* **Full Habit Tracking & Check-Ins:**
  * **Switch (`switch`):** Toggle daily habit completion on or off and view streak/check-in attributes (`current_value`, `goal`, `unit`, `total_check_ins`, `completed_cycles`).
  * **Progress / Time Tracking (`number`):** Directly view or set today's progress or time (e.g., minutes read, glasses of water) for quantifiable habits.
  * **Quick Step Check-In (`button`):** One-click button to check in a habit or increment its daily progress by one configured step.
  * **Custom Action (`ticktick_todo.habit_checkin`):** Easily add time/progress (e.g., `add_value: 15`) or check in habits from automations, scripts, or NFC tags.
* **Fast Parallel Syncing:** Fetches all project lists and habits concurrently in the background with built-in rate-limit protection.
* **Automatic Re-Authentication:** Prompts you directly in the Home Assistant UI if your OAuth session ever expires.
* **Device Grouping:** All lists and habits are neatly grouped under a single "TickTick" device.

---

## 🛠️ Prerequisites

* **Home Assistant:** Version `2024.8.0` or newer.
* **TickTick Developer Credentials:** Because Home Assistant runs locally on your own server, OAuth2 requires your own free TickTick Developer App credentials (takes about 2 minutes):

1. Log in to the [TickTick Developer Center](https://developer.ticktick.com/manage).
2. Click on **Manage Apps** and create a new app (Web App).
3. Set the **OAuth redirect URL** to exactly:
   `https://my.home-assistant.io/redirect/oauth`
4. Save the app to get your **Client ID** and **Client Secret**.

---

## 📦 Installation via [HACS](https://hacs.xyz/)

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=M4RC-XX&repository=homeassistant_ticktick_todo&category=integration" target="_blank"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

1. Open Home Assistant and navigate to **HACS**.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Paste the URL of this repository and select **Integration** as the category.
4. Search for "TickTick To-Do" in HACS and click **Download**.
5. **Restart** Home Assistant.

---

## ⚙️ Configuration

1. Go to **Settings -> Devices & Services**.
2. Click the three dots in the top right and select **Application Credentials**.
3. Click **Add Application Credentials**.
4. Select **TickTick To-Do** as the integration.
5. Enter a name (e.g., "TickTick API") and paste your **Client ID** and **Client Secret**.
6. Go back to *Devices & Services* and click **Add Integration**.
7. Search for **TickTick To-Do** and follow the OAuth flow to authorize your account.

---

## 🎯 Using Habits in Automations

In addition to the automatically created `switch`, `number`, and `button` entities for each habit, you can use the `ticktick_todo.habit_checkin` action to check in or manually add time/progress to a habit:

```yaml
# Example: Add 15 minutes towards your "Read" habit check-in today
action: ticktick_todo.habit_checkin
data:
  entity_id: switch.ticktick_habit_read
  add_value: 15
```

```yaml
# Example: Complete a habit by name for a specific date
action: ticktick_todo.habit_checkin
data:
  habit_id: "Workout"
```

---

## 🇩🇪 Deutsche Anleitung

### Funktionsumfang
* **Dynamische Listenerkennung:** Findet automatisch alle TickTick-Projekte (inkl. lokalisiertem *Posteingang*) sowie aktive **Habits (Gewohnheiten)** und erkennt neu angelegte Listen/Habits im laufenden Betrieb ohne Neustart.
* **Aufgabenverwaltung & Notizen:** Aufgaben erstellen, abhaken, umbenennen, löschen sowie **Beschreibungen/Notizen** und **Fälligkeitsdaten** (inkl. Uhrzeit & korrekter Zeitzone) bearbeiten.
* **Habit-Tracking & Check-Ins:**
  * **Schalter (`switch`):** Zeigt an, ob ein Habit heute bereits erfüllt wurde, und lässt sich direkt abhaken oder zurücksetzen (inkl. Attributen wie `total_check_ins`, `goal`, `current_value`).
  * **Fortschritt / Zeit (`number`):** Für Habits mit Mengen- oder Zeitzielen (z. B. *30 Min. lesen* oder *8 Gläser Wasser*) wird automatisch ein Zahlenfeld für den heutigen Stand angelegt.
  * **Schnell-Check-In (`button`):** Erhöht den heutigen Fortschritt per Klick um eine Schrittweite (`step`) bzw. hakt das Habit ab.
  * **Aktion (`ticktick_todo.habit_checkin`):** Ermöglicht es in Automationen, Zeit oder Fortschritt manuell zu addieren (z. B. `add_value: 15`).

### Voraussetzungen
* **Home Assistant:** Mindestens Version `2024.8.0`.
* **TickTick App:** Erstelle eine kostenlose Web-App im [TickTick Developer Center](https://developer.ticktick.com/manage) mit der Redirect-URL `https://my.home-assistant.io/redirect/oauth`.

### Installation
Füge dieses Repository als "Benutzerdefiniertes Repository" in HACS hinzu, lade es herunter und starte Home Assistant neu.

### Einrichtung
Hinterlege deine Client-ID und dein Secret unter *Einstellungen -> Geräte & Dienste -> Drei-Punkte-Menü -> Anmeldedaten für Anwendungen*. Füge danach die Integration "TickTick To-Do" ganz normal hinzu.

---

## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

*Disclaimer: This project is not affiliated with or endorsed by TickTick.*
