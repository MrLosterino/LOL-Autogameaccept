import os
import requests
import base64
import time
import threading
import urllib3
import tkinter as tk
from tkinter import messagebox

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # HTTPS-Warnungen unterdrücken

script_running = False


def find_lockfile():
    """Sucht die Lockfile automatisch in Standardpfaden."""
    standard_paths = [
        "C:/Riot Games/League of Legends/Lockfile",
        "D:/Games/Riot Games/League of Legends/Lockfile",
        "F:/Riot Games/League of Legends/Lockfile",
        os.path.expanduser("~/Riot Games/League of Legends/Lockfile"),
    ]

    for path in standard_paths:
        if os.path.exists(path):
            return path

    messagebox.showwarning("Lockfile nicht gefunden",
                           "Die Lockfile wurde nicht im Standardpfad gefunden. Bitte den Installationsordner angeben.")
    return None


def get_lcu_credentials():
    """Liest die Lockfile-Daten aus, um die LCU API-URL und Auth-Informationen zu erhalten."""
    lockfile_path = find_lockfile()
    if not lockfile_path:
        return None, None

    with open(lockfile_path, "r") as lockfile:
        data = lockfile.read().split(":")
        process_name, pid, port, password, protocol = data

    base_url = f"https://127.0.0.1:{port}"
    auth = base64.b64encode(f"riot:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    return base_url, headers


def get_gameflow_status(base_url, headers):
    """Überprüft den aktuellen Spielstatus (z.B. Matchmaking, InProgress, etc.)."""
    url = f"{base_url}/lol-gameflow/v1/gameflow-phase"
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.text.strip('"')  # Entfernt Anführungszeichen
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def accept_match(base_url, headers):
    """Versucht, ein gefundenes Spiel automatisch anzunehmen."""
    url = f"{base_url}/lol-matchmaking/v1/ready-check/accept"  # Geänderter Endpunkt
    try:
        print(f"[DEBUG] Sende POST-Anfrage an: {url}")
        response = requests.post(url, headers=headers, verify=False)
        if response.status_code == 204:  # Erfolgreich angenommen
            print("[INFO] Spiel erfolgreich angenommen.")
            return True
        else:
            print(f"[WARN] Fehler beim Annehmen des Spiels: {response.status_code}, {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Ausnahme beim Annehmen des Spiels: {e}")
        return False


def monitor_matchmaking(status_label):
    """
    Überwacht den Spielstatus und versucht automatisch, Spiele anzunehmen.
    """
    global script_running
    credentials = get_lcu_credentials()
    if not credentials or not credentials[0]:
        status_label.config(text="Status: Nicht verbunden", bg="gray")
        return

    base_url, headers = credentials
    status_label.config(text="Status: Verbunden, Suche läuft...", bg="blue")

    while script_running:
        gameflow_status = get_gameflow_status(base_url, headers)
        print(f"[DEBUG] Aktueller Spielstatus: {gameflow_status}")

        if gameflow_status == "ReadyCheck":
            status_label.config(text="Status: ReadyCheck", bg="orange")
            print("[INFO] ReadyCheck erkannt. Versuche, das Spiel anzunehmen...")
            if accept_match(base_url, headers):
                status_label.config(text="Status: Spiel angenommen!", bg="green")
            else:
                print("[WARN] Das Spiel konnte nicht angenommen werden.")

        elif gameflow_status == "ChampSelect":
            status_label.config(text="Status: Championauswahl", bg="purple")
            print("[INFO] Spieler ist in der Championauswahl.")

        elif gameflow_status == "InProgress":
            status_label.config(text="Status: Im Spiel", bg="green")
            print("[INFO] Spieler ist im Spiel. Pausiere Monitoring...")
            while gameflow_status == "InProgress" and script_running:
                time.sleep(2)
                gameflow_status = get_gameflow_status(base_url, headers)

        elif gameflow_status in ["EndOfGame", "None"]:
            status_label.config(text="Status: Warte auf Matchmaking", bg="yellow")
            print("[INFO] Spiel ist beendet. Warte auf nächste Runde...")

        else:
            status_label.config(text=f"Status: {gameflow_status} (unbekannt)", bg="gray")
            print(f"[WARN] Unbekannter Status erkannt: {gameflow_status}")

        time.sleep(2)


def start_monitoring(status_label, start_button, stop_button):
    """Startet das Matchmaking-Monitoring."""
    global script_running
    if script_running:
        messagebox.showinfo("Info", "Das Skript läuft bereits.")
        return

    script_running = True
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    thread = threading.Thread(target=monitor_matchmaking, args=(status_label,))
    thread.start()


def stop_monitoring(start_button, stop_button):
    """Stoppt das Matchmaking-Monitoring."""
    global script_running
    script_running = False
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


def create_gui():
    """Erstellt die grafische Benutzeroberfläche für den Spielstatus."""
    root = tk.Tk()
    root.title("LoL Spielstatus")
    root.geometry("400x300")

    # Status-Anzeige
    status_label = tk.Label(root, text="Status: Nicht verbunden", font=("Arial", 14), bg="gray", fg="white", width=40,
                            height=10)
    status_label.pack(pady=10)

    # Start/Stop-Buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    start_button = tk.Button(button_frame, text="Starten", font=("Arial", 12), bg="green", fg="white", width=10,
                             command=lambda: start_monitoring(status_label, start_button, stop_button))
    start_button.grid(row=0, column=0, padx=5)

    stop_button = tk.Button(button_frame, text="Stoppen", font=("Arial", 12), bg="red", fg="white", width=10,
                            command=lambda: stop_monitoring(start_button, stop_button), state=tk.DISABLED)
    stop_button.grid(row=0, column=1, padx=5)

    root.mainloop()


if __name__ == "__main__":
    create_gui()