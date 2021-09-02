import random
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto
from itertools import chain
from typing import Optional, Any, Dict, Tuple, List

from blaseball_mike.models import Player, Team
from dateutil.parser import isoparse

from game_transformer.state import TeamState, PlayerState

random.seed(0)  # For stability while testing


class PitchType(Enum):
    BALL = auto()
    STRIKE_LOOKING = auto()
    STRIKE_SWINGING = auto()
    FOUL = auto()
    SINGLE = auto()
    DOUBLE = auto()
    TRIPLE = auto()
    HOME_RUN = auto()
    FLYOUT = auto()
    GROUND_OUT = auto()
    FIELDERS_CHOICE = auto()
    DOUBLE_PLAY = auto()


@dataclass
class Pitch:
    batter_id: str
    appearance_count: int
    pitch_type: PitchType
    original_text: str


SIMPLE_PITCH_TYPES = {
    5: PitchType.BALL,  # walk -> ball
    7: PitchType.FLYOUT,
    8: PitchType.GROUND_OUT,
    9: PitchType.HOME_RUN,
    14: PitchType.BALL,
    15: PitchType.FOUL,
    27: PitchType.BALL,  # mild pitch -> ball
}
NON_PITCH_TYPES = {
    0,  # let's go
    1,  # play ball
    2,  # half inning start
    4,  # base steal
    11,  # end of game
    12,  # batter up
    20,  # solar panels runs overflow
    21,  # home field advantage
    24,  # party
    25,  # strike zapped
    26,  # weather changes
    28,  # inning becomes outing
    30,  # black hole activation
    31,  # sun2 activation
    33,  # birds circle, no unshelling
    34,  # friend of crows
    35,  # unshelling
    36,  # triple threat
    37,  # free refill
    39,  # coffee bean
    40,  # feedback swap blocked
    # 41,  # feedback swap (i need to swap the players in my data)
    45,  # superallergic reaction
    47,  # allergic reaction
    48,  # player gained Reverberating
    # 49,  # reverb wiggle (i need to swap the players in my data)
    51,  # blooddrain, normal
    52,  # blooddrain, siphon
    53,  # blooddrain, sealant
    # 54,  # incineration (i need to swap the players in my data)
    55,  # blocked incineration (fireproof/fire eater)
    62,  # baserunners swept in Flooding
    63,  # salmon
    64,  # polarity shift
    65,  # enter secret base
    66,  # exit secret base
    67,  # consumer attack
    69,  # echo chamber
    70,  # grind rail
    71,  # tunnels
    72,  # peanut mister
    73,  # peanut flavor
    74,  # taste the infinite
    76,  # event horizon activates
    77,  # event horizon awaits
    78,  # solar panels await
    79,  # solar panels activate
    84,  # return from elsewhere
    85,  # over under
    86,  # under over
    88,  # undersea
    91,  # homebody
    92,  # superyummy
    93,  # perk
    96,  # earlbird
    97,  # late to the party
    99,  # shame donor
}


def get_pitch_type(feed_event: Dict[str, Any]):
    event_type: int = feed_event['type']
    description = feed_event['description']

    if event_type in SIMPLE_PITCH_TYPES:
        return SIMPLE_PITCH_TYPES[event_type]
    elif event_type == 6:
        if " strikes out looking." in description:
            return PitchType.STRIKE_LOOKING
        elif " strikes out swinging." in description:
            return PitchType.STRIKE_SWINGING
        else:
            assert ("charmed" in description and
                    "strike out willingly" in description)
            return None  # Fill this with random pitches
    elif event_type == 10:
        if " hits a Single!" in description:
            return PitchType.SINGLE
        elif " hits a Double!" in description:
            return PitchType.DOUBLE
        elif " hits a Triple!" in description:
            return PitchType.TRIPLE
        elif " hits a Quadruple!" in description:
            # downgrades ur quadruple
            return PitchType.TRIPLE
        else:
            assert " home run!" in description or " grand slam!" in description
            return PitchType.HOME_RUN
    elif event_type == 13:
        if "Strike, swinging" in description:
            return PitchType.STRIKE_SWINGING
        else:
            assert ("Strike, looking" in description or
                    "Strike, flinching" in description)
            return PitchType.STRIKE_LOOKING
    elif event_type in NON_PITCH_TYPES:
        return None

    raise RuntimeError("Unknown event type")


class GameRecorder:
    def __init__(self, updates, prefix):
        self.prefix = prefix

        # Updates with play count 0 have the wrong timestamp
        time_update = next(u for u in updates if u['data']['playCount'] > 0)

        # Chronicler adds timestamp so I can depend on it existing
        self.team = TeamState(updates, time_update['timestamp'], prefix)

        self.pitches: List[Pitch] = []

    def record_event(self, feed_event: dict, game_event: Optional[dict]):
        update_type = feed_event['type']

        if update_type == 12:  # Batter up
            self._batter_up(feed_event)
        elif update_type == 23:  # shellsewhere
            self.team.advance_batter()
        else:
            pitch_type = get_pitch_type(feed_event)
            if pitch_type is not None:
                self.pitches.append(Pitch(
                    batter_id=self.team.batter().id,
                    appearance_count=self.team.appearance_count,
                    pitch_type=pitch_type,
                    original_text=feed_event['description']
                ))

    def _batter_up(self, feed_event: dict):
        # Figure out whether the batter actually advanced
        assert self.team.batter().name != self.team.next_batter().name

        expected_desc = (f"{self.team.next_batter().name} batting for the "
                         f"{self.team.nickname}")
        if expected_desc in feed_event['description']:
            # Regular advancement
            self.team.advance_batter()
            return

        expected_desc = (f"{self.team.batter().name} batting for the "
                         f"{self.team.nickname}")
        if expected_desc in feed_event['description']:
            # No advancement
            return

        expected_desc = f"is Inhabiting {self.team.next_batter().name}!"
        if expected_desc in feed_event['description']:
            # Regular advancement + haunting
            self.team.advance_batter()
            return

        expected_desc = f"is Inhabiting {self.team.batter().name}!"
        if expected_desc in feed_event['description']:
            # No advancement + haunting
            return

        raise RuntimeError("Who is batting?")

    def has_pitches_for(self, player_id):
        return any(pitch.batter_id == player_id for pitch in self.pitches)

    def pitches_for(self, player_id, appearance_count):
        # Make reasonable effort to avoid an infinite loop
        if not self.has_pitches_for(player_id):
            raise RuntimeError("No pitches for player")

        def pitch_filter(pitch: Pitch):
            return (pitch.batter_id == player_id and
                    pitch.appearance_count == appearance_count)

        appearance_pitches = filter(pitch_filter, self.pitches)

        def random_pitches():
            player_pitches = [pitch for pitch in self.pitches
                              if pitch.batter_id == player_id]
            while True:
                yield random.choice(player_pitches)

        # Return pitches from this appearance until they are exhausted, then
        # return random pitches from this batter during this game
        return chain(appearance_pitches, random_pitches())

    def reload_lineup(self, feed_event: dict):
        timestamp = isoparse(feed_event['created']) + timedelta(seconds=180)
        team = Team.load_at_time(self.team.id, timestamp)

        self.team.lineup = [PlayerState.from_player(p) for p in team.lineup]

    def replace_player(self, feed_event: dict):
        a_id, b_id = feed_event['playerTags']

        def get_replacement(player_id):
            timestamp = isoparse(feed_event['created']) + timedelta(seconds=180)
            player = Player.load_one_at_time(player_id, timestamp)
            return PlayerState.from_player(player)

        # Try both orders. This matters for feedback.
        for victim_id, replacement_id in [(a_id, b_id), (b_id, a_id)]:
            if self.team.pitcher.id == victim_id:
                self.team.pitcher = get_replacement(replacement_id)
                return  # gotta early return or it might un-swap
            try:
                idx = [p.id for p in self.team.lineup].index(victim_id)
            except ValueError:
                pass  # must have been the other team
            else:
                self.team.lineup[idx] = get_replacement(replacement_id)
                return  # gotta early return or it might un-swap
