# -*- coding: utf-8 -*-
"""A maze for https://www.healthjoy.com/ — a multi-page marketing site.

Read-only: HealthJoy is a third-party production site, so this maze only
navigates public pages and checks each one renders. It never submits the
contact/demo or login forms (those pages are modeled, their forms left alone).

Because the header nav is a hover mega-menu (its links aren't reliably
clickable), pages are reached with ``visit(url)`` — direct navigation — which
is the natural fit for a deep-linkable content site. Each page is identified by
its URL path and considered healthy when its hero heading has rendered.
"""
from edumaze import Budgets, Node, Site

BASE = "https://www.healthjoy.com"


class Marketing(Node):
    """A public HealthJoy page. Healthy == its hero heading rendered."""

    heading = ""

    def accept(self, page):
        assert page.by_role("heading", name=self.heading).visible(), \
            f"{self.url}: hero heading {self.heading!r} did not render"

    def nav(self, *extra):
        """Links present on (almost) every page: home and the demo/contact CTA."""
        return [
            self.visit("Home", BASE + "/", to=Home),
            self.visit("Contact", BASE + "/contact", to=Contact),
            *extra,
        ]


# --- the hub ---------------------------------------------------------------
class Home(Marketing):
    url = "/"
    heading = "One Platform"

    def options(self):
        return [
            self.visit("Benefits Operating System",
                       BASE + "/what-we-do/benefitsoperatingsystem", to=BenefitsOS),
            self.visit("Member Experience",
                       BASE + "/what-we-do/member-experience", to=MemberExperience),
            self.visit("Client Dashboard",
                       BASE + "/what-we-do/client-dash", to=ClientDashboard),
            self.visit("Care Partners", BASE + "/care-partners", to=CarePartners),
            self.visit("Benefit Consultants",
                       BASE + "/who-we-serve/benefit-consultants", to=BenefitConsultants),
            self.visit("Employers",
                       BASE + "/who-we-serve/employers", to=Employers),
            self.visit("About", BASE + "/company/about", to=About),
            self.visit("Resources", BASE + "/resources", to=Resources),
            self.visit("Contact", BASE + "/contact", to=Contact),
            self.visit("Privacy Policy", BASE + "/privacy-policy", to=Privacy),
            self.visit("Terms of Use", BASE + "/terms-of-use", to=Terms),
        ]


# --- what we do ------------------------------------------------------------
class BenefitsOS(Marketing):
    url = "/what-we-do/benefitsoperatingsystem"
    heading = "One Benefits"
    def options(self): return self.nav()


class MemberExperience(Marketing):
    url = "/what-we-do/member-experience"
    heading = "A Benefits Experience"
    def options(self): return self.nav()


class ClientDashboard(Marketing):
    url = "/what-we-do/client-dash"
    heading = "Data-Driven"
    def options(self): return self.nav()


class CarePartners(Marketing):
    url = "/care-partners"
    heading = "curated network"
    def options(self): return self.nav()


# --- who we serve ----------------------------------------------------------
class BenefitConsultants(Marketing):
    url = "/who-we-serve/benefit-consultants"
    heading = "Stop Chasing Engagement"
    def options(self): return self.nav()


class Employers(Marketing):
    url = "/who-we-serve/employers"
    heading = "Great Plans"
    def options(self): return self.nav()


# --- company / content -----------------------------------------------------
class About(Marketing):
    url = "/company/about"
    heading = "Benefits Engineered for Outcomes"
    def options(self): return self.nav(
        self.visit("Care Partners", BASE + "/care-partners", to=CarePartners))


class Resources(Marketing):
    url = "/resources"
    heading = "Insights From HealthJoy"
    def options(self): return self.nav()


# --- form pages: modeled, but NEVER submitted ------------------------------
class Contact(Marketing):
    url = "/contact"
    heading = "See HealthJoy In Action"  # has a demo-request form; we don't fill it
    def options(self): return [self.visit("Home", BASE + "/", to=Home)]


# --- legal -----------------------------------------------------------------
class Privacy(Marketing):
    url = "/privacy-policy"
    heading = "Privacy Policy"
    def options(self): return [self.visit("Home", BASE + "/", to=Home)]


class Terms(Marketing):
    url = "/terms-of-use"
    heading = "Terms of Use"
    def options(self): return [self.visit("Home", BASE + "/", to=Home)]


class HealthJoy(Site):
    id = "healthjoy"
    base_url = BASE + "/"
    domain_allowlist = ["www.healthjoy.com"]  # stay on-site; external links not modeled
    entry = Home
    roles = []                                 # public site, no login
    budgets = Budgets(max_actions=40)
    seed_data = {}
