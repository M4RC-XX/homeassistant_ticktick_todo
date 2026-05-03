<p align="center">
  <img src="images/logo.jpg" width="100" height="100" alt="TickTick Logo">
</p>

# TickTick To-Do Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [!TIP]
> **Deutschsprachige Anleitung:** Eine deutsche Version dieser Dokumentation findest du [weiter unten](#-deutsche-anleitung).

An unofficial but powerful Home Assistant integration for [TickTick](https://ticktick.com/). This integration uses the native `todo` platform to bring your tasks directly into your smart home dashboard.

## ✨ Features

* **Auto-Discovery:** Automatically finds and adds all your TickTick projects (including Inbox) as separate To-Do entities.
* **Full Task Management:** Create, complete, uncomplete, rename, and permanently delete tasks.
* **Due Dates:** Full support for due dates and specific due times.
* **Completed Tasks:** View finished tasks directly within the Home Assistant UI.
* **Device Grouping:** All lists are neatly grouped under a "TickTick Account" device.

---

## 🛠️ Prerequisites

To use this integration, you need your own TickTick developer credentials. It's free and takes about 2 minutes:

1. Log in to the [TickTick Developer Center](https://developer.ticktick.com/).
2. Click on **Manage Apps** and create a new app (Web App).
3. Set the **OAuth redirect URL** to exactly:
   `https://my.home-assistant.io/redirect/oauth`
4. Save the app to get your **Client ID** and **Client Secret**.

---

## 📦 Installation via HACS

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

## 🇩🇪 Deutsche Anleitung

### Voraussetzungen
Erstelle eine Web-App im [TickTick Developer Center](https://developer.ticktick.com/) mit der Redirect-URL `https://my.home-assistant.io/redirect/oauth`.

### Installation
Füge dieses Repository als "Benutzerdefiniertes Repository" in HACS hinzu, lade es herunter und starte Home Assistant neu.

### Einrichtung
Hinterlege deine Client-ID und dein Secret unter *Einstellungen -> Geräte & Dienste -> Drei-Punkte-Menü -> Anmeldedaten für Anwendungen*. Füge danach die Integration "TickTick To-Do" ganz normal hinzu.

---

## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

*Disclaimer: This project is not affiliated with or endorsed by TickTick.*