import random
from copy import deepcopy
from typing import Optional, List

from game_transformer.GameRecorder import GameRecorder, PitchType, Pitch
from game_transformer.state import PlayerState, TeamState, first_truthy

HIT_NAME = {
    0: 'Single',
    1: 'Double',
    2: 'Triple',
}


class GameProducer:
    def __init__(self, updates: List[dict], home_recorder: GameRecorder,
                 away_recorder: GameRecorder):
        self.updates = updates
        self.home_recorder = home_recorder
        self.away_recorder = away_recorder

        self.expects_lets_go = True
        self.expects_play_ball = False
        self.expects_half_inning_start = False
        self.expects_batter_up = False
        self.expects_pitch = False
        self.expects_inning_end = False
        self.expects_game_end = False

        # Updates with play count 0 have the wrong timestamp
        time_update = next(u for u in updates if u['data']['playCount'] > 0)
        self.game_start = time_update['timestamp']

        # Chronicler adds timestamp so I can depend on it existing
        self.home = TeamState(updates, self.game_start, 'home')
        self.away = TeamState(updates, self.game_start, 'away')

        self.active_pitch_source = None

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
        team_state = self.batting_team()
        return team_state.lineup[team_state.batter_index]

    def batting_team(self) -> TeamState:
        return self.away if self.game_update['topOfInning'] else self.home

    def fielding_team(self) -> TeamState:
        return self.home if self.game_update['topOfInning'] else self.away

    def __iter__(self):
        return self

    def __next__(self):
        return_val = None
        if self.expects_lets_go:
            self._lets_go()
        elif self.expects_play_ball:
            return_val = deepcopy(self._play_ball())
        elif self.expects_half_inning_start:
            self._half_inning_start()
        elif self.expects_batter_up:
            self._batter_up()
        elif self.expects_pitch:
            self._pitch()
        elif self.expects_inning_end:
            self._inning_end()
        elif self.expects_game_end:
            self._game_end()
        elif self.game_update['finalized']:
            raise StopIteration()
        else:
            raise RuntimeError("Unexpected state in GameProducer")

        self._update_scores()
        self.game_update['playCount'] += 1
        # one thousand plays ought to be enough for anyone
        assert self.game_update['playCount'] < 1_000

        if return_val is None:
            return_val = deepcopy(self.game_update)

        # Reset stuff that should be reset every game update
        self.game_update['scoreUpdate'] = ""
        self.game_update['scoreLedger'] = ""

        return return_val

    def _lets_go(self):
        self.expects_lets_go = False
        self.expects_play_ball = True

        self.game_update['lastUpdate'] = "Let's Go!"
        self.game_update['gameStart'] = True
        self.game_update['phase'] = 1
        self.game_update['awayPitcher'] = self.away.pitcher.id
        self.game_update['awayPitcherName'] = self.away.pitcher.name
        self.game_update['awayTeamBatterCount'] = -1
        self.game_update['homePitcher'] = self.home.pitcher.id
        self.game_update['homePitcherName'] = self.home.pitcher.name
        self.game_update['homeTeamBatterCount'] = -1

    def _play_ball(self):
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

    def _half_inning_start(self):
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

        self.game_update['lastUpdate'] = description

        self.expects_half_inning_start = False
        self.expects_batter_up = True

    def _batter_up(self):
        assert self.expects_batter_up
        if self.game_update['topOfInning']:
            recorder = self.away_recorder
        else:
            recorder = self.home_recorder

        first_batter = self.batter().id
        self.batting_team().advance_batter()
        while not recorder.has_pitches_for(self.batter().id):
            self.batting_team().advance_batter()
            # Prevent infinite loop
            assert self.batter() != first_batter

        batter = self.batter()
        prefix = self.prefix()
        self.game_update[prefix + 'Batter'] = batter.id
        self.game_update[prefix + 'BatterName'] = batter.name

        self.game_update['lastUpdate'] = (f"{batter.name} batting for the "
                                          f"{self.batting_team().nickname}.")
        self.game_update[prefix + 'TeamBatterCount'] += 1

        self.expects_batter_up = False
        self.expects_pitch = True

        # Set up pitch source
        self.active_pitch_source = recorder.pitches_for(
            self.batter().id, self.batting_team().appearance_count)

    def _pitch(self):
        pitch: Pitch = next(self.active_pitch_source)
        assert pitch.batter_id == self.batter().id

        if pitch.pitch_type == PitchType.BALL:
            self._ball()
        elif pitch.pitch_type == PitchType.FOUL:
            self._foul()
        elif pitch.pitch_type == PitchType.GROUND_OUT:
            self._fielding_out("ground out", pitch.original_text)
        elif pitch.pitch_type == PitchType.FLYOUT:
            self._fielding_out("flyout", pitch.original_text)
        elif pitch.pitch_type == PitchType.SINGLE:
            self._hit(0)
        elif pitch.pitch_type == PitchType.DOUBLE:
            self._hit(1)
        elif pitch.pitch_type == PitchType.TRIPLE:
            self._hit(2)
        elif pitch.pitch_type == PitchType.STRIKE_SWINGING:
            self._strike("swinging")
        elif pitch.pitch_type == PitchType.STRIKE_LOOKING:
            self._strike("looking")
        elif pitch.pitch_type == PitchType.HOME_RUN:
            self._home_run()
        else:
            breakpoint()

    def update_base_steal(self, feed_event: dict, game_update: Optional[dict]):
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
                self._apply_scoring_extras(parsed_extras)
            else:
                assert len(parsed_extras) == 0
        else:
            assert parsed_steal.data == 'caught_stealing'

            self._remove_baserunner_by_index(stealer_idx)
            self._out(game_update, for_batter=False)

        self._record_runs(runs_scored)
        self.game_update['lastUpdate'] = feed_event['description']

    def _walk(self):
        self.game_update['lastUpdate'] = f"{self.batter().name} draws a walk."

        self._player_to_base(self.batter(), 0)  # no base instincts
        self._end_atbat()

    def _fielding_out(self, out_text: str, original_description: str):
        assert self.expects_pitch

        def description(fielder: PlayerState):
            return f"{batter.name} hit a {out_text} to {fielder.name}."

        batter = self.batter()
        # Find the fielder
        fielder = next(fielder for fielder in self.fielding_team().lineup
                       if description(fielder) in original_description)

        self.game_update['lastUpdate'] = description(fielder)

        self._maybe_advance_baserunners()
        self._out()

    def _maybe_advance_baserunners(self):
        next_occupied_base = None
        for runner_i in range(len(self.game_update['baseRunners'])):
            base = self.game_update['basesOccupied'][runner_i]
            assert next_occupied_base is None or next_occupied_base > base
            if next_occupied_base is None or base + 1 < next_occupied_base:
                # TODO: Hook up a decision source
                if random.random() > 0.5:
                    self.game_update['basesOccupied'][runner_i] += 1

    def _out(self, for_batter=True):
        self.game_update['halfInningOuts'] += 1

        if self.game_update['halfInningOuts'] >= 3:  # no maintenance mode
            self._end_half_inning(for_batter)
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

    def _end_half_inning(self, for_batter=True):
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

        # If the half ends and it wasn't the batter's out, the batter count is
        # decreased because I guess the at bat doesn't count. This is observably
        # different from not incrementing the count when the next at-bat starts
        if not for_batter:
            self.game_update[self.prefix() + 'TeamBatterCount'] -= 1
            # Next time a batter comes up, call the same one
            self.batting_team().batter_index -= 1

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

    def _ball(self):
        self.game_update['atBatBalls'] += 1

        if self.game_update['atBatBalls'] >= 4:  # no walks in any parks
            self._walk()
        else:
            self._output_count_description("Ball")

    def _foul(self):
        if self.game_update['atBatStrikes'] < 2:
            self.game_update['atBatStrikes'] += 1

        self._output_count_description("Foul Ball")

    def _strike(self, kind: str):
        self.game_update['atBatStrikes'] += 1

        if self.game_update['atBatStrikes'] >= 3:  # 3 strikes only
            description = f"{self.batter().name} strikes out {kind}"
            self.game_update['lastUpdate'] = description
            self._out()
        else:
            self._output_count_description("Strike, " + kind)

    def _output_count_description(self, text):
        balls = self.game_update['atBatBalls']
        strikes = self.game_update['atBatStrikes']
        description = f"{text}. {balls}-{strikes}"
        self.game_update['lastUpdate'] = description

    def _home_run(self):
        batter = self.batter()
        num_runners = len(self.game_update['baseRunners'])

        if num_runners == 0:
            desc = f"{batter.name} hit a solo home run!"
        elif num_runners == 3:
            desc = f"{batter.name} hit a grand slam!"
        else:
            desc = f"{batter.name} hit a {num_runners}-run home run!"

        # Yeet the batter straight to 4th. This pushes everyone else into
        # scoring range
        self._player_to_base(batter, 3)
        # Score runners now so I can override the description
        self._update_scores()

        # Set description after updating scores to override scorer names
        self.game_update['lastUpdate'] = desc

        self._end_atbat()

    def _hit(self, to_base: int):
        assert self.expects_pitch

        batter = self.batter()
        self.game_update['lastUpdate'] = (f"{batter.name} hit a "
                                          f"{HIT_NAME[to_base]}!")

        self._player_to_base(batter, to_base)
        self._maybe_advance_baserunners()

        self._end_atbat()

    def _update_scores(self):
        runs_scored = 0
        for runner_i in reversed(range(len(self.game_update['basesOccupied']))):
            if self.game_update['basesOccupied'][runner_i] < 3:  # no fifth base
                continue

            player_name = self.game_update['baseRunnerNames'][runner_i]
            self.game_update['lastUpdate'] += f"\n{player_name} scores!"

            self._remove_baserunner_by_index(runner_i)
            runs_scored += self._score_runs(1)
        self._record_runs(runs_scored)

    def _game_end(self):
        assert self.expects_game_end

        away_text = f"{self.away.nickname} {self.game_update['awayScore']}"
        home_text = f"{self.home.nickname} {self.game_update['homeScore']}"
        if self.game_update['homeScore'] > self.game_update['awayScore']:
            self.game_update['lastUpdate'] = f"{home_text}, {away_text}"
        else:
            self.game_update['lastUpdate'] = f"{away_text}, {home_text}"

        self.game_update['finalized'] = True
        self.game_update['gameComplete'] = True

        self.expects_game_end = False

    def _record_runs(self, runs_scored):
        if runs_scored == 1:
            self.game_update['scoreUpdate'] = f"1 Run scored!"
        elif runs_scored != 0:
            self.game_update['scoreUpdate'] = f"{runs_scored} Runs scored!"

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
        # First just shove the player on the base
        self.game_update['baseRunners'].append(batter.id)
        self.game_update['baseRunnerNames'].append(batter.name)
        self.game_update['baseRunnerMods'].append('')  # no mods
        self.game_update['basesOccupied'].append(base_num)
        self.game_update['baserunnerCount'] += 1

        # Then go through the bases, advancing baserunners as needed to keep
        # them in the proper order
        highest_occupied_base = -1
        for runner_i in reversed(range(len(self.game_update['basesOccupied']))):
            # If the runner on or before the highest occupied base, advance them
            # to the base after the highest occupied base
            if (self.game_update['basesOccupied'][runner_i] <=
                    highest_occupied_base):
                next_base = highest_occupied_base + 1
                self.game_update['basesOccupied'][runner_i] = next_base
            highest_occupied_base = self.game_update['basesOccupied'][runner_i]

        # Scoring players is handled centrally as the last step of a pitch

    def _inning_end(self):
        assert self.expects_inning_end

        inning = self.game_update['inning'] + 1
        self.game_update['lastUpdate'] = f"Inning {inning} is now an Outing."
        self.game_update['phase'] = 2

        self.expects_inning_end = False
        self.expects_half_inning_start = True

    def _end_game(self):
        self.game_update['topInningScore'] = 0
        self.game_update['bottomInningScore'] = 0
        self.game_update['halfInningScore'] = 0
        self.game_update['phase'] = 7

        self.expects_pitch = False
        self.expects_game_end = True
