"""FastAPI Echo 服务：解析 / 演示回合，下游拿到结构化 VoiceTurn。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from structured_llm.serve import (
    fake_tts_consume,
    parse_generation_to_response,
)


class ParseRequest(BaseModel):
    text: str = Field(..., description="模型原始生成文本（含 think + [json]）")
    input: Optional[dict[str, Any]] = Field(
        None, description="可选用户输入，用于静音一致性等校验"
    )
    schema_path: str = "schemas/echo_turn.schema.json"


class TurnRequest(BaseModel):
    """作品集演示：用户 JSON + 可选 raw_output（无 GPU 时直接喂 fixture 文本）。"""

    input: dict[str, Any]
    raw_output: Optional[str] = Field(
        None,
        description="若提供则只做契约解析；否则返回 501（本服务默认不强制加载 GPU）",
    )
    schema_path: str = "schemas/echo_turn.schema.json"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Echo Structured Turn API",
        description=(
            "将小模型多块输出解析为 VoiceTurn。"
            "与训练 / 评测共用 structured_llm.contract。"
        ),
        version="0.3.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/parse")
    def parse_raw(body: ParseRequest) -> dict[str, Any]:
        """原始生成文本 → 解析后的 VoiceTurn；失败返回 errors。"""
        resp = parse_generation_to_response(
            body.text,
            schema_path=body.schema_path,
            input_obj=body.input,
        )
        if not resp.get("ok"):
            # 业务失败仍返回 200 + ok=false，便于客户端读 errors；也可视作 422
            return resp
        resp["tts"] = fake_tts_consume(resp["voice"])
        return resp

    @app.post("/v1/turn")
    def turn(body: TurnRequest) -> dict[str, Any]:
        """
        演示入口：用户 JSON + raw_output（推荐 fixture / 已生成文本）。

        有 GPU 生成需求时请用 scripts/evaluate.py --mode generate，
        本 API 专注「下游吃结构化结果」。
        """
        if not body.raw_output:
            raise HTTPException(
                status_code=501,
                detail=(
                    "未提供 raw_output。请传入模型生成文本，"
                    "或使用 scripts/demo_request.py --fixture。"
                ),
            )
        resp = parse_generation_to_response(
            body.raw_output,
            schema_path=body.schema_path,
            input_obj=body.input,
        )
        resp["input"] = body.input
        if resp.get("ok"):
            resp["tts"] = fake_tts_consume(resp["voice"])
            # 假 TTS 消费者：服务端日志侧体现通道分离
            print(fake_tts_consume(resp["voice"], as_log_line=True))
        return resp

    return app


app = create_app()
