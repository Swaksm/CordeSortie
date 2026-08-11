from cordesortie.scheduler.manager import (
    _HARD_FLOOR_SECONDS,
    _MAX_BACKOFF_MINUTES,
    _compute_delay_seconds,
    _jitter,
)


def test_jitter_stays_within_spread():
    base = 300.0
    for _ in range(500):
        value = _jitter(base, spread=0.15)
        assert 300.0 * 0.85 <= value <= 300.0 * 1.15


def test_jitter_default_spread_centered_on_base():
    base = 60.0
    samples = [_jitter(base) for _ in range(500)]
    assert min(samples) >= base * 0.85
    assert max(samples) <= base * 1.15


def test_delay_never_below_hard_floor_on_success():
    # Intervalle de 1 min : jitter pourrait descendre a 51s sans le plancher.
    for _ in range(200):
        delay = _compute_delay_seconds(1, error=False, consecutive_errors=0)
        assert delay >= _HARD_FLOOR_SECONDS


def test_delay_never_below_hard_floor_on_first_error():
    # Regression : le backoff sur un intervalle court ne doit jamais descendre
    # sous le plancher, meme au tout premier echec (avant que le backoff n'ait
    # eu la chance de grossir).
    for _ in range(200):
        delay = _compute_delay_seconds(1, error=True, consecutive_errors=1)
        assert delay >= _HARD_FLOOR_SECONDS


def test_backoff_grows_with_consecutive_errors():
    interval = 5
    delays = [
        _compute_delay_seconds(interval, error=True, consecutive_errors=n)
        for n in (1, 2, 3, 4)
    ]
    # Jitter ajoute du bruit mais la tendance doit rester croissante sur des
    # deltas de cet ordre de grandeur (x2 a chaque etape, largement > le spread).
    assert delays[0] < delays[1] < delays[2] < delays[3]


def test_backoff_caps_at_max_backoff_minutes():
    # Beaucoup d'erreurs consecutives : le backoff doit plafonner, pas continuer
    # a doubler indefiniment.
    for _ in range(50):
        delay = _compute_delay_seconds(60, error=True, consecutive_errors=20)
        assert delay <= _MAX_BACKOFF_MINUTES * 60 * 1.15 + 1


def test_success_delay_matches_requested_interval_within_jitter():
    interval_minutes = 5
    for _ in range(200):
        delay = _compute_delay_seconds(interval_minutes, error=False, consecutive_errors=0)
        base = interval_minutes * 60
        assert base * 0.85 <= delay <= base * 1.15
