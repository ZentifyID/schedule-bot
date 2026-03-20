"""Shared constants for schedule bot."""

from __future__ import annotations

RU_NUMERATOR = "\u0447\u0438\u0441\u043b\u0438\u0442\u0435\u043b\u044c"
RU_DENOMINATOR = "\u0437\u043d\u0430\u043c\u0435\u043d\u0430\u0442\u0435\u043b\u044c"
RU_NO = "\u043d\u0435\u0442"

WEEKDAY_MON = "\u043f\u043e\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u0438\u043a"
WEEKDAY_TUE = "\u0432\u0442\u043e\u0440\u043d\u0438\u043a"
WEEKDAY_WED = "\u0441\u0440\u0435\u0434\u0430"
WEEKDAY_THU = "\u0447\u0435\u0442\u0432\u0435\u0440\u0433"
WEEKDAY_FRI = "\u043f\u044f\u0442\u043d\u0438\u0446\u0430"
WEEKDAY_SAT = "\u0441\u0443\u0431\u0431\u043e\u0442\u0430"
WEEKDAY_SUN = "\u0432\u043e\u0441\u043a\u0440\u0435\u0441\u0435\u043d\u044c\u0435"

WEEKDAYS_WORKING = [WEEKDAY_MON, WEEKDAY_TUE, WEEKDAY_WED, WEEKDAY_THU, WEEKDAY_FRI]
WEEKDAY_RU = {
    0: WEEKDAY_MON,
    1: WEEKDAY_TUE,
    2: WEEKDAY_WED,
    3: WEEKDAY_THU,
    4: WEEKDAY_FRI,
    5: WEEKDAY_SAT,
    6: WEEKDAY_SUN,
}

MONTHS_RU = {
    "\u044f\u043d\u0432\u0430\u0440\u044f": 1,
    "\u0444\u0435\u0432\u0440\u0430\u043b\u044f": 2,
    "\u043c\u0430\u0440\u0442\u0430": 3,
    "\u0430\u043f\u0440\u0435\u043b\u044f": 4,
    "\u043c\u0430\u044f": 5,
    "\u0438\u044e\u043d\u044f": 6,
    "\u0438\u044e\u043b\u044f": 7,
    "\u0430\u0432\u0433\u0443\u0441\u0442\u0430": 8,
    "\u0441\u0435\u043d\u0442\u044f\u0431\u0440\u044f": 9,
    "\u043e\u043a\u0442\u044f\u0431\u0440\u044f": 10,
    "\u043d\u043e\u044f\u0431\u0440\u044f": 11,
    "\u0434\u0435\u043a\u0430\u0431\u0440\u044f": 12,
}

ROMAN_ORDER = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
}

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
