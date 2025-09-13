mlx_lm.lora \
    --config adapters/adapter_config.json

mlx_lm.generate \
    --model mlx-community/Llama-3.2-1B-Instruct-8bit \
    --adapter adapters \
    --prompt "What projects have you worked on recently?"

# Option 1: Fuse to MLX format (recommended)
mlx_lm.fuse --model mlx-community/Llama-3.2-1B-Instruct-8bit --adapter adapters --save-path fused_adapter --de-quantize