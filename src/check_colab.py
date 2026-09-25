import sys
import torch

print("=== Colab Remote Environment Check ===")
print("Python Version:", sys.version)
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device Name:", torch.cuda.get_device_name(0))
    print("Device Memory: {:.2f} GB".format(torch.cuda.get_device_properties(0).total_memory / 1e9))
