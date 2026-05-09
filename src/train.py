import argparse
import math
import os
import time
from contextlib import nullcontext

import torch
import yaml
from torch.optim import AdamW

from dataset import get_batch, load_tokens
from model import GPT, GPTConfig


device = "cuda" if torch.cuda.is_available() else "cpu"


def amp_context(enabled):
    if enabled:
        return torch.amp.autocast("cuda", dtype=torch.float16)
    return nullcontext()


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@torch.no_grad()
def estimate_loss(model, train_data, val_data, block_size, batch_size, eval_iters, use_amp=False):
    model.eval()
    out = {}

    for split, data in [("train", train_data), ("val", val_data)]:
        losses = []
        for _ in range(eval_iters):
            x, y = get_batch(data, block_size, batch_size, device)
            with amp_context(use_amp):
                _, loss = model(x, y)
            losses.append(loss.item())
        out[split] = sum(losses) / len(losses)

    model.train()
    return out


def get_lr(it, max_lr, min_lr, warmup_iters, max_iters):
    if warmup_iters > 0 and it < warmup_iters:
        return max_lr * (it + 1) / warmup_iters
    if it > max_iters:
        return min_lr

    decay_den = max(1, max_iters - warmup_iters)
    decay_ratio = min(1.0, (it - warmup_iters) / decay_den)
    coeff = 0.5 * (1.0 + math.cos(math.pi * decay_ratio))
    return min_lr + coeff * (max_lr - min_lr)


def save_checkpoint(path, model, cfg, step, val_loss=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "model": model.state_dict(),
        "config": cfg,
        "step": step,
    }
    if val_loss is not None:
        payload["val_loss"] = val_loss
    torch.save(payload, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/yuspec_gamedev_10m.yaml")
    parser.add_argument("--max-iters", type=int)
    parser.add_argument("--eval-iters", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--out-dir")
    parser.add_argument("--init-from", help="Optional checkpoint to initialize model weights from")
    args = parser.parse_args()

    cfg = load_config(args.config)
    model_cfg = GPTConfig(**cfg["model"])
    train_cfg = cfg["training"]

    if args.max_iters is not None:
        train_cfg["max_iters"] = args.max_iters
    if args.eval_iters is not None:
        train_cfg["eval_iters"] = args.eval_iters
    if args.batch_size is not None:
        train_cfg["batch_size"] = args.batch_size
    if args.out_dir is not None:
        train_cfg["out_dir"] = args.out_dir

    train_data = load_tokens(cfg["data"]["train_bin"])
    val_data = load_tokens(cfg["data"]["val_bin"])

    model = GPT(model_cfg).to(device)
    if args.init_from:
        ckpt = torch.load(args.init_from, map_location=device)
        model.load_state_dict(ckpt["model"])
        print(f"initialized from {args.init_from}")

    optimizer = AdamW(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        weight_decay=train_cfg["weight_decay"],
        betas=(0.9, 0.95),
    )

    batch_size = train_cfg["batch_size"]
    grad_accum = train_cfg["gradient_accumulation_steps"]
    block_size = model_cfg.block_size
    eval_iters = train_cfg.get("eval_iters", 50)
    out_dir = train_cfg.get("out_dir", "checkpoints")
    use_amp = bool(train_cfg.get("use_amp", device == "cuda")) and device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_val_loss = float("inf")
    t0 = time.time()

    for step in range(train_cfg["max_iters"]):
        lr = get_lr(
            step,
            train_cfg["learning_rate"],
            train_cfg["min_lr"],
            train_cfg["warmup_iters"],
            train_cfg["max_iters"],
        )

        for param_group in optimizer.param_groups:
            param_group["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        total_loss = 0.0

        for _ in range(grad_accum):
            x, y = get_batch(train_data, block_size, batch_size, device)
            with amp_context(use_amp):
                _, loss = model(x, y)
            loss = loss / grad_accum
            scaler.scale(loss).backward()
            total_loss += loss.item()

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        if step % 100 == 0:
            dt = time.time() - t0
            print(f"step {step} | loss {total_loss:.4f} | lr {lr:.6f} | {dt:.1f}s")
            t0 = time.time()

        should_eval = step > 0 and step % train_cfg["eval_interval"] == 0
        is_last_step = step == train_cfg["max_iters"] - 1
        if should_eval or is_last_step:
            losses = estimate_loss(model, train_data, val_data, block_size, batch_size, eval_iters, use_amp)
            print(f"eval step {step} | train {losses['train']:.4f} | val {losses['val']:.4f}")

            if losses["val"] < best_val_loss:
                best_val_loss = losses["val"]
                save_checkpoint(os.path.join(out_dir, "best.pt"), model, cfg, step, best_val_loss)
                print(f"saved {os.path.join(out_dir, 'best.pt')}")

        if step > 0 and step % train_cfg["save_interval"] == 0:
            save_checkpoint(os.path.join(out_dir, f"step_{step}.pt"), model, cfg, step)


if __name__ == "__main__":
    main()
