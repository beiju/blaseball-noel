import random
from dataclasses import dataclass
from enum import Enum, auto
from itertools import chain
from typing import Optional, Any, Dict, Tuple, List

from game_transformer.state import TeamState


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


SIMPLE_PITCH_TYPES = {
    5: PitchType.BALL,  # walk -> ball
    7: PitchType.FLYOUT,
    8: PitchType.GROUND_OUT,
    9: PitchType.HOME_RUN,
    14: PitchType.BALL,
    15: PitchType.FOUL,
}
NON_PITCH_TYPES = {
    0,  # let's go
    1,  # play ball
    2,  # half inning start
    4,  # base steal
    11,  # end of game
    12,  # batter up
    25,  # strike zapped
    28,  # inning becomes outing
    52,  # blooddrain
    73,  # peanut flavor
    92,  # superyummy
}

JsonDict = Dict[str, Any]
EventData = Tuple[JsonDict, Optional[JsonDict]]


def get_pitch_type(feed_event: Dict[str, Any]):
    event_type: int = feed_event['type']
    description = feed_event['description']

    if event_type in SIMPLE_PITCH_TYPES:
        return SIMPLE_PITCH_TYPES[event_type]
    elif event_type == 6:
        if " strikes out looking." in description:
            return PitchType.STRIKE_LOOKING
        else:
            assert " strikes out swinging." in description
            return PitchType.STRIKE_SWINGING
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

    raise RuntimeError("Unknown pitch type")


class GameRecorder:
    def __init__(self, updates, prefix):
        # Updates with play count 0 have the wrong timestamp
        time_update = next(u for u in updates if u['data']['playCount'] > 0)

        # Chronicler adds timestamp so I can depend on it existing
        self.team = TeamState(updates, time_update['timestamp'], prefix)

        self.current_atbat: List[EventData] = []

        self.pitches: List[Pitch] = []

    def record_event(self, feed_event: dict, game_event: Optional[dict]):
        update_type = feed_event['type']

        if update_type == 12:  # Batter up
            self._batter_up(feed_event)
        else:
            pitch_type = get_pitch_type(feed_event)
            if pitch_type is not None:
                self.pitches.append(Pitch(
                    batter_id=self.team.batter().id,
                    appearance_count=self.team.appearance_count,
                    pitch_type=pitch_type
                ))

    def _batter_up(self, feed_event: dict):
        # Figure out whether the batter actually advanced
        assert self.team.batter().name != self.team.next_batter().name

        expected_desc = (f"{self.team.batter().name} batting for the "
                         f"{self.team.nickname}.")
        if feed_event['description'] == expected_desc:
            # No advancement
            return

        expected_desc = (f"{self.team.next_batter().name} batting for the "
                         f"{self.team.nickname}.")
        if feed_event['description'] == expected_desc:
            # Regular advancement
            self.team.advance_batter()
            return

        raise RuntimeError("Who is batting?")

    def pitches_for(self, player_id, appearance_count):
        # Make reasonable effort to avoid an infinite loop
        if not any(pitch.batter_id == player_id for pitch in self.pitches):
            raise RuntimeError("No pitches for player")

        def pitch_filter(pitch: Pitch):
            return (pitch.batter_id == player_id and
                    pitch.appearance_count == appearance_count)

        appearance_pitches = filter(pitch_filter, self.pitches)

        def random_pitches():
            while True:
                pitch = random.choice(self.pitches)
                if pitch.batter_id == player_id:
                    yield pitch

        # Return pitches from this appearance until they are exhausted, then
        # return random pitches from this batter during this game
        return chain(appearance_pitches, random_pitches())
