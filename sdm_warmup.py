
from commands.typed import TypedSayCommand
from cvars import ConVar
from engines.server import queue_server_command, execute_server_command
from filters.players import PlayerIter
from filters.weapons import WeaponClassIter
from listeners.tick import Delay
from listeners.tick import Repeat
from players._base import Player
from weapons.restrictions import WeaponRestrictionHandler
from .utils import bot_spawn, sdm_logger, player_freeze, message_show
from .api import sdm_api
from .sdm_single import  sdm_single
from simple_settings import settings

class Warmup_handle:
    def __init__(self):
        self.state_warmup = True
        self.handle_flag = False
        self.checking = Repeat(self.players_quantity)
        self.players_to_start_sdm = settings.PAYERS_TO_START
        self.player_weapon = "weapon_glock"
        self.bot_weapon = "weapon_knife"
        self.single_player_weapon_restrict = WeaponRestrictionHandler()

    def players_quantity(self):
        sdm_logger.info(f"connected players: {len(PlayerIter('human'))}")
        # TODO: prevent connecting more than we want (check on_player_connect) and provide reconnect
        if len(PlayerIter('human')) >= self.players_to_start_sdm:# Server maximum clients for round
            authorized_clients = list()
            for player in PlayerIter('human'):
                sdm_logger.debug(f'Checking player {player.index} whose nickname is {player.name}')
                backend_approved = sdm_api.request_server_loads(player, hostname=ConVar('hostname').get_string())
                if backend_approved:
                    authorized_clients.append(player.index)
            if len(authorized_clients) >= self.players_to_start_sdm and self.state_warmup:
                sdm_logger.debug('Starting game preparation')
                self.stop()
                sdm_logger.debug(f'Preparing game for player {authorized_clients[0]}')
                self.game_prepare(authorized_clients[0])
            else:
                sdm_logger.debug(f'Number of clients is {len(authorized_clients)} To start we need {self.players_to_start_sdm} and state of warmup is {self.state_warmup}')

    def game_prepare(self, authorized_client):
        sdm_api.request_get_game(hostname=ConVar('hostname').get_string())
        player_freeze()
        message_show("Начнется через", 5, x=-1, y=0.15) #without
        if self.players_to_start_sdm > 1:
            sdm_logger.warning('Multiplayer requested. Assigning single player mode.')
        Delay(6, self.game_start, (authorized_client, sdm_single, sdm_api))
        self.state_warmup = False
        sdm_logger.debug('==============sdm_warmup ended=============')

    def game_start(self, player_index: int, game_mode, api):
        if api.input_json['weapon_for_user']:
            self.player_weapon = api.input_json['weapon_for_user']
            sdm_logger.debug(f'Current player from backend {self.player_weapon}')
        else:
            sdm_logger.debug(f'No weapon for player from backend Leaving {self.player_weapon}')
        if api.input_json['weapon_for_bot'] and api.input_json['weapon_for_bot'] != "weapon_knife":
            self.bot_weapon = api.input_json['weapon_for_bot']
            sdm_logger.debug(f'Current bot from backend {self.bot_weapon}')
        else:
            sdm_logger.debug(f'No weapon for bot from backend Leaving {self.bot_weapon}')
        game_mode.single_start = True
        ConVar('mp_roundtime').set_int(api.input_json["game_time"] // 60)  # in minutes
        ConVar('mp_round_restart_delay').set_int(14)
        ConVar('mp_teammates_are_enemies').set_int(0)
        ConVar('bot_difficulty').set_int(api.input_json.get("difficulty", 1))
        sdm_logger.info(f"Bot difficulty is set to {ConVar('bot_difficulty').get_int()}")
        queue_server_command('bot_kick')
        queue_server_command('mp_warmup_end')
        if not self.state_warmup:
            self.spawn_enemies(player_index, api)

            #sdm_logger.debug(f'Restriction of {bot_team[player.team]} team from {self.player_weapon} is done')
        else:
            sdm_logger.error('Warmup was not finished. Skipping game start.')

    def start(self):
        if not self.handle_flag:
            self.handle_flag = True
            self.checking.start(2)

    def stop(self):
        self.handle_flag = False
        self.checking.stop()

    def spawn_enemies(self, player_index, api):
        player = Player(player_index)
        bot_team = {3: "t", 2: "ct"}  # 3 means player is ct, 2 means player is t
        bot_count = api.input_json["bots_count"] if api.input_json["bots_count"] else 8
        play_sound = False
        if api.input_json["models_for_bot"] == 'zombie':
            play_sound = True
        Delay(1.0, bot_spawn, (bot_count, bot_team[player.team], play_sound))

w_h = Warmup_handle()