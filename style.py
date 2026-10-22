from pathlib import Path

BASE = Path(__file__).parent

RULES = """Write a LinkedIn post about one news item, the way a real working professional would write it by hand.
- Start with the specific thing that happened, not a hook or a question.
- Add one real opinion or observation: why it matters, or what you'd watch next.
- 80 to 150 words, short paragraphs, plain everyday words, first person where natural.
- Never use emojis or emoticons anywhere in the post.
- At most 2 relevant hashtags at the very end, or none.
- Never use em dashes or en dashes. Use commas or full stops instead.
- No bullet lists, no numbered lists, no bold or italics, no headings, no quotation marks around phrases.
- Avoid these words and phrases: "game-changer", "revolutionize", "in today's fast-paced world",
  "excited to share", "let's dive in", "unlock", "landscape", "delve", "leverage", "paradigm",
  "it's worth noting", "at the end of the day", "the future of".
- Don't end with a question or "Thoughts?".
- Vary sentence length. Mix short sentences with longer ones. It's fine to be a little informal.
- Use only facts that appear in the title and snippet you are given. Do not add product names,
  version numbers, figures or claims that are not in them."""

def style_prompt() -> str:
    rules = RULES
    examples_file = BASE / "examples.txt"
    if examples_file.exists():
        examples = examples_file.read_text(encoding="utf-8").strip()
        if examples:
            rules += (
                "\n\nHere are real posts by the author. Match their voice, "
                "sentence length, and structure, but do not copy their wording "
                "or topics:\n\n" + examples
            )
    return rules