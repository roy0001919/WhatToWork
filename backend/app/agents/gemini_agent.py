from typing import Any
from uuid import UUID

from google.genai import types
from sqlalchemy.orm import Session

from app.agents.tool_registry import ToolRegistry
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agent import AgentToolCall, AgentToolResult
from app.services.llm_provider import llm_provider


class GeminiAgent:
    MAX_TOOL_ROUNDS = 5

    SYSTEM_INSTRUCTION = """
You are WhatToWork, an AI Job Search and Automation Agent.

Your responsibilities:
- Understand the user's job search goals and candidate profile.
- Discover relevant job opportunities from the available job database.
- Evaluate geographic and employment eligibility separately from job discovery.
- Analyze job requirements and candidate matching.
- Rank opportunities and explain actionable recommendations.

Core rules:
1. Use available tools whenever real job data or analysis is needed.
2. Never invent job listings, company details, tool results, or analysis results.
3. Use only the registered functions provided to you.
4. Do not claim a tool succeeded unless its result confirms success.
5. If a tool fails, explain the limitation honestly.
6. Respect the user's profile when evaluating eligibility.
7. Never request or expose passwords, API keys, or unnecessary personal data.
8. Do not claim that a job application has been submitted.
9. Respond in the same language as the user's message.
10. Summarize tool results accurately and clearly.

Job search strategy:
1. Separate the candidate's current residence from the job's location.
   The candidate's country is an eligibility consideration, not automatically
   a job-location search filter.
2. Never set the search_jobs country argument to the candidate's residence
   merely because the candidate lives there.
3. Only use the country argument when the user explicitly requests jobs
   located in a particular country or geographic market.
4. For worldwide or international remote searches, omit country unless
   the user specifies a target job country.
5. Apply workplace_type="remote" when the user explicitly requests remote
   jobs. Do not add unrequested employment or location restrictions.
6. Search broadly before narrowing results. The keyword search uses substring
   matching, so prefer broad terms such as "Python" over an entire job title
   such as "Python Backend Engineer".
7. When useful, search with multiple relevant broad keywords or job-title
   variations. Avoid assuming one keyword search represents the whole market.
8. The search tool returns at most 20 jobs per call. Inspect total, skip,
   limit, and returned items. If more relevant results are needed and
   additional results exist, continue with the next skip offset.
9. Do not repeatedly request the same page. Track job IDs and avoid duplicates
   when combining results from multiple searches or pages.
10. Use a reasonable number of search calls. Prioritize collecting enough
    relevant candidates to satisfy the user's requested result count.
11. Do not analyze every database result unnecessarily. First discover
    candidates, then check eligibility and analyze the most relevant jobs.

Eligibility and analysis:
1. Evaluate whether the employer accepts the candidate's actual residence
   or working location using check_eligibility.
2. Do not assume that a job is available worldwide just because it says
   "remote".
3. Do not assume that a job is unavailable merely because its listed country
   differs from the candidate's residence.
4. Distinguish confirmed eligibility from uncertain or unavailable information.
5. Use analyze_job when a detailed skill and experience match is needed.
6. Do not present uncertain eligibility as confirmed eligibility.

Final response:
- State how many jobs were actually found and returned.
- Distinguish search results from jobs that passed eligibility checks.
- Clearly identify limitations, missing information, and uncertain results.
- Never describe test or example records as genuine vacancies.
"""

    @classmethod
    def _build_config(
        cls,
        enable_tools: bool = True,
    ) -> types.GenerateContentConfig:
        config_kwargs = {
            "system_instruction": cls.SYSTEM_INSTRUCTION,
            "automatic_function_calling": (
                types.AutomaticFunctionCallingConfig(disable=True)
            ),
        }

        if enable_tools:
            declarations = ToolRegistry.get_declarations()

            functions = [
                types.FunctionDeclaration(
                    name=item["name"],
                    description=item.get("description", ""),
                    parameters_json_schema=item["parameters"],
                )
                for item in declarations
            ]

            config_kwargs["tools"] = [
                types.Tool(function_declarations=functions)
            ]

        return types.GenerateContentConfig(**config_kwargs)

    @staticmethod
    def _serialize_content(content: types.Content) -> dict[str, Any]:
        return content.model_dump(mode="json", exclude_none=True)

    @staticmethod
    def _content_text(content: types.Content) -> str | None:
        parts = content.parts or []
        text = "\n".join(part.text for part in parts if part.text)
        return text.strip() or None

    @classmethod
    def run(
        cls,
        message: str,
        profile_id: int,
        db: Session,
        conversation_id: UUID,
    ) -> dict[str, Any]:

        if not message or not message.strip():
            raise ValueError("Message cannot be empty.")

        if type(profile_id) is not int or profile_id <= 0:
            raise ValueError("Invalid profile_id.")

        if not isinstance(conversation_id, UUID):
            raise ValueError("Invalid conversation_id.")

        history = ConversationRepository.get_messages(
            db=db,
            conversation_id=conversation_id,
        )

        contents: list[types.Content] = []

        for item in history:
            if item.gemini_payload:
                contents.append(
                    types.Content.model_validate(item.gemini_payload)
                )

        pending_messages: list[dict[str, Any]] = []

        user_content = types.Content(
            role="user",
            parts=[types.Part(text=message.strip())],
        )

        contents.append(user_content)

        pending_messages.append({
            "role": "user",
            "content": message.strip(),
            "gemini_payload": cls._serialize_content(user_content),
        })

        tool_calls: list[AgentToolCall] = []
        tool_results: list[AgentToolResult] = []

        config = cls._build_config()

        def save_pending_messages() -> None:
            for item in pending_messages:
                ConversationRepository.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role=item["role"],
                    content=item.get("content"),
                    gemini_payload=item.get("gemini_payload"),
                )

        for round_index in range(cls.MAX_TOOL_ROUNDS):
            response = llm_provider.generate_content(
                contents=contents,
                config=config,
            )

            candidates = response.candidates or []
            if not candidates:
                raise RuntimeError(
                    "Gemini returned no response candidates."
                )

            candidate_content = candidates[0].content
            if candidate_content is None:
                raise RuntimeError(
                    "Gemini returned an empty candidate."
                )

            contents.append(candidate_content)

            candidate_text = cls._content_text(candidate_content)
            pending_messages.append({
                "role": "assistant",
                "content": candidate_text,
                "gemini_payload": cls._serialize_content(candidate_content),
            })

            parts = candidate_content.parts or []
            function_calls = [
                part.function_call
                for part in parts
                if part.function_call is not None
            ]

            if not function_calls:
                final_text = response.text or candidate_text
                if not final_text:
                    raise RuntimeError(
                        "Gemini returned no final text."
                    )

                final_text = final_text.strip()
                save_pending_messages()

                return {
                    "message": final_text,
                    "tool_calls": tool_calls,
                    "tool_results": tool_results,
                }

            response_parts = []

            for function_call in function_calls:
                name = function_call.name or "unknown"
                call_id = function_call.id
                arguments = dict(function_call.args or {})

                tool_calls.append(
                    AgentToolCall(
                        id=call_id,
                        name=name,
                        arguments=arguments,
                    )
                )

                executed_result = ToolRegistry.execute(
                    name=name,
                    arguments=arguments,
                    db=db,
                    profile_id=profile_id,
                )

                result = executed_result.model_copy(
                    update={"id": call_id}
                )
                tool_results.append(result)

                function_response = types.FunctionResponse(
                    name=name,
                    id=call_id,
                    response=result.model_dump(
                        mode="json",
                        exclude={"id"},
                    ),
                )

                response_parts.append(
                    types.Part(function_response=function_response)
                )

            tool_response_content = types.Content(
                role="user",
                parts=response_parts,
            )

            contents.append(tool_response_content)

            pending_messages.append({
                "role": "tool",
                "content": None,
                "gemini_payload": cls._serialize_content(
                    tool_response_content
                ),
            })

            if round_index == cls.MAX_TOOL_ROUNDS - 1:
                final_response = llm_provider.generate_content(
                    contents=contents,
                    config=cls._build_config(enable_tools=False),
                )

                final_candidates = final_response.candidates or []
                if not final_candidates:
                    raise RuntimeError(
                        "Gemini returned no final response candidates."
                    )

                final_content = final_candidates[0].content
                if final_content is None:
                    raise RuntimeError(
                        "Gemini returned an empty final response."
                    )

                final_text = (
                    final_response.text
                    or cls._content_text(final_content)
                )

                if not final_text:
                    final_text = (
                        "I completed the available tool executions, "
                        "but could not generate a detailed summary. "
                        "Please review the collected tool results."
                    )

                final_text = final_text.strip()
                contents.append(final_content)

                pending_messages.append({
                    "role": "assistant",
                    "content": final_text,
                    "gemini_payload": cls._serialize_content(final_content),
                })

                save_pending_messages()

                return {
                    "message": final_text,
                    "tool_calls": tool_calls,
                    "tool_results": tool_results,
                }

        raise RuntimeError(
            "Agent execution ended unexpectedly."
        )
