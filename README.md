# What?

https://noel.beiju.me/

Noel dares to ask: what if blaseball was baseball? It reinterprets every* game 
using just the rules of Baseball. You get 3 strikes per out, 3 outs per inning,
4 bases on the field, and 0 players set on fire.

\* Currently just season 12

# Why?

This grew out of a slightly more sensible project, which (if I ever actually 
complete it) will let you separate the effects of some of Blaseball's silliest
rules for analysis. That, in turn, grew out of frustration with trying to follow
the game starting around season 19. 

While I was working on taking the fun out of Blaseball, I wondered: why not take
*all* the fun out of Blaseball? Don't answer that.

# How?

It was important to me, for some reason, that Noel should not just paper over 
the Blasebally things and pretend they're not happening. It would've been easy 
to "undo" a feedback or an incineration by just renaming the players and keeping
the performances the same. However, I wanted to know how the player change 
actually affected the game. Obviously this is not perfectly knowable, but I can
generate a performance that's realistic to the incinerated (etc.) player.

Noel transforms games in a two-step process. The Recorder records each team's
performance separately. It divides the game into "appearances", a poorly chosen
term that means "all the pitches that happen to a team between when a batter 
steps up to the plate and when the next batter does". In the simple case an 
appearance is a Plate Appearance, but appearances also combine consecutive 
Reverberating PAs as well as whatever you call that thing where a batter will 
be interrupted by an inning-ending caught stealing and will start over at the 
top of the next inning.

Once a game has been Recorded, the Producer generates new game events from these
pitch lists. It includes a poor simulacrum of the Blaseball sim, following the 
same motions the Blaseball sim does. However, when it needs to output a pitch,
instead of generating a random one it goes into the record of appearances and 
pulls those pitches in order, then computes the consequences of that pitch
(runners moving around the bases, runs being scored, outs being gotten). If it
runs out of pitches (for example, when the batter walked after only 3 balls due 
to Walk in the Park), or runs out of appearances (such as when all of the 
non-Reverberating players get to play more because Don Mitchell is no longer
hogging all the PAs), it reaches into a grab bag and pulls out a random pitch
to the current batter from the current game. (In future I plan to also track
pitchers, so it will be a pitch from the correct pitcher, too.) This way of 
generating pitches generates games that are 100% faithful to the original game
when no Blaseball nonsense was involved, and are accurately representative of
the batter's ability when they can't be faithful to the original.

There are two other sources of "decisions" besides pitches: runner advancement 
and base stealing. I handle runner advancement by tracking how far each runner
advanced on each pitch -- which is great for the faithful recreation part, but
if a random pitch was drawn the chances that the right baserunner will have
an advancement amount recorded for that pitch are small. To fill these gaps, I
once again draw randomly from all the advancement decisions (yes or no, and how
far) that player made during the game.

Stealing is handled a little differently, since it preempts a pitch instead of
being part of it. I keep a record of steal decisions for each time the player
made it on base. Each decision is either steal, caught stealing (yes that's a
player decision), or stay. Before every pitch I look at the next entry in every
baserunner's steal decision list to see if they decided to steal. Like before, 
if I run out of entries I choose a random decision from that game. I take care
to match up when the decisions are recorded with when they are checked so that
the steal happens in the same place in the generated game if nothing else has
changed.

By tracking pitches, runner advancement, and base stealing in this way I am able
to perfectly recreate a game that had no nonsense, but also generate a plausible
game to fill in the gaps where nonsense was removed.

# Can I ask questions with more than one word?

Yes.

# What works?

Season 12 *should* work. Every game in Season 12 generates without throwing an
error, but I haven't checked them for accuracy. I am reasonably sure Day 1 
works, and the most exciting ones that I know work are the Wings and 
Firefighters games on Day 79. These both had incinerations and in both games you
can see not only the lack of incineration message, but the player comes up to
bat later in the inning.

Seasons other than 12 do not work. Seasons before 12 don't have the feed, which
I am *heavily* reliant on, and seasons after 12 have nonsense that I haven't
been able to correct for yet (scattering is messing up my parsing).

# What can it undo?

Anything that has a bespoke message. Incinerations, feedbacks, reverbs, 
elsewhere, shelled (pitches are filled in if the batter played at all that 
game, otherwise they are just skipped), some bloods (Charm, Electric). It can't
undo anything where the exact effect can't be computed: Over/Underperforming,
some other bloods (Grass, 0 No). The only very noticeable Blaseball effect I've 
seen that remains is 0 No -- Chorby Short's legendary plate appearances remain
intact, and you can't prove that it was 0 No doing that and not just some 
really, really, really, really, really, really, really improbable luck.

# How is it displayed?

I host a customized copy of [Before](https://before.sibr.dev/) which points to
a proxy of Chronicler instead of the real thing. Everything else is passed 
through as-is, but the original game events are replaced with the corresponding
game event from Noel's generated games. It's very much a prototype, and it
doesn't work properly if the generated game is longer than the original (it 
will just abruptly skip to the end when the original game gets to its end).
Future plans include using Blasement to integrate it better.

# So just the stream events then?

Yeah. In future I want to edit the teams too, and more importantly the 
standings, but that's a later problem. You can open the team pages and it will
show the actual world, Blaseball nonsense and all, but that doesn't seem to
affect the games.

# Was it worth it?

Making this helped me better understand some technical aspects of Blaseball and 
that's going to be useful in future projects. But as far as improving Blaseball,
obviously not. Despite my whining in seasons 19-23, Blaseball is better for 
having the nonsense and I wouldn't want it any other way.

# Acknowledgements

Thanks to iliana for creating [Before][before], helping me run a copy myself, 
and giving me permission to host bastardized versions of it.

Thanks to the people behind [Chronicler][chron] and [Eventually][eventually], 
without which I simply would not have had the data that enables this to exist.

Thanks to Brella for assistance with [Blasement][blasement], even though it 
didn't make the final cut.

Thanks to SIBR for hosting the [cursed viewer competition][cursed] that pushed 
me to create this in the first place.

And thanks to a cactus in the SIBR discord server for the idea for 
https://chorby-soup.beiju.me/, a "project" which has a vastly better payoff
for orders of magnitude less effort. 

[before]: https://github.com/iliana/before
[chron]: https://github.com/xSke/Chronicler
[eventually]: https://github.com/alisww/eventually
[blasement]: https://github.com/UnderMybrella/the-blasement
[cursed]: https://cursed.sibr.dev/

# Wait I forgot to mention something

"Blaseball" is replaced with "Baseball" throughout the entire site (except the
`_before` pages). The code to do that is in a script tag in the index.html and
it's some high quality cursed material. Recommended reading.