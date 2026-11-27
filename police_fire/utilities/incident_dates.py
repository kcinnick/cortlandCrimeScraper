"""Resolve reported event dates without paid APIs or publication-date defaults."""
from datetime import date, datetime, timedelta
import re


WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july',
          'august', 'september', 'october', 'november', 'december')
MONTH_PATTERN = '|'.join(month[:3] + r'(?:' + month[3:] + r')?\.?' for month in MONTHS)
DATE_PATTERN = (
    r'(?:(?:last|this|next)\s+)?(?:' + '|'.join(WEEKDAYS) + r')\b'
    r'|yesterday\b|today\b|\d{4}-\d{2}-\d{2}\b'
    r'|(?:' + MONTH_PATTERN + r')\s+\d{1,2}(?:st|nd|rd|th)?\b(?:,?\s+\d{4}\b)?'
)
# Only dates attached to past event verbs, not arbitrary court/hearing dates.
EVENT_DATE = re.compile(
    r'\b(?P<event>occurred|happened|charged|arrested|reported|crashed|assaulted|stole)'
    r'\s+(?:(?:on|early|late|at|the)\s+|\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\s+)*'
    r'(?P<date>' + DATE_PATTERN + r')', re.IGNORECASE,
)


def publication_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def resolve_reference(reference, published):
    reference = reference.lower().strip()
    if reference.startswith('next '):
        return None
    weekday = reference.split()[-1]
    if weekday in WEEKDAYS:
        offset = (published.weekday() - WEEKDAYS.index(weekday)) % 7
        if reference.startswith('last ') and offset == 0:
            offset = 7
        return published - timedelta(days=offset)
    if reference in ('today', 'yesterday'):
        return published - timedelta(days=reference == 'yesterday')
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', reference):
            result = date.fromisoformat(reference)
        else:
            match = re.fullmatch(
                r'([a-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?', reference,
            )
            if not match:
                return None
            month_name, day, year = match.groups()
            month = next(index for index, name in enumerate(MONTHS, 1)
                         if name == month_name or name[:3] == month_name)
            result = date(int(year) if year else published.year, month, int(day))
            if not year and result > published:
                result = result.replace(year=published.year - 1)
        return result if result <= published else None
    except (ValueError, StopIteration):
        return None


def infer_incident_date(details, legal_actions, published):
    """Prefer an occurrence date; otherwise use an explicitly dated arrest/charge.

    Input must describe ONE incident, not a multi-incident article. Conflicting
    references stay unknown. Bare weekdays mean the latest day on or before
    publication, so a Tuesday event in a Tuesday article can be that same day.
    """
    published = publication_date(published)
    occurrence_dates, other_dates = set(), set()
    unresolved_occurrence = False
    for text in (details or '', legal_actions or ''):
        for match in EVENT_DATE.finditer(text):
            occurrence = match['event'].lower() in {'occurred', 'happened', 'crashed', 'assaulted', 'stole'}
            resolved = resolve_reference(match['date'], published)
            if resolved is None:
                unresolved_occurrence = unresolved_occurrence or occurrence
                continue
            (occurrence_dates if occurrence else other_dates).add(resolved)
    if unresolved_occurrence:
        return None
    candidates = occurrence_dates or other_dates
    return next(iter(candidates)) if len(candidates) == 1 else None
