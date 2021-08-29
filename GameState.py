from dataclasses import dataclass
from typing import Dict, Callable, Optional, List
from blaseball_mike.models import Team


def mod_for_player(player):
    return ""


@dataclass
class PlayerState:
    id: str
    name: str
    mod: str


@dataclass
class TeamState:
    nickname: str
    pitcher: PlayerState
    lineup: List[PlayerState]
    batter_index: int

    def __init__(self, update: dict, timestamp: str, prefix: str):
        team = Team.load_at_time(update[prefix + 'Team'], timestamp)
        self.nickname = team.get_nickname()

        self.pitcher = PlayerState(id=update[prefix + 'Pitcher'],
                                   name=update[prefix + 'PitcherName'],
                                   mod=update[prefix + 'PitcherMod'])

        self.lineup = [
            PlayerState(player.id, player.name, mod_for_player(player))
            for player in team.lineup
        ]

        self.batter_index = -1


class GameState:
    UpdateFunction = Callable[['GameState', dict, Optional[dict]], dict]
    update_type: Dict[int, UpdateFunction] = {}

    def __init__(self, first_update_full: dict):
        """
        Create a GameState
        
        Takes a first_update to get game-specific parameters that should be
        static for the whole game. This should be the first available update
        after "Let's Go!" and "Play ball!" 
        :param first_update_full:
        """
        first_update = first_update_full['data']
        timestamp = first_update_full['timestamp']

        self.expects_lets_go = True
        self.expects_play_ball = False
        self.expects_inning_start = False
        self.expects_batter_up = False
        self.expects_pitch = False

        self.away = TeamState(first_update, timestamp, 'away')
        self.home = TeamState(first_update, timestamp, 'home')

        self.game_update = {
            'id': first_update['id'],
            'day': first_update['day'],
            'phase': 2,
            'rules': first_update['rules'],
            'shame': False,
            'inning': 0,
            'season': first_update['season'],
            'weather': first_update['weather'],
            'awayOdds': first_update['awayOdds'],
            'awayOuts': first_update['awayOuts'],
            'awayTeam': first_update['awayTeam'],
            'homeOdds': first_update['homeOdds'],
            'homeOuts': first_update['homeOuts'],
            'homeTeam': first_update['homeTeam'],
            'outcomes': [],
            'awayBalls': first_update['awayBalls'],
            'awayBases': first_update['awayBases'],
            'awayScore': 0,
            'finalized': False,
            'gameStart': False,
            'homeBalls': first_update['homeBalls'],
            'homeBases': first_update['homeBases'],
            'homeScore': 0,
            'playCount': 0,
            'stadiumId': first_update['stadiumId'],
            'statsheet': first_update['statsheet'],
            'atBatBalls': 0,
            'awayBatter': None,
            'homeBatter': None,
            'lastUpdate': "",
            'tournament': first_update['tournament'],
            'awayPitcher': None,
            'awayStrikes': first_update['awayStrikes'],
            'baseRunners': [],
            'homePitcher': None,
            'homeStrikes': first_update['homeStrikes'],
            'repeatCount': 0,  # what
            'scoreLedger': "",
            'scoreUpdate': "",
            'seriesIndex': first_update['seriesIndex'],
            'terminology': first_update['terminology'],
            'topOfInning': True,
            'atBatStrikes': 0,
            'awayTeamName': first_update['awayTeamName'],
            'gameComplete': False,
            'homeTeamName': first_update['homeTeamName'],
            'isPostseason': first_update['isPostseason'],
            'isTitleMatch': first_update['isTitleMatch'],
            'seriesLength': first_update['seriesLength'],
            'awayBatterMod': "",
            'awayTeamColor': first_update['awayTeamColor'],
            'awayTeamEmoji': first_update['awayTeamEmoji'],
            'basesOccupied': [],
            'homeBatterMod': "",
            'homeTeamColor': first_update['homeTeamColor'],
            'homeTeamEmoji': first_update['homeTeamEmoji'],
            'awayBatterName': "",
            'awayPitcherMod': "",
            'baseRunnerMods': [],
            'gameStartPhase': -1,
            'halfInningOuts': 0,
            'homeBatterName': "",
            'homePitcherMod': "",
            'newInningPhase': -1,
            'topInningScore': 0,
            'awayPitcherName': "",
            'baseRunnerNames': [],
            'baserunnerCount': 0,
            'halfInningScore': 0,
            'homePitcherName': "",
            'awayTeamNickname': first_update['awayTeamNickname'],
            'homeTeamNickname': first_update['homeTeamNickname'],
            'secretBaserunner': None,
            'bottomInningScore': 0,
            'awayTeamBatterCount': 0,
            'homeTeamBatterCount': 0,
            'awayTeamSecondaryColor': first_update['awayTeamSecondaryColor'],
            'homeTeamSecondaryColor': first_update['homeTeamSecondaryColor'],
        }

    def update(self, feed_event, game_update):
        GameState.update_type[feed_event['type']](self, feed_event, game_update)
        return self.game_update

    def update_lets_go(self, feed_event: dict, game_update: Optional[dict]):
        assert self.expects_lets_go
        assert feed_event['description'] == "Let's Go!"
        assert game_update is None or game_update['lastUpdate'] == ""
        self.expects_lets_go = False
        self.expects_play_ball = True

    def update_play_ball(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_play_ball
        assert feed_event['description'] == "Play ball!"
        self.expects_play_ball = False
        self.expects_inning_start = True

        self.game_update['inning'] = -1
        self.game_update['playCount'] = 2
        self.game_update['gameStart'] = True
        self.game_update['lastUpdate'] = "Play ball!"
        self.game_update['topOfInning'] = False
        self.game_update['awayTeamBatterCount'] = -1
        self.game_update['homeTeamBatterCount'] = -1

    def update_inning_start(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_inning_start

        self.game_update['playCount'] += 1
        self.game_update['phase'] = 6  # whatever that means
        self.game_update['gameStartPhase'] = 10  # ???
        self.game_update['inning'] += 1
        self.game_update['topOfInning'] = not self.game_update['topOfInning']

        # This is not strictly updated _every_ inning start, but it does get
        # set on the first inning start and it doesn't hurt to overwrite it
        self.game_update['awayPitcher'] = self.away.pitcher.id
        self.game_update['awayPitcherName'] = self.away.pitcher.name
        self.game_update['awayPitcherMod'] = self.away.pitcher.mod
        self.game_update['homePitcher'] = self.home.pitcher.id
        self.game_update['homePitcherName'] = self.home.pitcher.name
        self.game_update['homePitcherMod'] = self.home.pitcher.mod

        top_or_bottom = "Top" if self.game_update['topOfInning'] else "Bottom"
        inning = self.game_update['inning'] + 1
        team_name = self.game_update[self.prefix() + 'TeamName']
        description = f"{top_or_bottom} of {inning}, {team_name} batting."

        self.game_update['lastUpdate'] = description
        assert feed_event['description'] == description

        self.expects_inning_start = False
        self.expects_batter_up = True

    def update_batter_up(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_batter_up

        team_state = self.away if self.game_update['topOfInning'] else self.home
        team_state.batter_index += 1

        batter = team_state.lineup[team_state.batter_index]
        self.game_update[self.prefix() + 'Batter'] = batter.id
        self.game_update[self.prefix() + 'BatterName'] = batter.name
        self.game_update[self.prefix() + 'BatterMod'] = batter.mod

        description = f"{batter.name} batting for the {team_state.nickname}."

        assert feed_event['description'] == description

        self.expects_batter_up = False
        self.expects_pitch = True

    def prefix(self):
        if self.game_update['topOfInning']:
            return 'away'
        else:
            return 'home'


GameState.update_type = {
    0: GameState.update_lets_go,
    1: GameState.update_play_ball,
    2: GameState.update_inning_start,
    12: GameState.update_batter_up,
}
