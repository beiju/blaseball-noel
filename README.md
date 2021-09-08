# What?

https://noel.beiju.me/

Noel dares to ask: what if blaseball was baseball? It reinterprets every* game 
using just the rules of Baseball. You get 3 strikes per out, 3 outs per inning,
4 bases on the field, and 0 players set on fire.

\* Currently just ~~hyped for~~ season 12.

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
pulls those pitches in order. It then computes the consequences of that pitch
(runners moving around the bases, runs being scored, outs being gotten). If it
runs out of pitches (for example, when the batter walked after only 3 balls due 
to Walk in the Park), or runs out of appearances (such as when all of the 
non-Reverberating players get to play more because Don Mitchell is no longer
hogging all the PAs), it reaches into a grab bag and pulls out a random pitch
to the current batter from the current game. In future I plan to also track
pitchers, so it will be a pitch from the correct pitcher, too. This way of 
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
to ensure that every time a decision is recorded, it is consumed in the 
corresponding game event if the game state has not diverged for some other 
reason. This means that if a steal or caught stealing happened in the original
Blaseball game, it will happen in the exact same place in the Noel game as long
as nothing else has changed.

By tracking pitches, runner advancement, and base stealing in this way I am able
to perfectly recreate Blaseball games that had no nonsense in them already, but 
also generate a plausible game to fill in the gaps whenever nonsense had to be
removed.

# Can I ask questions with more than one word?

Yes.

# What works?

Season 12 *should* work. Every game in Season 12 generates without throwing an
error, but I haven't checked them for accuracy. I am reasonably sure Day 1 
works, and the most exciting ones that I know work are the Wings and 
Firefighters games on Day 79. These both had incinerations and in both games you
can see not only the lack of incineration message, but the player comes up to
bat later in the inning.

# Why no seasons after 12?

Noel needs to understand Blaseball on a pretty deep level. Thankfully I don't
need to fully understand the nonsense, just understand it enough to know that a
nonsense is happening. But it still needs to understand a lot. I rely on the 
feed, which only exists in seasons 12+, for that understanding.

It stops at season 12 essentially because nearly every form of nonsense requires
dedicated code. Even though I'm going to remove it, I still need to understand
its effect on the game state or I won't be able to correctly parse the rest of
the game. The particular roadblock that stops season 13 from working is 
scattering, particularly of -easley Day. Unfortunately, even with the feed and
its `playerTags`, there are many events where players are identified only by 
name and I need to match them as such. Scattered really interferes with that
and I wasn't able to fix it by the SIBR hackathon deadline.

# But my team didn't exist

Listen, I get it. My team didn't(?) exist(?) either. Sometimes that's how it be.

# What can it undo?

Anything that has a bespoke message. Incinerations, feedbacks, reverbs, 
elsewhere, shelled (pitches are filled in if the batter played at all that 
game, otherwise they are just skipped), some bloods (Charm, Electric). It can't
undo anything where the exact effect can't be computed: Over/Underperforming,
some other bloods (Grass, 0 No). The only very noticeable Blaseball effect I've 
seen that remains is 0 No -- Chorby Short's legendary plate appearances remain
intact. But listen, you can't prove that it was 0 No doing that and not just 
some really, really, really, really, really, really, really improbable luck.

One point is that, by construction, it can only undo things that happened within
the game. Noel's starting point is the universe as it existed in Blaseball at 
the start of the game, so if a player is incinerated you will see the 
replacement start to bat in the next game. This was a decision I made to make
this thing feasible at all. It would be very interesting to see what happens if
the player survives the whole season, but that would be a different project.

# How is it displayed?

I host a customized copy of [Before](https://before.sibr.dev/) which points to
a proxy of Chronicler instead of the real thing. Everything else is passed 
through as-is, but the original game events are replaced with the corresponding
game event from Noel's generated games. It's very much a prototype, and it
doesn't work properly if the generated game is longer than the original (it 
will just abruptly skip to the end when the original game gets to its end).
Future plans include using [Blasement][blasement] to display game states 
without relying on there being a one-to-one mapping between my generated game
updates and the StreamEvents from Chronicler.

# So just the stream events then?

Yeah. In future I want to edit the teams too, and more importantly the 
standings, but that's a later problem. You can open the team pages and it will
show the actual world, Blaseball nonsense and all, but that doesn't seem to
affect the games.

# But won't it break if...

Probably.

## ...Blaseball Happens to a player after only a small number of actions?

It's true that if, for example, a batter only gets a single ground out before
being incinerated, Noel will continue generating PAs for them with only one 
action to draw from. I toyed with the idea of using the replacement player for 
the entire game instead, but decided the artefact still being visible in the
data was interesting, so I kept it.

For pitchers it might be a different story. I will have to see what's the 
quickest a pitcher has been incinerated (etc.), but if it's before they pitched 
to every player I will have a problem. If they throw one Ball and then get 
incinerated I will have a *big* problem. In that case I may be forced to use the
replacement player for the whole game.

## ...a player does nothing *but* nonsense?

Then that player deserves to be removed from the batting order. If it's a 
pitcher... god help us all.

## ...in the postseason?

Your grammar is questionable. But yes, it will. At first it will be fine, but
what if a postseason round only went to game 3 in Blaseball, but it should go
to game 4 in Noel? What if the team that should advance in Noel is different to
the team that advanced in Blaseball? The current implementation doesn't check
that at all, it just accepts the teams that Blaseball matched up.

I think the best thing to do in this scenario is to search through the *entire
season* to build a list of pitches this batter took against this pitcher on this
team (as a Crabs fan, I am duty bound to believe defense is real). Failing that, 
pitches this batter took against this pitcher on any team will have to do. Then
I can generate a new game wholesale from those pitches, advancements, and steal
decisions.

The unanswered question is how far back to look. I think it's neat that in Noel,
sometimes players just suddenly get better or worse. In Blaseball we know it's
from a blooddrain, peanut, consumer attack, party, etc. But in Noel, sometimes 
players just have something going on and we don't know what it is. They have 
their own lives and we don't necessarily know what they're going through. 
Should I make any effort to preserve those trends in Noel? Or is a player 
suddenly regressing to the mean, in whichever direction, part of the story?

## ...season 24?

Season 24 is not real and cannot hurt me.

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