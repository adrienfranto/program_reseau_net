#!/usr/bin/env python3
"""
Client Python simple pour le serveur de streaming audio
Permet de contrôler la lecture et d'écouter le stream
"""

import requests
import time
import os

class AudioStreamClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        self.session = requests.Session()
        self.is_playing = False
        self.current_track = None
        self.playlist = []
        
    def check_connection(self):
        """Vérifier la connexion au serveur"""
        try:
            response = self.session.get(f"{self.server_url}/api/playlist", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_playlist(self):
        """Obtenir la playlist actuelle"""
        try:
            response = self.session.get(f"{self.server_url}/api/playlist")
            if response.status_code == 200:
                data = response.json()
                self.playlist = data.get('playlist', [])
                self.is_playing = data.get('is_playing', False)
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération de la playlist: {e}")
            return False
    
    def play(self):
        """Démarrer la lecture"""
        try:
            response = self.session.get(f"{self.server_url}/api/play")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur play: {e}")
            return False
    
    def pause(self):
        """Mettre en pause"""
        try:
            response = self.session.get(f"{self.server_url}/api/pause")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur pause: {e}")
            return False
    
    def next_track(self):
        """Piste suivante"""
        try:
            response = self.session.get(f"{self.server_url}/api/next")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur next: {e}")
            return False
    
    def previous_track(self):
        """Piste précédente"""
        try:
            response = self.session.get(f"{self.server_url}/api/previous")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur previous: {e}")
            return False
    
    def select_track(self, index):
        """Sélectionner une piste"""
        try:
            response = self.session.get(f"{self.server_url}/api/select/{index}")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur select: {e}")
            return False
    
    def add_local_file(self, filepath):
        """Ajouter un fichier local"""
        try:
            data = {"filepath": filepath}
            response = self.session.post(f"{self.server_url}/api/add_local", json=data)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"Erreur add_local: {e}")
            return False
    
    def download_stream(self, output_file="stream_output.mp3", duration=30):
        """Télécharger le stream audio pendant une durée donnée"""
        try:
            print(f"📡 Enregistrement du stream pendant {duration}s dans {output_file}...")
            
            response = self.session.get(f"{self.server_url}/stream", stream=True, timeout=duration+5)
            
            start_time = time.time()
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
                        if time.time() - start_time > duration:
                            break
            
            print(f"✅ Stream enregistré dans {output_file}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur stream: {e}")
            return False

def print_menu():
    """Afficher le menu"""
    print("\n" + "="*50)
    print("🎵 CLIENT AUDIO STREAMING")
    print("="*50)
    print("1. ▶️  Play")
    print("2. ⏸️  Pause") 
    print("3. ⏭️  Piste suivante")
    print("4. ⏮️  Piste précédente")
    print("5. 📝 Afficher playlist")
    print("6. 🎯 Sélectionner piste")
    print("7. ➕ Ajouter fichier local")
    print("8. 📡 Enregistrer stream (30s)")
    print("9. 🔄 Actualiser")
    print("0. ❌ Quitter")
    print("="*50)

def display_playlist(client):
    """Afficher la playlist"""
    if not client.get_playlist():
        print("❌ Impossible de récupérer la playlist")
        return
    
    if not client.playlist:
        print("📝 Playlist vide")
        return
    
    print(f"\n📝 Playlist ({len(client.playlist)} pistes):")
    print("="*80)
    for i, track in enumerate(client.playlist):
        status = "🎵" if i == 0 else "  "  # Approximation, tu peux améliorer
        title = track.get('title', track.get('filename', 'Sans titre'))
        artist = track.get('artist', 'Inconnu')
        print(f"{status} {i+1:2d}. {title} - {artist}")
    print("="*80)

def main():
    """Fonction principale"""
    print("🚀 Démarrage du client audio streaming...\n")
    
    # Créer le client
    client = AudioStreamClient()
    
    # Vérifier la connexion
    print("🔗 Vérification de la connexion au serveur...")
    if not client.check_connection():
        print("❌ Impossible de se connecter au serveur")
        print("ℹ️  Assurez-vous que le serveur Flask est démarré sur http://localhost:5000")
        input("Appuyez sur Entrée pour quitter...")
        return
    
    print("✅ Connecté au serveur")
    
    # Charger la playlist initiale
    client.get_playlist()
    
    # Boucle principale
    while True:
        try:
            print_menu()
            
            # État actuel
            status = "▶️ EN LECTURE" if client.is_playing else "⏸️ EN PAUSE"
            print(f"État: {status}")
            
            choice = input("\nChoisissez une option: ").strip()
            
            if choice == "1":
                if client.play():
                    print("✅ Lecture démarrée")
                else:
                    print("❌ Impossible de démarrer la lecture")
            
            elif choice == "2":
                if client.pause():
                    print("⏸️ Lecture mise en pause")
                else:
                    print("❌ Impossible de mettre en pause")
            
            elif choice == "3":
                if client.next_track():
                    print("⏭️ Piste suivante")
                else:
                    print("❌ Impossible de passer à la piste suivante")
            
            elif choice == "4":
                if client.previous_track():
                    print("⏮️ Piste précédente")
                else:
                    print("❌ Impossible de revenir à la piste précédente")
            
            elif choice == "5":
                display_playlist(client)
            
            elif choice == "6":
                index_str = input("Entrez le numéro de la piste à sélectionner: ").strip()
                if index_str.isdigit():
                    index = int(index_str) - 1
                    if client.select_track(index):
                        print(f"🎯 Piste {index + 1} sélectionnée")
                    else:
                        print("❌ Sélection invalide")
                else:
                    print("❌ Veuillez entrer un numéro valide")
            
            elif choice == "7":
                filepath = input("Entrez le chemin complet du fichier audio local à ajouter: ").strip()
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    if client.add_local_file(filepath):
                        print("➕ Fichier ajouté à la playlist")
                    else:
                        print("❌ Impossible d'ajouter le fichier")
                else:
                    print("❌ Fichier non trouvé")
            
            elif choice == "8":
                duration_str = input("Durée de l'enregistrement en secondes (par défaut 30): ").strip()
                duration = 30
                if duration_str.isdigit():
                    duration = int(duration_str)
                output_file = input("Nom du fichier de sortie (par défaut stream_output.mp3): ").strip()
                if output_file == "":
                    output_file = "stream_output.mp3"
                client.download_stream(output_file=output_file, duration=duration)
            
            elif choice == "9":
                if client.get_playlist():
                    print("🔄 Playlist actualisée")
                else:
                    print("❌ Impossible d'actualiser la playlist")
            
            elif choice == "0":
                print("❌ Fermeture du client...")
                break
            
            else:
                print("❌ Option invalide, veuillez réessayer.")
        
        except KeyboardInterrupt:
            print("\n❌ Fermeture du client par interruption clavier")
            break

if __name__ == "__main__":
    main()
