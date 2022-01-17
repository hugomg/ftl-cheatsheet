#!/usr/bin/python

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

def abort(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

def log(msg):
    print(msg, file=sys.stderr)

def num_range(lo, hi):
    """Convert a min/max range to human-readable form"""
    if lo == hi:
        return str(lo)
    else:
        return '{}-{}'.format(lo, hi)

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
    'room'    : "random room(?)",
    'reactor' : "reactor",
}

damage_effect = {
    'all'    : "breach and fire",
    "fire"   : "fire",
    "breach" : "breach",
    "random" : "may cause breach or fire",
}

resource_name_singular = {
    'drones'  : "drone part",
    'fuel'    : "fuel",
    'missile' : "missile",
    'missiles': "missile",
    'scrap'   : "scrap",
}

resource_name_plural = {
    'drones'  : "drone parts",
    'fuel'    : "fuel",
    'missile' : "missiles",
    'missiles': "missiles",
    'scrap'   : "scrap",
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

    'standard': 'scrap and resources',
    'stuff'   : 'resources and scrap',

    'augment' : 'scrap and <strong>random augment</strong>',
    'drone'   : 'scrap and <strong>random drone</strong>',
    'weapon'  : 'scrap and <strong>random weapon</strong>',
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
event_known_tags = set([
    'augment',
    'autoReward',
    'boarders',
    'choice',
    'crewMember',
    'damage',
    'distressBeacon',
    'drone',
    'environment',
    'fleet',
    'img',
    'item_modify',
    'modifyPursuit',
    'quest',
    'removeCrew',
    'remove',
    'repair',
    'reveal_map',
    'secretSector',
    'ship',
    'status',
    'store',
    'text',
    'unlockShip',
    'upgrade',
    'weapon',
])

# Children of <ship> nodes
ship_known_tags = set([
    'crew',
    'destroyed',
    'deadCrew',
    'escape',
    'gotaway',
    'surrender',
])

# Children of <eventList> nodes
group_known_tags = set([
    'event',
])

def check_child_nodes(parent, known_tags):
    for child in parent:
        tag = child.tag
        if tag not in known_tags:
            log("Not yet implemented: " + tag)
            known_tags.add(tag)

#
# Event graph
#
# The first thing we do is parse all the event nodes into an event graph, giving each node an unique ID.
# This serves two purposes. First, it allows us to parse the files in any order, without worrying about
# references to events we haven't processed yet. Secondly, it will allow us to de-duplicate events with
# repeated choices (such as DESTROYED_DEFAULT and DEAD_CREW_DEFAULT). To simplify this deduplication,
# we represent the data using namedTuples and we store all the event actions in a single HTML string.
# 
# Note: eventid may refer to either an individual event, or to an event group. Unfortunately, there
# are some identifiers (e.g. NEBULA_PIRATE) that are used both as an eventList and as an individual
# event. Therefore, the meaning depends on context. If we are in an event group, then child events
# prioritize the individual event namespace. Otherwise, the event group namespace takes priority.

from collections import namedtuple

Event = namedtuple('Event', [
    'text_html',    # html string: Message when arriving at event
    'actions_html', # html string: List of effects from the event
    'choices', # optional list (req, msg, eventid)
    'fight',   # optional fightid
])

Fight = namedtuple('Fight', [
    'destroyed', # eventid
    'dead_crew', # eventid
    'gotaway',   # eventid
    'surrender', # eventid
])

#
# Note: in 
#

texts_dict = {} # <testList>
event_dict = {} # <event>
ship_dict  = {} # <ship>
group_dict = {} # <eventList>

anon_events = 0
def gen_event_id():
    global anon_events
    anon_events += 1
    return 'evt-{}'.format(anon_events)


def build_graph():
    for filename in glob.glob("./*.xml"):
        tree = ET.parse(filename)

        for txtgroup in tree.iterfind('textList'):
            key = txtgroup.get('name')
            assert key not in texts_dict
            texts_dict[key] = txtgroup
        
        for event in tree.iterfind("event"):
            graph_add_event(event, None)

        for group in tree.iterfind('eventList'):
            graph_add_group(group)

        for ship in tree.iterfind("ship"):
            graph_add_ship(ship)


def blueprint_event(what, node):
    """Common functionality for adding weapon/drone/augment"""
    
    id = node.get('name')
    if id == 'RANDOM':
        return '<li><strong>Random {what}</strong>'.format(what = H(what))
    elif id == 'DLC_AUGMENTS' or id == 'DLC_DRONES' or id == 'DLC_WEAPONS':
        return '<li><strong>Random {what}</strong> (from Advanced Edition)'.format(what = H(what))
    else:
        name = blueprint_name[id]
        return '<li><strong>{what}</strong> ({name})'.format(what = H(what), name = H(name))

def event_link(id):
    return '<a href="#event-{id}">{id}</a>'.format(id = H(id))

def group_link(id):
    return '<a href="#list-{id}">{id}</a>'.format(id = H(id))

def ship_link(id):
    return '<a href="#ship-{id}">{id}</a>'.format(id = H(id))

def graph_add_event(event, enemy_ship_name):
    """Interpret one <event> node from the xml file"""
    # Note: We set the enemy_ship_name param in the <ship> child case

    # Consistency check
    check_child_nodes(event, event_known_tags)

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
            out.append('<ul class="textlist">')
            for child_text_node in texts_dict[textID].iterfind('text'):
                text = translate_message(child_text_node)
                out.append('<li>{text}'.format(text = H(text)))
            out.append('</ul>')

            text_html = ''.join(out)
        else:
            # Single text
            text = translate_message(text_node)
            text_html = '{text}'.format(text = H(text))
    else:
        # Missing text
        text_html = ""

    #
    # Outcomes
    #

    actions = []
    ends_with_fight = False

    fleet = event.find('fleet')
    if fleet is not None:
        # Show ally or rebel fleet on background
        pass

    img = event.find('img')
    if img is not None:
        # Custom background image
        pass

    ship = event.find('ship')
    if ship is not None:
        shipID = ship.get('load')
        if shipID:
            url_html = ship_link(shipID)
            enemy_ship_name = shipID
                    
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

        if shipID:
            if is_hostile:
                actions.append('<li><strong>Fight</strong> a {url_html}'.format(url_html = url_html))
            else:
                actions.append('<li><strong>Encounter</strong> a {url_html}'.format(url_html = url_html))
        else:
            if is_hostile:
                actions.append('<li><strong>Fight</strong>')
            else:
                actions.append('<li><strong>End fight</strong>')

        if is_hostile and enemy_ship_name:
            ends_with_fight = True

    hazard = event.find('environment')
    if hazard is not None:
        typ = hazard.get('type')
        if typ == 'asteroid':
            actions.append('<li><strong>Environmental Hazard</strong>: asteroid field')
        elif typ == 'nebula':
            actions.append('<li><strong>Environmental Hazard</strong>: nebula')
        elif typ == 'pulsar':
            actions.append('<li><strong>Environmental Hazard</strong>: pulsar')
        elif typ == 'storm':
            actions.append('<li><strong>Environmental Hazard</strong>: ion storm')
        elif typ == 'sun':
            actions.append('<li><strong>Environmental Hazard</strong>: red giant star')
        elif typ == 'PDS':
            target = hazard.get('target')
            if target == 'all':
                actions.append('<li><strong>Confused Anti-Ship Battery</strong> targeting both ships')
            elif target == 'enemy':
                actions.append('<li><strong>Friendly Anti-Ship Battery</strong> targeting the enemy')
            elif target == 'player':
                actions.append('<li><strong>Anti-Ship Battery</strong> targeting us')

    boarders = event.find('boarders')
    if boarders is not None:
        lo = int(boarders.get('min'))
        hi = int(boarders.get('max'))
        cls = boarders.get('class') or 'random'

        num = num_range(lo, hi)

        if cls == 'random':
            spc = 'enemies'
        else:
            spc = species_name[cls]
        
        actions.append('<li><strong>Boarded</strong> by {num} {spc}</strong>'.format(
            num = H(num),
            spc = H(spc)))

    remove = event.find('remove')
    if remove is not None:
        name = remove.get('name')
        actions.append('<li><strong>Remove</strong> {name}'.format(name = H(name)))

    crew = event.find('crewMember')
    if crew is not None:
        amount_str = crew.get('amount')
        cls        = crew.get('class')
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

        if amount_num < 0:
            n = str(abs(amount_num))
            actions.append('<li><strong>Lose {n} random crew</strong>'.format(n = H(n)))
        elif amount_num == 0:
            abort("receive 0 crew")
        else: # amount_num > 0:
            actions.append('<li><strong>New crewmember</strong>{extra_str}'.format(extra_str = H(extra_str)))

    removeCrew = event.find('removeCrew')
    if removeCrew is not None:
        cls = removeCrew.get('class') or 'random'

        if cls == 'random':
            spc = "random"
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

        actions.append('<li><strong>Lose 1 {cls} crew</strong> {clone_msg}'.format(
            cls = H(cls),
            clone_msg = clone_html))

    repair = event.find('repair')
    if repair is not None:
        # Repair station at Last Stand
        # I think this is redundant? There is another <damage>  tag for the hull repair
        pass

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
        systemID = status.get('system')
        amount   = status.get('amount')

        system = system_name[systemID]
         
        if typ == 'clear':
            actions.append('<li><strong>Restore power</strong> to {system}'.format(system = H(system)))

        elif typ == 'divide':
            if amount != '2': abort("expected <status> divide is not by 2")
            actions.append('<li><strong>Half power</strong> to {system}'.format(system = H(system)))
             
        elif typ == 'limit':
            actions.append('<li><strong>Limit power</strong> to {system}, down to {amount}'.format(
                system = H(system),
                amount = H(amount)))

        elif typ == 'loss':
            actions.append('<li><strong>Reduce power</strong> to {system} by {amount}'.format(
                system = H(system),
                amount = H(amount)))
        else:
            abort("Unknown <status> type: "+typ)

    augment = event.find('augment')
    if augment is not None:
        actions.append( blueprint_event('Augment', augment) )

    weapon = event.find('weapon')
    if weapon is not None:
        actions.append( blueprint_event('Weapon', weapon) )

    drone = event.find('drone')
    if drone is not None:
        actions.append( blueprint_event('drone', drone) )

    item_modify = event.find('item_modify')
    if item_modify is not None:
        for item in item_modify.iterfind('item'):
            typ = item.get('type')
            lo  = int(item.get('min'))
            hi  = int(item.get('max'))

            if abs(lo) == 1 and abs(hi) == 1:
                what = resource_name_singular[typ]
            else:
                what = resource_name_plural[typ]
            
            if lo >= 0 and hi >= 0:
                rng = num_range(lo, hi)
                actions.append('<li><strong>Receive</strong> {rng} {what}'.format(
                    rng = H(rng),
                    what = H(what)))
            elif lo <= 0 and hi <= 0:
                rng = num_range(-hi, -lo)
                actions.append('<li><strong>Pay</strong> {rng} {what}'.format(
                    rng = H(rng),
                    what = H(what)))
            else:
                abort("nonsensical resource range")

    reward = event.find('autoReward')
    if reward is not None:
        level = reward.get('level').upper()
        kind  = reward.text

        level_html = autoreward_level_html[level]
        kind_html  = autoreward_kind_html[kind]

        actions.append('<li><strong>{level_html}</strong> {kind_html}'.format(
            level_html = level_html,
            kind_html = kind_html))

    pursuit = event.find('modifyPursuit')
    if pursuit is not None:
        amount_str = pursuit.get('amount')
        amount_num = int(amount_str)

        n = str(abs(amount_num))
        
        if amount_num > 0:
            actions.append('<li><strong>Rebel fleet advances</strong> {n} jumps'.format(n = H(n)))
        elif amount_num < 0:
            actions.append('<li><strong>Rebel fleet delayed</strong> by {n} jumps'.format(n = H(n)))
        else:
             abort('fleet pursuit 0?')

    reveal_map = event.find('reveal_map')
    if reveal_map is not None:
        actions.append('<li><strong>Reveal sector map</strong>')

    secret_sector = event.find('secretSector')
    if secret_sector is not None:
        actions.append('<li><strong>Travel</strong> to the crystal sector!')

    quest = event.find('quest')
    if quest is not None:
        id = quest.get('event')
        url_html = event_link(id)
        actions.append('<li><strong>Add quest marker</strong> for {url_html}'.format(url_html = url_html))

    unlock = event.find("unlockShip")
    if unlock is not None:
        id = unlock.get('id')
        name = unlock_name[id]
        actions.append('<li><strong>Unlock</strong> the {name}'.format(name = H(name)))

    upgrade = event.find("upgrade")
    if upgrade is not None:
        amount   = upgrade.get('amount')
        systemID = upgrade.get('system')

        system = system_name[systemID]
        html = '<li><strong>Upgrade</strong> {system}'.format(system = H(system))
        if amount != '1':
            html += ' (by {amount})'.format(amount = H(amount))
        actions.append(html)

    store = event.find('store')
    if store is not None:
        actions.append('<li><strong>Opens a store</strong>')



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
            
            is_blue = (
                (choice.get('req') is not None) and
                (choice.get('hidden') == 'true') and
                (choice.get('blue') != 'false'))
     
            sub_event = choice.find('event')
            if sub_event is not None:
                eventID = graph_add_event(sub_event, enemy_ship_name)
            else:
                log("EMPTY CHOICE: " + id)
                eventID = None

            parsed_choices.append( (text, is_blue, eventID) )
        parsed_choices = tuple(parsed_choices)

    #
    # End
    #

    
    if actions:
        actions_html = '<ul>' + '\n'.join(actions) + '</ul>'
    else:
        actions_html = ''

    if ends_with_fight:
        fight = enemy_ship_name
    else:
        fight = None

    if (not actions) and (not parsed_choices) and (not ends_with_fight):
        actions_html = '<ul><li>Nothing happens</ul>'

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

ship_event_types = ['destroyed', 'deadCrew', 'gotaway', 'surrender']

def graph_add_ship(ship):

    # Consistency check
    check_child_nodes(ship, ship_known_tags)

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
        'dead_crew': evts['deadCrew'],
        'gotaway'  : evts['gotaway'],
        'surrender': evts['surrender'],
    }
    return key

def graph_add_group(group):

    # Consistency check
    check_child_nodes(group, group_known_tags)

    cases = []
    for event in group.iterfind('event'):
        eventID = graph_add_event(event, None)
        cases.append((1, eventID))

    key = group.get("name")
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
                # group priority
                if   b in group_nparents: group_nparents[b] += 1
                elif b in event_nparents: event_nparents[b] += 1
        if ev.fight:
            ship_nparents[ev.fight] += 1

    for a, group in group_dict.items():
        for (_, b) in group:
            # event priority
            if   b in event_nparents: event_nparents[b] += 1
            elif b in group_nparents: group_nparents[b] += 1

    for a, ship in ship_dict.items():
        for tag, b in ship.items():
            # group priority
            if   b in group_nparents: group_nparents[b] += 1
            elif b in event_nparents: event_nparents[b] += 1

#
# Root events
#
# Events that are not reachable from these are considered to be unused test/debug events
#


root_event_set  = set()
root_event_list = []

def add_root_event(name):
    if name in event_dict:
        if name not in root_event_set:
            root_event_set.add(name)
            root_event_list.append(name)
    elif name in group_dict:
        for (_, ev) in group_dict[name]:
            add_root_event(ev)
    else:
        abort('event does not exist')

def add_root_group(name):
    if name in event_dict:
        if name not in root_event_set:
            root_event_set.add(name)
            root_event_list.append(name)
    elif name in group_dict:
        for (_, ev) in group_dict[name]:
            add_root_event(ev)
    else:
        abort('event does not exist')

def init_root_events():

    tree = ET.parse("sector_data.xml")
    for sector in tree.iterfind("sectorDescription"):
        start_event = sector.find("startEvent")
        if start_event is not None:
            add_root_event(start_event.text)
        for lst in sector.iterfind("event"):
            add_root_group(lst.get("name"))
    add_root_event('START_GAME')
    add_root_group('OVERRIDE_NEUTRAL')
    add_root_group('NO_FUEL')
    add_root_group('NO_FUEL_DISTRESS')

#
# HTML
#

# For checking missing events
printed_events = set()
printed_groups = set()
printed_ships = set()

def goto_url(url):
    print('<ul><li>Goto {url}</ul>'.format(url = url))

def goto_group_or_event(name):
    if   name in group_dict:
        if group_nparents[name] == 1: output_group(name)
        else: goto_url(group_link(name))          
    elif name in event_dict:
        if event_nparents[name] == 1: output_event(name)
        else: goto_url(event_link(name))
    else:
        assert False

def goto_event_or_group(name):
    if name in event_dict:
        if event_nparents[name] == 1: output_event(name)
        else: goto_url(event_link(name))
    elif   name in group_dict:
        if group_nparents[name] == 1: output_group(name)
        else: goto_url(group_link(name))
    else:
        assert False

def output_event(eventID, is_root=False):
    event = event_dict[eventID]
    printed_events.add(eventID)

    if is_root or (event.choices and len(event.choices) >= 2):
        # Don't print the text for events without a choice,
        # This reduces clutter, and the total Kb of the webpage.
        print(event.text_html)

    print(event.actions_html)

    if event.choices and event.fight:
        log('choice and ship fight: '+ eventID)

    if event.choices:
        print('<ol>')
        for (text, is_blue, nextID) in event.choices:
            cls = 'option blue' if is_blue else 'option'
            print('<li><span class="{cls}">{text}</span>'.format(cls = H(cls), text = H(text)))
            print('<div>')
            goto_group_or_event(nextID)
            print('</div>')
        print('</ol>')

    #if event.fight:
        #print('Show fight results here')

def output_group(groupID):
    group = group_dict[groupID]
    printed_groups.add(groupID)

    if len(group) == 1:
        # Simple case of no choice
        (_, nextID) = group[0]
        goto_event_or_group(nextID)

    else:
    
        m = 0
        for (weight, _) in group:
            m += weight

        print('<ul>')
        for (n, nextID) in group:
            print('<li> {n}/{m}'.format(n = H(str(n)), m = H(str(m))))
            #print('<li> {p}%'.format(p =  "%.0f"%math.floor(100.0 * n / m)))
            goto_event_or_group(nextID)
        print('</ul>')

def output_ship(shipID):
    ship = ship_dict[shipID]
    printed_ships.add(shipID)

    def case(evtID, msg):
        print('<li><em>{msg}'.format(msg = H(msg)))
        print('<div>')
        goto_group_or_event(evtID)
        print('</div>')

    destroyed = ship.get('destroyed')
    dead_crew = ship.get('dead_crew')
    gotaway   = ship.get('gotaway')
    surrender = ship.get('surrender')

    print('<ul>')
    if destroyed: case(destroyed, "You destroy the enemy ship")
    if dead_crew: case(dead_crew, "You kill the enemy crew")
    if gotaway:   case(gotaway,   "The enemy ship escaped")
    if surrender: case(surrender, "The enemy ship offers to surrender")
    print('</ul>')



def output_html():

    print("""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>FTL Cheatsheet</h1>
    <p>This page summarizes all the events in <a href="https://subsetgames.com/ftl.html">FTL Advanced Edition</a>.
       I created it because I got tired of wading through slow wiki pages and unreadable XML data files,
       when I am trying to remember what a particular event does.
       Use Ctrl-F to find the event your are looking for, and have fun!
       <p>Note: Some events in the list may be test/debug events, which cannot be encountered via normal gameplay.""")

    # Events
    print('<h1>Events</h1>')
    for key in event_dict:
        if event_nparents[key] != 1:
            print('<h2 id="event-{key}">{key}</h2>'.format(key = H(key)))
            print('<div class="indent">')
            output_event(key, is_root=True)
            print('</div>')

    # Event groups
    print('<h1>Event Pools</h1>')
    for key in group_dict:   
        print('<h2 id="list-{key}">{key}</h2>'.format(key = H(key)))
        print('<div class="indent">')
        output_group(key)
        print('</div>')
        
    # Ships
    print('<h1>Fights</h1>')
    for key in ship_dict:
        print('<h2 id="ship-{key}">{key}</h2>'.format(key = H(key)))
        print('<div class="indent">')
        output_ship(key)
        print('</div>')

    print("""
</body>
</html>""")

#
# Main
#


def main():

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

    for e in event_dict:
        if e not in printed_events:
            log("!!"+e)

    log('DISTRESS_ENGI_REBEL_RESULT' in event_dict)

if __name__ == "__main__":
    main()
