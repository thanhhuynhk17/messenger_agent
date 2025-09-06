import re
from typing import List, Optional

def extract_final_answer(text: str) -> Optional[str]:
    """
    Trích xuất nội dung đầu tiên trong thẻ <react_final_answer>...</react_final_answer>.
    Nếu không tìm thấy thì trả về None.
    """
    match = re.search(r"<react_final_answer>(.*?)</react_final_answer>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None