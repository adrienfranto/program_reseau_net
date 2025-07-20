from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import threading
import time
import base64
import wave
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Variables globales pour la diffusion
current_stream = None
connected_clients = set()
audio_buffer = []
is_streaming = False
stream_info = {
    'title': 'Diffusion Audio',
    'listeners': 0,
    'start_time': None,
    'status': 'stopped',
    'current_file': None
}

DEFAULT_AUDIO_FILE = 'Agrad.mp3'
AUDIO_FOLDER = 'audio'

@app.route('/stream')
def stream():
    current_file = stream_info.get('current_file') or DEFAULT_AUDIO_FILE
    audio_file = os.path.join(AUDIO_FOLDER, current_file)
    if not os.path.exists(audio_file):
        for f in os.listdir(AUDIO_FOLDER):
            if f.lower().endswith(('.mp3', '.wav', '.ogg')):
                audio_file = os.path.join(AUDIO_FOLDER, f)
                break
        else:
            return "Aucun fichier audio trouvé", 404

    def generate():
        with open(audio_file, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                yield data
                time.sleep(0.01)

    # Détecte le type MIME
    if audio_file.lower().endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif audio_file.lower().endswith('.wav'):
        mimetype = 'audio/wav'
    elif audio_file.lower().endswith('.ogg'):
        mimetype = 'audio/ogg'
    else:
        mimetype = 'application/octet-stream'

    return Response(stream_with_context(generate()), mimetype=mimetype)

class AudioStreamer:
    def __init__(self):
        self.is_active = False
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 2
        self.chunk_size = 1024
        self.current_position = 0
        self.loop_enabled = True

    def start_stream(self, audio_file_path=None):
        global is_streaming, stream_info

        if not audio_file_path:
            audio_file_path = os.path.join(AUDIO_FOLDER, DEFAULT_AUDIO_FILE)

        if not os.path.exists(audio_file_path):
            logger.warning(f"Fichier audio non trouvé: {audio_file_path}")
            os.makedirs(AUDIO_FOLDER, exist_ok=True)
            return self._start_simulation_mode()

        try:
            file_extension = os.path.splitext(audio_file_path)[1].lower()
            if file_extension == '.wav':
                success = self._load_wav_file(audio_file_path)
            elif file_extension == '.mp3':
                success = self._load_mp3_file(audio_file_path)
            elif file_extension == '.ogg':
                success = self._load_ogg_file(audio_file_path)
            else:
                logger.error(f"Format audio non supporté: {file_extension}")
                return self._start_simulation_mode()

            if success:
                self.is_active = True
                is_streaming = True
                stream_info['status'] = 'streaming'
                stream_info['start_time'] = datetime.now().isoformat()
                stream_info['current_file'] = os.path.basename(audio_file_path)

                streaming_thread = threading.Thread(target=self._stream_audio)
                streaming_thread.daemon = True
                streaming_thread.start()

                logger.info(f"Diffusion audio démarrée: {audio_file_path}")
                return True
            else:
                return self._start_simulation_mode()

        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la diffusion: {e}")
            return self._start_simulation_mode()

    def _load_ogg_file(self, file_path):
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_ogg(file_path)
            audio = audio.set_frame_rate(44100).set_channels(2)
            self.audio_data = audio.raw_data
            self.sample_rate = audio.frame_rate
            self.channels = audio.channels
            return True
        except ImportError:
            logger.warning("pydub n'est pas installé. Impossible de lire les fichiers OGG.")
            logger.info("Installez pydub avec: pip install pydub")
            return False
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier OGG: {e}")
            return False

    def _load_wav_file(self, file_path):
        try:
            with wave.open(file_path, 'rb') as wav_file:
                self.sample_rate = wav_file.getframerate()
                self.channels = wav_file.getnchannels()
                self.audio_data = wav_file.readframes(wav_file.getnframes())
            return True
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier WAV: {e}")
            return False

    def _load_mp3_file(self, file_path):
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(file_path)
            audio = audio.set_frame_rate(44100).set_channels(2)
            self.audio_data = audio.raw_data
            self.sample_rate = audio.frame_rate
            self.channels = audio.channels
            return True
        except ImportError:
            logger.warning("pydub n'est pas installé. Impossible de lire les fichiers MP3.")
            logger.info("Installez pydub avec: pip install pydub")
            return False
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier MP3: {e}")
            return False

    def _start_simulation_mode(self):
        global is_streaming, stream_info
        self.is_active = True
        is_streaming = True
        stream_info['status'] = 'streaming'
        stream_info['start_time'] = datetime.now().isoformat()
        stream_info['current_file'] = 'Simulation (bruit blanc)'

        streaming_thread = threading.Thread(target=self._stream_simulation)
        streaming_thread.daemon = True
        streaming_thread.start()

        logger.info("Mode simulation activé - diffusion de bruit blanc")
        return True

    def stop_stream(self):
        global is_streaming, stream_info
        self.is_active = False
        is_streaming = False
        stream_info['status'] = 'stopped'
        stream_info['start_time'] = None
        stream_info['current_file'] = None
        self.current_position = 0
        socketio.emit('stream_stopped')
        logger.info("Diffusion audio arrêtée")

    def _stream_audio(self):
        if not self.audio_data:
            return

        bytes_per_sample = 2  # 16-bit audio
        chunk_size = self.chunk_size * self.channels * bytes_per_sample
        total_chunks = len(self.audio_data) // chunk_size

        while self.is_active:
            start_pos = self.current_position * chunk_size
            end_pos = min(start_pos + chunk_size, len(self.audio_data))

            if start_pos >= len(self.audio_data):
                if self.loop_enabled:
                    self.current_position = 0
                    continue
                else:
                    self.stop_stream()
                    break

            chunk = self.audio_data[start_pos:end_pos]
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
            socketio.emit('audio_chunk', {
                'data': encoded_chunk,
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'chunk_index': self.current_position,
                'total_chunks': total_chunks,
                'timestamp': time.time()
            })

            self.current_position += 1
            sleep_time = self.chunk_size / self.sample_rate
            time.sleep(sleep_time)

    def _stream_simulation(self):
        import random
        chunk_counter = 0
        while self.is_active:
            import math
            frequency = 440
            amplitude = 0.1
            chunk_data = []
            for i in range(self.chunk_size):
                sample_time = (chunk_counter * self.chunk_size + i) / self.sample_rate
                sample_value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * sample_time))
                sample_bytes = sample_value.to_bytes(2, 'little', signed=True)
                chunk_data.extend(sample_bytes)
                chunk_data.extend(sample_bytes)  # stéréo
            encoded_chunk = base64.b64encode(bytes(chunk_data)).decode('utf-8')
            socketio.emit('audio_chunk', {
                'data': encoded_chunk,
                'sample_rate': self.sample_rate,
                'channels': 2,
                'chunk_index': chunk_counter,
                'is_simulation': True,
                'timestamp': time.time()
            })
            chunk_counter += 1
            time.sleep(0.1)

# Instance du streamer
audio_streamer = AudioStreamer()

@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier envoyé'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nom de fichier vide'})
    if file and file.filename.lower().endswith(('.mp3', '.wav', '.ogg')):
        save_path = os.path.join(AUDIO_FOLDER, file.filename)
        file.save(save_path)
        return jsonify({'success': True, 'filename': file.filename})
    return jsonify({'success': False, 'message': 'Format non supporté'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    try:
        data = request.get_json() or {}
        audio_file = data.get('audio_file')
        if audio_file:
            audio_file_path = os.path.join(AUDIO_FOLDER, audio_file)
        else:
            audio_file_path = None
        success = audio_streamer.start_stream(audio_file_path)
        if success:
            socketio.emit('stream_started', {
                'title': stream_info['title'],
                'start_time': stream_info['start_time'],
                'current_file': stream_info['current_file']
            })
            return jsonify({
                'success': True,
                'message': 'Diffusion démarrée',
                'current_file': stream_info['current_file']
            })
        else:
            return jsonify({'success': False, 'message': 'Erreur lors du démarrage'})
    except Exception as e:
        logger.error(f"Erreur API start_stream: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    try:
        audio_streamer.stop_stream()
        return jsonify({'success': True, 'message': 'Diffusion arrêtée'})
    except Exception as e:
        logger.error(f"Erreur API stop_stream: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stream/status', methods=['GET'])
def get_stream_status():
    return jsonify({
        'is_streaming': is_streaming,
        'listeners': len(connected_clients),
        'stream_info': stream_info
    })

@app.route('/api/audio/files', methods=['GET'])
def list_audio_files():
    try:
        if not os.path.exists(AUDIO_FOLDER):
            os.makedirs(AUDIO_FOLDER, exist_ok=True)
        audio_files = []
        supported_formats = ['.wav', '.mp3', '.ogg']
        for file in os.listdir(AUDIO_FOLDER):
            if any(file.lower().endswith(fmt) for fmt in supported_formats):
                file_path = os.path.join(AUDIO_FOLDER, file)
                file_size = os.path.getsize(file_path)
                audio_files.append({
                    'name': file,
                    'size': file_size,
                    'is_default': file == DEFAULT_AUDIO_FILE
                })
        return jsonify({
            'files': audio_files,
            'default_file': DEFAULT_AUDIO_FILE
        })
    except Exception as e:
        logger.error(f"Erreur lors de la liste des fichiers: {e}")
        return jsonify({'error': str(e)})

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    connected_clients.add(client_id)
    stream_info['listeners'] = len(connected_clients)
    logger.info(f"Client connecté: {client_id}")
    emit('stream_status', {
        'is_streaming': is_streaming,
        'stream_info': stream_info
    })
    socketio.emit('listeners_update', {
        'count': len(connected_clients)
    })

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    connected_clients.discard(client_id)
    stream_info['listeners'] = len(connected_clients)
    logger.info(f"Client déconnecté: {client_id}")
    socketio.emit('listeners_update', {
        'count': len(connected_clients)
    })

@socketio.on('join_stream')
def handle_join_stream():
    client_id = request.sid
    join_room('audio_stream')
    emit('joined_stream', {
        'message': 'Connecté au flux audio',
        'is_streaming': is_streaming,
        'stream_info': stream_info
    })

@socketio.on('leave_stream')
def handle_leave_stream():
    client_id = request.sid
    leave_room('audio_stream')
    emit('left_stream', {
        'message': 'Déconnecté du flux audio'
    })

def create_sample_audio_file():
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
    sample_file = os.path.join(AUDIO_FOLDER, 'sample.wav')
    if not os.path.exists(sample_file):
        try:
            import wave
            import math
            sample_rate = 44100
            duration = 10
            frequency = 440
            samples = []
            for i in range(int(sample_rate * duration)):
                sample_time = i / sample_rate
                sample_value = int(16384 * math.sin(2 * math.pi * frequency * sample_time))
                samples.append(sample_value)
            with wave.open(sample_file, 'w') as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                for sample in samples:
                    wav_file.writeframes(sample.to_bytes(2, 'little', signed=True))
                    wav_file.writeframes(sample.to_bytes(2, 'little', signed=True))
            logger.info(f"Fichier audio d'exemple créé: {sample_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du fichier d'exemple: {e}")

@socketio.on('player_command')
def handle_player_command(data):
    emit('player_command', data, broadcast=True)

if __name__ == '__main__':
    for folder in ['templates', 'static', AUDIO_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    create_sample_audio_file()
    print("🎵 Serveur de diffusion audio en continu")
    print("📡 Démarrage du serveur...")
    print("🌐 Interface web: http://localhost:5000")
    print("⚙️  Administration: http://localhost:5000/admin")
    print(f"🎼 Fichier audio par défaut: {DEFAULT_AUDIO_FILE}")
    print(f"📁 Dossier audio: {AUDIO_FOLDER}")
    default_path = os.path.join(AUDIO_FOLDER, DEFAULT_AUDIO_FILE)
    if os.path.exists(default_path):
        print(f"✅ Fichier par défaut trouvé: {default_path}")
    else:
        print(f"⚠️  Fichier par défaut non trouvé: {default_path}")
        print("   Mode simulation activé automatiquement")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)