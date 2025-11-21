from scraper import get_tournaments

slug = "2025-2026"
tournaments = get_tournaments(slug)
print(f"Tournaments for {slug}:")
for t in tournaments:
    print(f"  {t['name']} ({t['url']})")
