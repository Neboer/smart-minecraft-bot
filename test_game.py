import sys

from example import run_player_smoke_tests, run_preview_mode


def test_player_intent_smoke_suite() -> None:
    """Run the example smoke suite under pytest."""
    run_player_smoke_tests(verbose=False)


def main() -> None:
    run_preview_mode()
    # run_player_smoke_tests(verbose=True)


if __name__ == "__main__":
    main()
