from dataclasses import dataclass
from typing import List

from blaseball_mike.models import Player, Team


@dataclass
class PlayerState:
    id: str
    name: str

    @classmethod
    def from_player(cls, player: Player):
        return PlayerState(id=player.id, name=player.name)


@dataclass
class TeamState:
    nickname: str
    pitcher: PlayerState
    lineup: List[PlayerState]
    batter_index: int
    appearance_count: int

    def __init__(self, updates: List[dict], timestamp: str, prefix: str):
        team = Team.load_at_time(first_truthy(updates, prefix + 'Team'),
                                 timestamp)
        self.nickname = team.get_nickname()

        self.pitcher = PlayerState(
            id=first_truthy(updates, prefix + 'Pitcher'),
            name=first_truthy(updates, prefix + 'PitcherName'))
        assert self.pitcher.id
        assert self.pitcher.name

        self.lineup = [PlayerState.from_player(p) for p in team.lineup]

        self.batter_index = -1
        self.appearance_count = 0

    def advance_batter(self):
        self.batter_index += 1
        if self.batter_index >= len(self.lineup):
            self.batter_index = 0
            self.appearance_count += 1

    def batter(self):
        return self.lineup[self.batter_index]

    def next_batter(self):
        index = (self.batter_index + 1) % len(self.lineup)
        return self.lineup[index]


def first_truthy(updates, key):
    for update in updates:
        if update['data'][key]:
            return update['data'][key]