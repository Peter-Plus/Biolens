"""Server-owned model catalog; positioning is not a benchmark ranking."""
DEFAULT_MODEL = "qwen3.7-flash"
MODELS = [
    {"id": "qwen3.6-flash", "label": "轻量 · Qwen3.6 Flash", "description": "简单问答与轻量任务"},
    {"id": "qwen3.7-flash", "label": "快速 · Qwen3.7 Flash", "description": "日常问答与基础分析，默认选项"},
    {"id": "qwen3.7-plus", "label": "均衡 · Qwen3.7 Plus", "description": "文献整理与综合分析"},
    {"id": "qwen3.8-flash", "label": "高效增强 · Qwen3.8 Flash", "description": "兼顾能力与响应效率"},
    {"id": "qwen3.7-max", "label": "高阶 · Qwen3.7 Max", "description": "复杂分析与多步任务"},
    {"id": "qwen3.8-max", "label": "旗舰 · Qwen3.8 Max", "description": "千问当前最强旗舰，优先质量"},
]


def select_model(value=None):
    model = value or DEFAULT_MODEL
    if model not in {item["id"] for item in MODELS}:
        raise ValueError("该模型不在服务端开放列表中，请重新选择模型。")
    return model
