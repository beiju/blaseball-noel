from dataclasses import dataclass
from functools import partial
from itertools import chain
from typing import Dict, Callable, Optional, List, Set
from blaseball_mike.models import Team, Player
import logging

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

PITCHER_MOD_ORDER = ['COFFEE_RALLY']
BATTER_MOD_ORDER = ['COFFEE_RALLY']
BASERUNNER_MOD_ORDER = ['BLASERUNNING', 'COFFEE_RALLY']


@dataclass
class PlayerState:
    id: str
    name: str
    mods: Set[str]
    legacy_item: Optional[str]

    @classmethod
    def from_player(cls, player: Player):
        legacy_item = None
        if player.bat.id:  # `bat` is truthy even if player doesn't have one
            legacy_item = player.bat.name

        return PlayerState(id=player.id,
                           name=player.name,
                           mods=set(mods_for_player(player)),
                           legacy_item=legacy_item)


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
            mods={update['data'][prefix + 'PitcherMod'] for update in updates
                  if update['data'][prefix + 'PitcherMod'] != ''},
            # Pitchers may have legacy items but they're never displayed
            legacy_item='')
        assert self.pitcher.id
        assert self.pitcher.name

        self.lineup = [PlayerState.from_player(p) for p in team.lineup]

        self.batter_index = -1

    def advance_batter(self):
        self.batter_index += 1
        if self.batter_index >= len(self.lineup):
            self.batter_index = 0


def first_truthy(updates, key):
    for update in updates:
        if update['data'][key]:
            return update['data'][key]


def mods_for_player(player):
    for mod in chain(player.perm_attr, player.seas_attr,
                     player.game_attr, player.item_attr):
        yield mod.id

    # Yield mod from legacy items
    if player.bat.attr:
        yield player.bat.attr.id


def show_mod_from_list(mod_list: List[str], player: PlayerState):
    for mod in mod_list:
        if mod in player.mods:
            return mod
    return ''


show_pitcher_mod = partial(show_mod_from_list, PITCHER_MOD_ORDER)
show_batter_mod = partial(show_mod_from_list, BATTER_MOD_ORDER)
show_runner_mod = partial(show_mod_from_list, BASERUNNER_MOD_ORDER)


class GameState:
    UpdateFunction = Callable[['GameState', dict, Optional[dict]], dict]
    update_type: Dict[int, UpdateFunction] = {}

    def __init__(self, updates: List[dict]):
        self.log = logging.getLogger("TEST")
        self.expects_lets_go = True
        self.expects_play_ball = False
        self.expects_half_inning_start = False
        self.expects_batter_up = False
        self.expects_pitch = False
        self.expects_inning_end = False
        self.expects_game_end = False

        # Chronicler adds timestamp so I can depend on it existing
        self.away = TeamState(updates, updates[0]['timestamp'], 'away')
        self.home = TeamState(updates, updates[0]['timestamp'], 'home')
        self.haunter = None

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

    def prefix(self, negate=False):
        if self.game_update['topOfInning'] != negate:
            return 'away'
        else:
            return 'home'

    def top_or_bottom(self, negate=False):
        if self.game_update['topOfInning'] != negate:
            return 'top'
        else:
            return 'bottom'

    def batter(self) -> PlayerState:
        if self.haunter:
            return self.haunter
        team_state = self.batting_team()
        return team_state.lineup[team_state.batter_index]

    def batting_team(self) -> TeamState:
        return self.away if self.game_update['topOfInning'] else self.home

    def fielding_team(self) -> TeamState:
        return self.home if self.game_update['topOfInning'] else self.away

    def update(self, feed_event, game_update):
        print("type", f"{feed_event['type']},".ljust(4),
              feed_event['description'].replace("\n", "\n          "))

        # Always reset this, since scores are rare
        self.game_update['scoreUpdate'] = ""
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
        self.game_update['awayPitcherMod'] = show_pitcher_mod(self.away.pitcher)
        self.game_update['awayTeamBatterCount'] = -1
        self.game_update['homePitcher'] = self.home.pitcher.id
        self.game_update['homePitcherName'] = self.home.pitcher.name
        self.game_update['homePitcherMod'] = show_pitcher_mod(self.home.pitcher)
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
        if not self.game_update['topOfInning']:
            # I am just copying observed behavior here. No idea what it means.
            if self.game_update['inning'] == -1:
                self.game_update['gameStartPhase'] = 10
            else:
                self.game_update['gameStartPhase'] += 1

            self.game_update['inning'] += 1

        self.game_update['topOfInning'] = not self.game_update['topOfInning']
        self.game_update['halfInningScore'] = 0

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

        parsed = Parsers.batter_up.parse(feed_event['description'])

        team_state = self.batting_team()
        team_state.advance_batter()

        if parsed.children[0].data == 'inhabiting':
            haunter_name, haunted_name = parsed.children[0].children
            haunter = Player.load_one_at_time(feed_event['playerTags'][0],
                                              feed_event['created'])
            assert haunter_name == haunter.name
            assert haunted_name == self.batter().name
            self.haunter = PlayerState.from_player(haunter)
            parsed.children.pop(0)

        parsed_batter_up, *parsed_rest = parsed.children
        parsed_batter_name, parsed_team_name = parsed_batter_up.children
        batter = self.batter()

        assert team_state.nickname == parsed_team_name
        assert batter.name == parsed_batter_name

        for parsed_item in parsed_rest:
            assert parsed_item.data == 'wielding'
            parsed_bat, = parsed_item.children

            assert parsed_bat == batter.legacy_item

        prefix = self.prefix()
        self.game_update[prefix + 'Batter'] = batter.id
        self.game_update[prefix + 'BatterName'] = batter.name
        self.game_update[prefix + 'BatterMod'] = show_batter_mod(batter)

        self.game_update['lastUpdate'] = feed_event['description']
        self.game_update[prefix + 'TeamBatterCount'] += 1

        self.expects_batter_up = False
        self.expects_pitch = True

    def update_base_steal(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.steal.parse(feed_event['description'])
        parsed_steal, *parsed_extras = parsed.children
        assert parsed_steal.data in {'stolen_base', 'caught_stealing'}
        stealer_name, base_name = parsed_steal.children
        base_stolen = BASE_NUM_FOR_NAME[base_name]
        # Find the baserunner who is one before the base they tried to
        # steal. You can't steal to any other base (with this event type)
        stealer_idx = self.game_update['basesOccupied'].index(base_stolen - 1)
        assert self.game_update['baseRunnerNames'][stealer_idx] == stealer_name

        runs_scored = 0
        if parsed_steal.data == 'stolen_base':
            # Must do this before advancing baserunners or the indices are off
            self.game_update['basesOccupied'][stealer_idx] += 1
            expects_extras = False

            if parsed_extras and parsed_extras[0].data == 'blaserunning':
                parsed_blaserunning = parsed_extras.pop(0)
                parsed_blaserunner_name, = parsed_blaserunning.children
                assert stealer_name == parsed_blaserunner_name
                runs_scored += self._score_runs(0.2)
                expects_extras = True

            if base_stolen + 1 == self.game_update[self.prefix() + 'Bases']:
                runs_scored += self._score_player(stealer_name)
                expects_extras = True

            if expects_extras:
                self._apply_scoring_extras(parsed_extras, stealer_name)
            else:
                assert len(parsed_extras) == 0
        else:
            assert parsed_steal.data == 'caught_stealing'

            self._remove_baserunner_by_index(stealer_idx)
            self._update_out(for_batter=False)

        self._record_runs(runs_scored)
        self.game_update['lastUpdate'] = feed_event['description']

    def update_walk(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        batter = self.batter()
        description = batter.name + " draws a walk."

        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description

        self._update_walk_generic(batter)

    def _update_walk_generic(self, batter):
        self._player_to_base(batter, 0)  # Until the Beams get here
        self._end_atbat()

    def update_strikeout(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        batter = self.batter()
        for kind in ['swinging', 'looking']:
            description = f"{batter.name} strikes out {kind}."

            if description == feed_event['description']:
                self.game_update['lastUpdate'] = description
                break
        else:
            assert False

        self._update_out()

    def update_flyout(self, feed_event: dict, game_update: Optional[dict]):
        self._update_fielding_out(feed_event, game_update)

    def update_ground_out(self, feed_event: dict, game_update: Optional[dict]):
        self._update_fielding_out(feed_event, game_update)

    def _update_fielding_out(self, feed_event: dict,
                             game_update: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.fielding_out.parse(feed_event['description'])

        batter = self.batter()
        if parsed.data == 'ground_out_full' or parsed.data == 'flyout_full':
            parsed_out, *parsed_scores = parsed.children
            batter_name, fielder = parsed_out.children
            assert any(fielder == defender.name
                       for defender in self.fielding_team().lineup)
        elif parsed.data == 'double_play_full':
            parsed_out, *parsed_scores = parsed.children
            batter_name, = parsed_out.children

            # The first out of a double play can't be the out that ends the
            # inning... right?
            self.game_update['halfInningOuts'] += 1
            assert (self.game_update['halfInningOuts'] <
                    self.game_update[self.prefix() + 'Outs'])

            # Need to update scoring players early so we can tell who got out
            self._update_scores(parsed_scores)
            parsed_scores = []

            # Have to figure out which baserunner gets out. I suppose you could
            # deduce it sometimes from future events but for now I require the
            # game update
            assert game_update is not None
            set_diff = (set(self.game_update['baseRunners']) -
                        set(game_update['baseRunners']))
            assert len(set_diff) == 1
            batter_out_id = set_diff.pop()
            batter_out_i = self.game_update['baseRunners'].index(batter_out_id)
            self._remove_baserunner_by_index(batter_out_i)
        else:
            assert parsed.data == 'fielders_choice'
            (parsed_out, *parsed_scores, parsed_reaches) = parsed.children
            runner_out, base_name = parsed_out.children
            batter_name, = parsed_reaches.children

            base_i = self.game_update['baseRunnerNames'].index(runner_out)
            self.game_update['baseRunners'][base_i] = batter.id
            self.game_update['baseRunnerNames'][base_i] = batter.name
            self.game_update['baseRunnerMods'][base_i] = show_runner_mod(batter)

        assert batter_name == batter.name

        self._update_scores(parsed_scores)
        self.game_update['lastUpdate'] = feed_event['description']

        self._update_out()
        # This must be last or it errors when this event ends the half-inning
        self._maybe_advance_baserunners(game_update)

    def _maybe_advance_baserunners(self, game_update):
        # Baserunner advancement on outs/hits is one of the few things that
        # can't be reconstructed from the feed. Just copy it over if we can.
        if game_update is not None:
            assert (len(self.game_update['basesOccupied']) ==
                    len(game_update['basesOccupied']))
            self.game_update['basesOccupied'] = game_update['basesOccupied']

    def _update_out(self, for_batter=True):
        self.game_update['halfInningOuts'] += 1

        if (self.game_update['halfInningOuts'] >=  # I see you, Crowvertime
                self.game_update[self.prefix() + 'Outs']):
            self._end_half_inning()
        elif for_batter:
            # Only end the at bat if the out belongs to the runner. Which it
            # usually does, but not for e.g. caught stealing.
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

        self.haunter = None

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
        if self.top_or_bottom() == 'bottom':
            self.game_update['topInningScore'] = 0
            self.game_update['bottomInningScore'] = 0
            self.game_update['halfInningScore'] = 0

        self.expects_batter_up = False
        if (self.game_update['inning'] >= 8 and
                self.game_update[self.prefix() + 'Score'] <
                self.game_update[self.prefix(negate=True) + 'Score']):
            # Game ends if inning number is at least 9 (1-indexed) and currently
            # batting team is losing
            return self._end_game()
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

    def update_strike_zapped(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        description = "The Electricity zaps a strike away!"
        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description

        assert self.game_update['atBatStrikes'] > 0
        self.game_update['atBatStrikes'] -= 1

    def update_mild_pitch(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.mild_pitch.parse(feed_event['description'])
        (mild_pitch, parsed_pitch, *parsed_rest) = parsed.children

        assert mild_pitch.data == 'mild_pitch'
        mild_pitcher_name, = mild_pitch.children
        assert mild_pitcher_name == self.fielding_team().pitcher.name

        if parsed_pitch.data == 'ball':
            parsed_balls, parsed_strikes = parsed_pitch.children
            self.game_update['atBatBalls'] += 1
            assert self.game_update['atBatBalls'] == int(parsed_balls)
            assert self.game_update['atBatStrikes'] == int(parsed_strikes)
        else:
            assert parsed_pitch.data == 'walk'
            parsed_walker, = parsed_pitch.children
            batter = self.batter()
            assert parsed_walker == batter.name
            self._update_walk_generic(batter)

        # Everything else should be a score
        self._update_scores(parsed_rest)

        self.game_update['lastUpdate'] = feed_event['description']

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

    def update_home_run(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_pitch

        batter = self.batter()

        runs_scored = self._score_runs(1)
        while self.game_update['baserunnerCount'] > 0:
            self._remove_baserunner_by_index(0)
            runs_scored += self._score_runs(1)

        run_desc = "solo" if runs_scored == 1 else f"{runs_scored}-run"
        description = f"{batter.name} hits a {run_desc} home run!"

        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description

        self._record_runs(runs_scored)
        self._end_atbat()

    def update_hit(self, feed_event: dict, game_update: Optional[dict]):
        assert self.expects_pitch

        parsed = Parsers.hit.parse(feed_event['description'])
        (parsed_hit, *parsed_rest) = parsed.children
        batter_name, base_name = parsed_hit.children

        batter = self.batter()
        assert batter_name == batter.name

        self._update_scores(parsed_rest)

        self.game_update['lastUpdate'] = feed_event['description']
        self._player_to_base(batter, BASE_NUM_FOR_HIT[base_name])
        self._end_atbat()
        # This must be last or it errors when this event ends the half-inning
        self._maybe_advance_baserunners(game_update)

    def _update_scores(self, parsed_rest):
        runs_scored = 0
        for parsed_item in parsed_rest:
            assert parsed_item.data in {'score', 'sacrifice'}

            scoring_player_name, *parsed_extras = parsed_item.children
            runs_scored += self._score_player(scoring_player_name)

            self._apply_scoring_extras(parsed_extras, scoring_player_name)
        self._record_runs(runs_scored)

    def _apply_scoring_extras(self, parsed_extras, scoring_player_name):
        for parsed_sub_item in parsed_extras:
            assert parsed_sub_item.data == 'use_free_refill'
            parsed_name, parsed_name2 = parsed_sub_item.children
            assert parsed_name == parsed_name2
            # Free refill can be used by the runner or the scoring player or, if
            # the stars align, the pitcher
            assert (parsed_name == scoring_player_name or
                    parsed_name == self.fielding_team().pitcher.name or
                    parsed_name == self.batter().name)

            self.game_update['halfInningOuts'] -= 1

            # Need to clear mod from the scoring player
            if (self.fielding_team().pitcher.name == parsed_name and
                    'COFFEE_RALLY' in self.fielding_team().pitcher.mods):
                self.fielding_team().pitcher.mods.remove('COFFEE_RALLY')
                self.game_update[self.prefix(negate=True) + 'PitcherMod'] = \
                    show_pitcher_mod(self.fielding_team().pitcher)
            else:
                possible_refillers = [p for p in self.batting_team().lineup
                                      if (p.name == parsed_name and
                                          'COFFEE_RALLY' in p.mods)]

                # If this assertion fails it's because there are two players
                # with the same name and I need to figure out which one used
                # their free refill
                assert len(possible_refillers) == 1

                # This throws if it's not in the set, which is what we want
                refiller = possible_refillers[0]
                refiller.mods.remove('COFFEE_RALLY')

                # Clear from this player if they're the batter
                if self.batter().id == refiller.id:
                    self.game_update[self.prefix() + 'BatterMod'] = \
                        show_batter_mod(refiller)

                # Clear from any instances of this player who are on base
                for runner_i, runner_id in \
                        enumerate(self.game_update['baseRunners']):
                    if runner_id == refiller.id:
                        self.game_update['baseRunnerMods'][runner_i] = \
                            show_runner_mod(refiller)

    def update_game_score(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_game_end

        away_text = f"{self.away.nickname} {self.game_update['awayScore']}"
        home_text = f"{self.home.nickname} {self.game_update['homeScore']}"
        if self.game_update['homeScore'] > self.game_update['awayScore']:
            description = f"{home_text}, {away_text}"
        else:
            description = f"{away_text}, {home_text}"

        assert description == feed_event['description']
        self.game_update['lastUpdate'] = description

        self.game_update['finalized'] = True
        self.game_update['gameComplete'] = True

    def _record_runs(self, runs_scored):
        if runs_scored == 1:
            self.game_update['scoreUpdate'] = f"1 Run scored!"
        elif runs_scored != 0:
            self.game_update['scoreUpdate'] = f"{runs_scored} Runs scored!"

    def _score_player(self, scoring_player_name):
        # I thought you could assume the scoring player was the 0th, but nope!
        # https://reblase.sibr.dev/game/259150c5-e086-4d6c-b2da-80b576885059
        #   #e6d37189-3fff-95b2-a542-1266836a1f64
        index = self.game_update['baseRunnerNames'].index(scoring_player_name)

        self._remove_baserunner_by_index(index)
        return self._score_runs(1)

    def _remove_baserunner_by_index(self, list_index):
        self.game_update['baseRunners'].pop(list_index)
        self.game_update['baseRunnerNames'].pop(list_index)
        self.game_update['baseRunnerMods'].pop(list_index)
        self.game_update['basesOccupied'].pop(list_index)
        self.game_update['baserunnerCount'] -= 1

    def _score_runs(self, runs: float):
        self.game_update[self.prefix() + 'Score'] += runs
        self.game_update['halfInningScore'] += runs
        self.game_update[self.top_or_bottom() + 'InningScore'] += runs

        return runs

    def _player_to_base(self, batter: PlayerState, base_num: int):
        self._advance_baserunners_past_base(base_num)

        self.game_update['baseRunners'].append(batter.id)
        self.game_update['baseRunnerNames'].append(batter.name)
        self.game_update['baseRunnerMods'].append(show_runner_mod(batter))
        self.game_update['basesOccupied'].append(base_num)
        self.game_update['baserunnerCount'] += 1

    def update_inning_end(self, feed_event: dict, _: Optional[dict]):
        assert self.expects_inning_end

        inning = self.game_update['inning'] + 1
        description = f"Inning {inning} is now an Outing."

        assert feed_event['description'] == description
        self.game_update['lastUpdate'] = description
        self.game_update['phase'] = 2

        self.expects_inning_end = False
        self.expects_half_inning_start = True

    def _advance_baserunners_past_base(self, past_base):
        # Doing truly TDD stuff here. Implementations that will work exactly on
        # the test cases provided and not the general case.
        occupied = self.game_update['basesOccupied']
        if not occupied:
            return []
        elif len(occupied) == 1:
            if occupied[0] <= past_base:
                occupied[0] = past_base + 1

    def _end_game(self):
        self.game_update['topInningScore'] = 0
        self.game_update['bottomInningScore'] = 0
        self.game_update['halfInningScore'] = 0
        self.game_update['phase'] = 7

        self.expects_pitch = False
        self.expects_game_end = True

    def update_flavor_text(self, feed_event: dict, _: Optional[dict]):
        # I don't know if this only happens in place of a pitch, but we'll see!
        assert self.expects_pitch

        # There is nothing to do but copy over the description
        self.game_update['lastUpdate'] = feed_event['description']


GameState.update_type = {
    0: GameState.update_lets_go,
    1: GameState.update_play_ball,
    2: GameState.update_half_inning_start,
    4: GameState.update_base_steal,
    5: GameState.update_walk,
    6: GameState.update_strikeout,
    7: GameState.update_flyout,
    8: GameState.update_ground_out,
    9: GameState.update_home_run,
    10: GameState.update_hit,
    11: GameState.update_game_score,
    12: GameState.update_batter_up,
    13: GameState.update_strike,
    14: GameState.update_ball,
    15: GameState.update_foul_ball,
    25: GameState.update_strike_zapped,
    27: GameState.update_mild_pitch,
    28: GameState.update_inning_end,
    73: GameState.update_flavor_text,
}
