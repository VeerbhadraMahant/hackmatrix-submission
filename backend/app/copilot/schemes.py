"""Indian money deadlines and schemes, with dates computed from today's date.

Only fixed statutory / recurring dates are listed (advance tax, ITR, 80C year-end, quarterly small-savings
rate reviews). The government can extend or change any of them, so every item carries an official link
and the UI says to confirm there. One-off announcements (e.g. a new Sovereign Gold Bond tranche) are
NOT invented: the evergreen list tells the user to watch the official source instead.
"""
from __future__ import annotations

from datetime import date

NOTE = "These follow the usual yearly calendar. The government can extend or change them, so confirm on the official site."
IT = "https://www.incometax.gov.in"


def _next(month: int, day: int, today: date) -> date:
    d = date(today.year, month, day)
    return d if d >= today else date(today.year + 1, month, day)


# (id, name, what to do, month, day, link)
_DEADLINES = [
    ("adv-tax-jun", "Advance tax, 1st instalment", "15% of the year's tax if your tax after TDS is over ₹10,000.", 6, 15, IT),
    ("adv-tax-sep", "Advance tax, 2nd instalment", "Cumulative 45% of the year's tax.", 9, 15, IT),
    ("adv-tax-dec", "Advance tax, 3rd instalment", "Cumulative 75% of the year's tax.", 12, 15, IT),
    ("adv-tax-mar", "Advance tax, last instalment", "Full 100% of the year's tax.", 3, 15, IT),
    ("itr-jul", "Income tax return (non-audit)", "File last year's ITR. Salaried people usually file by this date.", 7, 31, IT),
    ("itr-belated", "Late / revised ITR cut-off", "Last chance to file a late or corrected return for the year.", 12, 31, IT),
    ("tax-save", "Tax-saving year end", "Last day of the financial year: ELSS, PPF, NPS (extra ₹50,000 under 80CCD(1B)), tax-saver FD under 80C.", 3, 31, IT),
    ("ppf-sukanya", "Keep PPF and Sukanya accounts active", "Deposit the yearly minimum (PPF ₹500, Sukanya ₹250) before the year ends.", 3, 31, "https://www.indiapost.gov.in"),
    ("rates-q", "Small-savings interest rates reviewed", "PPF, Sukanya, NSC and SCSS rates are reset each quarter, announced just before 1 Jan / Apr / Jul / Oct.", 1, 1, "https://www.nsiindia.gov.in"),
]

_EVERGREEN = [
    ("PM Jan Dhan Yojana", "Zero-balance savings account with RuPay card and accident cover. Open any time at a bank.", "https://pmjdy.gov.in"),
    ("Atal Pension Yojana", "Fixed monthly pension of ₹1,000 to ₹5,000 after age 60 for ages 18 to 40.", "https://www.npscra.nsdl.co.in"),
    ("PM Suraksha Bima / PM Jeevan Jyoti", "Very low-cost accident (₹20/yr) and life (₹436/yr) cover, renewed each year in May.", "https://www.jansuraksha.gov.in"),
    ("Sukanya Samriddhi Yojana", "High-interest savings for a girl child's education and marriage, tax-free under 80C.", "https://www.indiapost.gov.in"),
    ("National Pension System (NPS)", "Retirement investing with an extra ₹50,000 tax deduction under 80CCD(1B).", "https://www.npscra.nsdl.co.in"),
    ("Senior Citizen Savings Scheme", "Quarterly-interest savings for age 60+, up to ₹30 lakh.", "https://www.indiapost.gov.in"),
    ("Sovereign Gold Bonds", "Government gold bonds with 2.5% yearly interest. New tranches are announced by RBI when issued, so check rbi.org.in for the current one.", "https://www.rbi.org.in"),
]


def upcoming(today: date | None = None) -> dict:
    today = today or date.today()
    items = sorted(
        ({"id": i, "name": n, "what": w, "date": (d := _next(m, dd, today)).isoformat(), "days_left": (d - today).days, "link": link}
         for i, n, w, m, dd, link in _DEADLINES),
        key=lambda x: x["days_left"],
    )
    return {
        "today": today.isoformat(),
        "note": NOTE,
        "deadlines": items,
        "always_open": [{"name": n, "what": w, "link": link} for n, w, link in _EVERGREEN],
    }


def nudges(today: date | None = None, limit: int = 3) -> list[str]:
    """Friendly one-liners for the nearest deadlines, shown as chat messages."""
    out = []
    for it in upcoming(today)["deadlines"][:limit]:
        d = date.fromisoformat(it["date"])
        when = "today" if it["days_left"] == 0 else f"in {it['days_left']} days"
        out.append(f"Heads up: {it['name']} is {when} ({d.day} {d.strftime('%b %Y')}). {it['what']}")
    return out
