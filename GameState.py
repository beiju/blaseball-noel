from dataclasses import dataclass
from typing import Dict, Callable, Optional, List
from blaseball_mike.models import Team

from parsers import Parsers

BASE_NUM_FOR_HIT = {
    'Single': 0,
    'Double': 1,
    'Triple': 2,
    'Quadruple': 3,
}

BASE_NUM_FOR_NAME = {
    'first': 0,
    'second': 1,
    'third': 2,
    'fourth': 3,
}


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

    def __init__(self, updates: List[dict], timestamp: str, prefix: str):
        team = Team.load_at_time(first_truthy(updates, prefix + 'Team'),
                                 timestamp)
        self.nickname = team.get_nickname()

        self.pitcher = PlayerState(
            id=first_truthy(updates, prefix + 'Pitcher'),
            name=first_truthy(updates, prefix + 'PitcherName'),
            mod=first_truthy(updates, prefix + 'PitcherMod') or '')
        assert self.pitcher.id
        assert self.pitcher.name

        self.lineup = [
            PlayerState(player.id, player.name, mod_for_player(player))
            for player in team.lineup
        ]

        self.batter_index = -1


def first_truthy(updates, key):
    for update in updates:
        if update['data'][key]:
            return update['data'][key]


class GameState:
    UpdateFunction = Callable[['GameState', dict, Optional[dict]], dict]
    update_type: Dict[int, UpdateFunction] = {}

    def __init__(self, updates: List[dict]):
        self.expects_lets_go = True
        self.expects_play_ball = False
        self.expects_half_inning_start = False
        self.expects_batter_up = False
        self.expects_pitch = False
        self.expects_inning_end = False

        # Chronicler adds timestamp so I can depend on it existing
        self.away = TeamState(updates, updates[0]['timestamp'], 'away')
        self.home = TeamState(updates, updates[0]['timestamp'], 'home')

        self.game_update = {
            'id': updates[0]['data']['id'],
            'day': updates[0]['data']['day'],
            'phase': 2,
            'rules': updates[0]['data']['rules'],
            'shame': False,
            'inning': 0,
            'season': updates[0]['data']['season'],
            'weather': updates[0]['data']['weather'],
            'awayOdds': first_truthy(updates, 'awayOdds'),
            'awayOuts': first_truthy(updates, 'awayOuts'),
            'awayTeam': first_truthy(updates, 'awayTeam'),
            'homeOdds': first_truthy(updates, 'homeOdds'),
            'homeOuts': first_truthy(updates, 'homeOuts'),
            'homeTeam': first_truthy(updates, 'homeTeam'),
            'outcomes': [],
            'awayBalls': first_truthy(updates, 'awayBalls'),
            'awayBases': first_truthy(updates, 'awayBases'),
            'awayScore': 0,
            'finalized': False,
            'gameStart': False,
            'homeBalls': first_truthy(updates, 'homeBalls'),
            'homeBases': first_truthy(updates, 'homeBases'),
            'homeScore': 0,
            'playCount': 0,
            'stadiumId': updates[0]['data']['stadiumId'],
            'statsheet': updates[0]['data']['statsheet'],
            'atBatBalls': 0,
            'awayBatter': None,
            'homeBatter': None,
            'lastUpdate': "",
            'tournament': updates[0]['data']['tournament'],
            'awayPitcher': None,
            'awayStrikes': first_truthy(updates, 'awayStrikes'),
            'baseRunners': [],
            'homePitcher': None,
            'homeStrikes': first_truthy(updates, 'homeStrikes'),
            'repeatCount': 0,  # what
            'scoreLedger': "",
            'scoreUpdate': "",
            'seriesIndex': updates[0]['data']['seriesIndex'],
            'terminology': updates[0]['data']['terminology'],
            'topOfInning': True,
            'atBatStrikes': 0,
            'awayTeamName': first_truthy(updates, 'awayTeamName'),
            'gameComplete': False,
            'homeTeamName': first_truthy(updates, 'homeTeamName'),
            'isPostseason': updates[0]['data']['isPostseason'],
            'isTitleMatch': updates[0]['data']['isTitleMatch'],
            'seriesLength': updates[0]['data']['seriesLength'],
            'awayBatterMod': "",
            'awayTeamColor': first_truthy(updates, 'awayTeamColor'),
            'awayTeamEmoji': first_truthy(updates, 'awayTeamEmoji'),
            'basesOccupied': [],
            'homeBatterMod': "",
            'homeTeamColor': first_truthy(updates, 'homeTeamColor'),
            'homeTeamEmoji': first_truthy(updates, 'homeTeamEmoji'),
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
            'awayTeamNickname': first_truthy(updates, 'awayTeamNickname'),
            'homeTeamNickname': first_truthy(updates, 'homeTeamNickname'),
            'secretBaserunner': None,
            'bottomInningScore': 0,
            'awayTeamBatterCount': 0,
            'homeTeamBatterCount': 0,
            'awayTeamSecondaryColor': first_truthy(updates,
                                                   'awayTeamSecondaryColor'),
            'homeTeamSecondaryColor': first_truthy(updates,
                                                   'homeTeamSecondaryColor'),
        }

    def prefix(self):
        if self.game_update['topOfInning']:
            return 'away'
        else:
            return 'home'

    def batter(self) -> PlayerState:
        team_state = self.batting_team()
        return team_state.lineup[team_state.batter_index]

    def batting_team(self) -> TeamState:
        return self.away if self.game_update['topOfInning'] else self.home

    def fielding_team(self) -> TeamState:
        return self.home if self.game_update['topOfInning'] else self.away

    def update(self, feed_event, game_update):
        print(feed_event['description'])
        update_func = GameState.update_type[feed_event['type']]
        returned = update_func(self, feed_event, game_update)

        if returned is not None:
            return returned

        self.game_update['playCount'] += 1
        return self.game_update

    def update_lets_go(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_lets_go
        assert feed_event['description'] == "Let's Go!"
        self.expects_lets_go = False
        self.expects_play_ball = True

        self.game_update['lastUpdate'] = "Let's Go!"
        self.game_update['gameStart'] = True
        self.game_update['phase'] = 1
        self.game_update['awayPitcher'] = self.away.pitcher.id
        self.game_update['awayPitcherName'] = self.away.pitcher.name
        self.game_update['awayPitcherMod'] = self.away.pitcher.mod
        self.game_update['awayTeamBatterCount'] = -1
        self.game_update['homePitcher'] = self.home.pitcher.id
        self.game_update['homePitcherName'] = self.home.pitcher.name
        self.game_update['homePitcherMod'] = self.home.pitcher.mod
        self.game_update['homeTeamBatterCount'] = -1

    def update_play_ball(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_play_ball
        assert feed_event['description'] == "Play ball!"
        self.expects_play_ball = False
        self.expects_half_inning_start = True

        self.game_update['phase'] = 2
        self.game_update['inning'] = -1
        self.game_update['lastUpdate'] = "Play ball!"
        self.game_update['topOfInning'] = False
        # This does double duty: the normal increment for the special game
        # update, which doesn't get an automatic increment, and an extra
        # increment which is needed for the stored game update, which does also
        # get an automatic increment
        self.game_update['playCount'] += 1

        # This makes backward progress. Don't reverse it, just return a modified
        # game update
        special_game_update = self.game_update.copy()
        special_game_update['awayPitcher'] = None
        special_game_update['awayPitcherName'] = ''
        special_game_update['awayPitcherMod'] = ''
        special_game_update['homePitcher'] = None
        special_game_update['homePitcherName'] = ''
        special_game_update['homePitcherMod'] = ''
        special_game_update['homeTeamBatterCount'] = -1

        return special_game_update

    def update_half_inning_start(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_half_inning_start

        self.game_update['phase'] = 6  # whatever that means
        self.game_update['gameStartPhase'] = 10  # ???
        if not self.game_update['topOfInning']:
            self.game_update['inning'] += 1
        self.game_update['topOfInning'] = not self.game_update['topOfInning']

        top_or_bottom = "Top" if self.game_update['topOfInning'] else "Bottom"
        inning = self.game_update['inning'] + 1
        team_name = self.game_update[self.prefix() + 'TeamName']
        description = f"{top_or_bottom} of {inning}, {team_name} batting."

        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description

        self.expects_half_inning_start = False
        self.expects_batter_up = True

    def update_batter_up(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_batter_up

        team_state = self.batting_team()
        team_state.batter_index += 1

        batter = self.batter()
        prefix = self.prefix()
        self.game_update[prefix + 'Batter'] = batter.id
        self.game_update[prefix + 'BatterName'] = batter.name
        self.game_update[prefix + 'BatterMod'] = batter.mod

        description = f"{batter.name} batting for the {team_state.nickname}."

        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description
        self.game_update[prefix + 'TeamBatterCount'] += 1

        self.expects_batter_up = False
        self.expects_pitch = True

    def update_flyout(self, feed_event: dict, game_update: Optional[dict]):
        self._update_fielding_out(feed_event, game_update)

    def update_ground_out(self, feed_event: dict, game_update: Optional[dict]):
        self._update_fielding_out(feed_event, game_update)

    def _update_fielding_out(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.fielding_out.parse(feed_event['description'])

        batter = self.batter()
        if parsed.data == 'ground_out' or parsed.data == 'flyout':
            batter_name, fielder = parsed.children
            assert any(fielder == defender.name
                       for defender in self.fielding_team().lineup)
        else:
            assert parsed.data == 'fielders_choice'
            (parsed_out, parsed_reaches) = parsed.children
            runner_out, base_name = parsed_out.children
            batter_name, = parsed_reaches.children

            base_i = self.game_update['baseRunnerNames'].index(runner_out)
            self.game_update['baseRunners'][base_i] = batter.id
            self.game_update['baseRunnerNames'][base_i] = batter.name
            self.game_update['baseRunnerMods'][base_i] = batter.mod

        assert batter_name == batter.name

        self.game_update['lastUpdate'] = feed_event['description']

        self._update_out()

    def _update_out(self):
        self.game_update['halfInningOuts'] += 1

        if (self.game_update['halfInningOuts'] >=  # I see you, Crowvertime
                self.game_update[self.prefix() + 'Outs']):
            self._end_half_inning()
        else:
            self._end_atbat()

    def _end_atbat(self):
        prefix = self.prefix()

        self.game_update[prefix + 'Batter'] = None
        self.game_update[prefix + 'BatterName'] = ''
        self.game_update[prefix + 'BatterMod'] = ''
        self.game_update['atBatBalls'] = 0
        self.game_update['atBatStrikes'] = 0

        self.expects_pitch = False
        self.expects_batter_up = True

    def _end_half_inning(self):
        self._end_atbat()

        self.game_update['baseRunners'] = []
        self.game_update['baseRunnerNames'] = []
        self.game_update['baseRunnerMods'] = []
        self.game_update['baseRunnerMods'] = []
        self.game_update['basesOccupied'] = []
        self.game_update['baserunnerCount'] = 0

        self.game_update['halfInningOuts'] = 0
        self.game_update['phase'] = 3

        self.expects_batter_up = False
        if self.game_update['topOfInning']:
            self.expects_half_inning_start = True
        else:
            self.expects_inning_end = True

    def update_ball(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        self.game_update['atBatBalls'] += 1
        self._update_count(feed_event, ["Ball"])

    def update_foul_ball(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        if (self.game_update['atBatStrikes'] + 1 <
                self.game_update[self.prefix() + 'Strikes']):
            self.game_update['atBatStrikes'] += 1

        self._update_count(feed_event, ["Foul Ball"])

    def update_strike(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        self.game_update['atBatStrikes'] += 1
        self._update_count(feed_event, ["Strike, swinging",
                                        "Strike, looking",
                                        "Strike, flinching"])

    def _update_count(self, feed_event, text_options):
        balls = self.game_update['atBatBalls']
        strikes = self.game_update['atBatStrikes']
        for text in text_options:
            description = f"{text}. {balls}-{strikes}"

            if feed_event['description'] == description:
                self.game_update['lastUpdate'] = description
                break
        else:
            assert False

    def update_hit(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.hit.parse(feed_event['description'])
        batter = self.batter()
        assert parsed.children[0] == batter.name

        self._end_atbat()

        base_reached = BASE_NUM_FOR_HIT[parsed.children[1]]

        self.game_update['lastUpdate'] = feed_event['description']
        self.game_update['baseRunners'].append(batter.id)
        self.game_update['baseRunnerNames'].append(batter.name)
        self.game_update['baseRunnerMods'].append(batter.mod)
        self.game_update['basesOccupied'].append(base_reached)
        self.game_update['baserunnerCount'] += 1


GameState.update_type = {
    0: GameState.update_lets_go,
    1: GameState.update_play_ball,
    2: GameState.update_half_inning_start,
    7: GameState.update_flyout,
    8: GameState.update_ground_out,
    10: GameState.update_hit,
    12: GameState.update_batter_up,
    13: GameState.update_strike,
    14: GameState.update_ball,
    15: GameState.update_foul_ball,
}
