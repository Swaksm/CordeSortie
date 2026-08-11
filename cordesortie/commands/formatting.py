"""Formatage de texte partagé entre /filtre list, le message épinglé d'un salon
d'alerte, et le salon info (voir info_channel.py)."""

from __future__ import annotations

from ..config import FilterProfile, GuildConfig


def _bounds_str(profile: FilterProfile) -> str:
    bounds = []
    if profile.price_min is not None:
        bounds.append(f"prix >= {profile.price_min}")
    if profile.price_max is not None:
        bounds.append(f"prix <= {profile.price_max}")
    return f" ({', '.join(bounds)})" if bounds else ""


def _badges(profile: FilterProfile) -> str:
    badges = []
    if profile.private:
        badges.append("🔒")
    if profile.paused:
        badges.append("⏸️")
    return f"{''.join(badges)} " if badges else ""


def format_profile_line(profile: FilterProfile) -> str:
    dispo = "disponible uniquement" if profile.only_available else "avec rupture"
    bounds_str = _bounds_str(profile)
    return (
        f"- {_badges(profile)}**{profile.name}** — sites: {', '.join(profile.sites)} — "
        f"`{profile.filter_expression}`{bounds_str} — {dispo} — "
        f"scrape toutes les {profile.scrape_interval_minutes} min — "
        f"<#{profile.alert_channel_id}>"
    )


def format_profile_details(
    profile: FilterProfile, *, creator_mention: str, created_at_str: str
) -> str:
    dispo = "disponible uniquement" if profile.only_available else "avec rupture (aussi)"
    bounds_str = _bounds_str(profile)
    prix_str = bounds_str.strip(" ()") if bounds_str else "aucune limite"
    return (
        f"**Profil de filtre : {profile.name}**\n"
        f"- Sites surveillés : {', '.join(profile.sites)}\n"
        f"- Expression : `{profile.filter_expression}`\n"
        f"- Prix : {prix_str}\n"
        f"- Disponibilité : {dispo}\n"
        f"- Intervalle de scrape : {profile.scrape_interval_minutes} min\n"
        f"- Créé par {creator_mention} le {created_at_str}"
    )


def format_info_summary(config: GuildConfig) -> str:
    if not config.profiles:
        return (
            "**CordeSortie — tableau de bord**\n\nAucun profil de filtre actif "
            "pour l'instant. Utilise `/filtre add` pour en créer un."
        )
    lines = [
        f"**CordeSortie — tableau de bord**\n\n{len(config.profiles)} profil(s) actif(s) :",
    ]
    lines.extend(format_profile_line(p) for p in config.profiles)
    return "\n".join(lines)
