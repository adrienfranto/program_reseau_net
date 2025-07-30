#!/usr/bin/env python3
"""
Script de démarrage pour le serveur de streaming audio
Compatible Windows 11 avec Python 3.11
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Vérifier la version de Python"""
    version = sys.version_info
    if version.major != 3 or version.minor < 8:
        print("❌ Python 3.8+ requis. Version actuelle:", f"{version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_requirements():
    """Installer les dépendances"""
    print("📦 Installation des dépendances...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        return False

def create_directories():
    """Créer les dossiers nécessaires"""
    directories = ['templates', 'static', 'uploads']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Dossier créé: {directory}")

def create_template_files():
    """Créer les fichiers template s'ils n'existent pas"""
    
    # Template index.html
    index_template = """<!-- Le contenu du template client sera ici -->
<!-- Copiez le contenu de l'artifact "Template HTML - Interface Client" -->
<!DOCTYPE html>
<html>
<head><title>Audio Streaming Client</title></head>
<body><h1>Copiez le template client ici</h1></body>
</html>
"""
    
    # Template admin.html
    admin_template = """<!-- Le contenu du template admin sera ici -->
<!-- Copiez le contenu de l'artifact "Template HTML - Interface Admin" -->
<!DOCTYPE html>
<html>
<head><title>Audio Streaming Admin</title></head>
<body><h1>Copiez le template admin ici</h1></body>
</html>
"""
    
    templates_dir = 'templates'
    
    if not os.path.exists(os.path.join(templates_dir, 'index.html')):
        with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_template)
        print("📄 Template index.html créé")
    
    if not os.path.exists(os.path.join(templates_dir, 'admin.html')):
        with open(os.path.join(templates_dir, 'admin.html'), 'w', encoding='utf-8') as f:
            f.write(admin_template)
        print("📄 Template admin.html créé")

def check_audio_files():
    """Vérifier s'il y a des fichiers audio de test"""
    audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    uploads_dir = 'uploads'
    
    if os.path.exists(uploads_dir):
        audio_files = []
        for file in os.listdir(uploads_dir):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(file)
        
        if audio_files:
            print(f"🎵 {len(audio_files)} fichier(s) audio trouvé(s) dans uploads/")
        else:
            print("ℹ️  Aucun fichier audio dans uploads/. Vous pouvez en ajouter via l'interface admin.")

def print_info():
    """Afficher les informations du serveur"""
    print("\n" + "="*60)
    print("🎵 SERVEUR DE STREAMING AUDIO")
    print("="*60)
    print(f"🖥️  Système: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("\n📡 URLs d'accès:")
    print("   Client:  http://localhost:5000")
    print("   Admin:   http://localhost:5000/admin") 
    print("   Stream:  http://localhost:5000/stream")
    print("\n🎮 Contrôles:")
    print("   - Utilisez l'interface admin pour ajouter des fichiers")
    print("   - Les clients peuvent écouter via l'interface client")
    print("   - Le streaming se fait en temps réel")
    print("\n🔧 Pour arrêter: Ctrl+C")
    print("="*60)

def main():
    """Fonction principale"""
    print("🚀 Démarrage du serveur de streaming audio...\n")
    
    # Vérifications
    if not check_python_version():
        return False
    
    create_directories()
    
    # Installation des dépendances
    if os.path.exists('requirements.txt'):
        install_requirements()
    
    create_template_files()
    check_audio_files()
    
    print_info()
    
    # Démarrer le serveur
    try:
        print("\n🎵 Démarrage du serveur Flask...")
        
        # Importer et démarrer l'application
        if os.path.exists('app.py'):
            import app
        else:
            print("❌ Fichier app.py non trouvé!")
            print("ℹ️  Copiez le code du serveur Flask dans un fichier 'app.py'")
            return False
            
    except KeyboardInterrupt:
        print("\n\n🛑 Serveur arrêté par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors du démarrage: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        input("\nAppuyez sur Entrée pour fermer...")
        sys.exit(1)