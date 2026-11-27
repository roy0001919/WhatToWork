import re


class PythonJobClassifier:
    CATEGORY_KEYWORDS = {
        "python_full_stack": [
            "full stack",
            "full-stack",
            "fullstack",
        ],
        "ai_llm": [
            "llm",
            "large language model",
            "rag",
            "retrieval augmented generation",
            "ai agent",
            "machine learning",
            "deep learning",
            "generative ai",
            "artificial intelligence",
            "nlp",
            "natural language processing",
        ],
        "data_engineering": [
            "data engineer",
            "data engineering",
            "etl",
            "airflow",
            "pandas",
            "pyspark",
            "spark",
            "data pipeline",
            "data pipelines",
            "data warehouse",
        ],
        "python_backend": [
            "backend",
            "back-end",
            "back end",
            "fastapi",
            "django",
            "flask",
            "rest api",
            "api development",
        ],
        "python_devops": [
            "devops",
            "dev ops",
            "site reliability",
            "sre",
            "dataops",
            "infrastructure automation",
            "infrastructure as code",
            "platform engineering",
            "platform engineer",
            "gitops",
        ],
        "python_data_analytics": [
            "data analyst",
            "data analysis",
            "data analytics",
            "statistical modelling",
            "statistical modeling",
            "predictive modelling",
            "predictive modeling",
            "business intelligence",
            "business analyst",
        ],
    }

    PYTHON_FRAMEWORKS = [
        "fastapi",
        "django",
        "flask",
    ]

    TECH_KEYWORDS = [
        "python",
        "fastapi",
        "django",
        "flask",
        "sqlalchemy",
        "pandas",
        "numpy",
        "pytorch",
        "tensorflow",
        "scikit-learn",
        "langchain",
        "llamaindex",
        "postgresql",
        "mysql",
        "redis",
        "docker",
        "kubernetes",
        "airflow",
        "spark",
        "pyspark",
        "react",
        "vue",
        "angular",
        "typescript",
        "javascript",
        "aws",
        "gcp",
        "azure",
    ]

    INCIDENTAL_PYTHON_PATTERNS = [
        r"\bpython\b.{0,40}\b(is a plus|nice to have|bonus|optional|preferred)\b",
        r"\b(python is preferred|python preferred)\b",
        r"\b(python knowledge is a plus)\b",
        r"\bbonus points\b.{0,200}\bpython\b",
        r"\bpython\b.{0,80}\b(bonus points|bonus skill)\b",
        r"\b(at least one of|one of the following)\b.{0,100}\bpython\b",
        r"\b(python|javascript|shell scripting)\b.{0,100}\b(preferred|nice to have|optional)\b",
        r"\b(python|javascript|js|go)\b.{0,60}\b(or|and)\b.{0,60}\b(python|javascript|js|go)\b",
        r"\b(python|javascript|js|go)\b.{0,100}\b(read/write basic scripts|basic scripting)\b",
        r"\b(python|powershell|bash|shell)\b.{0,60}\b(or|and/or)\b.{0,60}\b(python|powershell|bash|shell)\b",
        r"\b(python|r)\b.{0,50}\b(or|and/or)\b.{0,50}\b(python|r)\b",
        r"\b(python|javascript|python or bash|bash or python)\b.{0,100}\b(in addition|would be great|a plus|bonus)\b",
        r"\b(scripting languages|programming languages|any programming language)\b.{0,150}\bpython\b",
        r"\bpython\b.{0,100}\b(such as|for example|e\.g\.)\b",
        r"\b(nice-to-have|nice to have|preferred qualifications|bonus qualifications)\b.{0,200}\bpython\b",
        r"\b(python and bash|bash and python)\b.{0,80}\b(scripting ability|scripting skills|nice to have)\b",
        r"\b(scripting|automation)\b.{0,80}\b(python or|python,|python and/or)\b",
        r"\bpython\b.{0,80}\b(or similar technologies|or similar tools|or equivalent)\b",
        r"\b(python)\b.{0,80}\b(for data analysis|for analysis)\b",
    ]

    STRONG_PYTHON_PATTERNS = [
        r"\b(using|primarily in|written in|built in|developed in|based on)\s+python\b",
        r"\bpython\b.{0,50}\b(software development|software engineering|development experience|programming skills)\b",
        r"\b(pure python|python engineers|python engineering team|python software development)\b",
        r"\bpython\b.{0,60}\b(infra-as-code|infrastructure as code)\b",
        r"\b(develop|build|maintain|implement|create|write)\b.{0,80}\b(python scripts|python applications|python services|python tooling)\b",
        r"\b(python scripting|python automation|python programming)\b",
        r"\b(python)\b.{0,80}\b(automation|automated tooling|operational tooling|data pipelines|etl workflows)\b",
        r"\b(python)\b.{0,80}\b(statistical modelling|statistical modeling|predictive modelling|predictive modeling)\b",
        r"\b(strong fundamentals in|very good knowledge of|good knowledge of)\b.{0,100}\bpython\b",
        r"\bsolid python\b.{0,100}\b(statistical|predictive|modelling|modeling)\b",
        r"\b(proficiency in python|proficient in python|experience with python|experience in python)\b",
        r"\bpython\b.{0,40}\b(required|requirements|proficiency|proficient)\b",
    ]

    REQUIRED_PYTHON_PATTERNS = [
        r"\bpython\b.{0,40}\b(required|requirements|proficiency|proficient)\b",
        r"\bexperience with python\b",
        r"\bexperience in python\b",
        r"\bstrong python skills\b",
        r"\bpython programming skills\b",
        r"\bpython development experience\b",
        r"\bproficiency in python\b",
    ]

    @staticmethod
    def _normalize(text: str | None) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.lower()).strip()

    @classmethod
    def _contains_keyword(cls, text: str, keyword: str) -> bool:
        escaped = re.escape(keyword.lower())
        pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        return re.search(pattern, text) is not None

    @classmethod
    def _extract_tech_stack(cls, text: str) -> list[str]:
        return [
            technology
            for technology in cls.TECH_KEYWORDS
            if cls._contains_keyword(text, technology)
        ]

    @classmethod
    def _matches_patterns(cls, text: str, patterns: list[str]) -> bool:
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        )

    @classmethod
    def _has_python_signal(
        cls,
        title: str,
        description: str,
        raw_data: dict | None,
    ) -> tuple[bool, float, str]:

        if cls._contains_keyword(title, "python"):
            return (
                True,
                0.98,
                "Python is explicitly mentioned in the job title.",
            )

        for framework in cls.PYTHON_FRAMEWORKS:
            if cls._contains_keyword(title, framework):
                return (
                    True,
                    0.95,
                    f"{framework.title()} is a Python framework in the job title.",
                )

        has_python = cls._contains_keyword(description, "python")

        if not has_python:
            for framework in cls.PYTHON_FRAMEWORKS:
                framework_pattern = (
                    rf"\b(using|with|build|develop|developing|experience with)"
                    rf"\s+{re.escape(framework)}\b"
                )
                if re.search(framework_pattern, description):
                    return (
                        True,
                        0.90,
                        f"{framework.title()} is explicitly used in the job description.",
                    )

        if has_python:
            python_signal_description = re.sub(
                r"[^.!?]*\bpython\s+or\s+r\b[^.!?]*(?:[.!?]|$)",
                " ",
                description,
                flags=re.IGNORECASE,
            )

            if cls._matches_patterns(
                description,
                cls.INCIDENTAL_PYTHON_PATTERNS,
            ):
                independent_strong_signal = cls._matches_patterns(
                    python_signal_description,
                    cls.STRONG_PYTHON_PATTERNS,
                )

                if not independent_strong_signal:
                    return (
                        False,
                        0.15,
                        "Python is mentioned as an optional, preferred, alternative, or auxiliary skill.",
                    )

            if cls._matches_patterns(
                python_signal_description,
                cls.STRONG_PYTHON_PATTERNS,
            ):
                return (
                    True,
                    0.90,
                    "Python is explicitly connected to development or core job responsibilities.",
                )

            if cls._matches_patterns(
                python_signal_description,
                cls.REQUIRED_PYTHON_PATTERNS,
            ):
                return (
                    True,
                    0.85,
                    "Python is explicitly listed as a required skill.",
                )

            return (
                False,
                0.25,
                "Python is mentioned, but its role in the job responsibilities is unclear.",
            )

        raw_text = cls._normalize(str(raw_data)) if raw_data else ""

        if cls._contains_keyword(raw_text, "python"):
            return (
                False,
                0.15,
                "Python appears only in source metadata.",
            )

        return (
            False,
            0.0,
            "No strong Python-related signal was found.",
        )

    @classmethod
    def _detect_category(cls, text: str) -> str:
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            if any(
                cls._contains_keyword(text, keyword)
                for keyword in keywords
            ):
                return category

        return "other_python"

    @classmethod
    def classify(
        cls,
        title: str | None,
        description: str | None = None,
        raw_data: dict | None = None,
    ) -> dict:

        normalized_title = cls._normalize(title)
        normalized_description = cls._normalize(description)

        combined_text = (
            f"{normalized_title} {normalized_description}"
        ).strip()

        python_related, score, reason = cls._has_python_signal(
            normalized_title,
            normalized_description,
            raw_data,
        )

        tech_stack = cls._extract_tech_stack(combined_text)

        if not python_related:
            return {
                "python_related": False,
                "python_category": None,
                "python_match_score": score,
                "tech_stack": tech_stack,
                "reason": reason,
            }

        category = cls._detect_category(combined_text)

        return {
            "python_related": True,
            "python_category": category,
            "python_match_score": score,
            "tech_stack": tech_stack,
            "reason": reason,
        }
