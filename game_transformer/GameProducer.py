import random
import re
from copy import deepcopy
from typing import Optional, List

from game_transformer.GameRecorder import GameRecorder, PitchType, Pitch, \
    StealDecision
from game_transformer.state import PlayerState, TeamState, first_truthy

HIT_NAME = {
    0: 'Single',
    1: 'Double',
    2: 'Triple',
}

BASE_FROM_NAME = {
    'first': 0,
    'second': 1,
    'third': 2,
    'fourth': 3,
    'fifth': 3,
}

NAME_FROM_BASE = {
    0: 'first',
    1: 'second',
    2: 'third',
    3: 'fourth'
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
        try:
            time_update = next(u for u in updates if u['data']['playCount'] > 0)
        except StopIteration:
            raise RuntimeError("Couldn't get timestamp for game")
        self.game_start = time_update['timestamp']

        # Chronicler adds timestamp so I can depend on it existing
        self.home = TeamState(updates, self.game_start, 'home')
        self.away = TeamState(updates, self.game_start, 'away')

        self.active_pitch_source = None
        self.steal_sources = {}

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
            self.active_recorder = self.away_recorder
            self.inactive_recorder = self.home_recorder
        else:
            self.active_recorder = self.home_recorder
            self.inactive_recorder = self.away_recorder

        first_batter = self.batter().id
        self.batting_team().advance_batter()
        while not self.active_recorder.has_pitches_for(self.batter().id):
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
        self.active_pitch_source = self.active_recorder.pitches_for(
            self.batter().id, self.batting_team().appearance_count)

    def _pitch(self):
        did_steal = self._maybe_steal()

        if did_steal:
            return

        try:
            pitch: Pitch = next(self.active_pitch_source)
        except StopIteration:
            raise RuntimeError("Ran out of pitches")
        assert pitch.batter_id == self.batter().id

        if pitch.pitch_type == PitchType.BALL:
            self._ball()
        elif pitch.pitch_type == PitchType.FOUL:
            self._foul()
        elif pitch.pitch_type == PitchType.GROUND_OUT:
            self._fielding_out("ground out", pitch)
        elif pitch.pitch_type == PitchType.FLYOUT:
            self._fielding_out("flyout", pitch)
        elif pitch.pitch_type == PitchType.FIELDERS_CHOICE:
            self._fielders_choice(pitch)
        elif pitch.pitch_type == PitchType.DOUBLE_PLAY:
            self._double_play(pitch)
        elif pitch.pitch_type == PitchType.HIT:
            self._hit(pitch)
        elif pitch.pitch_type == PitchType.STRIKE_SWINGING:
            self._strike("swinging")
        elif pitch.pitch_type == PitchType.STRIKE_LOOKING:
            self._strike("looking")
        elif pitch.pitch_type == PitchType.HOME_RUN:
            self._home_run()
        else:
            raise RuntimeError("Unexpected pitch type")

    def _walk(self):
        self.game_update['lastUpdate'] = f"{self.batter().name} draws a walk."

        self._player_to_base(self.batter(), 0)  # no base instincts
        self._end_atbat()

    def _find_out_fielder(self, out_text, pitch):
        def description(fielder_name: str):
            # Can't match description using batter name because of haunting.
            # Also have to leave off the period because of 's shell
            return f" hit a {out_text} to {fielder_name}"

        if (pitch.pitch_type == PitchType.FIELDERS_CHOICE or
                pitch.pitch_type == PitchType.DOUBLE_PLAY):
            # This was a FC or DP converted to a normal out. Pick random fielder
            return random.choice(self.fielding_team().lineup)

        possible_fielders = [self.fielding_team().lineup[idx] for name, idx
                             in self.inactive_recorder.replacement_map.items()
                             if description(name) in pitch.original_text]

        if possible_fielders:
            return possible_fielders[0]

        possible_fielders = [f for f in self.fielding_team().lineup
                             if description(f.name) in pitch.original_text]

        if possible_fielders:
            return possible_fielders[0]

        raise RuntimeError("Couldn't find fielder")

    def _fielding_out(self, out_text: str, pitch: Pitch):
        assert self.expects_pitch

        batter = self.batter()
        fielder = self._find_out_fielder(out_text, pitch)

        self.game_update['lastUpdate'] = (
            f"{batter.name} hit a {out_text} to {fielder.name}."
        )

        self._maybe_advance_baserunners(pitch)
        self._out()

    def _eligible_for_runner_out(self, pitch: Pitch):
        # If only one out remaining, convert to ground out
        if self.game_update['halfInningOuts'] >= 2:
            return False

        # If nobody is on base, convert to ground out
        if not self.game_update['basesOccupied']:
            return False

        return True

    def _fielders_choice(self, pitch: Pitch):
        if not self._eligible_for_runner_out(pitch):
            return self._fielding_out("ground out", pitch)

        # Record the out on the out player
        player_out_index, base_name = self._find_player_out_fc(pitch)
        player_out_name = self.game_update['baseRunnerNames'][player_out_index]
        player_out_base = self.game_update['basesOccupied'][player_out_index]
        self._out(for_batter=False)
        self._remove_baserunner_by_index(player_out_index)

        if base_name is None:
            # Assume they were advancing 1 base.
            base_name = NAME_FROM_BASE[player_out_base + 1]

        # Record the hit for the batter
        self._hit(pitch)

        # Overwrite update text
        self.game_update['lastUpdate'] = (
            f"{player_out_name} out at {base_name} base.\n"
            f"{self.batter().name} reaches on fielder's choice."
        )

    def _double_play(self, pitch: Pitch):
        if not self._eligible_for_runner_out(pitch):
            return self._fielding_out("ground out", pitch)

        # Record the out on the out player
        player_out_index = self._find_player_out_dp(pitch)
        self._out(for_batter=False)
        self._remove_baserunner_by_index(player_out_index)

        # Record the out for the batter
        self._fielding_out("ground out", pitch)

        # Overwrite update text
        self.game_update['lastUpdate'] = (
            f"{self.batter().name} hit into a double play!"
        )

    def _maybe_advance_baserunners(self, pitch: Pitch):
        next_occupied_base = None
        # Iterating the list in order gets the closest-to-home runner first
        for runner_i, runner_id in enumerate(self.game_update['baseRunners']):
            base = self.game_update['basesOccupied'][runner_i]
            assert next_occupied_base is None or next_occupied_base > base

            # Figure out how much this runner wanted to advance
            try:
                advance_by = pitch.advancements[runner_id]
            except KeyError:
                advance_by = self.active_recorder.random_advancement(runner_id)

            # Prevent them from advancing to a base someone else is on
            if next_occupied_base is not None:
                advance_by = min(advance_by, next_occupied_base - 1 - base)

            # Record advancement
            assert advance_by >= 0
            self.game_update['basesOccupied'][runner_i] += advance_by
            next_occupied_base = self.game_update['basesOccupied'][runner_i]

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
        self.steal_sources = {}

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
            desc = f"{batter.name} hit a {num_runners + 1}-run home run!"

        # Score everyone directly
        runs_scored = self._score_runs(1)
        for runner_i in reversed(range(len(self.game_update['basesOccupied']))):
            self._remove_baserunner_by_index(runner_i)
            runs_scored += self._score_runs(1)
        self._record_runs(runs_scored)

        self.game_update['lastUpdate'] = desc

        self._end_atbat()

    def _hit(self, pitch: Pitch):
        # Note this function may receive a PitchType.FIELDERS_CHOICE pitch
        assert self.expects_pitch

        batter = self.batter()
        self.game_update['lastUpdate'] = (f"{batter.name} hits a "
                                          f"{HIT_NAME[pitch.base_reached]}!")

        # Everyone always advances at least the number of bases corresponding to
        # the hit
        for i, prev_base in enumerate(self.game_update['basesOccupied']):
            self.game_update['basesOccupied'][i] += pitch.base_reached + 1

        self._player_to_base(batter, pitch.base_reached)
        self._maybe_advance_baserunners(pitch)

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
        runner_id = self.game_update['baseRunners'].pop(list_index)
        self.game_update['baseRunnerNames'].pop(list_index)
        self.game_update['baseRunnerMods'].pop(list_index)
        self.game_update['basesOccupied'].pop(list_index)
        self.game_update['baserunnerCount'] -= 1

        # Don't need this steal source any more
        del self.steal_sources[runner_id]

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

        # Player can now steal! Get a source of steal decisions
        self.steal_sources[batter.id] = self.active_recorder.get_steal_source(
            batter.id, self.batting_team().appearance_count)
        # The steal source contains an extra decision (from the event where the
        # player got on base, which shouldn't have a decision but does for
        # reasons) and it's hard to fix it to not record that decision. Much
        # easier to just always discard the first decision.
        assert next(self.steal_sources[batter.id]) == StealDecision.STAY

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

    def _find_player_out_fc(self, pitch):
        # If only one baserunner, it must be them
        if len(self.game_update['baseRunners']) == 1:
            return 0, None

        match = re.search(r"out at (first|second|third|fourth|fifth) base",
                          pitch.original_text)
        assert match is not None
        out_at_base = BASE_FROM_NAME[match.group(1)]

        # If the player from the original out is on base, prefer them
        for index, name in enumerate(self.game_update['baseRunnerNames']):
            if (name + " out at ") in pitch.original_text:
                # If the base they were out at is still plausible, use it. This
                # means the base they were out at is after their current base
                # and there aren't any occupied bases in between.
                # Haha this code turned into a mess. Good luck.
                current_base = self.game_update['basesOccupied'][index]
                if out_at_base <= current_base:
                    return index, None
                for base_between in range(current_base + 1, out_at_base):
                    try:
                        between_i = \
                            self.game_update['basesOccupied'].find(base_between)
                    except ValueError:
                        # Then it's plausible; check next batter
                        continue
                    else:
                        # Only if they're going to advance past it
                        between_id = self.game_update['baseRunners'][between_i]
                        if (between_id in pitch.advancements and
                                base_between + pitch.advancements[between_id] >=
                                out_at_base):
                            # Then it's plausible; check next batter
                            continue
                    # Then it's not plausible, return None
                    return index, None
                # If I didn't return None yet, the original base is plausible
                return index, match.group(1)

        # Find whichever player can advance to whichever base the original out
        # was on. Iterates from third to first, which is forwards in the list.
        for index, base in enumerate(self.game_update['basesOccupied']):
            if base < out_at_base:
                return index, match.group(1)

        # If all else fails, default to the player farthest from scoring
        return len(self.game_update['baseRunners']) - 1, None

    def _find_player_out_dp(self, pitch):
        # If only one baserunner, it must be them
        if len(self.game_update['baseRunners']) == 1:
            return 0

        # Assume it's the farthest-from-home player who isn't in advancements.
        # Need to iterate the list backwards for this.
        for runner_i in reversed(range(len(self.game_update['baseRunners']))):
            runner_id = self.game_update['baseRunners'][runner_i]
            if runner_id not in pitch.advancements:
                return runner_i

        # If all else fails, default to the player farthest from scoring
        return len(self.game_update['baseRunners']) - 1

    def _maybe_steal(self):
        stole_base = False
        for runner_i, runner_id in enumerate(self.game_update['baseRunners']):
            try:
                decision = next(self.steal_sources[runner_id])
            except StopIteration:
                raise RuntimeError("Ran out of steals")

            # If someone already stole this turn I still have to consume the
            # decision to keep things synced but I discard it
            if stole_base:
                continue

            # Likewise if they can't steal I still have to consume the decision
            base = self.game_update['basesOccupied'][runner_i]
            if base + 1 in self.game_update['basesOccupied']:
                # Can't steal, a player is in the way
                continue

            if decision == StealDecision.STEAL:
                self._steal_base(runner_i)
                stole_base = True
            elif decision == StealDecision.CAUGHT:
                self._caught_stealing(runner_i)
                stole_base = True

        return stole_base

    def _steal_base(self, runner_i: int):
        self.game_update['basesOccupied'][runner_i] += 1
        thief_name = self.game_update['baseRunnerNames'][runner_i]
        base_name = NAME_FROM_BASE[self.game_update['basesOccupied'][runner_i]]

        self.game_update['lastUpdate'] = (
            f"{thief_name} steals {base_name} base!"
        )

    def _caught_stealing(self, runner_i: int):
        base_attempted = self.game_update['basesOccupied'][runner_i] + 1
        thief_name = self.game_update['baseRunnerNames'][runner_i]
        base_name = NAME_FROM_BASE[base_attempted]

        self._remove_baserunner_by_index(runner_i)
        self._out(for_batter=False)

        self.game_update['lastUpdate'] = (
            f"{thief_name} gets caught stealing {base_name} base."
        )
