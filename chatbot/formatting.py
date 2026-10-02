"""Reply post-processing shared by the views and the RAG pipeline."""
import re


def strip_markdown(text):
    """The chat widget renders plain text, so flatten any markdown the model still produces."""
    text = re.sub(r'```.*?```', '', text, flags=re.S)                    # code blocks
    text = re.sub(r'^[ \t]*\|?[ \t]*:?-{2,}[^\n]*\n?', '', text, flags=re.M)  # table separator rows
    text = re.sub(r'^[ \t]*\|(.*)\|[ \t]*$',                                    # table rows -> "a, b, c"
                  lambda m: ', '.join(c.strip() for c in m.group(1).split('|') if c.strip()),
                  text, flags=re.M)
    text = re.sub(r'^[ \t]{0,3}#{1,6}[ \t]*', '', text, flags=re.M)            # headings
    text = re.sub(r'^[ \t]*(?:[-*•]|\d+[.)])[ \t]+', '', text, flags=re.M)     # list markers
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)          # links
    text = re.sub(r'(\*\*|__)(.+?)\1', r'\2', text)                      # bold
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'\1', text)  # italics
    text = re.sub(r'`([^`]+)`', r'\1', text)                             # inline code
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
