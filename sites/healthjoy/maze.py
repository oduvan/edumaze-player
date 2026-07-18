# -*- coding: utf-8 -*-
"""A maze that WALKS https://www.healthjoy.com/ by clicking real links.

Read-only: HealthJoy is a third-party production site, so this maze only clicks
navigation links and checks each page renders. It never submits the contact or
login forms.

How it walks: every page carries the same footer navigation, so the shared
``footer_nav()`` below is the set of links the walker actually clicks to move
between pages. The walker starts at Home and hops page → page by clicking those
links — it does not open URLs directly. Each page is identified by its URL path
and considered healthy when its hero heading has rendered.

(The header nav is a hover mega-menu whose links aren't reliably clickable; the
footer exposes the same destinations as plain, clickable links, so we walk via
the footer.)
"""
from edumaze import Budgets, Node, Site


class Marketing(Node):
    """A public HealthJoy page. Healthy == its hero heading rendered.

    Every page shares the footer, so every page offers the same links to click.
    """

    heading = ""

    def matches(self, page):
        # Identity = correct URL path AND the hero heading has rendered. Tying
        # identity to the heading means the walker's settle-wait pauses until the
        # (Framer) page finishes rendering before it's judged — no false
        # "did-not-render" on a page that simply hadn't painted yet.
        return super().matches(page) and \
            page.by_role("heading", name=self.heading).visible()

    def accept(self, page):
        assert page.by_role("heading", name=self.heading).visible(), \
            f"{self.url}: hero heading {self.heading!r} did not render"

    def footer_nav(self):
        # Each entry is a real footer link the walker clicks by its visible text.
        return [
            self.go("The Benefits Operating System", to=BenefitsOS),
            self.go("Member Experience", to=MemberExperience),
            self.go("Client Dashboard", to=ClientDashboard),
            self.go("Care Partners", to=CarePartners),
            self.go("For Benefit Consultants", to=BenefitConsultants),
            self.go("For Employers", to=Employers),
            self.go("About Us", to=About),
            self.go("Blog", to=Resources),
            self.go("See HealthJoy in Action", to=Contact),
            self.go("Privacy Policy", to=Privacy),
            self.go("Terms of Use", to=Terms),
        ]

    def options(self):
        return self.footer_nav()


# Every page below is one class: its URL (identity) + hero heading (health).
# They all inherit the footer_nav() above as their set of clickable moves.
class Home(Marketing):
    url = "/"
    heading = "One Platform"


class BenefitsOS(Marketing):
    url = "/what-we-do/benefitsoperatingsystem"
    heading = "One Benefits"


class MemberExperience(Marketing):
    url = "/what-we-do/member-experience"
    heading = "A Benefits Experience"


class ClientDashboard(Marketing):
    url = "/what-we-do/client-dash"
    heading = "Data-Driven"


class CarePartners(Marketing):
    url = "/care-partners"
    heading = "curated network"


class BenefitConsultants(Marketing):
    url = "/who-we-serve/benefit-consultants"
    heading = "Stop Chasing Engagement"


class Employers(Marketing):
    url = "/who-we-serve/employers"
    heading = "Great Plans"


class About(Marketing):
    url = "/company/about"
    heading = "Benefits Engineered for Outcomes"


class Resources(Marketing):
    url = "/resources"
    heading = "Insights From HealthJoy"


class Contact(Marketing):
    # Has a demo-request form; we click TO it but never submit it.
    url = "/contact"
    heading = "See HealthJoy In Action"


class Privacy(Marketing):
    url = "/privacy-policy"
    heading = "Privacy Policy"


class Terms(Marketing):
    url = "/terms-of-use"
    heading = "Terms of Use"


class HealthJoy(Site):
    id = "healthjoy"
    base_url = "https://www.healthjoy.com/"
    domain_allowlist = ["www.healthjoy.com"]  # stay on-site; external links not modeled
    entry = Home
    roles = []                                 # public site, no login
    budgets = Budgets(max_actions=18)          # a bounded walk, not full N×N coverage
    seed_data = {}
