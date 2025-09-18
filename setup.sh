# Prerequisites (run if needed)
# - Python 3.8+
# - Git
# - macOS/Linux or Windows (WSL)

# Step 1: Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Step 2: Install Python dependencies for conversion
pip install -r requirements.txt

# Step 3: Install build tools (for quantization later)
# macOS:
#   brew install cmake
# Linux (Ubuntu/Debian):
#   sudo apt update && sudo apt install -y cmake build-essential

# Step 4: Build quantization tool (optional but recommended)
cd llama.cpp
mkdir build
cd build
cmake ..
make -j8 llama-quantize