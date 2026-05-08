import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from core.config import Config


def is_mock_mode():
    return not Config.OPENROUTER_API_KEY or Config.OPENROUTER_API_KEY == "your_openrouter_api_key_here"


def _call_openrouter(messages: list) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "messages": messages,
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"LLM API request failed: {e.code} - {error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API request failed: {e}")


def _escape_latex(value):
    text = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _normalize_url(value: str) -> str:
    if not value:
        return ""
    url = str(value).strip().replace("\\", "/")
    if url.startswith("http:/") and not url.startswith("http://"):
        url = url.replace("http:/", "http://", 1)
    if url.startswith("https:/") and not url.startswith("https://"):
        url = url.replace("https:/", "https://", 1)
    if url.startswith("www."):
        url = "https://" + url
    return url


def _escape_href(value: str) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _safe_href(value: str) -> tuple[str, str]:
    url = _normalize_url(value)
    if not url:
        return "", ""
    url = url.replace(" ", "%20").replace("&", "%26")
    if not re.match(r"^https?://", url):
        url = "https://" + url
    href = _escape_href(url)
    display = _escape_latex(url.replace("https://", "").replace("http://", ""))
    return href, display


def _ensure_list(value):
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _split_text(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("\n", ";").split(";") if part.strip()]


def _extract_json(response_text: str) -> dict:
    cleaned = response_text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    payload = json.loads(match.group(0) if match else cleaned)
    if not isinstance(payload, dict):
        raise json.JSONDecodeError("Expected JSON object", cleaned, 0)
    return payload


def analyze_match(profile_data: dict, job_description: str) -> dict:
    """Returns a dict with 'score' (int) and 'summary' (str)."""
    if is_mock_mode():
        return {
            "score": 88,
            "summary": "Your profile demonstrates strong alignment with this role! This is a SIMULATED AI RESPONSE because the OpenRouter API key is missing in your .env file."
        }

    prompt = f"""
You are an expert HR ATS system.
Evaluate the following candidate profile against the job description.
Return exactly a JSON object with two keys:
"score": an integer 0-100 representing match percentage.
"summary": a 2-3 sentence summary of why they match and what is missing.

Profile:
{json.dumps(profile_data, indent=2)}

Job Description:
{job_description}
    """

    response_text = _call_openrouter([{"role": "user", "content": prompt}])
    try:
        payload = _extract_json(response_text)
        if "score" in payload and "summary" in payload:
            return payload
    except json.JSONDecodeError:
        pass

    return {
        "score": 50,
        "summary": "AI could not properly analyze the match. Raw response: " + response_text[:100]
    }


def _filter_profile_for_job(profile_data: dict, job_description: str) -> dict:
    """
    Intelligently filter and enhance profile data to match job requirements.
    - Filters items to show only the most relevant ones.
    - Prioritizes items that match the job description.
    - Removes low-relevance content for brevity.
    """
    if is_mock_mode():
        return profile_data

    # Build a concise profile summary for the LLM
    profile_summary = {
        "work_experience": profile_data.get("work_experience", []),
        "education": profile_data.get("education", []),
        "skills_hard": profile_data.get("skills_hard", []),
        "skills_soft": profile_data.get("skills_soft", []),
        "projects": profile_data.get("projects", []),
        "certifications": profile_data.get("certifications", []),
        "volunteer": profile_data.get("volunteer", []),
        "languages": profile_data.get("languages", []),
    }

    prompt = f"""
You are an expert resume strategist.
Given a candidate profile and job description, intelligently filter and prioritize the data.

INSTRUCTIONS:
1. For work_experience: Select max 3 most relevant roles. For each, pick max 4 most impactful bullets.
2. For projects: Select max 2 most relevant. Keep only the 2-3 most impressive bullets per project.
3. For skills_hard: Keep only skills explicitly mentioned or strongly relevant to the job. Limit to 3 categories max.
4. For skills_soft: Keep only 3-4 most relevant soft skills.
5. For certifications: Keep only certifications relevant to the job. Max 5.
6. For volunteer: Keep only if relevant to job. Max 1-2 entries.
7. For education: Keep all education entries.
8. For languages: Keep all languages.

Return a JSON object with the same structure as the input, but FILTERED and PRIORITIZED.
Only include keys that have content. Remove empty arrays.
Prioritize quality over quantity. Focus on what makes this candidate stand out for THIS specific job.

CANDIDATE PROFILE:
{json.dumps(profile_summary, indent=2)}

JOB DESCRIPTION:
{job_description}
    """

    try:
        response_text = _call_openrouter([{"role": "user", "content": prompt}])
        filtered = _extract_json(response_text)
        
        # Preserve non-filtered fields from original (e.g., contact info, summary, photo)
        result = {
            "contact": profile_data.get("contact"),
            "summary": profile_data.get("summary"),
            "photo_path": profile_data.get("photo_path"),
            "interests": profile_data.get("interests"),
            "publications": profile_data.get("publications"),
            "affiliations": profile_data.get("affiliations"),
            "conferences": profile_data.get("conferences"),
        }
        
        # Merge filtered fields
        for key in ["work_experience", "education", "skills_hard", "skills_soft", "projects", 
                    "certifications", "volunteer", "languages"]:
            if key in filtered and filtered[key]:
                result[key] = filtered[key]
        
        return result
    except Exception:
        # If filtering fails, return original profile
        return profile_data


def generate_latex(profile_data: dict, job_description: str, job_title=None) -> str:
    """Generates a fixed-layout LaTeX CV string."""
    
    # Intelligently filter profile data to match job requirements
    if job_description:
        profile_data = _filter_profile_for_job(profile_data, job_description)
    
    contact = profile_data.get("contact") or {}
    summary_text = str(profile_data.get("summary") or "").strip()

    if not summary_text and not is_mock_mode():
        prompt = f"""
You write concise CV summaries only.
Use the profile data and job description to produce a 2-3 sentence professional summary.
Keep it factual, ATS-friendly, and grounded only in the supplied information.
Return only JSON with a single key:
{{"summary":"..."}}

Profile Data:
{json.dumps(profile_data, indent=2)}

Job Description:
{job_description}
        """
        try:
            payload = _extract_json(_call_openrouter([{"role": "user", "content": prompt}]))
            summary_text = str(payload.get("summary", "")).strip() or summary_text
        except Exception:
            pass

    if not summary_text:
        summary_text = (
            "Experienced professional with a practical track record across the roles, projects, and skills captured in the profile. "
            "The layout is tuned to keep the CV concise, readable, and aligned with the target role."
        )

    name = _escape_latex(contact.get("name", "Full Name") or "Full Name")
    title = _escape_latex(job_title or contact.get("headline", "Professional Profile") or "Professional Profile")

    photo_path = str(profile_data.get("photo_path") or "").strip()
    photo_target = ""
    photo_comments = []
    if photo_path:
        source = Path(photo_path)
        if source.exists():
            photo_target = f"cv_photo{source.suffix.lower() or '.jpg'}"
            photo_comments = [
                f"% CVIFY_PHOTO_SOURCE: {source}",
                f"% CVIFY_PHOTO_TARGET: {photo_target}",
            ]

    def contact_line(items):
        return " \\quad\n    ".join([item for item in items if item])

    phone = str(contact.get("phone", "") or "").strip()
    email = str(contact.get("email", "") or "").strip()
    location = str(contact.get("location", "") or "").strip()
    linkedin = str(contact.get("linkedin", "") or "").strip()
    portfolio = str(contact.get("portfolio", "") or "").strip()

    line_one = []
    if phone:
        line_one.append(rf"\faIcon{{phone}} \textbf{{{_escape_latex(phone)}}}")
    if email:
        mailto = _escape_href(f"mailto:{email}")
        line_one.append(rf"\faIcon{{envelope}} \href{{{mailto}}}{{\textbf{{{_escape_latex(email)}}}}}")

    line_two = []
    if linkedin:
        linkedin_href, linkedin_display = _safe_href(linkedin)
        if linkedin_href:
            line_two.append(rf"\faIcon{{linkedin}} \href{{{linkedin_href}}}{{\textbf{{{linkedin_display}}}}}")
    if portfolio:
        portfolio_href, portfolio_display = _safe_href(portfolio)
        if portfolio_href:
            line_two.append(rf"\faIcon{{globe}} \href{{{portfolio_href}}}{{\textbf{{{portfolio_display}}}}}")
    if location:
        line_two.append(rf"\faIcon{{map-marker-alt}} \textbf{{{_escape_latex(location)}}}")

    def bullets(items, indent="        "):
        return [f"{indent}\\resumeItem{{{_escape_latex(item)}}}" for item in items if str(item).strip()]

    def section(title_text, body_lines, spacing="5pt"):
        if not body_lines:
            return []
        return [
            f"%----------{title_text.upper()}----------",
            rf"\section{{{_escape_latex(title_text)}}}",
            rf"\vspace{{{spacing}}}",
            *body_lines,
        ]

    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"",
        r"% Essential packages",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage[margin=0.6in, top=0.2in]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage{titlesec}",
        r"\usepackage{xcolor}",
        r"\usepackage{hyperref}",
        r"\usepackage{fontawesome5}",
        r"\usepackage{multicol}",
        r"\usepackage{ragged2e}",
        r"\usepackage{graphicx}",
        r"\usepackage{array}",
        r"",
        r"% Color definitions",
        r"\definecolor{headercolor}{RGB}{0,66,124}",
        r"\definecolor{accentcolor}{RGB}{220,95,0}",
        r"\definecolor{textcolor}{RGB}{40,40,40}",
        r"",
        r"% Hyperref setup",
        r"\hypersetup{",
        r"    colorlinks=true,",
        r"    linkcolor=headercolor,",
        r"    urlcolor=headercolor,",
        r"}",
        r"",
        r"% Section formatting with compact spacing",
        r"\titleformat{\section}",
        r"    {\Large\bfseries\color{headercolor}}",
        r"    {}",
        r"    {0em}",
        r"    {}[\titlerule]",
        r"\titlespacing*{\section}{0pt}{6pt}{2pt}",
        r"",
        r"% Global spacing settings - optimized for single page",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0pt}",
        r"\setlist{itemsep=0pt,topsep=1pt,parsep=0pt,partopsep=0pt,leftmargin=0.15in}",
        r"",
        r"% Custom commands with minimal spacing",
        r"\newcommand{\resumeSubheading}[4]{",
        r"    \vspace{-1pt}\item[]",
        r"    \begin{tabular*}{\textwidth}[t]{l@{\extracolsep{\fill}}r}",
        "        \\textbf{#1} & \\textbf{#2} \\\\",
        "        \\textit{\\small#3} & \\textit{\\small #4} \\\\",
        r"    \end{tabular*}\vspace{-3pt}",
        r"}",
        r"",
        r"\newcommand{\resumeProjectHeading}[2]{",
        r"    \vspace{-1pt}\item[]",
        r"    \begin{tabular*}{\textwidth}[t]{l@{\extracolsep{\fill}}r}",
        "        \\textbf{#1} & \\textit{\\small #2} \\\\",
        r"    \end{tabular*}\vspace{-3pt}",
        r"}",
        r"",
        r"\newcommand{\resumeItem}[1]{",
        r"    \item\small{#1}",
        r"}",
        r"",
        r"% Command for rectangular photo",
        r"\newcommand{\cvphoto}[1]{%",
        r"    \includegraphics[width=2.5cm, height=3.2cm, keepaspectratio=false]{#1}",
        r"}",
        r"",
        r"% Remove page numbers",
        r"\pagestyle{empty}",
        r"",
        r"\begin{document}",
    ]

    lines.extend(photo_comments)
    lines.append(r"%----------HEADER WITH PHOTO----------")
    lines.append("")
    lines.append(r"\begin{minipage}[c]{2.5cm}")
    lines.append(r"    \raggedright")
    lines.append(rf"    \cvphoto{{{photo_target}}}" if photo_target else r"    ~")
    lines.append(r"\end{minipage}")
    lines.append(r"\hfill")
    lines.append(r"\begin{minipage}[c]{15cm}")
    lines.append(r"    \centering")
    lines.append("    {{\\Huge \\textbf{{\\color{{headercolor}}{}}}}} \\\\".format(name))
    lines.append(r"    \vspace{0pt}")
    lines.append("    {{\\Large {}}} \\\\".format(title))
    lines.append(r"    \vspace{2pt}")
    lines.append(r"    \small")
    lines.append("    " + contact_line(line_one))
    lines.append(r"    \vspace{0pt}")
    lines.append("    " + contact_line(line_two))
    lines.append(r"\end{minipage}")
    lines.append(r"\hfill")
    lines.append(r"\begin{minipage}[t]{2.5cm}")
    lines.append(r"    ~")
    lines.append(r"\end{minipage}")
    lines.append("")
    lines.append(r"\vspace{-1pt}")

    lines.extend(section("Professional Summary", [r"\begin{itemize}", rf"    \resumeItem{{{_escape_latex(summary_text)}}}", r"\end{itemize}"]))

    # Professional Experience (only if has content)
    experience_lines = []
    for entry in _ensure_list(profile_data.get("work_experience")):
        if not isinstance(entry, dict):
            continue
        role = _escape_latex(entry.get("title", "Role") or "Role")
        company = _escape_latex(entry.get("company", "Company") or "Company")
        location_text = _escape_latex(entry.get("location", "") or "")
        start = str(entry.get("start", "") or "").strip()
        end = str(entry.get("end", "") or "").strip()
        date_range = _escape_latex(f"{start} -- {end}".strip(" -")) if (start or end) else ""
        experience_bullets = bullets(_ensure_list(entry.get("bullets")))
        if not experience_bullets:
            experience_bullets = [r"        \resumeItem{Selected accomplishments and responsibilities are available in the profile data.}"]
        experience_lines.extend([
            r"\resumeSubheading",
            f"    {{{role}}}{{{company}}}",
            f"    {{{location_text}}}",
            f"    {{{date_range}}}",
            r"    \begin{itemize}",
            *experience_bullets,
            r"    \end{itemize}",
        ])
    if experience_lines:
        lines.extend(section("Professional Experience", [r"\begin{itemize}", *experience_lines, r"\end{itemize}"]))

    # Education (only if has content)
    education_lines = []
    for entry in _ensure_list(profile_data.get("education")):
        if not isinstance(entry, dict):
            continue
        school = _escape_latex(entry.get("institution", "Institution") or "Institution")
        degree = _escape_latex(entry.get("degree", "Degree") or "Degree")
        field = _escape_latex(entry.get("field", "") or "")
        gpa = str(entry.get("gpa", "") or "").strip()
        start = str(entry.get("start", "") or "").strip()
        end = str(entry.get("end", "") or "").strip()
        date_range = _escape_latex(f"{start} -- {end}".strip(" -")) if (start or end) else ""
        subtitle = degree if not field else f"{degree} in {field}"
        extra = f"GPA: {gpa}" if gpa else ""
        education_lines.extend([
            r"\resumeSubheading",
            f"    {{{school}}}{{{date_range}}}",
            f"    {{{subtitle}}}",
            f"    {{{extra}}}",
        ])
    if education_lines:
        lines.extend(section("Education", [r"\begin{itemize}", *education_lines, r"\end{itemize}"]))

    # Technical Skills (only if has content)
    skills_lines = []
    for entry in _ensure_list(profile_data.get("skills_hard")):
        if isinstance(entry, dict):
            category = _escape_latex(entry.get("category", "Skills") or "Skills")
            skills = ", ".join(_escape_latex(skill) for skill in _ensure_list(entry.get("skills")))
            if skills:
                skills_lines.append(rf"    \resumeItem{{\textbf{{{category}:}} {skills}}}")
    soft_skills = ", ".join(_escape_latex(skill) for skill in _ensure_list(profile_data.get("skills_soft")))
    if soft_skills:
        skills_lines.append(rf"    \resumeItem{{\textbf{{Soft Skills:}} {soft_skills}}}")
    if skills_lines:
        lines.extend(section("Technical Skills", [r"\begin{itemize}", *skills_lines, r"\end{itemize}"]))

    # Technical Projects (only if has content)
    project_lines = []
    for entry in _ensure_list(profile_data.get("projects")):
        if not isinstance(entry, dict):
            continue
        project_name = _escape_latex(entry.get("name", "Project") or "Project")
        link_value = str(entry.get("link", "") or "").strip()
        description = str(entry.get("description", "") or "").strip()
        heading = project_name
        href_value, display_value = _safe_href(link_value)
        if href_value:
            heading = heading + rf" \href{{{href_value}}}{{\faIcon{{github}}}}"
        project_bullets = [part.strip() for part in re.split(r"[\.\n]+", description) if part.strip()]
        if not project_bullets:
            project_bullets = ["Concise project details are captured in the application profile."]
        project_lines.extend([
            r"\resumeProjectHeading",
            f"   {{{heading}}}{{{display_value if display_value else _escape_latex(description[:80])}}}",
            r"   \begin{itemize}",
            *bullets(project_bullets[:3], indent="       "),
            r"   \end{itemize}",
        ])
    if project_lines:
        lines.extend(section("Technical Projects", [r"\begin{itemize}", *project_lines, r"\end{itemize}"]))

    # Leadership & Community Impact (only if has content)
    leadership_lines = []
    for entry in _ensure_list(profile_data.get("volunteer")):
        if not isinstance(entry, dict):
            continue
        role = _escape_latex(entry.get("role", "Role") or "Role")
        organization = _escape_latex(entry.get("organization", "Organization") or "Organization")
        description = str(entry.get("description", "") or "").strip()
        leadership_bullets = [part.strip() for part in re.split(r"[\.\n]+", description) if part.strip()]
        if not leadership_bullets:
            leadership_bullets = ["Volunteer experience details are available in the profile data."]
        leadership_lines.extend([
            r"\resumeSubheading",
            f"    {{{role}}}{{{organization}}}",
            r"    {Community Impact}",
            r"    {}",
            r"    \begin{itemize}",
            *bullets(leadership_bullets[:3]),
            r"    \end{itemize}",
        ])
    if leadership_lines:
        lines.extend(section("Leadership & Community Impact", [r"\begin{itemize}", *leadership_lines, r"\end{itemize}"]))

    # Certifications (only if has content)
    cert_lines = []
    for entry in _ensure_list(profile_data.get("certifications")):
        if isinstance(entry, dict):
            issuer = _escape_latex(entry.get("issuer", "Issuer") or "Issuer")
            cert_name = _escape_latex(entry.get("name", "Certification") or "Certification")
            date_value = _escape_latex(entry.get("date", "") or "")
            suffix = f" ({date_value})" if date_value else ""
            cert_lines.append(rf"    \resumeItem{{\textbf{{{issuer}:}} {cert_name}{suffix}}}")
    if cert_lines:
        lines.extend(section("Certifications", [r"\vspace{-10pt}", r"\begin{multicols}{2}", r"\begin{itemize}", *cert_lines, r"\end{itemize}", r"\end{multicols}"]))

    # Additional Information (only if has content)
    additional_lines = []
    languages = ", ".join(
        f"{_escape_latex(entry.get('language', ''))} ({_escape_latex(entry.get('proficiency', ''))})"
        for entry in _ensure_list(profile_data.get("languages"))
        if isinstance(entry, dict) and entry.get("language")
    )
    interests = ", ".join(_escape_latex(item) for item in _split_text(profile_data.get("interests")))
    publications = ", ".join(
        _escape_latex(entry.get("name", ""))
        for entry in _ensure_list(profile_data.get("publications"))
        if isinstance(entry, dict) and entry.get("name")
    )
    affiliations = ", ".join(
        _escape_latex(entry.get("name", ""))
        for entry in _ensure_list(profile_data.get("affiliations"))
        if isinstance(entry, dict) and entry.get("name")
    )
    conferences = ", ".join(
        _escape_latex(entry.get("name", ""))
        for entry in _ensure_list(profile_data.get("conferences"))
        if isinstance(entry, dict) and entry.get("name")
    )
    if languages:
        additional_lines.append(rf"    \resumeItem{{\textbf{{Languages:}} {languages}}}")
    if interests:
        additional_lines.append(rf"    \resumeItem{{\textbf{{Interests:}} {interests}}}")
    if publications:
        additional_lines.append(rf"    \resumeItem{{\textbf{{Publications:}} {publications}}}")
    if affiliations:
        additional_lines.append(rf"    \resumeItem{{\textbf{{Affiliations:}} {affiliations}}}")
    if conferences:
        additional_lines.append(rf"    \resumeItem{{\textbf{{Conferences:}} {conferences}}}")
    if additional_lines:
        lines.extend(section("Additional Information", [r"\begin{itemize}", *additional_lines, r"\end{itemize}"]))

    lines.append(r"\end{document}")
    return "\n".join(lines)


def enhance_text(original_text: str) -> str:
    """Enhances a CV bullet point or summary for better impact."""
    if not original_text or len(original_text) < 5:
        return original_text

    if is_mock_mode():
        return original_text + " (Enhanced with powerful action verbs placeholder)"

    prompt = f"""
You are an expert resume writer.
Rewrite the following text to be more impactful, concise, and professional.
Use strong action verbs and highlight accomplishments if present.
Return ONLY the enhanced text. No introductory remarks, no quotes.

Original Text:
{original_text}
    """

    response_text = _call_openrouter([{"role": "user", "content": prompt}])
    return response_text.replace('"', '').strip()


def apply_latex_prompt(latex_source: str, instruction: str, job_description: str = "") -> str:
    """Applies a user instruction to a LaTeX CV and returns updated LaTeX source."""
    if not latex_source or not instruction:
        return latex_source

    if is_mock_mode():
        return latex_source + f"\n% MOCK_EDIT: {instruction}"

    prompt = f"""
You are a LaTeX CV editor.
Given the LaTeX source and a user instruction, update the LaTeX to apply the change.

Rules:
- Return ONLY the full updated LaTeX document.
- Do NOT add markdown fences or commentary.
- Preserve existing structure, packages, and custom commands.
- Only change content needed to satisfy the instruction.

LaTeX Source:
{latex_source}

Instruction:
{instruction}

Job Description (context only):
{job_description}
    """

    response_text = _call_openrouter([{"role": "user", "content": prompt}])
    updated = response_text.replace("```latex", "").replace("```", "").strip()
    if "\\documentclass" not in updated:
        return latex_source
    return updated
