import argparse
import json
import math
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from peft import PeftModel
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer


class SFTDataset(Dataset):
    def __init__(self, path, tokenizer, max_length):
        self.rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        messages = self.rows[index]["messages"]
        prompt_messages = messages[:-1]
        answer = messages[-1]["content"]

        prompt = self.tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        full = prompt + answer + self.tokenizer.eos_token

        full_ids = self.tokenizer(full, truncation=True, max_length=self.max_length)["input_ids"]
        prompt_ids = self.tokenizer(prompt, truncation=True, max_length=self.max_length)["input_ids"]

        labels = full_ids.copy()
        prompt_len = min(len(prompt_ids), len(labels))
        labels[:prompt_len] = [-100] * prompt_len

        return {
            "input_ids": torch.tensor(full_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def collate(batch, pad_id):
    max_len = max(item["input_ids"].size(0) for item in batch)
    input_ids = []
    labels = []
    attention_mask = []

    for item in batch:
        pad_len = max_len - item["input_ids"].size(0)
        input_ids.append(torch.cat([item["input_ids"], torch.full((pad_len,), pad_id, dtype=torch.long)]))
        labels.append(torch.cat([item["labels"], torch.full((pad_len,), -100, dtype=torch.long)]))
        attention_mask.append(torch.cat([torch.ones(item["input_ids"].size(0), dtype=torch.long), torch.zeros(pad_len, dtype=torch.long)]))

    return {
        "input_ids": torch.stack(input_ids),
        "labels": torch.stack(labels),
        "attention_mask": torch.stack(attention_mask),
    }


@torch.no_grad()
def evaluate(model, loader, device, max_batches=20):
    model.eval()
    losses = []
    for idx, batch in enumerate(loader):
        if idx >= max_batches:
            break
        batch = {key: value.to(device) for key, value in batch.items()}
        out = model(**batch)
        losses.append(out.loss.item())
    model.train()
    return sum(losses) / max(1, len(losses))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--train", default="data/qwen_sft/train.jsonl")
    parser.add_argument("--val", default="data/qwen_sft/val.jsonl")
    parser.add_argument("--out-dir", default="checkpoints/qwen2_5_0_5b_gamedev_lora")
    parser.add_argument("--init-adapter")
    parser.add_argument("--max-length", type=int, default=768)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=400)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        trust_remote_code=True,
    ).to(device)
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    if args.init_adapter:
        model = PeftModel.from_pretrained(model, args.init_adapter, is_trainable=True)
    else:
        lora_cfg = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        )
        model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()
    model.train()

    train_ds = SFTDataset(args.train, tokenizer, args.max_length)
    val_ds = SFTDataset(args.val, tokenizer, args.max_length)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda batch: collate(batch, tokenizer.pad_token_id),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=lambda batch: collate(batch, tokenizer.pad_token_id),
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    total_steps = args.max_steps
    step = 0
    best_val = math.inf
    started = time.time()

    while step < total_steps:
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            out = model(**batch)
            loss = out.loss / args.grad_accum
            loss.backward()

            if (step + 1) % args.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

            if step % 20 == 0:
                print(f"step {step} | loss {loss.item() * args.grad_accum:.4f} | {time.time() - started:.1f}s")
                started = time.time()

            if step > 0 and step % args.eval_interval == 0:
                val_loss = evaluate(model, val_loader, device)
                print(f"eval step {step} | val {val_loss:.4f}")
                if val_loss < best_val:
                    best_val = val_loss
                    out_dir = Path(args.out_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    model.save_pretrained(out_dir)
                    tokenizer.save_pretrained(out_dir)
                    print(f"saved {out_dir}")

            step += 1
            if step >= total_steps:
                break

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"final saved {out_dir}")


if __name__ == "__main__":
    main()
