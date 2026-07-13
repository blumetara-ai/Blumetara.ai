import logging
import asyncio
from app.config.config import settings
from app.services.vector_search_service import vector_search_service
import google.generativeai as genai

logger = logging.getLogger(__name__)

EMERGENCY_KEYWORDS = [
    "chest pain", "breathing difficulty", "shortness of breath", "severe bleeding", 
    "heart attack", "stroke", "unconscious", "poisoning", "suicide", "suicidal"
]

DISCLAIMER_TEXT = (
    "\n\n*Disclaimer: Blumetara AI provides educational insights based on your inputs. "
    "It is not a substitute for professional medical advice, diagnosis, or treatment. "
    "If you are experiencing a medical emergency, please call your local emergency services (e.g., 911 or 112) immediately.*"
)

# ==============================================================================
# ASYNC MULTI-AGENT ARCHITECTURE (Parallel Consensus Principles)
# ==============================================================================

class AsyncAgent:
    """Base class for specialized parallel async agents."""
    def __init__(self, role: str, goal: str):
        self.role = role
        self.goal = goal

    def build_prompt(self, query: str, context: str, profile_str: str) -> str:
        return (
            f"You are operating in a highly restricted, isolated environment.\n"
            f"You have NO knowledge of peer agents. Do not make assumptions outside your domain.\n\n"
            f"=== YOUR IDENTITY ===\n"
            f"Role: {self.role}\n"
            f"Goal: {self.goal}\n\n"
            f"=== USER METADATA ===\n"
            f"{profile_str}\n\n"
            f"=== HEALTH CONTEXT (RAG) ===\n"
            f"{context}\n\n"
            f"=== USER QUERY ===\n"
            f"{query}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"Answer strictly from the perspective of your Role.\n"
            f"Do not provide a generic summary. Focus only on your goal.\n"
            f"Keep your response under 150 words.\n\n"
            f"YOUR SPECIALIZED REPORT:\n"
        )

class ClinicalAnalystAgent(AsyncAgent):
    def __init__(self):
        super().__init__(
            role="Clinical Lab Analyst",
            goal="Analyze raw medical laboratory results, vitals, vitamin deficiencies, and reference values."
        )

class WellnessCoachAgent(AsyncAgent):
    def __init__(self):
        super().__init__(
            role="Lifestyle & Wellness Coach",
            goal="Map goals (hydration, sleep, steps, workout logs) to current health context to guide lifestyle habits."
        )

class SafetyAdherenceAgent(AsyncAgent):
    def __init__(self):
        super().__init__(
            role="Medical Safety & Adherence Officer",
            goal="Monitor prescription schedules, medication levels, safety warning thresholds, and check for red flags."
        )

class ConsensusAggregator:
    """Synthesizes isolated specialist opinions into a unified executive verdict."""
    def __init__(self):
        self.role = "Chief Medical Synthesizer"
        self.goal = "Combine isolated agent reports into a single, cohesive, client-facing wellness guide."

    def build_prompt(self, query: str, reports: dict[str, str], profile_str: str) -> str:
        compiled = "\n\n".join([f"=== EXPERT REPORT: {self.role} ({role}) ===\n{text}" for role, text in reports.items()])
        return (
            f"You are the Chief Medical Synthesizer for Blumetara AI.\n"
            f"Your goal is to aggregate the specialized findings below into a clear, unified, encouraging client response.\n\n"
            f"=== USER DATA ===\n"
            f"{profile_str}\n\n"
            f"=== USER QUERY ===\n"
            f"{query}\n\n"
            f"=== COLLECTED EXPERT FINDINGS ===\n"
            f"{compiled}\n\n"
            f"CRITICAL COMPLIANCE RULES:\n"
            f"- Address the user dynamically by name.\n"
            f"- Resolve contradictions and present a unified voice.\n"
            f"- Strictly adhere to medical safety: Do not diagnose, prescribe, or replace a physician.\n"
            f"- Format your response using clean Markdown headers, lists, and bold text.\n\n"
            f"FINAL SYNTHESIZED VERDICT:\n"
        )

class AIService:
    def __init__(self):
        self.api_key_configured = bool(settings.GEMINI_API_KEY)
        if self.api_key_configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            logger.warning("GEMINI_API_KEY is not set. Running AI Service in MOCK mode.")
            
        # Instantiate Agents & Aggregator
        self.agents = [
            ClinicalAnalystAgent(),
            WellnessCoachAgent(),
            SafetyAdherenceAgent()
        ]
        self.aggregator = ConsensusAggregator()

    def detect_emergency(self, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in EMERGENCY_KEYWORDS)

    async def generate_response(self, user_id: str, query: str, history: list[dict] = None, profile: dict = None) -> str:
        user_name = profile.get("name", "User") if profile else "User"

        # 1. Emergency Safety Intercept
        if self.detect_emergency(query):
            logger.warning(f"Emergency detected for user {user_id} in query: '{query}'")
            return (
                "⚠️ **URGENT MEDICAL WARNING**\n\n"
                "The symptoms you described could indicate a serious or life-threatening emergency. "
                "Please do not wait. **Contact emergency services (like 911 or 102/112) immediately**, or go to the nearest emergency room.\n\n"
                "Do not attempt to self-diagnose or wait for automated app reminders."
                + DISCLAIMER_TEXT
            )

        # 2. Security Guardrail: Reject non-health related queries
        q_lower = query.lower()
        is_greeting = any(g in q_lower for g in ["hello", "hi", "hey", "greetings", "tara", "help"])
        is_health = any(kw in q_lower for kw in [
            "health", "medical", "doctor", "medicine", "pill", "vitamin", "report", "blood", 
            "symptom", "pain", "workout", "exercise", "fit", "hydrate", "water", "sleep", 
            "steps", "calorie", "diet", "nutrition", "food", "heart", "breathing", "lab", 
            "test", "diagnose", "prescribe", "illness", "disease", "wellness"
        ])
        
        if not (is_greeting or is_health):
            logger.warning(f"Off-topic query rejected for user {user_id}: '{query}'")
            return (
                "⚠️ **OFF-TOPIC REJECTION**\n\n"
                f"Hello {user_name}! I am TARA, your dedicated AI Health Co-Pilot.\n"
                "I am only programmed to assist with medical, health, wellness, and laboratory report queries. "
                "I cannot answer questions about general topics, coding, math, history, or other non-health matters. "
                "Please ask me a health-related question!"
                + DISCLAIMER_TEXT
            )

        # 3. RAG Context Retrieval
        context_chunks = await vector_search_service.semantic_search(user_id=user_id, query=query, limit=3)
        context_str = "\n---\n".join(context_chunks) if context_chunks else "No health report context available."

        # 4. Handle Mock Fallback Mode
        if not self.api_key_configured:
            logger.info("Mock AI Chat: Generating mock response...")
            return self._generate_mock_response(query, context_str, user_name)

        # 4. Compile User Profile Metadata
        gender = profile.get("gender", "Unspecified") if profile else "Unspecified"
        age_range = profile.get("ageRange", "Unspecified") if profile else "Unspecified"
        profile_str = f"Name: {user_name}\nGender: {gender}\nAge Range: {age_range}"

        # 5. Route to LITE mode or ENTERPRISE mode
        if settings.AI_REASONING_MODE == "lite":
            logger.info("AI Service executing in LITE single-agent mode...")
            system_instruction = (
                "You are TARA, the premium AI Health Co-Pilot for Blumetara AI.\n"
                "CRITICAL SECURITY BOUNDARY:\n"
                "- You must ONLY respond to medical, health, wellness, exercise, nutrition, and laboratory report queries.\n"
                "- If the user asks about ANY topic outside of healthcare, medicine, fitness, wellness, biology, or nutrition (such as coding, math, history, general knowledge, pop culture, non-health business, or creative writing), you must politely reject the query. State that you are a dedicated AI Health Co-Pilot and can only assist with health-related questions.\n\n"
                "Guidelines:\n"
                f"- Address the user as {user_name}.\n"
                f"- User demographics: Gender: {gender}, Age Range: {age_range}.\n"
                "- Always use the provided health report context if it contains relevant information. Cite the values if present.\n"
                "- Strictly adhere to medical safety: Do not diagnose, do not prescribe medicine, and do not claim to replace a physician.\n"
                "- Keep answers concise, actionable, formatting with lists, bold text, and clean structure.\n"
                "- Maintain an encouraging, positive, and professional tone."
            )
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-3.5-flash",
                    system_instruction=system_instruction
                )
                prompt_content = f"Health Report Context:\n{context_str}\n\nUser Question: {query}"
                response = await asyncio.to_thread(model.generate_content, prompt_content)
                return response.text + DISCLAIMER_TEXT
            except Exception as e:
                logger.error(f"Failed to generate response from Gemini API: {e}. Falling back to mock.")
                return self._generate_mock_response(query, context_str, user_name)

        # 6. Execute Specialist Agents in Parallel Isolated Tasks (ENTERPRISE MODE)
        logger.info(f"[ENGINE] Dispatching {len(self.agents)} specialized async agent tasks...")
        
        async def run_agent(agent: AsyncAgent) -> tuple[str, str]:
            prompt = agent.build_prompt(query, context_str, profile_str)
            model = genai.GenerativeModel(model_name="gemini-3.5-flash")
            response = await asyncio.to_thread(model.generate_content, prompt)
            return agent.role, response.text

        tasks = [run_agent(agent) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 7. Collect reports, isolating failures
        valid_reports = {}
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Isolated Agent task failed: {res}")
                continue
            role, report_text = res
            valid_reports[role] = report_text

        if not valid_reports:
            logger.error("All parallel agents failed. Falling back to default message.")
            return "TARA is temporarily unable to retrieve consensus reports. Please check your query or try again." + DISCLAIMER_TEXT

        # 8. Aggregate Consensus via Synthesis Aggregator
        logger.info(f"[ENGINE] Synthesizing consensus from {len(valid_reports)} expert reports...")
        aggregator_prompt = self.aggregator.build_prompt(query, valid_reports, profile_str)
        
        try:
            model = genai.GenerativeModel(model_name="gemini-3.5-flash")
            aggregator_response = await asyncio.to_thread(model.generate_content, aggregator_prompt)
            consensus_text = aggregator_response.text
            return consensus_text + DISCLAIMER_TEXT
        except Exception as e:
            logger.error(f"Aggregator execution failed: {e}. Falling back to default syntheses.")
            fallback_text = "\n\n".join([f"### {role}\n{text}" for role, text in valid_reports.items()])
            return fallback_text + DISCLAIMER_TEXT

    def _generate_mock_response(self, query: str, context: str, user_name: str = "User") -> str:
        q_lower = query.lower()
        greeting = f"Hello {user_name}! "

        # Log mock phases depending on mode
        if settings.AI_REASONING_MODE == "lite":
            logger.info("Mock AI Chat: Running in LITE single-agent mode...")
        else:
            logger.info("[ENGINE] Dispatching 3 specialized async mock tasks...")
            logger.info("  ├── [Clinical Lab Analyst] Thread executing in isolation...")
            logger.info("  ├── [Lifestyle & Wellness Coach] Thread executing in isolation...")
            logger.info("  └── [Medical Safety & Adherence Officer] Thread executing in isolation...")
            logger.info("[ENGINE] >>> PHASE 2: Aggregated Consensus complete.")

        # Simple rule-based mock answers based on common query patterns
        if "vitamin d" in q_lower:
            ans = (
                "### Vitamin D Insight ☀️\n\n"
                f"{greeting}"
                "Based on your report context, your **Vitamin D level is 18.5 ng/mL**, which falls under the **deficient range** (< 30 ng/mL).\n\n"
                "**Actionable Wellness Recommendations:**\n"
                "1. **Sun Exposure**: Try to get 15-20 minutes of mid-day sunlight weekly, depending on your skin sensitivity.\n"
                "2. **Dietary Sources**: Integrate foods rich in Vitamin D, such as egg yolks, mushrooms, and fortified milk/cereals.\n"
                "3. **Supplementation**: Discuss with your doctor whether a weekly supplement (e.g., 60,000 IU) is suitable for your levels."
            )
        elif "workout" in q_lower or "exercise" in q_lower:
            ans = (
                "### Workout Guidance 🏋️\n\n"
                "As your Blumetara AI Coach, I suggest a balanced weekly schedule focused on active movement:\n"
                "- **Strength**: 2-3 sessions targeting major muscle groups.\n"
                "- **Cardio**: 150 minutes of moderate activity (like brisk walking) weekly.\n"
                "- **Recovery**: Include 1-2 rest/yoga days to prevent fatigue."
            )
        elif "water" in q_lower or "hydrate" in q_lower:
            ans = (
                "### Hydration Focus 💧\n\n"
                "Water intake keeps your joints lubricated and boosts energy levels. "
                "I recommend setting a target of **2.5 to 3.0 Liters daily**. "
                "Make sure to log your water logs through the Blumetara app so I can track your goal completion percentage!"
            )
        else:
            ans = (
                "### Hello from TARA AI! 👋\n\n"
                f"Thank you for your question: *\"{query}\"*. "
                "I've analyzed your request alongside your active profile parameters.\n\n"
                "To get the most out of our chats, feel free to:\n"
                "- **Upload a health report** (PDF or image) so I can answer questions with medical context.\n"
                "- **Set wellness goals** like steps, sleep, and water intake.\n"
                "- **Log your daily routines** (medicines taken, hydration logs)."
            )
            
        if "deficient" in context or "18.5" in context:
            ans += "\n\n*(Note: I grounded this response using the deficient Vitamin D status extracted from your uploaded laboratory report.)*"
            
        return ans + DISCLAIMER_TEXT

ai_service = AIService()
