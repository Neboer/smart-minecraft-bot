#!/usr/bin/env python3
"""Watch a trained DQN agent play the smart-bot game with the 3D visualiser.

One action is taken every second, matching the REPL-player demo cadence.
The visualiser runs on the main thread; the agent loop runs in a daemon thread.
Close the window to quit.

Usage:
    python -m interactive.reinforcementai.demo_dqn
    python -m interactive.reinforcementai.demo_dqn --model temp/rlai_models/dqn_woodbot_latest.zip
    python -m interactive.reinforcementai.demo_dqn --fps 2
"""

import argparse
import os
import sys
import threading
import time

MODEL_DIR  = os.path.join("temp", "rlai_models")
MODEL_NAME = "dqn_woodbot"
LATEST     = os.path.join(MODEL_DIR, f"{MODEL_NAME}_latest.zip")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo DQN agent in smart-bot")
    parser.add_argument("--model", default=None,
                        help=f"Path to .zip model (default: {LATEST})")
    parser.add_argument("--fps", type=float, default=1.0,
                        help="Actions per second (default: 1.0)")
    parser.add_argument("--seed", type=int, default=0,
                        help="World seed for reproducible demo")
    args = parser.parse_args()

    model_path = args.model or LATEST
    if not os.path.exists(model_path):
        print(f"[error] model not found: {model_path}")
        print("  Train first:  python -m interactive.reinforcementai.train_dqn")
        return

    from gymnasium.wrappers import FlattenObservation
    from stable_baselines3 import DQN
    from interactive.reinforcementai.WorldGYM import WorldGYM, ACTION_NAMES
    from visualize.viewer import run_visualizer

    print(f"[demo] loading model: {model_path}")
    env   = FlattenObservation(WorldGYM(seed=args.seed, max_steps=999_999))
    model = DQN.load(model_path, device="cpu")  # CPU is plenty for inference

    obs, _ = env.reset()

    # Grab stable references — these objects are mutated in-place each tick
    # so the visualiser will always see the current state.
    game_world = env.unwrapped._game.world
    player     = env.unwrapped._player

    world_lock = threading.Lock()
    stop_event = threading.Event()
    step_secs  = 1.0 / max(args.fps, 0.1)

    def agent_loop() -> None:
        nonlocal obs
        tick          = 0
        total_planks  = 0.0

        while not stop_event.is_set():
            action, _state = model.predict(obs, deterministic=True)
            action_name = ACTION_NAMES[int(action)]

            with world_lock:
                obs, reward, _terminated, truncated, info = env.step(int(action))
            total_planks += reward
            tick += 1

            print(
                f"  tick={tick:4d}  action={action_name:<14s}"
                f"  reward={reward:+.0f}  planks_total={total_planks:.0f}"
            )

            if truncated:
                # Shouldn't happen with max_steps=999_999, but handle gracefully
                print("[demo] episode ended — resetting")
                with world_lock:
                    obs, _ = env.reset()

            if stop_event.is_set():
                break
            time.sleep(step_secs)

    thread = threading.Thread(target=agent_loop, daemon=True)
    thread.start()

    print(f"[demo] visualiser starting ({args.fps:.1f} actions/s) — close window to quit")
    sys.argv = [sys.argv[0]]
    try:
        # game=None → visualiser reads live world state without auto-ticking
        run_visualizer(game_world, player, game=None, world_lock=world_lock)
    finally:
        stop_event.set()

    print("[demo] done.")


if __name__ == "__main__":
    main()
