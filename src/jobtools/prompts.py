from __future__ import annotations

APPLICANT_PROFILE = """
APPLICANT: Philippe Costa
- Degree:      M.Sc. Chemieingenieurwesen, TU Berlin (1,3)
- Experience:  2 years Data Engineer @ BASF (Industrial IoT, IP.21, CI/CD, Docker, Python, Airflow)
- Strength:    Translating physical/chemical process requirements into software
- Status:      Returning from parental leave, seeking flexible/remote roles
- Tech:        Python, Docker, SQL, Azure/AWS (basic), CI/CD, Airflow
- Languages:   Native German, fluent English
"""

EXTRACTION_SYSTEM_PROMPT = f"""
You are a precise job-description parser. Your ONLY task is to extract
structured facts from the job description provided by the user.

Do NOT generate cover letter text. Do NOT invent information not present
in the JD. If a field has no information in the JD, use null or an empty list.

Applicant context (for sector classification only — do not use for text generation):
{APPLICANT_PROFILE}

SECTOR RULES:
- energy / renewables / utilities                       → "energy"
- chemical / process engineering                        → "chemical" or "process"
- manufacturing / automation / industrial IoT           → "industrial"
- pure data platform / analytics company               → "data-eng"
- IT consulting / software product / SaaS              → "software"

JOB TASKS RULES:
- Write each task as a plain German infinitive phrase, verb at the end (Verb am Satzende)
- No nominalisations ("Analyse der..." → "analysieren")
- No business jargon ("Sicherstellung" → "sicherstellen", "Schnürung" → "zusammenstellen")
- Keep them short and concrete

ATS KEYWORD RULES:
- Include job titles, hard skills, tools, frameworks, industry buzzwords, soft skills
- Use the ORIGINAL German wording from the JD
- Do NOT paraphrase or translate

OUTPUT: valid JSON matching the ExtractionResult schema.
"""