# -*- coding: utf-8 -*-
"""
US Stock Module-Level LLM Analyzer

Orchestrates 6 module-level LLM calls for US stock analysis.
Each module's raw data is sent to the LLM with a domain-specific prompt,
producing a rich analytical text that replaces the simple score+signal.

After all 6 module calls complete, the results feed into a final synthesis
LLM call (handled by GeminiAnalyzer) for the comprehensive Decision Dashboard.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MODULE_NAMES = ["macro", "sector", "fundamental", "technical", "events", "sentiment"]

MODULE_DISPLAY_NAMES = {
    "macro": "Macro Environment",
    "sector": "Sector Context",
    "fundamental": "Fundamental Snapshot",
    "technical": "Multi-Timeframe Technical",
    "events": "Event Calendar & Catalysts",
    "sentiment": "Sentiment & Flow",
}


@dataclass
class ModuleInsight:
    """LLM-generated analysis for a single module."""

    module_name: str
    score: int
    analysis: str = ""
    key_findings: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    signal: str = ""
    outlook: str = "neutral"
    success: bool = True
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_name": self.module_name,
            "display_name": MODULE_DISPLAY_NAMES.get(self.module_name, self.module_name),
            "score": self.score,
            "analysis": self.analysis,
            "key_findings": self.key_findings,
            "risk_factors": self.risk_factors,
            "signal": self.signal,
            "outlook": self.outlook,
            "success": self.success,
            "fallback_used": self.fallback_used,
        }


@dataclass
class USStockModuleInsights:
    """Collection of all 6 module LLM insights."""

    macro: Optional[ModuleInsight] = None
    sector: Optional[ModuleInsight] = None
    fundamental: Optional[ModuleInsight] = None
    technical: Optional[ModuleInsight] = None
    events: Optional[ModuleInsight] = None
    sentiment: Optional[ModuleInsight] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for name in MODULE_NAMES:
            insight = getattr(self, name, None)
            if insight is not None:
                result[name] = insight.to_dict()
            else:
                result[name] = None
        return result

    def to_synthesis_text(self) -> str:
        """Format all module insights into a structured text for the final synthesis prompt."""
        sections = []
        for name in MODULE_NAMES:
            insight = getattr(self, name, None)
            if insight is None:
                continue

            display = MODULE_DISPLAY_NAMES.get(name, name)
            lines = [f"### {display} (Score: {insight.score}/100)"]

            if insight.analysis:
                lines.append(f"\n{insight.analysis}")

            if insight.key_findings:
                lines.append("\n**Key Findings:**")
                for f in insight.key_findings:
                    lines.append(f"- {f}")

            if insight.risk_factors:
                lines.append("\n**Risk Factors:**")
                for r in insight.risk_factors:
                    lines.append(f"- {r}")

            if insight.signal:
                lines.append(f"\n**Signal:** {insight.signal}")
            if insight.outlook:
                lines.append(f"**Outlook:** {insight.outlook}")

            sections.append("\n".join(lines))

        return "\n\n".join(sections)

    def get_successful_count(self) -> int:
        count = 0
        for name in MODULE_NAMES:
            insight = getattr(self, name, None)
            if insight is not None and insight.success:
                count += 1
        return count


class USStockModuleAnalyzer:
    """
    Orchestrates 6 module-level LLM calls for US stock analysis.

    Each module's raw data is sent to the LLM with a domain-specific prompt,
    producing a rich analytical text. Failed calls fall back to data-only insights.

    Usage:
        module_analyzer = USStockModuleAnalyzer(gemini_analyzer, config)
        insights = module_analyzer.analyze_all(code, stock_name, bundle_dict)
    """

    def __init__(self, analyzer, config=None):
        """
        Args:
            analyzer: GeminiAnalyzer instance (used for _call_api_with_retry)
            config: Config object (optional, for max_workers, temperature, etc.)
        """
        self.analyzer = analyzer
        self.config = config
        self.max_workers = getattr(config, "us_module_llm_max_workers", 2) if config else 2
        self.temperature = getattr(config, "us_module_llm_temperature", 0.7) if config else 0.7
        self.max_tokens = getattr(config, "us_module_llm_max_tokens", 2048) if config else 2048

    def analyze_all(
        self,
        code: str,
        stock_name: str,
        bundle_dict: Dict[str, Any],
    ) -> USStockModuleInsights:
        """
        Run 6 module LLM calls with configurable concurrency.

        Args:
            code: US stock ticker (e.g. "AAPL")
            stock_name: Stock name (e.g. "Apple Inc.")
            bundle_dict: Serialized USStockAnalysisBundle (from bundle.to_dict())

        Returns:
            USStockModuleInsights with all module analysis results
        """
        logger.info(f"[{code}] Starting module-level LLM analysis (max_workers={self.max_workers})...")
        insights = USStockModuleInsights()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for module_name in MODULE_NAMES:
                module_data = bundle_dict.get(module_name)
                if module_data is None:
                    logger.debug(f"[{code}] Module '{module_name}' has no data, skipping LLM call")
                    continue
                futures[module_name] = executor.submit(
                    self._analyze_module, module_name, module_data, code, stock_name
                )

            for module_name, future in futures.items():
                try:
                    insight = future.result(timeout=120)
                    setattr(insights, module_name, insight)
                    logger.info(
                        f"[{code}] Module '{module_name}' LLM analysis done "
                        f"(score={insight.score}, outlook={insight.outlook})"
                    )
                except Exception as e:
                    logger.warning(f"[{code}] Module '{module_name}' LLM call failed: {e}, using fallback")
                    fallback = self._create_fallback_insight(module_name, bundle_dict.get(module_name))
                    setattr(insights, module_name, fallback)

        success_count = insights.get_successful_count()
        logger.info(f"[{code}] Module LLM analysis completed: {success_count}/6 modules analyzed successfully")
        return insights

    def _analyze_module(
        self, module_name: str, module_data: Dict[str, Any], code: str, stock_name: str
    ) -> ModuleInsight:
        """Run a single module LLM call."""
        from src.us_stock_modules.us_stock_prompt import MODULE_SYSTEM_PROMPTS, build_module_prompt

        system_prompt = MODULE_SYSTEM_PROMPTS.get(module_name)
        if not system_prompt:
            raise ValueError(f"No system prompt defined for module '{module_name}'")

        user_prompt = build_module_prompt(module_name, module_data, code, stock_name)

        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }

        response_text = self.analyzer._call_api_with_retry(
            user_prompt, generation_config, system_prompt_override=system_prompt
        )

        return self._parse_module_response(module_name, response_text, module_data)

    @staticmethod
    def _infer_outlook_from_score(score: int) -> str:
        """Infer outlook from numeric score when LLM doesn't provide one."""
        if score >= 65:
            return "bullish"
        elif score <= 35:
            return "bearish"
        return "neutral"

    def _parse_module_response(
        self, module_name: str, response_text: str, module_data: Dict[str, Any]
    ) -> ModuleInsight:
        """Parse the LLM response JSON into a ModuleInsight."""
        score = module_data.get("score", 50) if module_data else 50

        try:
            # Clean markdown fences
            cleaned = response_text.strip()
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)

            # Extract JSON object
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = cleaned[start:end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")

            # Determine outlook: use LLM response, but cross-check against score
            raw_outlook = data.get("outlook", "")
            if raw_outlook and raw_outlook.lower() in ("bullish", "bearish", "neutral"):
                llm_outlook = raw_outlook.lower()
            else:
                llm_outlook = None
                logger.debug(
                    f"Module '{module_name}': outlook '{raw_outlook}' invalid or missing"
                )

            score_outlook = self._infer_outlook_from_score(score)

            if llm_outlook is None:
                # LLM didn't provide valid outlook — use score-based
                outlook = score_outlook
            elif llm_outlook == "neutral" and score_outlook != "neutral":
                # LLM defaulted to neutral but score clearly disagrees — override
                outlook = score_outlook
                logger.info(
                    f"Module '{module_name}': LLM said 'neutral' but score={score} "
                    f"implies '{score_outlook}' — overriding outlook"
                )
            else:
                # LLM gave bullish/bearish, or both LLM and score agree on neutral
                outlook = llm_outlook

            return ModuleInsight(
                module_name=module_name,
                score=score,
                analysis=data.get("analysis", ""),
                key_findings=data.get("key_findings", []),
                risk_factors=data.get("risk_factors", []),
                signal=data.get("signal", ""),
                outlook=outlook,
                success=True,
                fallback_used=False,
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"Module '{module_name}' LLM response parse failed: {e}. "
                f"Using raw text as analysis."
            )
            # Use the raw response text as analysis if JSON parsing fails
            return ModuleInsight(
                module_name=module_name,
                score=score,
                analysis=response_text.strip()[:2000],
                key_findings=[],
                risk_factors=[],
                signal=f"Score: {score}/100",
                outlook=self._infer_outlook_from_score(score),
                success=True,
                fallback_used=False,
            )

    def _create_fallback_insight(
        self, module_name: str, module_data: Optional[Dict[str, Any]]
    ) -> ModuleInsight:
        """Create a minimal ModuleInsight from raw data when LLM call fails."""
        score = module_data.get("score", 50) if module_data else 50
        signal = ""

        # Extract the most relevant signal from raw data
        if module_data:
            for key in ["market_regime", "relative_strength", "valuation_signal", "cycle_resonance",
                        "iv_hv_signal", "analyst_consensus"]:
                if key in module_data:
                    signal = str(module_data[key])
                    break

        return ModuleInsight(
            module_name=module_name,
            score=score,
            analysis=f"Data available (score: {score}/100) but LLM analysis unavailable.",
            key_findings=[],
            risk_factors=[],
            signal=signal or f"Score: {score}/100",
            outlook=self._infer_outlook_from_score(score),
            success=False,
            fallback_used=True,
        )
