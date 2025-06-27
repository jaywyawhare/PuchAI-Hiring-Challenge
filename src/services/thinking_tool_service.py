"""
Thinking Tool Service for dynamic, reflective problem-solving.
Provides a step-by-step, revisable, and branchable process for complex analysis and planning.
"""
import os
import json
from typing import Dict, Any, Optional, List
import logging
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from ..models.base import RichToolDescription, ToolService

logger = logging.getLogger(__name__)

class ThinkingToolEngine:
    """Engine for dynamic, reflective, and branching problem-solving."""
    def __init__(self):
        self.thought_history: List[Dict[str, Any]] = []
        self.branches: Dict[str, List[Dict[str, Any]]] = {}
        self.disable_thought_logging = os.environ.get("DISABLE_THOUGHT_LOGGING", "false").lower() == "true"

    def validate_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        required = ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
        for key in required:
            if key not in data:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Missing required field: {key}"))
        if not isinstance(data["thought"], str):
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'thought' must be a string"))
        if not isinstance(data["nextThoughtNeeded"], bool):
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'nextThoughtNeeded' must be a boolean"))
        if not isinstance(data["thoughtNumber"], int) or data["thoughtNumber"] < 1:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'thoughtNumber' must be an integer >= 1"))
        if not isinstance(data["totalThoughts"], int) or data["totalThoughts"] < 1:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'totalThoughts' must be an integer >= 1"))
        if "isHypothesis" in data and data["isHypothesis"] is not None and not isinstance(data["isHypothesis"], bool):
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'isHypothesis' must be a boolean"))
        if "isVerification" in data and data["isVerification"] is not None and not isinstance(data["isVerification"], bool):
            raise McpError(ErrorData(code=INTERNAL_ERROR, message="'isVerification' must be a boolean"))
        return data

    def format_thought(self, thought_data: Dict[str, Any]) -> str:
        prefix = "🔄 Revision" if thought_data.get("isRevision") else ("🌿 Branch" if thought_data.get("branchFromThought") else "💭 Thought")
        context = ""
        if thought_data.get("isRevision"):
            context = f" (revising thought {thought_data.get('revisesThought')})"
        elif thought_data.get("branchFromThought"):
            context = f" (from thought {thought_data.get('branchFromThought')}, ID: {thought_data.get('branchId')})"
        if thought_data.get("isHypothesis"):
            prefix = "🧪 Hypothesis"
        elif thought_data.get("isVerification"):
            prefix = "✅ Verification"
        header = f"{prefix} {thought_data['thoughtNumber']}/{thought_data['totalThoughts']}{context}"
        border_len = max(len(header), len(thought_data['thought'])) + 4
        border = "─" * border_len
        thought_line = thought_data['thought'].ljust(border_len - 2)
        return f"""
┌{border}┐
│ {header} │
├{border}┤
│ {thought_line} │
└{border}┘"""

    def extract_branches(self, thought_text: str) -> List[str]:
        """
        Dynamically extract possible reasoning branches from the thought text.
        This can be replaced with more advanced NLP, but for now uses simple rules.
        """
        import re
        branches = set()
        # Look for explicit dilemmas/questions
        if re.search(r'\b(should|do you|is it right|is it wrong|must|could|would|can you)\b', thought_text, re.I):
            branches.add("yes")
            branches.add("no")
        # Look for keywords suggesting tradeoffs or values
        if re.search(r'\b(consequence|outcome|result|harm|benefit|cost|save|risk|reward|loss|gain)\b', thought_text, re.I):
            branches.add("consequentialist")
        if re.search(r'\b(rule|law|duty|obligation|right|wrong|moral|immoral|principle)\b', thought_text, re.I):
            branches.add("rule-based")
        if re.search(r'\b(risk|uncertain|unknown|chance|probability|possibility)\b', thought_text, re.I):
            branches.add("risk-analysis")
        # Fallback: if no branches found, just continue the thought
        if not branches:
            branches.add("continue")
        return list(branches)

    def auto_generate_thoughts(self, initial_data: Dict[str, Any], max_depth: int = 5) -> List[Dict[str, Any]]:
        from copy import deepcopy
        queue = [deepcopy(initial_data)]
        all_thoughts = []
        explored = set()
        depth = 0
        while queue and depth < max_depth:
            current = queue.pop(0)
            # Remove unserializable fields
            current = {k: v for k, v in current.items() if not hasattr(v, '__dict__') and not callable(v)}
            key = json.dumps({k: v for k, v in current.items() if k in ("thought", "thoughtNumber", "branchId")}, sort_keys=True)
            if key in explored:
                continue
            explored.add(key)
            all_thoughts.append(current)
            # Dynamically extract branches from the current thought
            branches = self.extract_branches(current["thought"])
            for branch in branches:
                if branch == "continue":
                    continue  # Don't branch, just continue
                branch_data = deepcopy(current)
                branch_data["thought"] = f"[{branch.capitalize()} branch] {current['thought']}"
                branch_data["branchId"] = branch
                branch_data["branchFromThought"] = current["thoughtNumber"]
                branch_data["thoughtNumber"] += 1
                queue.append(branch_data)
            depth += 1
        return all_thoughts

    def process_thought(self, data: Dict[str, Any]) -> Dict[str, Any]:
        td = self.validate_input(data)
        # Remove unserializable fields from td
        td_serializable = {k: v for k, v in dict(td).items() if not hasattr(v, '__dict__') and not callable(v)}
        if td_serializable["thoughtNumber"] > td_serializable["totalThoughts"]:
            td_serializable["totalThoughts"] = td_serializable["thoughtNumber"]
        self.thought_history.append(dict(td_serializable))
        if td_serializable.get("branchFromThought") and td_serializable.get("branchId"):
            if td_serializable["branchId"] not in self.branches:
                self.branches[td_serializable["branchId"]] = []
            self.branches[td_serializable["branchId"]].append(dict(td_serializable))
        if not self.disable_thought_logging:
            logger.info(self.format_thought(td_serializable))
        response = {
            "thoughtNumber": td_serializable["thoughtNumber"],
            "totalThoughts": td_serializable["totalThoughts"],
            "nextThoughtNeeded": td_serializable["nextThoughtNeeded"],
            "branches": list(self.branches.keys()),
            "thoughtHistoryLength": len(self.thought_history)
        }
        if td_serializable.get("isHypothesis"):
            response["hypothesis"] = td_serializable["thought"]
        if td_serializable.get("isVerification"):
            response["verification"] = td_serializable["thought"]
        if data.get("returnFullHistory"):
            response["thoughtHistory"] = [dict(t) for t in self.thought_history]
        if data.get("auto_iterate"):
            max_depth = data.get("max_depth", 5)
            auto_thoughts = self.auto_generate_thoughts(td_serializable, max_depth)
            response["autoGenerated"] = [dict(t) if not isinstance(t, dict) else t for t in auto_thoughts]
        return {
            "content": [
                TextContent(type="text", text=json.dumps(response, indent=2))
            ]
        }

class ThinkingToolService(ToolService):
    """Thinking tool service providing dynamic, reflective problem-solving capabilities."""
    
    def __init__(self):
        super().__init__("thinking_tool")
        self.engine = ThinkingToolEngine()
    
    def get_tool_descriptions(self) -> Dict[str, RichToolDescription]:
        """Get tool descriptions for thinking tool service."""
        return {
            "thinking_tool": RichToolDescription(
                description=(
                    "A detailed tool for dynamic and reflective problem-solving through thoughts.\n"
                    "This tool helps analyze problems through a flexible thinking process that can adapt and evolve.\n"
                    "Each thought can build on, question, or revise previous insights as understanding deepens.\n\n"
                    "When to use this tool:\n"
                    "- Breaking down complex problems into steps\n"
                    "- Planning and design with room for revision\n"
                    "- Analysis that might need course correction\n"
                    "- Problems where the full scope might not be clear initially\n"
                    "- Problems that require a multi-step solution\n"
                    "- Tasks that need to maintain context over multiple steps\n"
                    "- Situations where irrelevant information needs to be filtered out\n\n"
                    "Key features:\n"
                    "- Adjust total_thoughts up or down as you progress\n"
                    "- Question or revise previous thoughts\n"
                    "- Add more thoughts even after reaching what seemed like the end\n"
                    "- Express uncertainty and explore alternative approaches\n"
                    "- Branch or backtrack as needed\n"
                    "- Generate and verify solution hypotheses\n"
                    "- Repeat the process until satisfied\n"
                    "- Provide a correct answer\n\n"
                    "Parameters explained:\n"
                    "- thought: Your current thinking step (regular, revision, question, realization, hypothesis, verification)\n"
                    "- nextThoughtNeeded: True if you need more thinking, even if at what seemed like the end\n"
                    "- thoughtNumber: Current number in sequence (can go beyond initial total if needed)\n"
                    "- totalThoughts: Current estimate of thoughts needed (can be adjusted up/down)\n"
                    "- isRevision: If this thought revises previous thinking\n"
                    "- revisesThought: If isRevision is true, which thought number is being reconsidered\n"
                    "- branchFromThought: If branching, which thought number is the branching point\n"
                    "- branchId: Identifier for the current branch (if any)\n"
                    "- needsMoreThoughts: If reaching end but realizing more thoughts needed\n"
                    "- isHypothesis: If this thought is a hypothesis\n"
                    "- isVerification: If this thought is a verification step\n"
                    "- returnFullHistory: If true, returns the full thought history\n"
                    "- autoIterate: If true, automatically generate and explore all branches.\n"
                    "- maxDepth: Maximum depth for auto-generated thought exploration.\n"
                ),
                use_when=(
                    "Use for breaking down complex problems, planning, analysis, or tasks needing context over multiple steps.\n"
                    "Ideal for situations where revision, branching, or dynamic adjustment of steps is needed."
                ),
                side_effects=(
                    "Maintains a history of thoughts, supports revision and branching, logs formatted thoughts unless disabled."
                )
            )
        }
    
    def register_tools(self, mcp):
        """Register thinking tools with the MCP server."""
        self.logger.info("Registering thinking tools...")
        
        @mcp.tool(description=self.get_tool_descriptions()["thinking_tool"].model_dump_json())
        async def thinking_tool(
            thought: str,
            nextThoughtNeeded: bool,
            thoughtNumber: int,
            totalThoughts: int,
            isRevision: Optional[bool] = None,
            revisesThought: Optional[int] = None,
            branchFromThought: Optional[int] = None,
            branchId: Optional[str] = None,
            needsMoreThoughts: Optional[bool] = None,
            isHypothesis: Optional[bool] = None,
            isVerification: Optional[bool] = None,
            returnFullHistory: Optional[bool] = None,
            autoIterate: Optional[bool] = None,
            maxDepth: Optional[int] = None
        ) -> List[TextContent]:
            logger.info(f"thinking_tool called (thinking_tool_service) with thought_number={thoughtNumber}, total_thoughts={totalThoughts}")
            data = locals()
            try:
                result = self.engine.process_thought(data)
                logger.info(f"thinking_tool output (thinking_tool_service): {result['content'][0].text[:200]}..." if len(result['content'][0].text) > 200 else f"thinking_tool output (thinking_tool_service): {result['content'][0].text}")
                return result["content"]
            except Exception as e:
                logger.error(f"thinking_tool error (thinking_tool_service): {e}")
                return [TextContent(type="text", text=json.dumps({"error": str(e), "status": "failed"}, indent=2))]
