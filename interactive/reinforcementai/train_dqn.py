#!/usr/bin/env python3
"""Train a DQN agent to collect Planks in the smart-bot game.

Reward: +N for each N planks added to the player's inventory per tick.
Goal:   maximise plank collection rate (grow saplings → dig trees).

Usage:
    python -m interactive.reinforcementai.train_dqn
    python -m interactive.reinforcementai.train_dqn --resume
    python -m interactive.reinforcementai.train_dqn --resume --steps 1000000
"""

# ── Hyperparameters — edit freely ─────────────────────────────────────────────
TOTAL_TIMESTEPS        = 2_000_000   # default training budget
MAX_EPISODE_STEPS      = 500         # ticks per episode
SEED                   = 42

# DQN core
LEARNING_RATE          = 1e-4
BUFFER_SIZE            = 200_000     # replay buffer capacity (frames)
BATCH_SIZE             = 256
GAMMA                  = 0.99        # discount factor
EXPLORATION_FRACTION   = 0.30        # fraction of training spent on ε-decay
EXPLORATION_FINAL_EPS  = 0.05
TRAIN_FREQ             = 4           # update every N env steps
GRADIENT_STEPS         = 1          # gradient steps per update
TARGET_UPDATE_INTERVAL = 1_000       # hard-update target net every N steps
LEARNING_STARTS        = 10_000      # fill buffer before training

# Network  (MlpPolicy layers, both pi and qf share this arch)
NET_ARCH               = [512, 512, 256]

# Infrastructure
DEVICE                 = "cuda"      # "cuda" | "cpu"
CHECKPOINT_FREQ        = 100_000     # save intermediate checkpoint every N steps
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import os

MODEL_DIR  = os.path.join("temp", "rlai_models")
MODEL_NAME = "dqn_woodbot"
LATEST     = os.path.join(MODEL_DIR, f"{MODEL_NAME}_latest.zip")


def make_env(seed: int | None = None):
    from gymnasium.wrappers import FlattenObservation
    from interactive.reinforcementai.WorldGYM import WorldGYM
    return FlattenObservation(WorldGYM(seed=seed, max_steps=MAX_EPISODE_STEPS))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DQN on smart-bot")
    parser.add_argument("--resume", action="store_true",
                        help="Continue from latest saved checkpoint")
    parser.add_argument("--steps", type=int, default=TOTAL_TIMESTEPS,
                        help="Total training timesteps")
    args = parser.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    ckpt_dir = os.path.join(MODEL_DIR, "checkpoints")
    os.makedirs(ckpt_dir, exist_ok=True)

    from stable_baselines3 import DQN
    from stable_baselines3.common.callbacks import (
        CheckpointCallback,
        EvalCallback,
    )
    from stable_baselines3.common.monitor import Monitor

    train_env = make_env(seed=SEED)
    eval_env  = Monitor(make_env(seed=SEED + 1))

    if args.resume and os.path.exists(LATEST):
        print(f"[resume] loading {LATEST}")
        model = DQN.load(LATEST, env=train_env, device=DEVICE)
        # replay buffer is not persisted — exploration picks up where ε left off
    else:
        if args.resume:
            print(f"[warn] --resume set but {LATEST} not found — starting fresh")
        print("[train] initialising new DQN model")
        model = DQN(
            policy           = "MlpPolicy",
            env              = train_env,
            learning_rate    = LEARNING_RATE,
            buffer_size      = BUFFER_SIZE,
            batch_size       = BATCH_SIZE,
            gamma            = GAMMA,
            exploration_fraction     = EXPLORATION_FRACTION,
            exploration_final_eps    = EXPLORATION_FINAL_EPS,
            train_freq       = TRAIN_FREQ,
            gradient_steps   = GRADIENT_STEPS,
            target_update_interval   = TARGET_UPDATE_INTERVAL,
            learning_starts  = LEARNING_STARTS,
            policy_kwargs    = dict(net_arch=NET_ARCH),
            device           = DEVICE,
            verbose          = 1,
            seed             = SEED,
        )

    obs_dim = train_env.observation_space.shape[0]
    print(f"[info] obs={obs_dim}  actions={train_env.action_space.n}  "
          f"device={model.device}  steps={args.steps:,}")

    callbacks = [
        CheckpointCallback(
            save_freq   = CHECKPOINT_FREQ,
            save_path   = ckpt_dir,
            name_prefix = MODEL_NAME,
            verbose     = 1,
        ),
        EvalCallback(
            eval_env,
            best_model_save_path = MODEL_DIR,
            log_path             = MODEL_DIR,
            eval_freq            = CHECKPOINT_FREQ,
            n_eval_episodes      = 5,
            deterministic        = True,
            verbose              = 1,
        ),
    ]

    model.learn(
        total_timesteps    = args.steps,
        callback           = callbacks,
        reset_num_timesteps= not args.resume,
        progress_bar       = True,
    )

    model.save(LATEST)
    print(f"[done] model saved → {LATEST}")


if __name__ == "__main__":
    main()
