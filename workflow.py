# workflow.py
import json
import re
from langgraph.graph import StateGraph, END
from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from models import GraphState, SearchConfig
from prompts import LinkedInPrompts
from tools import (
    google_collect_linkedin_urls,
    chunk_list,
    scrape_batch,
    write_profiles_csv,
)

class Workflow:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.prompts = LinkedInPrompts()
        self.workflow = self.build_graph()
        
    @staticmethod
    def _extract_json_str(s: str) -> str:
        """
        Try to isolate a single JSON object from an LLM string, stripping code fences if present.
        """
        # Strip common code fences
        s = s.strip()
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)

        # Extract first {...} block if any wrapping text exists
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return s[start:end+1]
        return s

# ---- Nodes ----
    def _node_build_query(self, state: GraphState) -> GraphState:
        cfg: SearchConfig = state["config"]
        state["query_base"] = LinkedInPrompts.build_base_query(cfg.role, cfg.country)
        print(f"🔍 Base query: {state['query_base']}")
        state["current_page"] = 1
        return state

    def _node_search_pages(self, state: GraphState) -> GraphState:
        cfg: SearchConfig = state["config"]
        pages = cfg.pages or 1
        urls = google_collect_linkedin_urls(
            query_base=state["query_base"],
            pages=pages,
            per_page=cfg.per_page,
            browser=cfg.browser
        )
        for url in urls:
            print(f"🔗 Found URL: {url}")
        agg = set(state.get("urls", []))
        agg.update(urls)
        state["urls"] = sorted(agg)
        return state


    def _node_make_batches(self, state: GraphState) -> GraphState:
        cfg: SearchConfig = state["config"]
        state["batches"] = chunk_list(state["urls"], cfg.batch_size)
        return state

    def _node_next_batch(self, state: GraphState) -> GraphState:
        if not state["batches"]:
            state["current_batch"] = []
        else:
            state["current_batch"] = state["batches"].pop(0)
        return state

    def _node_scrape_batch(self, state: GraphState) -> GraphState:
        cfg: SearchConfig = state["config"]
        urls = state["current_batch"]
        if not urls:
            state["batch_results"] = []
            return state
        # Now returns [{"url": ..., "lines": [...]}, ...]
        results = scrape_batch(
            urls,
            browser=cfg.browser,
            storage_state=cfg.storage_state,
            max_lines=100,
        )
        state["batch_results"] = results
        return state

    def _node_extract_batch(self, state: GraphState) -> GraphState:
        """
        Use LLM to convert text lines -> structured fields:
        name, role, email, about, url
        """
        input_rows: List[Dict] = state.get("batch_results", [])
        extracted: List[Dict] = []

        for row in input_rows:
            url = row.get("url", "")
            lines = row.get("lines", [])
            if not lines:
                extracted.append({"name": "", "role": "", "email": "", "about": "", "url": url})
                continue

            system = SystemMessage(content=self.prompts.EXTRACT_SYSTEM)
            human = HumanMessage(content=self.prompts.extract_user(url, lines))

            try:
                llm_resp = self.llm.invoke([system, human])
                raw = getattr(llm_resp, "content", "") if llm_resp else ""
                json_str = self._extract_json_str(raw)
                data = json.loads(json_str)
                # Ensure all fields exist
                data = {
                    "name": data.get("name", "").strip(),
                    "role": data.get("role", "").strip(),
                    "email": data.get("email", "").strip(),
                    "about": data.get("about", "").strip(),
                    "url": data.get("url", url).strip() or url,
                }
            except Exception as e:
                data = {"name": "", "role": "", "email": "", "about": "", "url": url, "error": str(e)}
            extracted.append(data)

        state["batch_results"] = extracted  # overwrite with structured rows
        return state

    def _node_save_batch(self, state: GraphState) -> GraphState:
        cfg: SearchConfig = state["config"]
        if state["batch_results"]:
            msg = write_profiles_csv(state["batch_results"], cfg.output_csv)
            print(msg)
        return state

    @staticmethod
    def _router_continue_or_end(state: GraphState):
        return "continue" if state["batches"] else "end"

    # ---- Graph builder ----
    def build_graph(self):
        g = StateGraph(GraphState)

        g.add_node("build_query", self._node_build_query)
        g.add_node("search_pages", self._node_search_pages)
        g.add_node("make_batches", self._node_make_batches)
        g.add_node("next_batch", self._node_next_batch)
        g.add_node("scrape_batch", self._node_scrape_batch)
        g.add_node("extract_batch", self._node_extract_batch)  # <-- new
        g.add_node("save_batch", self._node_save_batch)

        g.set_entry_point("build_query")
        g.add_edge("build_query", "search_pages")
        g.add_edge("search_pages", "make_batches")
        g.add_edge("make_batches", "next_batch")
        g.add_edge("next_batch", "scrape_batch")
        g.add_edge("scrape_batch", "extract_batch")            # <-- new edge
        g.add_edge("extract_batch", "save_batch")              # <-- new edge

        g.add_conditional_edges(
            "save_batch",
            self._router_continue_or_end,
            {"continue": "next_batch", "end": END}
        )

        return g.compile()

    def run(self, config: SearchConfig) -> GraphState:
        initial_state = GraphState(config=config)
        final_state = self.workflow.invoke(initial_state, config={"recursion_limit": 500})
        return GraphState(**final_state)