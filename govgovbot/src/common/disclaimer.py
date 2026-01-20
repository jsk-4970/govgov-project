"""免責事項付与モジュール

AI生成回答に免責事項を付与する機能を提供します。
これは本プロジェクトの信頼性を守る生命線です。
"""


def add_disclaimer(answer: str, sources: list[str]) -> str:
    """
    回答に免責事項を付与する

    Args:
        answer: AIが生成した回答文
        sources: 参照元のURL・文書名のリスト

    Returns:
        免責事項が付与された回答文

    Raises:
        ValueError: answerが空文字列の場合
    """
    if not answer:
        raise ValueError("answer must not be empty")

    disclaimer = (
        "\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "※ この回答はAIによって生成されたものであり、\n"
        "100%の正確性を保証するものではありません。\n"
        "重要な判断を行う際は、必ず一次資料をご確認ください。\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # 参照元がある場合のみ追加
    if sources:
        sources_text = "\n".join([f"- {src}" for src in sources])
        sources_section = f"\n\n【参照元】\n{sources_text}"
    else:
        sources_section = ""

    return f"{answer}{disclaimer}{sources_section}"


def has_disclaimer(text: str) -> bool:
    """
    テキストに免責事項が含まれているか確認する

    Args:
        text: 確認するテキスト

    Returns:
        免責事項が含まれている場合True、そうでない場合False
    """
    disclaimer_marker = "この回答はAIによって生成されたものであり"
    return disclaimer_marker in text
