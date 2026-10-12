#!/usr/bin/python

# Copyright © 2022 Hugo Gualandi
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# OR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

import argparse
import xml.etree.ElementTree as ET
import glob
from html import escape as H
import math
import os
import sys

#
# Misc helper functions
#

def abort(*args):
    print(*args, file=sys.stderr)
    sys.exit(1)

def log(*args):
    print(*args, file=sys.stderr)

def num_range(lo, hi):
    """Convert a min/max range to human-readable form"""
    if lo == hi:
        return str(lo)
    else:
        return ' {}-{} '.format(lo, hi)

#
# Hardcoded translations text. Typically these are things that the cheatsheet
# must spell out in writing, but that the game does not.
#

species_name = {
    'anaerobic': "Lanius",
    'crystal'  : "Crystal",
    'energy'   : "Zoltan",
    'engi'     : "Engi",
    'ghost'    : "Ghost", #unused
    'human'    : "Human",
    'mantis'   : "Mantis",
    'rock'     : "Rock",
    'slug'     : "Slug",
    'traitor'  : "Traitor crewmember",
}

skill_name = {
    'all_skills': "all skills",
    'combat'    : "combat",
    'engines'   : "engines",
    'pilot'     : "pilot",
    'repair'    : "repair",
    'shields'   : "shields",
}

system_name = {
    'clonebay': "clone bay",
    'doors'   : "doors",
    'drones'  : "drones",
    'engine'  : "engines",
    'engines' : "engines",
    'hacking' : "hacking",
    'medbay'  : "medbay",
    'oxygen'  : "oxygen",
    'pilot'   : "piloting",
    'sensors' : "sensors",
    'shields' : "shields",
    'weapons' : "weapons",

    'random'  : "random system",
    'room'    : "random room",
    'reactor' : "reactor",
}

damage_effect = {
    'all'    : "breach and fire",
    "fire"   : "fire",
    "breach" : "breach",
    "random" : "may cause breach or fire",
}

resource_name = {
    'drones'  : "Drone Parts",
    'fuel'    : "Fuel",
    'missile' : "Missiles",
    'missiles': "Missiles",
    'scrap'   : "Scrap",
}

autoreward_kind_html = {
    'droneparts': 'drone parts and scrap',
    'fuel'      : 'fuel and scrap',
    'missiles'  : 'missiles and scrap',
    'scrap'     : 'scrap and resources',

    'droneparts_only': 'drone parts',
    'fuel_only'      : 'fuel',
    'missiles_only'  : 'missiles',
    'scrap_only'     : 'scrap',

    'standard': 'scrap and low resources',
    'stuff'   : 'resources and low scrap',

    #'augment' : 'scrap and <strong>random augment</strong>',
    #'drone'   : 'scrap and <strong>random drone</strong>',
    #'weapon'  : 'scrap and <strong>random weapon</strong>',
}

autoreward_level_html = {
    'LOW'    : 'Low',
    'MED'    : 'Medium',
    'MEDIUM' : 'Medium',
    'HIGH'   : 'High',
    'RANDOM' : 'Random',
}

unlock_name = {
    '1': "Stealth Cruiser",
    '2': "Mantis Cruiser" ,
   #'3': "Kestrel Cruiser",
    '4': "Federation Cruiser",
    '5': "Slug Cruiser",
    '6': "Rock Cruiser",
    '7': "Zoltan Cruiser",
    '8': "Crystal Cruiser",
   #'9': "Lanius Cruiser",
}

blueprintlist_name = {
    # A simple description is easier to read than the full list
    'WEAPONS_BOMBS_CHEAP': 'a random cheap bomb',
    'WEAPONS_MISSILES_EXPENSIVE': 'a random large rocket',
    'WEAPONS_CRYSTAL': 'a crystal weapon',
}

#
# Non-hardcoded text
#

translations = {}

def init_translations():
    for filename in [
        "text_achievements.xml",
        "text_blueprints.xml",
        "text_events.xml",
        "text_misc.xml",
        "text_sectorname.xml",
        "text_tooltips.xml",
        "text_tutorial.xml",
        ]:

        tree = ET.parse(filename)
        for node in tree.iterfind('text'):
            key = node.get('name')
            val = node.text
            if key in translations:
                abort("duplicate translation key "+key)
            translations[key] = val

def translate_message(text_node):
    """Get the english text for a <text> node"""

    # Hardcoded text
    msg = text_node.text
    if msg is not None: return msg

    # Regular translated string
    id = text_node.get('id')
    if id: return translations[id]

    # Multi-string
    # (Show just the first one, they should be interchangeable anyway)
    load = text_node.get('load')
    if load: return translate_message(texts_dict[load][0])

    # Fallback
    return '(no text)'

blueprint_name = {}

def init_blueprint_names():
    tree = ET.parse("./blueprints.xml")

    for k, v in blueprintlist_name.items():
        blueprint_name[k] = v

    for tag in ['augBlueprint', 'droneBlueprint', 'weaponBlueprint']:
        for blueprint in tree.iterfind(tag):
            id     = blueprint.get('name')
            title  = blueprint.find('title')
            if id in blueprint_name: abort('duplicate blueprint '+id)
            blueprint_name[id] = translate_message(title)

#
# XML Schema
# These are the lists of XML nodes that our program is aware of.
# If we encounter a xml node that is not in these lists we print a message to stderr,
# saying that there is a feature that we still need to implement.
#

# Children of the <event> nodes
event_schema = {
    'augment'       : set(['name']),
    'autoReward'    : set(['level']),
    'boarders'      : set(['min', 'max', 'class', 'breach']),
    'choice'        : set(['req', 'hidden', 'hiiden', 'blue', 'lvl', 'min_level', 'max_lvl', 'max_group']),
    'crewMember'    : set(['amount','class','type','id','all_skills','weapons','shields','pilot','engines','combat','repair']),
    'damage'        : set(['amount', 'system', 'effect']),
    'distressBeacon': set([]),
    'drone'         : set(['name']),
    'environment'   : set(['type', 'target']),
    'fleet'         : set([]),
    'img'           : set(['back', 'planet']),
    'item_modify'   : set(['type', 'min', 'max', 'steal']),
    'modifyPursuit' : set(['amount']),
    'quest'         : set(['event']),
    'removeCrew'    : set(['class', 'clone']),
    'remove'        : set(['name']),
    'repair'        : set([]),
    'reveal_map'    : set([]),
    'secretSector'  : set([]),
    'ship'          : set(['load', 'hostile']),
    'status'        : set(['type', 'target', 'system', 'amount']),
    'store'         : set([]),
    'text'          : set(['id', 'load', 'planet']),
    'unlockShip'    : set(['id']),
    'upgrade'       : set(['amount', 'system']),
    'weapon'        : set(['name']),

    'event': None, #buggy test event GHOST_DOCK
}

# Children of <ship> nodes
ship_schema = {
    'crew'     : set([]),
    'destroyed': set(['load']),
    'deadCrew' : set(['load']),
    'escape'   : set(['load', 'chance', 'min', 'max', 'timer']),
    'gotaway'  : set(['load']),
    'surrender': set(['load', 'chance', 'min', 'max']),
    'weaponOverride': None, # TODO
}

# Children of <eventList> nodes
group_schema = {
    'event': set(['load']),
}

def check_schema(parent, schema):
    for child in parent:
        tag = child.tag
        if tag in schema:
            attrs = schema[tag]
            if attrs is None: continue
            for k in child.attrib:
                if not k in attrs:
                    log('Unknown attr {}.{}.{}'.format(parent.tag, child.tag, k))
                    attrs.add(k)
        else:
            log(ET.tostring(parent))
            log("Unknown tag {}.{}".format(parent.tag, child.tag))
            schema[tag] = set([])

def check_child_nodes(parent, known_tags):
    for child in parent:
        tag = child.tag
        if tag not in known_tags:
            log("Not yet implemented", tag)
            known_tags.add(tag)

#
# Unused events (double checked by hand)
#

def set_of_lines(string):
    return set(string.split())

# Don't show friendly ships in "Fights" list.
peaceful_ships = set_of_lines("""
    CIVILIAN_SHIP
    ROCK_UNLOCK1
""")

# When the event name and group name overlap the group name takes precedence.
# In effect, these events become unused and are removed from their lists.
overlapped_event_names = set_of_lines("""
    BOARDERS_PIRATE
    NEBULA_PIRATE
    NEBULA_REBEL
""")

unused_events = set_of_lines("""
    ASTEROID_TEST
    AUTO_BAIT
    BIG_NAME_TEST
    BOARDERS_ASTEROID
    BOARDERS_ASTEROID_GHOST
    BOARDERS_HACKING_2
    BOARDER_TEST
    CASH_IN_DRONE
    CHARACTER_TEST
    CREW_DEAD_TEST
    CREW_TEST
    CRYSTAL_TEST
    DEATH_TEST
    DEMO_END
    DERELICT_TREASURE
    DOCK_BOMB_SALESMAN
    DUMMY
    ENGI_MONSTER
    ENGI_REFUGEES
    FREE_AUG
    FREE_AUGMENT
    FREE_NANO
    FUEL_ESCAPE_FLEET
    FUEL_ESCAPE_PDS
    FUEL_ESCAPE_PULSAR
    FUEL_FLEET_DISTRESS
    FUEL_OFF_ROCK_CURIOUS
    GHOST_BOARDED
    GHOST_SCRAP
    GHOST_SHIP
    LONE_SHUTTLE
    MANTIS_CAPTURE_COMMANDO
    MANTIS_GAMBLE
    NEBULA_NOTHING_TEST
    NEW
    NEWSHIP1
    NEWSHIP2
    PDS_TEST
    PULSAR
    QUEST_STORE
    PIRATE_SURRENDER_CIVILAN
    REBEL_AUTO_PDS
    REBEL_PDS
    REMOVAL_TEST
    ROCK_NURSERY
    ROCK_NURSERY_LOSE
    ROCK_NURSERY_WIN
    ROCK_ZOLTAN_HELP
    SLUG_DISTRESS_PILOTING
    START_DEMO
    STEALTH_1
    STEALTH_2
    STEALTH_3
    STEALTH_4
    STEALTH_5
    STEALTH_6
    STEALTH_7
    STORE_RESCUE
    TEST_EVENT
    TEST_EVENT2
    UNLOCK_STEALTH
    ZOLTAN_SURRENDER
""")



unused_groups = set_of_lines("""
    DERELICT_ENGI
    DERELICT_TREASURE_REWARD
    FUEL_OFF_ROCK_CURIOUS_LIST
    GHOST_BOARDING
    GHOST_DOCK
    GHOST_SHIP
    GHOST_SPACE
    GHOST_STAND
    HOSTILE2
    HOSTILE_BOARDING
    LONE_SHUTTLE_DESTROY
    LONE_SHUTTLE_WAIT
    MANTIS_CAPTURE_COMMANDO_KILL
    MANTIS_CAPTURE_COMMANDO_RELEASE
    MANTIS_CAPTURE_COMMANDO_TALK
    MANTIS_GAMBLE_BLUE
    MANTIS_GAMBLE_RED
    NEBULA_ROCK
    NEUTRAL_SLUG
    NON_HOSTILE
    ROCK_NURSERY_AUTHORITY
    ROCK_NURSERY_STUDENTS
    SAVE_CIVILIAN_LIST_LANIUS
    SLUG_DISTRESS_PILOTING_SWEAR
    QUESTS_CRYSTAL
    QUESTS_SLUG
""")

unused_ships = set_of_lines("""
    FUEL_OFF_ROCK_CURIOUS
    GHOST_SHIP
    IMPOSSIBLE_PIRATE
    JELLY_STATUS_PILOT
    LONG_ELITE
    NEWSHIP1
    NEWSHIP2
    NEW_TESTS
    REBEL_AUTO_BAIT
    ROCK_ZOLTAN_HELP_ROCK
    ROCK_ZOLTAN_HELP_ZOLTAN
    ZOLTAN_PIRATE
""")

#
# Event graph
#
# The first thing we do is parse all the event nodes into an event graph, giving each node an unique ID.
# This serves two purposes. First, it allows us to parse the files in any order, without worrying about
# references to events we haven't processed yet. Secondly, it will allow us to de-duplicate events with
# repeated choices (such as DESTROYED_DEFAULT and DEAD_CREW_DEFAULT). To simplify this deduplication,
# we represent the data using namedTuples and we store all the event actions in a single HTML string.


from collections import namedtuple

Event = namedtuple('Event', [
    'text_html',    # html string: Message when arriving at event
    'actions_html', # html string: List of effects from the event
    'choices', # optional list (req, msg, eventid)
    'fight',   # optional fightid
])

Fight = namedtuple('Fight', [
    'destroyed', # eventid
    'deadCrew', # eventid
    'gotaway',   # eventid
    'surrender', # eventid
])

event_keys = set()
group_keys = set()
ship_keys = set()

texts_dict = {} # <testList>
event_dict = {} # <event>
ship_dict  = {} # <ship>
group_dict = {} # <eventList>

quest_events_set = set()
quest_groups_set = set()

anon_events = 0
def gen_event_id():
    global anon_events
    anon_events += 1
    return 'evt-{}'.format(anon_events)


def build_graph():

    trees = [ET.parse(filename) for filename in glob.glob("*.xml")]

    # Compute the full set of event ids ahead of time
    # because when we process the <quest> item we need to know
    # what kind of thing it refers to. (Unfortunately, we cannot
    # use a shared ID for everythign because there are some events
    # and ships that have the same ID)
    for tree in trees:

        for event in tree.iterfind("event"):
            event_keys.add(event.attrib['name'])

        for ship in tree.iterfind("ship"):
            ship_keys.add(ship.attrib['name'])

        for group in tree.iterfind('eventList'):
            group_keys.add(group.attrib['name'].removeprefix("OVERRIDE_"))

    # Also compute text nodes ahead of time. Some files mention text nodes from
    # other files. For instance, events_ships.xml refers to surrender text).
    for tree in trees:
        for txtgroup in tree.iterfind('textList'):
            key = txtgroup.get('name')
            assert key not in texts_dict
            texts_dict[key] = [node for node in txtgroup.iterfind('text')]

    # Identify which events are overwritten
    overwritten = set()
    for tree in trees:
        for group in tree.iterfind('eventList'):
            name = group.get('name')
            if name.startswith('OVERRIDE_'):
                overwritten.add(name.removeprefix("OVERRIDE_"))

    for tree in trees:
        for event in tree.iterfind("event"):
            graph_add_event(event, None)

        for group in tree.iterfind('eventList'):
            if group.get('name') not in overwritten:
                graph_add_group(group)

        for ship in tree.iterfind("ship"):
            graph_add_ship(ship)

def blueprint_event(what, id):
    """Common functionality for adding weapon/drone/augment"""

    if id == 'RANDOM':
        return '<li><strong>{what}</strong>'.format(what = H(what))
    elif id == 'DLC_AUGMENTS' or id == 'DLC_DRONES' or id == 'DLC_WEAPONS':
        return '<li><strong>{what}</strong> (from Advanced Edition)'.format(what = H(what))
    else:
        name = blueprint_name[id]
        return '<li><strong>{what}</strong> ({name})'.format(what = H(what), name = H(name))

link_target_set = set()
anchor_set = set()

def make_link(typ, id):
    anchor = typ + '-' + id
    link_target_set.add(anchor)
    return '<a href="#{anchor}">{id}</a>'.format(anchor = H(anchor), id = H(id))

def event_link(id):
    return make_link('event', id)

def group_link(id):
    return make_link('list', id)

def ship_link(id):
    return make_link('ship', id)

def graph_add_event(event, enemy_ship_name):
    """Interpret one <event> node from the xml file"""
    # Note: We set the enemy_ship_name param in the <ship> child case

    # Consistency check
    check_schema(event, event_schema)

    key = event.get("name")

    loadevt = event.get('load')
    if loadevt:
        return loadevt

    text_node = event.find('text')
    if text_node is not None:
        textID = text_node.get('load')
        if textID:
            # Multiple texts
            out = []
            out.append('<ul class="texts">')
            for child_text_node in texts_dict[textID]:
                text = translate_message(child_text_node)
                out.append('<li>{text}'.format(text = H(text)))
            out.append('</ul>')

            text_html = ''.join(out)
        else:
            # Single text
            text = translate_message(text_node)
            text_html = '<p>{text}</p>'.format(text = H(text))
    else:
        # Missing text
        text_html = ""

    #
    # Outcomes
    #

    actions = []
    ends_with_fight = False

    hazard = event.find('environment')
    if hazard is not None:
        typ = hazard.get('type')
        if   typ == 'asteroid': what = "Asteroid Field"
        elif typ == 'nebula': what = "Nebula"
        elif typ == 'pulsar': what = "Pulsar"
        elif typ == 'storm': what = "Plasma Storm"
        elif typ == 'sun': what = "Red Star"
        elif typ == 'PDS':
            target = hazard.get('target')
            if   target == 'all': what = "Confused Anti-Ship Battery targeting both ships"
            elif target == 'enemy': what = "Friendly Anti-Ship Battery"
            elif target == 'player': what = "Anti-Ship Battery targeting us"
            else: assert False
        else: assert False

        actions.append('<li><strong>Environment</strong> is {what}'.format(what = H(what)))

    boarders = event.find('boarders')
    if boarders is not None:
        lo = int(boarders.get('min'))
        hi = int(boarders.get('max'))
        cls = boarders.get('class') or 'random'
        breach = boarders.get('breach')

        num = num_range(lo, hi)

        if cls == 'random':
            spc = 'enemies'
        else:
            spc = species_name[cls]

        if breach and breach.lower() == 'true':
            breach_html = ' (with <strong>breach</strong>)'
        else:
            breach_html = ''

        actions.append('<li><strong>Boarded</strong> by {num} {spc}</strong>{breach_html}'.format(
            num = H(num),
            spc = H(spc),
            breach_html = breach_html))

    remove = event.find('remove')
    if remove is not None:
        name = remove.get('name')
        actions.append('<li><strong>Remove</strong> {name}'.format(name = H(name)))

    item_modify = event.find('item_modify')
    if item_modify is not None:
        steal = item_modify.get('steal') # Determines if "trade" ammount is shown next to the parent choice

        # Show payments before rewards
        for direction in ['minus', 'plus']:
            for item in item_modify.iterfind('item'):
                typ = item.get('type')
                lo  = int(item.get('min'))
                hi  = int(item.get('max'))

                what = resource_name[typ]

                if lo >= 0 and hi >= 0:
                    if direction == 'plus':
                        rng = num_range(lo, hi)
                        actions.append('<li>+{rng} <strong>{what}</strong>'.format(
                            rng = H(rng),
                            what = H(what)))
                elif lo <= 0 and hi <= 0:
                    if direction == 'minus':
                        rng = num_range(-hi, -lo)
                        actions.append('<li>−{rng} <strong>{what}</strong>'.format(
                            rng = H(rng),
                            what = H(what)))
                else:
                    abort("nonsensical resource range")

    reward = event.find('autoReward')
    if reward is not None:
        level = reward.get('level').upper()
        kind  = reward.text

        if   kind == 'augment': kind = 'scrap_only'; blueprint = 'Augmentation'
        elif kind == 'drone':   kind = 'scrap_only'; blueprint = 'Drone Schematic'
        elif kind == 'weapon':  kind = 'scrap_only'; blueprint = 'Weapon'
        else : blueprint = None

        level_html = autoreward_level_html[level]
        kind_html  = autoreward_kind_html[kind]

        actions.append('<li><strong>{level_html}</strong> {kind_html}'.format(
            level_html = level_html,
            kind_html = kind_html))

        if blueprint:
            actions.append(blueprint_event(blueprint, 'RANDOM'))

    crew = event.find('crewMember')
    if crew is not None:
        amount_str = crew.get('amount')
        cls        = crew.get('class') or crew.get('type')
        id         = crew.get('id')

        amount_num = int(amount_str)

        extra = []

        if cls is not None and cls != 'random':
            extra.append(species_name[cls])

        for skid, skname in skill_name.items():
            val = crew.get(skid)
            if val:
                extra.append('with level {val} {skname}'.format(
                    val = H(val),
                    skname = H(skname)))
        #if id:
        #    name = translations[id]
        #    extra.append('called {name}'.format(name = H(name)))

        if extra:
            extra_str = " " + " ".join(extra)
        else:
            extra_str = ""

        n = str(abs(amount_num))

        if   amount_num <= -2: template = '<li><strong>Lose {n} Crew</strong>'
        elif amount_num == -1: template = '<li><strong>Lose Crew</strong>'
        elif amount_num ==  0: template = None; log("receive 0 crew")
        elif amount_num ==  1: template = '<li><strong>Gain Crew</strong>{extra_str}'
        elif amount_num >=  2: template = '<li><strong>Gain {n} Crew</strong>{extra_str}'

        if template:
            actions.append(template.format(n = H(n), extra_str = H(extra_str)))

    removeCrew = event.find('removeCrew')
    if removeCrew is not None:
        cls = removeCrew.get('class') or 'random'

        if cls == 'random':
            spc = ""
        else:
            spc = species_name[cls]

        clone = removeCrew.find('clone').text == 'true'
        if clone:
            clone_html = '(can be saved clone bay)'
        else:
            clone_html = '<strong>(cannot be cloned)</strong>'

        text_node = removeCrew.find('text')
        if text_node is not None:
            msg = translate_message(text_node)
        else:
            msg = ''

        actions.append('<li><strong>Lose {spc} Crew</strong> {clone_msg}'.format(
            spc = H(spc),
            clone_msg = clone_html))
    damages = event.findall('damage')
    if damages:

        # Hull damage
        hull = 0
        for damage in damages:
            hull += int(damage.get('amount'))

        if hull < 0:
             actions.append("<li>{amount} <strong>Hull Repair</strong>".format(amount = H(str(-hull))))
        elif hull > 0:
             actions.append('<li>{amount} <strong>Hull Damage</strong>'.format(amount = H(str(hull))))

        # System damage
        for damage in damages:
            systemID = damage.get('system')
            if systemID:
                system = system_name[systemID]
                amount = damage.get('amount')
                effect = damage.get('effect')
                if effect:
                    effect_msg = ' (' + damage_effect[effect] + ')'
                else:
                    effect_msg = ''

                actions.append('<li>{amount} <strong>System Damage</strong> to {system}{effect_msg}</strong>'.format(
                     amount = H(amount),
                     system = H(system),
                     effect_msg = H(effect_msg)))

    for status in event.iterfind('status'):
        typ      = status.get('type')
        target   = status.get('target')
        systemID = status.get('system') or '???'
        amount   = status.get('amount') or '???'

        system = system_name[systemID]

        if typ == 'clear':
            template = '<strong>Restore Power</strong> to {system}'

        elif typ == 'divide':
            if amount != '2': abort("expected <status> divide is not by 2")
            template = '<strong>Half Power</strong> to {system}'

        elif typ == 'limit':
            if amount == '0':
                template = '<strong>Disable</strong> {system}'
            else:
                template = '<strong>Limit Power</strong> to {system}, down to {amount}'

        elif typ == 'loss':
            template = '<strong>Reduce Power</strong> to {system} by {amount}'
        else:
            abort("Unknown <status> type:",typ)

        msg_html = template.format(system = H(system), amount = H(amount))
        if target == 'player':
            pass
        elif target == 'enemy':
            msg_html = '<strong>Enemy ship: </strong>' + msg_html
        else:
            abort('Unknown <status> target:', target)

        actions.append('<li>'+msg_html)

    pursuit = event.find('modifyPursuit')
    if pursuit is not None:
        amount_str = pursuit.get('amount')
        amount_num = int(amount_str)

        n = str(abs(amount_num))

        if n == '1':
            plural = 'jump'
        else:
            plural = 'jumps'

        if amount_num > 0:
            what = "Rebel Fleet Advances"
        elif amount_num < 0:
            what = "Rebel Fleet Delayed"
        else:
             abort('fleet pursuit 0?')

        actions.append('<li><strong>{what}</strong> by {n} {plural}'.format(
            what = H(what),
            n = H(n),
            plural = H(plural)))

    reveal_map = event.find('reveal_map')
    if reveal_map is not None:
        actions.append('<li><strong>Map Update</strong>')

    upgrade = event.find("upgrade")
    if upgrade is not None:
        amount   = upgrade.get('amount')
        systemID = upgrade.get('system')

        system = system_name[systemID]
        html = '<li><strong>Upgrade</strong> {system}'.format(system = H(system))
        if amount != '1':
            html += ' (by {amount})'.format(amount = H(amount))
        actions.append(html)

    augment = event.find('augment')
    if augment is not None:
        actions.append( blueprint_event('Augmentation', augment.get('name')) )

    weapon = event.find('weapon')
    if weapon is not None:
        actions.append( blueprint_event('Weapon', weapon.get('name')) )

    drone = event.find('drone')
    if drone is not None:
        actions.append( blueprint_event('Drone Schematic', drone.get('name')) )

    quest = event.find('quest')
    if quest is not None:
        id = quest.get('event')
        if id in event_keys:
            # This is the case for most quests
            quest_events_set.add(id)
            url_html = event_link(id)
        elif id in group_keys:
            # A few quests do this
            # e.g. ALISON_DEFECTOR_QUEST, HIDDEN_FEDERATION_BASE_LIST
            quest_groups_set.add(id)
            url_html = group_link(id)
        else:
            assert False
        actions.append('<li><strong>Quest</strong> marker for {url_html}'.format(url_html = url_html))

    unlock = event.find("unlockShip")
    if unlock is not None:
        id = unlock.get('id')
        name = unlock_name[id]
        actions.append('<li><strong>Unlock</strong> the {name}'.format(name = H(name)))

    secret_sector = event.find('secretSector')
    if secret_sector is not None:
        actions.append('<li><strong>Travel</strong> to the crystal sector!')

    store = event.find('store')
    if store is not None:
        actions.append('<li><strong>Enter Store</strong>')

    ship = event.find('ship')
    if ship is not None:
        hostility = ship.get('hostile')
        if hostility:
            hostility = hostility.lower()
            if   hostility == 'true':
                is_hostile = True
            elif hostility == 'false':
                is_hostile = False
            else:
                abort("Unknown hostile=" + hostility)
        else:
            is_hostile = False

        shipID = ship.get('load')
        if shipID:
            enemy_ship_name = shipID

        if shipID:
            if enemy_ship_name in peaceful_ships:
                name_html = enemy_ship_name
            else:
                name_html = ship_link(enemy_ship_name)

            if is_hostile:
                actions.append('<li><strong>Fight</strong> a {name_html}'.format(name_html = name_html))
            else:
                actions.append('<li><strong>Encounter</strong> a {name_html}'.format(name_html = name_html))
        else:
            if is_hostile:
                actions.append('<li><strong>Fight</strong>')
            else:
                actions.append('<li><strong>End Fight</strong>')

        if is_hostile and enemy_ship_name:
            assert enemy_ship_name not in peaceful_ships
            ends_with_fight = True

    #
    # Things that I ignore
    #

    fleet = event.find('fleet')
    if fleet is not None:
        # Show ally or rebel fleet on background
        pass

    img = event.find('img')
    if img is not None:
        # Custom background image
        # attrs: back planet
        pass

    repair = event.find('repair')
    if repair is not None:
        # Repair station at Last Stand
        # I think this is redundant? There is another <damage>  tag for the hull repair
        pass

    #
    # Choices
    #

    parsed_choices = None
    choice_node = event.findall("choice")
    if choice_node:
        parsed_choices = []
        for choice in choice_node:
            choice_text_node = choice.find('text')
            text = translate_message(choice_text_node)
            text = text.strip()

            req       = choice.get('req')
            blue      = choice.get('blue')
            min_level = choice.get('lvl') or choice.get('min_level')
            max_level = choice.get('max_lvl') or choice.get('max_level')
            hidden    = choice.get('hidden')
            if hidden: hidden = hidden.lower()

            # Remove redundant missile-cost from certain events
            # (The missile cost also appears in the results)
            text = text.removesuffix("[ Missiles: -1 ]")

            is_blue = ((req is not None) and (hidden == 'true') and (blue != 'false'))
            is_complex = (max_level or (min_level and min_level != '1'))

            if req and is_complex:
                if   (min_level is not None) and (max_level is not None):
                    req_msg = '({} ≤ {} ≤ {}) '.format(min_level, H(req), max_level)
                elif (min_level is not None) and (max_level is None):
                    req_msg = '({} ≥ {}) '.format(H(req), min_level)
                elif (min_level is  None)    and (max_level is not None):
                    req_msg = '({} ≤ {}) '.format(H(req), max_level)
                elif (min_level is  None)    and (max_level is None):
                    assert False
                else:
                    assert False
            else:
                req_msg = ''

            if req_msg and text.startswith('('):
                # In this case, the raw requirement is probably clearer than the
                # fancy english name. E.g. "weapons ≥ 6" instead of "Improved Weapons"
                i = text.index(')') + 2
                text = text[i:]

            sub_event = choice.find('event')
            if sub_event is not None:
                eventID = graph_add_event(sub_event, enemy_ship_name)
            else:
                log("EMPTY CHOICE", id)
                eventID = None

            parsed_choices.append( (req_msg+text, is_blue, eventID) )
        parsed_choices = tuple(parsed_choices)

    #
    # End
    #


    if actions:
        actions_html = '<ul class="result">' + '\n'.join(actions) + '</ul>'
    else:
        actions_html = ''

    if enemy_ship_name:
        fight = enemy_ship_name
    else:
        fight = None

    if (not actions) and (not parsed_choices) and (not ends_with_fight):
        actions_html = '<ul class="result"><li>Nothing happens</ul>'

    key = key or gen_event_id()
    assert key not in event_dict
    event_dict[key] = Event(
        text_html = text_html,
        actions_html = actions_html,
        choices = parsed_choices,
        fight = fight)
    return key

#
# Ship nodes
#

ship_event_types = ['destroyed', 'deadCrew', 'escape', 'gotaway', 'surrender']

def graph_add_ship(ship):

    # Consistency check
    check_schema(ship, ship_schema)

    key = ship.get("name")
    assert key

    crew = ship.find('crew')
    if crew is not None:
        # Describes the percentage of each species in the crew
        pass

    escape = ship.find('escape')
    if escape is not None:
        # The message that appears when the enemy tries to escape
        # Which is not very interesting for the cheatsheet
        # attrs: chance min max timer
        pass

    evts = {}
    for tag in ship_event_types:
        node = ship.find(tag)
        if node is not None:
            evts[tag] =  graph_add_event(node, None)
        else:
            evts[tag] = None

    assert key not in ship_dict
    ship_dict[key] = {
        'destroyed': evts['destroyed'],
        'deadCrew': evts['deadCrew'],
        'escape'   : evts['escape'],
        'gotaway'  : evts['gotaway'],
        'surrender': evts['surrender'], # attrs: chance min max
    }
    return key

def graph_add_group(group):

    key = group.get("name").removeprefix("OVERRIDE_")

    # Consistency check
    check_schema(group, group_schema)

    cases = []
    for event in group.iterfind('event'):
        eventID = graph_add_event(event, None)
        if eventID != key: # resolve self loops with overlapped names (eg. NEBULA_REBEL)
            cases.append((1, eventID))

    assert key not in group_dict
    group_dict[key] = cases

    return key

#
# Canonicalize
# Identify if when there are repeated choices in an event group
# For example,
#   [(1,'A'), (1, 'A'), (1, 'B')]
# becomes
#   [(2,'A'), (1, 'B')]
#

def contains_duplicate(group):
    n = len(group)
    for i in range(0, n):
        for j in range(0, i):
            ev1 = event_dict.get(group[i][1])
            ev2 = event_dict.get(group[j][1])
            if ev1 and ev2 and ev1 == ev2:
                return True
    return False

def merge_group(group):
    counts = []
    events = []
    for (c, id1) in group:
        ev1 = event_dict.get(id1)
        for i, id2 in enumerate(events):
            ev2 = event_dict.get(id2)
            if ev1 and ev2 and ev1 == ev2:
                counts[i] += c
                break
        else:
            counts.append(c)
            events.append(id1)
    return tuple(zip(counts, events))

def canonicalize_groups():
    for key, group in group_dict.items():
        if contains_duplicate(group):
            group_dict[key] = merge_group(group)

#
# Nesting
#
# If an event is only ever referenced by its parent event, then it is safe to render it
# nested inside the other event.
#

event_nparents = {}
group_nparents = {}
ship_nparents  = {}

def init_nesting():

    for k in event_dict:
        event_nparents[k] = 0

    for k in group_dict:
        group_nparents[k] = 0

    for k in ship_dict:
        ship_nparents[k] = 0

    for a, ev in event_dict.items():
        if ev.choices:
            for (_,_, b) in ev.choices:
                if   b in group_nparents: group_nparents[b] += 1
                elif b in event_nparents: event_nparents[b] += 1
        if ev.fight:
            ship_nparents[ev.fight] += 1

    for a, group in group_dict.items():
        for (_, b) in group:
            if   b in group_nparents: group_nparents[b] += 1
            elif b in event_nparents: event_nparents[b] += 1

    for a, ship in ship_dict.items():
        for tag, b in ship.items():
            if   b in group_nparents: group_nparents[b] += 1
            elif b in event_nparents: event_nparents[b] += 1

#
# Root events
#
# Events that are not reachable from these are considered to be unused test/debug events
#

# TODO untangle events and groups
root_event_set  = set()
root_event_list = []

def add_root_event(name):
    if name not in root_event_set:
        root_event_set.add(name)
        root_event_list.append(name)

    if name in event_dict:
        pass
    elif name in group_dict:
        for (_, ev) in group_dict[name]:
            add_root_event(ev)
    else:
        # event does not exist
        assert False

def init_root_events():

    # These appear to be hardcoded events
    # That don't happen at the start of a beacon
    add_root_event("STALEMATE_SURRENDER")
    add_root_event("BOSS_STALEMATE")
    add_root_event("CREW_STUCK")
    add_root_event("FUEL_ESCAPE_SUN")
    add_root_event("FUEL_ESCAPE_STORM")
    add_root_event("FUEL_ESCAPE_ASTEROIDS")
    add_root_event("AUGMENT_FULL")
    add_root_event("EQUIP_FULL")
    add_root_event("START_GAME")
    add_root_event("TUTORIAL_START")
    add_root_event("TUTORIAL_MISSILE")
    add_root_event("TUTORIAL_ENEMY")
    add_root_event("TOO_MANY_CREW")

    # These are hardcoded "structural" events
    # (events.xml)
    add_root_event("FINISH_BEACON")
    add_root_event("FINISH_BEACON_NEBULA")
    add_root_event("FLEET_EASY")
    add_root_event("FLEET_EASY_DLC")
    add_root_event("FLEET_EASY_BEACON")
    add_root_event("FLEET_EASY_BEACON_DLC")
    add_root_event("FLEET_HARD")
    # (events_fuel.xml)
    add_root_event('NO_FUEL_FLEET')
    add_root_event('NO_FUEL_FLEET_DLC')
    add_root_event('NO_FUEL')
    add_root_event('NO_FUEL_DISTRESS')
    # (events_nebula.xml)
    add_root_event("FLEET_EASY_NEBULA")

    # Sector events
    for sector in ET.parse("sector_data.xml").iterfind("sectorDescription"):
        start_event = sector.find("startEvent")
        if start_event is not None:
            add_root_event(start_event.text)

        for lst in sector.iterfind("event"):
            mincount = int(lst.get("min"))
            maxcount = int(lst.get("max"))
            if mincount <= maxcount and 0 < maxcount:
                add_root_event(lst.get("name"))

    # Boss events
    boss_sector = ET.parse("events_boss.xml")
    for event in boss_sector.iterfind("event"):
        add_root_event(event.get("name"))
    for event in boss_sector.iterfind("eventList"):
        add_root_event(event.get("name"))

#
# HTML
#

# For checking missing events
printed_events = set()
printed_groups = set()
printed_ships = set()

def goto_url(url):
    print('<ul class="result"><li>Go to {url}</ul>'.format(url = url))

def can_inline_event(name):
    return name.startswith('evt') or (
        event_nparents[name] == 1 and
        (name not in root_event_set) and
        (name not in quest_events_set))

def can_inline_group(name):
    return (
        group_nparents[name] == 1 and
        (name not in overlapped_event_names) and
        (name not in quest_groups_set))

def goto_group_or_event(name):
    if   name in group_dict:
        if can_inline_group(name):
            output_group(name)
        else:
            goto_url(group_link(name))
    elif name in event_dict:
        if can_inline_event(name):
            output_event(name)
        else:
            goto_url(event_link(name))
    else:
        assert False

def output_event(eventID, is_toplevel=False):
    event = event_dict[eventID]
    if eventID in printed_events: log('dupe', eventID)
    printed_events.add(eventID)

    if is_toplevel or (event.choices and len(event.choices) >= 2) :
        # Don't print the text for events without a choice, to reduce clutter
        print(event.text_html)
    else:
        print('<div class="inner">{text}</div>'.format(text = event.text_html))

    print(event.actions_html)

    if event.choices:
        print('<ol class="choice">')
        for (text, is_blue, nextID) in event.choices:
            cls_html = 'class="blue"' if is_blue else ''
            print('<li><em {cls_html}>{text}</em>'.format(cls_html = cls_html, text = H(text)))
            print('<div>')
            goto_group_or_event(nextID)
            print('</div>')
        print('</ol>')

def output_group(groupID):
    group = group_dict[groupID]
    if groupID in printed_groups: log('dupe', groupID)
    printed_groups.add(groupID)

    m = 0
    for (weight, _) in group:
        m += weight

    print('<ul class="random">')
    for (n, nextID) in group:
        print('<li> {n}/{m}'.format(n = H(str(n)), m = H(str(m))))
        #print('<li> {p}%'.format(p =  "%2.0f"%math.floor(100.0 * n / m)))
        goto_group_or_event(nextID)
    if not group:
        print('<li> Nothing happens')

    print('</ul>')

def output_ship(shipID):
    ship = ship_dict[shipID]
    printed_ships.add(shipID)

    def case(evtID, msg):
        print('<li><em>{msg}</em>'.format(msg = H(msg)))
        print('<div>')
        goto_group_or_event(evtID)
        print('</div>')

    destroyed = ship.get('destroyed')
    deadCrew = ship.get('deadCrew')
    gotaway   = ship.get('gotaway')
    surrender = ship.get('surrender')

    print('<ul class="fight">')
    if destroyed: case(destroyed, "You destroy the enemy ship")
    if deadCrew: case(deadCrew, "You kill the enemy crew")
    if gotaway:   case(gotaway,   "The enemy ship escaped")
    if surrender: case(surrender, "The enemy ship offers to surrender")
    print('</ul>')

def begin_section(is_unused):
    if is_unused:
        print('<section class="unused">')
    else:
        print('<section>')

def end_section():
    print('</section>')


def output_anchor(typ, key):
    anchor = typ + '-' + key
    anchor_set.add(anchor)
    print('<h2 id="{anchor}"><a href="#{anchor}">{key}</a></h2>'.format(
        anchor = H(anchor),
        key = H(key)
    ))

def output_html():

    print("""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>FTL Cheatsheet</title>
    <style>

        body {
            /* More readable text*/
            font-family: sans-serif;
            color: #222;
            max-width:50em;
            margin: 0 auto;
            padding: 2em;
        }

        /* The "visited" colors for links is not very useful */
        a, a:visited { color: rgb(0, 0, 238); }

        /* Many of our link contain underscores, which look weird when underlined*/
        a { text-decoration: none; }
        a:hover, a:focus { text-decoration: underline; }

        h2 {
            font-size: medium;
        }

        h2 > a {
            color: inherit !important;
        }

        .unused {
            color: rgb(100,100,100);
        }

        .unused h2:after {
            font-size: smaller;
            content: " (unused)";
        }

        /* Our notation for lists */
        .texts  { list-style: circle;  } /* RNG text alternatives */
        .random { list-style: circle;  } /* RNG event alternatives */
        .result { list-style: disc;    } /* Event outcomes */
        .choice { list-style: decimal; } /* Player choice */
        .fight  { list-style: square;  } /* Ship fight */

        ul.fight > li {
            margin-top: 10px;
            margin-bottom: 10px;
        }

        ul.texts {
            padding-left: 0px;
        }

        .indent {
            padding-left: 20px;
        }

        .blue {
            color: #10aee8;
        }

        .inner { display: none; }
        body.showchildren .inner { display: block; }

        .unused { display: none; }
        body.showunused .unused { display: block; }
    </style>
</head>
<body>
    <h1>FTL Cheatsheet</h1>
    <p>This page summarizes all the events in <a href="https://subsetgames.com/ftl.html">FTL Advanced Edition</a>.
       I created it because I got tired of wading through slow wiki pages and unreadable XML data files.
       Press <kbd>Ctrl</kbd>-<kbd>F</kbd> to search for an event, and have fun!

    <p>If you have any feedback about this page, contact me via <a href="https://github.com/hugomg/ftl-cheatsheet/issues">Github</a>.

    <h3>Settings</h3>
    <ul style="list-style:none">
        <li><input type="checkbox" id="showinner"><label for="showinner">Show event responses</label>
        <li><input type="checkbox" id="showunused"><label for="showunused">Show unused events</label>
    </ul>

    <script>
        var toggleInner = document.getElementById('showinner')
        function updateInner() { document.body.classList.toggle('showchildren', toggleInner.checked); }
        updateInner();
        toggleInner.addEventListener('change', updateInner);

        var toggleUnused = document.getElementById('showunused')
        function updateUnused() { document.body.classList.toggle('showunused', toggleUnused.checked); }
        updateUnused();
        toggleUnused.addEventListener('change', updateUnused);
    </script>""")


    # Sorted alphabetically for consistency. And also because, coincidentally, the first
    # alphabetical event is one where the "show sub-event text" matters.
    items = []
    for key in event_dict: items.append((key, 'event'))
    for key in group_dict: items.append((key, 'group'))
    items.sort(key = lambda x: x[0])

    print('<h1>Events</h1>')
    for (key, typ) in items:
        if typ == 'event':
            if can_inline_event(key): continue
            begin_section(key in unused_events or key in overlapped_event_names)
            output_anchor('event', key)
            print('<div class="indent">')
            output_event(key, True)
            print('</div>')
            end_section()
        elif typ == 'group':
            if can_inline_group(key): continue
            begin_section(key in unused_groups)
            output_anchor('list', key)
            print('<div class="indent">')
            output_group(key)
            print('</div>')
            end_section()
        else:
            assert False

    # Ships
    print('<h1>Fights</h1>')
    for key in sorted(ship_dict.keys()):
        if key in peaceful_ships: continue
        begin_section(key in unused_ships)
        output_anchor('ship', key)
        print('<div class="indent">')
        output_ship(key)
        print('</div>')
        end_section()

    print("""
</body>
</html>""")

#
# Main
#


# Parse arguments
parser = argparse.ArgumentParser(description="Create an FTL Cheatsheet in HTML")
parser.add_argument('datadir', metavar='DATADIR', type=str, help="Path to FTL data folder")
args = parser.parse_args()

# Generate the HTML file
os.chdir(args.datadir)
init_translations()
init_blueprint_names()
build_graph()
canonicalize_groups()
init_nesting()
init_root_events()
output_html()

# Check for forgotten events
for k in event_dict:
    if k not in printed_events:
        if not k.startswith('evt-'):
            log('missing event', k)

for k in group_dict.keys():
    if k not in printed_groups:
        log('missing event', k)

for k in ship_dict.keys():
    if k not in printed_ships and k not in peaceful_ships:
        log('missing ship', k)

# Check for broken links
for k in link_target_set - anchor_set:
    log('broken link', k)

visited_events = set() # or groups...
visited_ships  = set()

#
# Sanity check for unused events
#

def traverse_event_or_group(id):
    if id in visited_events: return
    visited_events.add(id)

    if id in group_dict:
        group = group_dict[id]
        for (weight, childId) in group:
            traverse_event_or_group(childId)

    elif id in event_dict:
        evt = event_dict[id]
        if evt.choices:
            for (req, msg, childId) in evt.choices:
                traverse_event_or_group(childId)
        if evt.fight:
            traverse_ship(evt.fight)

    else:
        assert False

def traverse_ship(id):
    if id in visited_ships: return
    visited_ships.add(id)

    ship = ship_dict[id]
    for key in ship_event_types:
        child = ship.get(key)
        if child:
            traverse_event_or_group(child)

for id in root_event_list:
    traverse_event_or_group(id)
for id in quest_events_set:
    traverse_event_or_group(id)
for id in quest_groups_set:
    traverse_event_or_group(id)

events_not_visited = event_keys - visited_events - unused_events
if events_not_visited:
    log("===== EVENTS NOT VISITED =====")
    for id in sorted(events_not_visited): log(id)


groups_not_visited = group_keys - visited_events - unused_groups
if groups_not_visited:
    log("===== GROUPS NOT VISITED =====")
    for id in sorted(groups_not_visited): log(id)


ships_not_visited = ship_keys - visited_ships - unused_ships
if ships_not_visited:
    log("===== SHIPS NOT VISITED =====")
    for id in sorted(ships_not_visited): log(id)

# Check overlapped events
if (event_keys & group_keys) != overlapped_event_names:
    log("there is a problem with the overlapped event name list")
