"""Aspect interpretations"""

from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)


# Aspect interpretation keywords for enhanced output
ASPECT_INTERPRETATIONS = {
    'conjunction': {
        'keywords': ['fusion', 'intensity', 'new beginnings'],
        'nature': 'variable',
        'description': 'Merging of energies, can be harmonious or challenging depending on planets'
    },
    'opposition': {
        'keywords': ['tension', 'awareness', 'projection', 'relationships'],
        'nature': 'challenging',
        'description': 'Polarization requiring integration and balance'
    },
    'square': {
        'keywords': ['friction', 'action', 'challenge', 'growth'],
        'nature': 'challenging',
        'description': 'Dynamic tension that motivates change and development'
    },
    'trine': {
        'keywords': ['harmony', 'flow', 'ease', 'talent'],
        'nature': 'benefic',
        'description': 'Natural gifts and smooth energy flow'
    },
    'sextile': {
        'keywords': ['opportunity', 'cooperation', 'skill'],
        'nature': 'benefic',
        'description': 'Supportive energy that requires activation'
    },
    'quincunx': {
        'keywords': ['adjustment', 'health', 'service'],
        'nature': 'variable',
        'description': 'Requires adaptation and fine-tuning'
    },
    'semi-sextile': {
        'keywords': ['subtle', 'growth', 'awareness'],
        'nature': 'minor',
        'description': 'Mild supportive influence requiring attention'
    },
    'semi-square': {
        'keywords': ['irritation', 'minor friction', 'motivation'],
        'nature': 'minor challenging',
        'description': 'Minor tension that prompts small adjustments'
    },
    'sesquiquadrate': {
        'keywords': ['agitation', 'restlessness', 'drive'],
        'nature': 'minor challenging',
        'description': 'Persistent tension requiring resolution'
    }
}


# Planet combination specific interpretations
# Format: (planet1, planet2, aspect_type): {keywords, nature, description}
PLANET_COMBINATION_INTERPRETATIONS = {
    # Sun combinations (9 entries)
    ('Moon', 'Sun', 'conjunction'): {
        'keywords': ['integration', 'wholeness', 'new beginning', 'conscious emotion'],
        'nature': 'variable',
        'description': 'Unity of will and feeling, emotional clarity'
    },
    ('Sun', 'Venus', 'conjunction'): {
        'keywords': ['charm', 'creativity', 'pleasure', 'self-worth', 'beauty'],
        'nature': 'benefic',
        'description': 'Enhanced attractiveness and creative self-expression'
    },
    ('Mars', 'Sun', 'conjunction'): {
        'keywords': ['courage', 'drive', 'assertion', 'action', 'potential conflict'],
        'nature': 'variable',
        'description': 'Dynamic energy, assertiveness, need for action'
    },
    ('Jupiter', 'Sun', 'conjunction'): {
        'keywords': ['confidence', 'expansion', 'opportunity', 'optimism', 'success'],
        'nature': 'benefic',
        'description': 'Enhanced vitality, confidence, and opportunities for growth'
    },
    ('Saturn', 'Sun', 'conjunction'): {
        'keywords': ['discipline', 'responsibility', 'limitation', 'maturity', 'challenge'],
        'nature': 'variable',
        'description': 'Serious focus, self-discipline, karmic lessons'
    },
    ('Sun', 'Uranus', 'conjunction'): {
        'keywords': ['innovation', 'independence', 'breakthrough', 'sudden change', 'awakening'],
        'nature': 'inspirational',
        'description': 'Unique self-expression, sudden insights, need for freedom'
    },
    ('Neptune', 'Sun', 'conjunction'): {
        'keywords': ['inspiration', 'spirituality', 'idealism', 'confusion', 'transcendence'],
        'nature': 'inspirational',
        'description': 'Heightened sensitivity, spiritual awareness, potential confusion about identity'
    },
    ('Pluto', 'Sun', 'conjunction'): {
        'keywords': ['transformation', 'power', 'intensity', 'rebirth', 'control'],
        'nature': 'transformative',
        'description': 'Deep transformation of identity, power dynamics, regeneration'
    },
    ('Mercury', 'Sun', 'conjunction'): {
        'keywords': ['mental clarity', 'communication', 'learning', 'awareness', 'thought'],
        'nature': 'variable',
        'description': 'Enhanced mental focus, clear communication of will'
    },

    # Moon combinations (8 entries - Sun already covered above)
    ('Moon', 'Venus', 'conjunction'): {
        'keywords': ['emotional harmony', 'love', 'comfort', 'nurturing', 'beauty'],
        'nature': 'benefic',
        'description': 'Emotional warmth, artistic sensitivity, need for harmony'
    },
    ('Mars', 'Moon', 'conjunction'): {
        'keywords': ['emotional intensity', 'reactive', 'passion', 'urgency', 'defensiveness'],
        'nature': 'variable',
        'description': 'Emotional volatility, instinctive action, protective impulses'
    },
    ('Jupiter', 'Moon', 'conjunction'): {
        'keywords': ['emotional generosity', 'optimism', 'protection', 'abundance', 'faith'],
        'nature': 'benefic',
        'description': 'Emotional expansiveness, faith, generosity of feeling'
    },
    ('Moon', 'Saturn', 'conjunction'): {
        'keywords': ['emotional control', 'seriousness', 'duty', 'restriction', 'maturity'],
        'nature': 'variable',
        'description': 'Emotional reserve, sense of duty, need for security'
    },
    ('Moon', 'Uranus', 'conjunction'): {
        'keywords': ['emotional freedom', 'unpredictability', 'excitement', 'change', 'awakening'],
        'nature': 'inspirational',
        'description': 'Emotional independence, sudden mood changes, need for excitement'
    },
    ('Moon', 'Neptune', 'conjunction'): {
        'keywords': ['emotional sensitivity', 'empathy', 'psychic', 'idealism', 'confusion'],
        'nature': 'inspirational',
        'description': 'Deep emotional sensitivity, psychic receptivity, boundary dissolution'
    },
    ('Moon', 'Pluto', 'conjunction'): {
        'keywords': ['emotional transformation', 'intensity', 'depth', 'power', 'catharsis'],
        'nature': 'transformative',
        'description': 'Deep emotional transformation, powerful feelings, psychological insight'
    },
    ('Mercury', 'Moon', 'conjunction'): {
        'keywords': ['emotional expression', 'intuitive thinking', 'communication', 'memory', 'perception'],
        'nature': 'variable',
        'description': 'Integration of feeling and thought, emotional intelligence'
    },

    # Mercury combinations (7 entries - Sun and Moon already covered)
    ('Mercury', 'Venus', 'conjunction'): {
        'keywords': ['diplomatic', 'artistic expression', 'charm', 'pleasant communication', 'aesthetics'],
        'nature': 'benefic',
        'description': 'Charming communication, artistic thinking, diplomatic expression'
    },
    ('Mars', 'Mercury', 'conjunction'): {
        'keywords': ['quick thinking', 'sharp speech', 'debate', 'mental energy', 'argument'],
        'nature': 'variable',
        'description': 'Quick, decisive thinking, assertive communication, potential arguments'
    },
    ('Jupiter', 'Mercury', 'conjunction'): {
        'keywords': ['optimistic thinking', 'learning', 'wisdom', 'teaching', 'expansion'],
        'nature': 'benefic',
        'description': 'Optimistic mindset, love of learning, philosophical thinking'
    },
    ('Mercury', 'Saturn', 'conjunction'): {
        'keywords': ['serious thinking', 'concentration', 'practicality', 'criticism', 'discipline'],
        'nature': 'variable',
        'description': 'Methodical thinking, concentration, practical communication'
    },
    ('Mercury', 'Uranus', 'conjunction'): {
        'keywords': ['innovative thinking', 'genius', 'originality', 'sudden insight', 'unconventional'],
        'nature': 'inspirational',
        'description': 'Original thinking, sudden insights, unconventional communication'
    },
    ('Mercury', 'Neptune', 'conjunction'): {
        'keywords': ['imaginative thinking', 'intuition', 'creativity', 'confusion', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Imaginative thinking, intuitive perception, potential for confusion'
    },
    ('Mercury', 'Pluto', 'conjunction'): {
        'keywords': ['deep thinking', 'penetrating insight', 'persuasion', 'obsession', 'research'],
        'nature': 'transformative',
        'description': 'Penetrating mind, investigative thinking, transformative ideas'
    },

    # Venus combinations (6 entries - Sun, Moon, Mercury already covered)
    ('Mars', 'Venus', 'conjunction'): {
        'keywords': ['passion', 'attraction', 'desire', 'creativity', 'magnetism'],
        'nature': 'variable',
        'description': 'Passionate attraction, creative drive, sexual magnetism'
    },
    ('Jupiter', 'Venus', 'conjunction'): {
        'keywords': ['joy', 'abundance', 'love', 'generosity', 'beauty'],
        'nature': 'benefic',
        'description': 'Enhanced love and beauty, social success, generosity'
    },
    ('Saturn', 'Venus', 'conjunction'): {
        'keywords': ['commitment', 'loyalty', 'limitation', 'seriousness', 'duty in love'],
        'nature': 'variable',
        'description': 'Serious commitment, loyalty, potential restriction in love'
    },
    ('Uranus', 'Venus', 'conjunction'): {
        'keywords': ['unconventional love', 'excitement', 'freedom', 'attraction', 'change'],
        'nature': 'inspirational',
        'description': 'Unconventional relationships, sudden attractions, need for freedom in love'
    },
    ('Neptune', 'Venus', 'conjunction'): {
        'keywords': ['romantic idealism', 'spiritual love', 'compassion', 'illusion', 'transcendence'],
        'nature': 'inspirational',
        'description': 'Idealistic love, spiritual connection, potential for illusion'
    },
    ('Pluto', 'Venus', 'conjunction'): {
        'keywords': ['intense love', 'transformation', 'passion', 'obsession', 'depth'],
        'nature': 'transformative',
        'description': 'Intense, transformative love, deep passion, power in relationships'
    },

    # Mars combinations (5 entries - Sun, Moon, Mercury, Venus already covered)
    ('Jupiter', 'Mars', 'conjunction'): {
        'keywords': ['enthusiasm', 'courage', 'adventure', 'success', 'excess energy'],
        'nature': 'benefic',
        'description': 'Enthusiastic action, courage, success through initiative'
    },
    ('Mars', 'Saturn', 'conjunction'): {
        'keywords': ['controlled energy', 'frustration', 'discipline', 'endurance', 'strategic'],
        'nature': 'variable',
        'description': 'Disciplined action, controlled energy, potential frustration'
    },
    ('Mars', 'Uranus', 'conjunction'): {
        'keywords': ['sudden action', 'rebellion', 'innovation', 'breakthrough', 'impulsiveness'],
        'nature': 'inspirational',
        'description': 'Sudden, innovative action, breakthrough energy, potential recklessness'
    },
    ('Mars', 'Neptune', 'conjunction'): {
        'keywords': ['inspired action', 'confusion', 'idealism', 'spiritual drive', 'deception'],
        'nature': 'inspirational',
        'description': 'Inspired action, spiritual drive, potential confusion or deception'
    },
    ('Mars', 'Pluto', 'conjunction'): {
        'keywords': ['intense power', 'transformation', 'force', 'control', 'regeneration'],
        'nature': 'transformative',
        'description': 'Powerful transformative energy, intense drive, potential for control issues'
    },

    # Jupiter combinations (4 entries - Sun, Moon, Mercury, Venus, Mars already covered)
    ('Jupiter', 'Saturn', 'conjunction'): {
        'keywords': ['balanced growth', 'wisdom', 'structure', 'social order', 'responsibility'],
        'nature': 'variable',
        'description': 'Balance between expansion and contraction, structured growth'
    },
    ('Jupiter', 'Uranus', 'conjunction'): {
        'keywords': ['breakthrough', 'innovation', 'opportunity', 'freedom', 'sudden expansion'],
        'nature': 'inspirational',
        'description': 'Sudden opportunities, innovative growth, breakthrough expansion'
    },
    ('Jupiter', 'Neptune', 'conjunction'): {
        'keywords': ['spiritual growth', 'idealism', 'compassion', 'faith', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Spiritual expansion, idealistic vision, compassionate growth'
    },
    ('Jupiter', 'Pluto', 'conjunction'): {
        'keywords': ['transformation', 'power', 'success', 'intensity', 'regeneration'],
        'nature': 'transformative',
        'description': 'Powerful transformation, deep growth, success through transformation'
    },

    # Saturn combinations (3 entries - Sun, Moon, Mercury, Venus, Mars, Jupiter already covered)
    ('Saturn', 'Uranus', 'conjunction'): {
        'keywords': ['structured innovation', 'rebellion vs authority', 'breakthrough', 'tension', 'reform'],
        'nature': 'variable',
        'description': 'Tension between old and new, structured innovation, reform'
    },
    ('Neptune', 'Saturn', 'conjunction'): {
        'keywords': ['practical idealism', 'manifesting dreams', 'discipline', 'reality check', 'structure'],
        'nature': 'variable',
        'description': 'Manifesting ideals into reality, practical spirituality'
    },
    ('Pluto', 'Saturn', 'conjunction'): {
        'keywords': ['deep transformation', 'power', 'authority', 'reconstruction', 'karmic'],
        'nature': 'transformative',
        'description': 'Deep structural transformation, karmic authority, rebuilding foundations'
    },

    # Outer planet combinations (3 entries)
    ('Neptune', 'Uranus', 'conjunction'): {
        'keywords': ['visionary', 'spiritual awakening', 'innovation', 'idealism', 'inspiration'],
        'nature': 'inspirational',
        'description': 'Visionary innovation, spiritual awakening, inspired idealism'
    },
    ('Pluto', 'Uranus', 'conjunction'): {
        'keywords': ['revolutionary', 'breakthrough', 'transformation', 'liberation', 'upheaval'],
        'nature': 'transformative',
        'description': 'Revolutionary transformation, breakthrough change, liberation'
    },
    ('Neptune', 'Pluto', 'conjunction'): {
        'keywords': ['spiritual transformation', 'collective evolution', 'deep healing', 'transcendence', 'regeneration'],
        'nature': 'transformative',
        'description': 'Deep spiritual transformation, collective regeneration'
    },

    # Opposition aspects - key planet pairs
    ('Moon', 'Sun', 'opposition'): {
        'keywords': ['awareness', 'tension', 'full moon energy', 'relationship', 'culmination'],
        'nature': 'variable',
        'description': 'Conscious awareness of inner dynamics, relationship tension'
    },
    ('Jupiter', 'Sun', 'opposition'): {
        'keywords': ['overconfidence', 'expansion', 'growth through challenge', 'excess', 'learning'],
        'nature': 'growth-oriented',
        'description': 'Growth through opposition, learning through excess or overconfidence'
    },
    ('Saturn', 'Sun', 'opposition'): {
        'keywords': ['restriction', 'authority conflict', 'maturity', 'responsibility', 'limitation'],
        'nature': 'challenging',
        'description': 'Tension with authority, learning discipline and responsibility'
    },

    # Square aspects - key planet pairs
    ('Mars', 'Sun', 'square'): {
        'keywords': ['conflict', 'assertion', 'energy blocks', 'frustration', 'action'],
        'nature': 'challenging',
        'description': 'Energy conflicts, frustration leading to action, assertion challenges'
    },
    ('Jupiter', 'Sun', 'square'): {
        'keywords': ['overextension', 'growth', 'learning', 'excess', 'opportunity through challenge'],
        'nature': 'growth-oriented',
        'description': 'Growth through overextension, learning from excess'
    },
    ('Saturn', 'Sun', 'square'): {
        'keywords': ['obstacle', 'discipline', 'limitation', 'hard work', 'maturity'],
        'nature': 'challenging',
        'description': 'Obstacles requiring discipline, hard work leading to maturity'
    },
    ('Mars', 'Moon', 'square'): {
        'keywords': ['emotional tension', 'reactive', 'anger', 'urgency', 'action'],
        'nature': 'challenging',
        'description': 'Emotional volatility, reactive behavior, urgency to act'
    },

    # Trine aspects - key planet pairs
    ('Jupiter', 'Sun', 'trine'): {
        'keywords': ['confidence', 'success', 'growth', 'opportunity', 'optimism'],
        'nature': 'benefic',
        'description': 'Natural confidence, easy growth opportunities, success'
    },
    ('Saturn', 'Sun', 'trine'): {
        'keywords': ['discipline', 'achievement', 'structure', 'maturity', 'endurance'],
        'nature': 'benefic',
        'description': 'Natural discipline, steady achievement, structured success'
    },
    ('Mars', 'Sun', 'trine'): {
        'keywords': ['energy', 'courage', 'action', 'vitality', 'success'],
        'nature': 'benefic',
        'description': 'Natural energy flow, courageous action, vital success'
    },
    ('Moon', 'Sun', 'trine'): {
        'keywords': ['harmony', 'emotional balance', 'flow', 'integration', 'ease'],
        'nature': 'benefic',
        'description': 'Natural harmony between will and feeling, emotional ease'
    },

    # Sextile aspects - key planet pairs
    ('Jupiter', 'Sun', 'sextile'): {
        'keywords': ['opportunity', 'growth', 'optimism', 'potential', 'expansion'],
        'nature': 'benefic',
        'description': 'Growth opportunities requiring initiative, positive potential'
    },
    ('Saturn', 'Sun', 'sextile'): {
        'keywords': ['practical', 'opportunity', 'discipline', 'achievement', 'structure'],
        'nature': 'benefic',
        'description': 'Practical opportunities, disciplined achievement'
    },
    ('Mars', 'Sun', 'sextile'): {
        'keywords': ['energy', 'opportunity', 'action', 'initiative', 'courage'],
        'nature': 'benefic',
        'description': 'Energetic opportunities, action-oriented initiative'
    },
}


def get_planet_pair_key(obj1: str, obj2: str, aspect_type: str) -> tuple:
    """Create normalized key for planet pair lookups (alphabetically sorted)."""
    planets = sorted([obj1, obj2])
    return (planets[0], planets[1], aspect_type.lower())


def get_context_aware_interpretation(obj1: str, obj2: str, aspect_type: str) -> Dict[str, Any]:
    """
    Get interpretation based on planet combination and aspect type.

    Priority:
    1. Exact planet-pair + aspect match
    2. Jupiter benefic bias (growth-oriented for square/opposition)
    3. Pluto/Chiron = transformative
    4. Neptune/Uranus = inspirational
    5. Generic aspect interpretation (fallback)
    """
    # Try planet-specific interpretation first
    pair_key = get_planet_pair_key(obj1, obj2, aspect_type)
    if pair_key in PLANET_COMBINATION_INTERPRETATIONS:
        return PLANET_COMBINATION_INTERPRETATIONS[pair_key]

    # Jupiter benefic bias
    if 'Jupiter' in [obj1, obj2] and aspect_type.lower() in ['opposition', 'square']:
        return {
            'keywords': ['growth', 'expansion', 'excess', 'learning', 'opportunity'],
            'nature': 'growth-oriented',
            'description': f'Jupiter {aspect_type} brings growth through challenge'
        }

    # Pluto/Chiron = transformative
    if any(p in [obj1, obj2] for p in ['Pluto', 'Chiron']):
        base_interp = ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {})
        return {
            'keywords': base_interp.get('keywords', []) + ['transformation'],
            'nature': 'transformative',
            'description': base_interp.get('description', '')
        }

    # Neptune/Uranus = inspirational
    if any(p in [obj1, obj2] for p in ['Neptune', 'Uranus']):
        base_interp = ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {})
        return {
            'keywords': base_interp.get('keywords', []) + ['inspiration'],
            'nature': 'inspirational',
            'description': base_interp.get('description', '')
        }

    # Fallback to generic
    return ASPECT_INTERPRETATIONS.get(aspect_type.lower(), {
        'keywords': ['energy', 'connection', 'influence'],
        'nature': 'variable',
        'description': 'Planetary interaction'
    })


def normalize_aspects_to_list(aspects: Union[List[Dict[str, Any]], Dict[str, Any]],
                              filter_self_aspects: bool = True) -> List[Dict[str, Any]]:
    """
    Normalize aspects data to a flat list format and optionally filter self-aspects.

    The compact serializer returns aspects as a list for regular charts,
    but synastry/transit charts with aspects_to may return nested dicts.

    Args:
        aspects: Either a list of aspect dicts, or a nested dict structure
                 from synastry/transit charts
        filter_self_aspects: If True, remove aspects where active == passive
                           (default: True, as self-aspects are astrologically meaningless)

    Returns:
        Flat list of aspect dictionaries with self-aspects removed
    """
    aspect_list = []

    if isinstance(aspects, list):
        aspect_list = aspects
    elif isinstance(aspects, dict):
        # Handle nested dict format: {from_id: {to_id: aspect_data}}
        for from_key, to_aspects in aspects.items():
            if isinstance(to_aspects, dict):
                for to_key, aspect_data in to_aspects.items():
                    if isinstance(aspect_data, dict):
                        aspect_list.append(aspect_data)

    # Filter out self-aspects if requested
    if filter_self_aspects:
        original_count = len(aspect_list)
        aspect_list = [
            asp for asp in aspect_list
            if isinstance(asp, dict) and asp.get('active') != asp.get('passive')
        ]
        filtered_count = original_count - len(aspect_list)
        if filtered_count > 0:
            logger.debug(f"Filtered {filtered_count} self-aspects, {len(aspect_list)} aspects remaining")

    return aspect_list


def add_aspect_interpretations(aspects: Union[List[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance aspect data with context-aware interpretation based on planet combinations.

    Args:
        aspects: List of aspect dictionaries or nested dict structure

    Returns:
        Enhanced aspect list with planet-pair specific interpretation keywords
    """
    # Normalize to list and filter self-aspects
    aspect_list = normalize_aspects_to_list(aspects, filter_self_aspects=True)

    enhanced = []
    for aspect in aspect_list:
        if not isinstance(aspect, dict):
            continue

        obj1 = aspect.get('object1', '')
        obj2 = aspect.get('object2', '')
        aspect_type = aspect.get('type', '')

        # Get context-aware interpretation
        interp = get_context_aware_interpretation(obj1, obj2, aspect_type)

        aspect['keywords'] = interp.get('keywords', [])
        aspect['nature'] = interp.get('nature', 'variable')

        # Optional detailed interpretation
        if 'description' in interp:
            aspect['interpretation'] = interp['description']

        enhanced.append(aspect)

    logger.debug(f"Added context-aware interpretations to {len(enhanced)} aspects")
    return enhanced
