import numpy as np
import torch


def load_tokens(path):
    return np.memmap(path, dtype=np.uint16, mode="r")


def get_batch(data, block_size, batch_size, device):
    if len(data) <= block_size + 1:
        raise ValueError(
            f"Dataset has {len(data)} tokens, but block_size is {block_size}. "
            "Add more data or use a smaller block_size."
        )

    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([torch.from_numpy(data[i : i + block_size].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(data[i + 1 : i + 1 + block_size].astype(np.int64)) for i in ix])
    return x.to(device), y.to(device)
