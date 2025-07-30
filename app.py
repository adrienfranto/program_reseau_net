from flask import Flask, Response, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import threading
import time
import wave
import io
import json
from mutagen import File
from mutagen.id3 import ID3NoHeaderError
import base64
import mimetypes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
socketio = SocketIO(app, cors_allowed_origins="*")

class AudioStreamer:
    def __init__(self):
        self.current_track = None
        self.is_playing = False
        self.clients = set()
        self.playlist = []
        self.current_index = 0
        self.audio_data = None
        self.position = 0
        self.chunk_size = 4096
        
    def add_track(self, filepath):
        """Ajouter une piste à la playlist"""
        if os.path.exists(filepath):
            # Extraire les métadonnées
            try:
                audio_file = File(filepath)
                metadata = {
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'title': str(audio_file.get('TIT2', [os.path.basename(filepath)])[0]) if audio_file else os.path.basename(filepath),
                    'artist': str(audio_file.get('TPE1', ['Inconnu'])[0]) if audio_file else 'Inconnu',
                    'album': str(audio_file.get('TALB', ['Inconnu'])[0]) if audio_file else 'Inconnu',
                    'duration': getattr(audio_file, 'info', {}).length if audio_file else 0
                }
            except:
                metadata = {
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'title': os.path.basename(filepath),
                    'artist': 'Inconnu',
                    'album': 'Inconnu',
                    'duration': 0
                }
            
            self.playlist.append(metadata)
            return True
        return False
    
    def load_current_track(self):
        """Charger la piste actuelle"""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            track = self.playlist[self.current_index]
            try:
                with open(track['filepath'], 'rb') as f:
                    self.audio_data = f.read()
                self.current_track = track
                self.position = 0
                return True
            except Exception as e:
                print(f"Erreur lors du chargement: {e}")
                return False
        return False
    
    def get_audio_chunk(self):
        """Obtenir le prochain chunk audio"""
        if self.audio_data and self.position < len(self.audio_data):
            chunk = self.audio_data[self.position:self.position + self.chunk_size]
            self.position += len(chunk)
            return chunk
        return None
    
    def next_track(self):
        """Passer à la piste suivante"""
        if self.playlist:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            return self.load_current_track()
        return False
    
    def previous_track(self):
        """Revenir à la piste précédente"""
        if self.playlist:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            return self.load_current_track()
        return False

# Instance globale du streamer
streamer = AudioStreamer()

@app.route('/')
def index():
    """Page principale du client web"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Page d'administration"""
    return render_template('admin.html')

@app.route('/api/playlist')
def get_playlist():
    """Obtenir la playlist"""
    return jsonify({
        'playlist': streamer.playlist,
        'current_index': streamer.current_index,
        'is_playing': streamer.is_playing
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload d'un fichier audio"""
    if 'audio' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    # Créer le dossier uploads s'il n'existe pas
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    # Sauvegarder le fichier
    filepath = os.path.join(uploads_dir, file.filename)
    file.save(filepath)
    
    # Ajouter à la playlist
    if streamer.add_track(filepath):
        return jsonify({'success': True, 'message': 'Fichier ajouté à la playlist'})
    else:
        return jsonify({'error': 'Erreur lors de l\'ajout du fichier'}), 500

@app.route('/api/add_local', methods=['POST'])
def add_local_file():
    """Ajouter un fichier local à la playlist"""
    data = request.get_json()
    filepath = data.get('filepath')
    
    if streamer.add_track(filepath):
        return jsonify({'success': True, 'message': 'Fichier ajouté à la playlist'})
    else:
        return jsonify({'error': 'Fichier non trouvé ou erreur'}), 400

@app.route('/stream')
def audio_stream():
    """Stream audio principal"""
    def generate_audio():
        while True:
            if streamer.is_playing and streamer.current_track:
                chunk = streamer.get_audio_chunk()
                if chunk:
                    yield chunk
                else:
                    # Fin de la piste, passer à la suivante
                    if streamer.next_track():
                        socketio.emit('track_changed', {
                            'track': streamer.current_track,
                            'index': streamer.current_index
                        })
                    else:
                        time.sleep(0.1)
            else:
                time.sleep(0.1)
    
    return Response(generate_audio(), 
                   mimetype='audio/mpeg',
                   headers={'Cache-Control': 'no-cache'})

# Routes de contrôle
@app.route('/api/play')
def play():
    """Démarrer la lecture"""
    if not streamer.current_track and streamer.playlist:
        streamer.load_current_track()
    
    streamer.is_playing = True
    socketio.emit('playback_state', {'is_playing': True})
    return jsonify({'success': True})

@app.route('/api/pause')
def pause():
    """Mettre en pause"""
    streamer.is_playing = False
    socketio.emit('playback_state', {'is_playing': False})
    return jsonify({'success': True})

@app.route('/api/next')
def next_track():
    """Piste suivante"""
    if streamer.next_track():
        socketio.emit('track_changed', {
            'track': streamer.current_track,
            'index': streamer.current_index
        })
        return jsonify({'success': True, 'track': streamer.current_track})
    return jsonify({'error': 'Aucune piste suivante'}), 400

@app.route('/api/previous')
def previous_track():
    """Piste précédente"""
    if streamer.previous_track():
        socketio.emit('track_changed', {
            'track': streamer.current_track,
            'index': streamer.current_index
        })
        return jsonify({'success': True, 'track': streamer.current_track})
    return jsonify({'error': 'Aucune piste précédente'}), 400

@app.route('/api/select/<int:index>')
def select_track(index):
    """Sélectionner une piste spécifique"""
    if 0 <= index < len(streamer.playlist):
        streamer.current_index = index
        if streamer.load_current_track():
            socketio.emit('track_changed', {
                'track': streamer.current_track,
                'index': streamer.current_index
            })
            return jsonify({'success': True, 'track': streamer.current_track})
    return jsonify({'error': 'Index invalide'}), 400

# WebSocket events
@socketio.on('connect')
def on_connect():
    """Nouveau client connecté"""
    streamer.clients.add(request.sid)
    emit('connected', {
        'message': 'Connecté au serveur audio',
        'current_track': streamer.current_track,
        'is_playing': streamer.is_playing
    })
    print(f"Client connecté: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    """Client déconnecté"""
    streamer.clients.discard(request.sid)
    print(f"Client déconnecté: {request.sid}")

@socketio.on('join_room')
def on_join_room(data):
    """Rejoindre une room"""
    room = data['room']
    join_room(room)
    emit('status', {'message': f'Rejoint la room {room}'})

if __name__ == '__main__':
    # Créer les dossiers nécessaires
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    print("Serveur de diffusion audio démarré!")
    print("Interface client: http://localhost:5000")
    print("Interface admin: http://localhost:5000/admin")
    print("Stream audio: http://localhost:5000/stream")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)