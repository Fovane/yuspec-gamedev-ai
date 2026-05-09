$ErrorActionPreference = "Stop"

& .\.venv\Scripts\python -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu128
& .\.venv\Scripts\python -c "import torch; print('torch=', torch.__version__); print('cuda_available=', torch.cuda.is_available()); print('torch_cuda=', torch.version.cuda); print('device=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
