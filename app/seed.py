"""Idempotent seed script for initial production data.

Usage:
    uv run python -m app.seed

Seeds: 2 coaches (Alex + Atiyeh), 4 packages, 3 success stories. Re-running
upserts by slug; existing rows are updated in-place.
"""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.coach import Coach
from app.models.package import Package, PackageTier, PricingModel
from app.models.success_story import SuccessStory

log = structlog.get_logger(__name__)


@dataclass
class CoachSeed:
    email: str
    name: str
    slug: str
    title: str
    bio_short: str
    bio_long: str
    calendly_url: str
    sort_order: int


@dataclass
class PackageSeed:
    slug: str
    name: str
    tier: PackageTier
    pricing_model: PricingModel
    amount_cents: int
    description: str
    features: list[str]
    starting_from: bool = False


@dataclass
class SuccessStorySeed:
    slug: str
    client_name: str
    client_role_after: str
    client_company_after: str
    story_short: str
    coach_slug: str
    is_featured: bool
    sort_order: int
    story_long: str = ""
    client_role_before: str | None = None


COACHES_SEED: list[CoachSeed] = [
    CoachSeed(
        email="alex@career-flow.com",
        name="Alex Cakic",
        slug="alex",
        title="Career Coach, Co-founder",
        bio_short=(
            "Helps technical professionals turn ambition into a concrete career strategy — "
            "from job-search execution to leadership development."
        ),
        bio_long=(
            "Alex is a career coach and co-founder of Career Flow. He partners with software "
            "engineers, product managers, and tech leaders to translate big career ambition "
            "into specific, repeatable plays — building referral networks, sharpening "
            "interview craft, and positioning for senior roles. Before coaching he spent over "
            "a decade in product and engineering, and he sees coaching as the leverage point "
            "that compounds the right work."
        ),
        calendly_url="https://calendly.com/alex-career-flow/30min",
        sort_order=0,
    ),
    CoachSeed(
        email="atiyeh@career-flow.com",
        name="Atiyeh Keshavarz Safi",
        slug="atiyeh",
        title="Career Coach, Co-founder",
        bio_short=(
            "Works with career changers and mid-career operators to redefine their "
            "professional identity and step confidently into bigger roles."
        ),
        bio_long=(
            "Atiyeh is a career coach and co-founder of Career Flow. She works most closely "
            "with professionals navigating identity-defining career changes — pivoting "
            "industries, recovering momentum after a layoff, or stepping into senior "
            "leadership. Her coaching combines strategic clarity with the inner work that "
            "makes ambitious change sustainable."
        ),
        calendly_url="https://calendly.com/atiyeh-career-flow/30min",
        sort_order=1,
    ),
]


PACKAGES_SEED: list[PackageSeed] = [
    PackageSeed(
        slug="navigator",
        name="The Career Flow Navigator",
        tier=PackageTier.NAVIGATOR,
        pricing_model=PricingModel.SUBSCRIPTION_MONTHLY,
        amount_cents=120000,
        description=(
            "Designed for ambitious professionals strategically navigating the job market, "
            "breaking into competitive industries, and leveraging powerful networking for "
            "accelerated growth."
        ),
        features=[
            "Job search blueprint",
            "Referral mastery",
            "Interview confidence",
            "Resume optimisation",
            "Premium LinkedIn visibility",
            "Dedicated email and chat support",
        ],
    ),
    PackageSeed(
        slug="architect",
        name="The Professional Brand Architect",
        tier=PackageTier.ARCHITECT,
        pricing_model=PricingModel.SUBSCRIPTION_MONTHLY,
        amount_cents=160000,
        description=(
            "For professionals defining a unique professional identity, expanding influence, "
            "and positioning themselves for career advancement."
        ),
        features=[
            "Personal brand audit",
            "Leadership presence",
            "Leadership influence",
            "Corporate visibility strategy",
            "Strategic career conversations",
            "Networking for impact",
            "Real-time guidance",
        ],
    ),
    PackageSeed(
        slug="accelerator",
        name="The Holistic Career Accelerator",
        tier=PackageTier.ACCELERATOR,
        pricing_model=PricingModel.SUBSCRIPTION_MONTHLY,
        amount_cents=210000,
        starting_from=True,
        description=(
            "The ultimate partnership for a complete career overhaul — combining aggressive "
            "job-search strategies with deep personal branding and leadership development."
        ),
        features=[
            "All benefits of Navigator and Architect packages",
            "Integrated strategic planning",
            "Priority access and extended engagement",
            "Strategic introductions and unparalleled networking",
            "High-level career strategy and leadership development",
        ],
    ),
    PackageSeed(
        slug="group-cohort",
        name="Career Flow Group Cohort",
        tier=PackageTier.GROUP,
        pricing_model=PricingModel.ONE_TIME,
        amount_cents=80000,
        description=(
            "A six-week group programme covering job-search strategy, networking, "
            "interviewing, and personal brand — together with a small cohort of motivated "
            "professionals."
        ),
        features=[
            "Six weekly live workshops",
            "Shared accountability and peer feedback",
            "Templates and frameworks you keep",
            "Office hours with the coaching team",
        ],
    ),
]


SUCCESS_STORIES_SEED: list[SuccessStorySeed] = [
    SuccessStorySeed(
        slug="cristi-persado",
        client_name="Cristi G",
        client_role_after="Frontend Engineer",
        client_company_after="Persado",
        story_short=(
            "Landed a frontend engineering role at Persado within three months of starting "
            "Alex's mentorship — first tech job after a career change."
        ),
        story_long=(
            "Aleks was my first mentor while trying to change careers and land my first tech "
            "job. He has all the experience and skills I needed to update my resume and "
            "practice for job interviews.\n\n"
            "Thanks to his mentorship program, I landed my first job as a software engineer "
            "within 3 months of being under his guidance. I highly recommend Aleks if you are "
            "trying to improve your resume, land a new job, or get insightful knowledge from "
            "his experience and feedback. He has been professional, patient, and supportive "
            "throughout my career growth."
        ),
        coach_slug="alex",
        is_featured=True,
        sort_order=0,
    ),
    SuccessStorySeed(
        slug="maryam-flore",
        client_name="Maryam N",
        client_role_after="Full Stack Developer",
        client_company_after="Flore",
        story_short=(
            "Navigated a difficult career transition with Atiyeh's coaching — clear plan, "
            "real accountability, signed offer at Flore."
        ),
        story_long=(
            "If you ever get the chance to work with or be mentored by Atiyeh, don't "
            "hesitate — she's the real deal. I was fortunate to have her in my corner during "
            "a difficult period of unemployment and career transition, and her guidance made "
            "all the difference.\n\n"
            "She didn't just offer encouragement — she helped me create a clear plan, stay "
            "focused, and held me accountable in the kindest way possible. Her ability to "
            "listen, reflect, and offer grounded advice gave me the clarity and confidence I "
            "needed to keep moving forward.\n\n"
            "Atiyeh brings a rare mix of honesty, empathy, and strategic thinking that makes "
            "you feel both supported and empowered. I'm incredibly grateful for her "
            "mentorship and can't recommend her enough to anyone navigating uncertain or "
            "evolving paths."
        ),
        coach_slug="atiyeh",
        is_featured=True,
        sort_order=1,
    ),
    SuccessStorySeed(
        slug="jose-cisco",
        client_name="Jose C",
        client_role_after="Software Engineer",
        client_company_after="Cisco",
        story_short=(
            "Found a coach who gently pushed him out of his comfort zone — landed at Cisco "
            "with newfound confidence and clarity."
        ),
        story_long=(
            "Working with Alex has been an incredible experience. From the very first "
            "session, it was clear that he's not just knowledgeable but he genuinely cares "
            "about your growth. He has a gift for breaking things down in a way that feels "
            "approachable, even when you're facing something new or challenging.\n\n"
            "He creates a space where you feel safe stepping out of your comfort zone by "
            "gently pushing you to reach higher while also keeping you grounded and "
            "accountable. Talking to him feels less like a formal mentorship and more like "
            "chatting with a friend who wants to see you win."
        ),
        coach_slug="alex",
        is_featured=True,
        sort_order=2,
    ),
    SuccessStorySeed(
        slug="leah-uber",
        client_name="Leah W",
        client_role_after="Software Engineering Intern",
        client_company_after="Uber",
        story_short=(
            "Resume revisions, interview prep, and a referral-first networking playbook — "
            "Leah landed a software engineering internship at Uber."
        ),
        story_long=(
            "I had the pleasure of being mentored by Alex. Throughout our mentorship, he was "
            "always incredibly patient and responsive, making sure to answer my questions "
            "thoughtfully and thoroughly. He gave me actionable advice not just on technical "
            "skills, but also on navigating my career path, and his feedback was always "
            "practical and encouraging.\n\n"
            "Alex also helped me revise my resume, prepare for interviews, and shared "
            "valuable tips on how to connect with people and build my network. Through his "
            "mentorship, my goals became much clearer, and I gained a lot more confidence in "
            "myself and my next steps. I really appreciated how available and supportive he "
            "was — it always felt like he genuinely cared about helping me grow. I would "
            "highly recommend him to anyone looking for a thoughtful and committed coach or "
            "mentor."
        ),
        coach_slug="alex",
        is_featured=False,
        sort_order=3,
    ),
]


async def upsert_coaches() -> dict[str, Coach]:
    async with AsyncSessionLocal() as db:
        existing = {c.slug: c for c in (await db.execute(select(Coach))).scalars().all()}
        result: dict[str, Coach] = {}
        for entry in COACHES_SEED:
            coach = existing.get(entry.slug)
            payload = asdict(entry)
            if coach is None:
                coach = Coach(**payload)
                db.add(coach)
            else:
                for field_name, value in payload.items():
                    setattr(coach, field_name, value)
            result[entry.slug] = coach
        await db.commit()
        for coach in result.values():
            await db.refresh(coach)
        return result


async def upsert_packages() -> None:
    async with AsyncSessionLocal() as db:
        existing = {p.slug: p for p in (await db.execute(select(Package))).scalars().all()}
        for entry in PACKAGES_SEED:
            pkg = existing.get(entry.slug)
            payload = asdict(entry)
            if pkg is None:
                pkg = Package(**payload)
                db.add(pkg)
            else:
                for field_name, value in payload.items():
                    setattr(pkg, field_name, value)
        await db.commit()


async def upsert_success_stories(coaches: dict[str, Coach]) -> None:
    async with AsyncSessionLocal() as db:
        existing = {s.slug: s for s in (await db.execute(select(SuccessStory))).scalars().all()}
        now = datetime.now(UTC)
        for entry in SUCCESS_STORIES_SEED:
            coach = coaches.get(entry.coach_slug)
            payload = asdict(entry)
            payload.pop("coach_slug", None)
            payload["coach_id"] = coach.id if coach else None
            payload["published_at"] = now
            story = existing.get(entry.slug)
            if story is None:
                story = SuccessStory(**payload)
                db.add(story)
            else:
                for field_name, value in payload.items():
                    setattr(story, field_name, value)
        await db.commit()


async def seed() -> None:
    coaches = await upsert_coaches()
    await upsert_packages()
    await upsert_success_stories(coaches)
    log.info("seed.complete")


if __name__ == "__main__":
    asyncio.run(seed())


# `field` is imported above so that dataclass default_factory could be used
# if we later need mutable defaults; suppress the unused-import nag.
_ = field
