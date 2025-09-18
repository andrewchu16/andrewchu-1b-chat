# Step 5: Convert safetensors to GGUF (run from project root)
python llama.cpp/convert_hf_to_gguf.py fused_adapter/ --outfile models/andrewchu-1b-chat-f16.gguf

# Step 6: Quantize model (optional)
./llama.cpp/build/bin/llama-quantize models/andrewchu-1b-chat-f16.gguf models/andrewchu-1b-chat-q4_k_m.gguf Q4_K_M