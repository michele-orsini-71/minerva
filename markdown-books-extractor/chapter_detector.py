import re


def detect_chapters(content: str) -> list[dict]:
    chapter_pattern = r'^(#{2,4})\s+(.+)$'

    matches = list(re.finditer(chapter_pattern, content, re.MULTILINE))

    if len(matches) == 0:
        raise ValueError("No chapters detected in file. Expected headers (##, ###, or ####)")

    chapters = []

    for index, match in enumerate(matches):
        chapter_title = match.group(2).strip()
        start_pos = match.end()

        if index + 1 < len(matches):
            end_pos = matches[index + 1].start()
        else:
            end_pos = len(content)

        chapter_content = content[start_pos:end_pos].strip()

        if chapter_content:
            chapters.append({
                "title": chapter_title,
                "content": chapter_content,
                "index": index
            })

    return chapters
