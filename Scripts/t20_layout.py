"""T20 authored dimensions (cm); shared by generation and saved-asset inspection."""
MAP = '/Game/Prototype/Maps/L_Prototype'
LEGACY = '/Game/Prototype/Maps/L_LegacyPrototype'
UI = '/Game/UI/WBP_ExplorationPrompt'
ENV = '/Game/Prototype/Environment/T20'
BOX_POINTS = [(-1000., 350., 50.), (1000., 350., 50.), (0., -1100., 50.)]
ENTRANCE = (0., 1700., 0.)
START = (0., 1750., 110.)
THREAT_OFFSET = (0., -300., -3.)
# x min/max, y min/max; walkable floor top is 0, ceiling underside is 400.
ROOMS = [('Entry', -800, 800, 900, 2100), ('Hall', -240, 240, -500, 900),
         ('A', -1400, -240, -500, 900), ('B', 240, 1400, -500, 900),
         ('C', -800, 800, -1500, -500)]
# Wall centre and size in XY. Openings: 360 cm entry/C, 400 cm A/B.
WALLS = [
    (0, 2100, 1620, 20), (-800, 1500, 20, 1200), (800, 1500, 20, 1200),
    (-790, 900, 1220, 20), (790, 900, 1220, 20),
    (-1400, 200, 20, 1420), (1400, 200, 20, 1420),
    (-240, -250, 20, 500), (-240, 650, 20, 500),
    (240, -250, 20, 500), (240, 650, 20, 500),
    (-790, -500, 1220, 20), (790, -500, 1220, 20),
    (-800, -1000, 20, 1000), (800, -1000, 20, 1000), (0, -1500, 1620, 20)]
COLOURS = {'Entry': (.12, .75, .43), 'Hall': (.65, .72, .72),
           'A': (.10, .55, 1.), 'B': (1., .52, .10), 'C': (.67, .30, .95)}
