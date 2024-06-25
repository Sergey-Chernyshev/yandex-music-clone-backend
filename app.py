from flask import Flask, request
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from yandex_music import Client
import json
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('YANDEXMUSIC_TOKEN')

app = Flask(__name__)
app.debug = True
# CORS(app, resources={r"/*": {"origins": "http://localhost:3000", "methods": ["GET", "POST"], "allowed_headers": ["my-custom-header"], "supports_credentials": True}})
# socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000", manage_session=False)
CORS(app, resources={r"/*": {"origins": "http://192.168.1.75:3000", "methods": ["GET", "POST"], "allowed_headers": ["my-custom-header"], "supports_credentials": True}})
socketio = SocketIO(app, cors_allowed_origins="http://192.168.1.75:3000", manage_session=False)



# music
client = Client(token).init()


# class Treck:
#     def __init__(self, track_id, track_title, track_time, track_timing):
#         self.track_id = track_id
#         self.track_url = client.users_likes_tracks()[0].fetch_track().get_download_info()[0].get_direct_link()
#         self.track_title = track_title
#         self.track_time = track_time
#         self.track_timing = track_timing




class RoomManager:
    def __init__(self, room_id, socket_id):
        self.room_id = room_id
        self.sockets_id = [socket_id]
        self.play = False
        self.track = None
        self.track_title = ""
        self.track_url = client.users_likes_tracks()[0].fetch_track().get_download_info()[0].get_direct_link()
        self.time_listen = 0.0
        self.liked_tracks = client.users_likes_tracks()

        self.palyingTrack = {
            "trackId": None,
            "trackTitle": None,
            "trackUrl": None,
            "trackCoverUrl": None,
            "trackArtistsName": [],
        }

        self.preloadTrack = {
            "trackId": None,
            "trackTitle": None,
            "trackUrl": None,
            "trackCoverUrl": None,
            "trackArtistsName": [],
        }

        # Создаем список для хранения всех треков
        all_tracks = []

        # # Итерируемся по понравившимся трекам и получаем каждый трек
        # for liked_track in liked_tracks[0:10]:
        #     track = liked_track.fetch_track()
        #     all_tracks.append(track)

        # playlist = client.users_playlists(playlist_id)
        # if not playlist or not playlist.tracks:
        #     print("Треки в плейлисте не найдены.")
        # else:
        #     tracks = playlist.tracks
        #     for track_short in tracks:
        #         track = track_short.track
        #         artists = ', '.join(artist.name for artist in track.artists) if track.artists else "Unknown Artist"
                
    


        self.allTracks = all_tracks




    def change_track_for_all_users(self):        
        # data['trackId']
        for s_id in self.sockets_id:
            socketio.emit('changePlayingTrack', json.dumps(self.palyingTrack), room=s_id)

    def add_user(self, socket_id):
        self.sockets_id.append(socket_id)
        return True

    def remove_user(self, socket_id):
        if socket_id not in self.sockets_id:
            return False
        self.sockets_id.remove(socket_id)
        return True

    def send_message_to_all_room(self, message):
        for s_id in self.sockets_id:
            # print(f"Message sent to {s_id} in room: {self.room_id}")
            pass

    def change_pause_track_on_all(self):
        for s_id in self.sockets_id:
            # print(f"Changing playback for {s_id} in room: {self.room_id}")
            socketio.emit('changePauseTrack', self.play, room=s_id)

    def synchronization_data(self):
        data = {
            "track": self.track,
            "time_listen": self.time_listen
        }
        for s_id in self.sockets_id:
            # print(f"Changing playback for {s_id} in room: {self.room_id}")
            socketio.emit('changePauseTrack', data, room=s_id)



class Server:
    def __init__(self):
        self.rooms = {}
        self.sockets_with_rooms = {}

        @socketio.on('connect')
        def handle_connect():
            print(f'A user connected with socket: {request.sid}')
            pass

        @socketio.on('getAllTracks')
        def handle_get_all_tracks(user_id):
            playlist = client.users_playlists(3)
            all_tracks = []
            tracks = playlist.tracks

            for track_short in tracks:
                track = track_short.track
                cover_url = track.get_cover_url("800x800") if track.cover_uri else "Обложка отсутствует"
                artists_names = ', '.join(artist.name for artist in track.artists) if track.artists else "Неизвестный артист"
                data = {
                    "trackCoverUrl": cover_url, 
                    "trackTitle": track.title if track.title else "Название отсутствует", 
                    "trackArtistsName": artists_names, 
                    "trackId": track.id if track.id else "ID отсутствует"
                }
                all_tracks.append(data)

            if user_id in self.rooms:
                socketio.emit('getAllTracks', json.dumps(all_tracks), room=request.sid)


        @socketio.on('joinRoom')
        def handle_join_room(user_id):
            print(user_id)
            self.sockets_with_rooms[request.sid] = user_id
            if user_id in self.rooms:
                room = self.rooms[user_id]
                room.add_user(request.sid)
                self.rooms[user_id] = room
                print("Successfully joined the room")
                print(room)
            else:
                self.rooms[user_id] = RoomManager(user_id, request.sid)
                print("Room created")

        @socketio.on('disconnect')
        def handle_disconnect():
            if request.sid in self.sockets_with_rooms:
                # print("socketsWithRooms:", self.sockets_with_rooms)
                user_id = self.sockets_with_rooms[request.sid]
                room = self.rooms[user_id]
                room.remove_user(request.sid)
                self.rooms[user_id] = room
                # print(f"User with socket: {request.sid} disconnected from room: {user_id}")
                del self.sockets_with_rooms[request.sid]

        @socketio.on('changePauseTrack')
        def handle_change_pause_track(data):
            user_id = data['userId']
            t_p = data['tP']
            print(self.rooms)
            print(self.rooms[user_id])
            print(user_id, t_p)
            room = self.rooms[user_id]
            room.play = t_p
            # print("Track state:", t_p)
            room.change_pause_track_on_all()
            self.rooms[user_id] = room

        @socketio.on("changeTrackOnPlay")
        def change_track_on_play(data):
            print(data)
            track_id = data["idNewTrack"]
            user_id = data["userId"]
            track_url = client.tracks(track_id)[0].get_download_info()[0].get_direct_link()
            print(client.tracks(track_id)[0])

            room = self.rooms[user_id]
            room.track_url = track_url
            self.rooms[user_id] = room

            room.palyingTrack = {
                "trackId": client.tracks(track_id)[0].id,
                "trackTitle": client.tracks(track_id)[0].title,
                "trackUrl": client.tracks(track_id)[0].get_download_info()[0].get_direct_link(),
                "trackCoverUrl": client.tracks(track_id)[0].get_cover_url("800x800"),
                "trackArtistsName": client.tracks(track_id)[0].artistsName(),
            }
            
            self.rooms[user_id] = room

            room.change_track_for_all_users()
            # print("New track url: ", track_url)
        
        @socketio.on("preloadTrack")
        def handle_preload_track(data):
            # print("Preload track url: ", data)
            track_id = data["idTrack"]
            user_id = data["userId"]
            preload_track_info = {
                "trackId": client.tracks(track_id)[0].id,
                "trackTitle": client.tracks(track_id)[0].title,
                "trackUrl": client.tracks(track_id)[0].get_download_info()[0].get_direct_link(),
                "trackCoverUrl": client.tracks(track_id)[0].get_cover_url("800x800"),
                "trackArtistsName": client.tracks(track_id)[0].artistsName(),
            }
            socketio.emit("preloadTrack", json.dumps(preload_track_info), room=request.sid)

        @socketio.on("loadNextTracksToQueque")
        def handle_load_next_tracks_to_queue(data):
            key_start = data["key_start"]
            albom_id = data["albom_id"]





@app.route('/')
def index():
    return 'Hello World'

if __name__ == '__main__':
    server = Server()
    socketio.run(app, host='0.0.0.0', port=8000)
