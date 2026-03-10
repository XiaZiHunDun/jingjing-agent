"""
晶晶助手 Agent 模块

封装晶晶助手的核心 Agent 逻辑。
"""

from typing import List, Optional, Dict, Any, Generator
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from src.llm import get_llm, get_current_provider
from src.tools import get_basic_tools
from src.memory.vector_store import get_vector_store, create_rag_tool


JINGJING_SYSTEM_PROMPT = """你是一个智能助手，名叫 "晶晶"。你可以：

1. 进行友好的对话
2. 使用计算器进行数学计算
3. 查询当前时间
4. 搜索知识库获取技术信息
5. 查询城市天气
6. 获取网页摘要
7. 翻译文本（支持多语言）

请用中文回答，保持友好和专业。如果需要使用工具，请先使用工具获取信息再回答。

重要规则：
- 当使用知识库搜索工具时，工具返回的内容中会包含"📚 参考来源"信息
- 你必须在最终回答中完整保留这些来源引用信息，不要删除或修改
- 来源引用应该显示在回答的末尾"""


class JingjingAgent:
    """晶晶助手 Agent 类"""
    
    def __init__(
        self, 
        memory: Optional[MemorySaver] = None,
        system_prompt: str = JINGJING_SYSTEM_PROMPT
    ):
        self.memory = memory or MemorySaver()
        self.system_prompt = system_prompt
        self.llm = get_llm()
        self.tools = self._build_tools()
        self.agent = self._build_agent()
    
    def _build_tools(self) -> List[BaseTool]:
        """构建工具列表"""
        tools = get_basic_tools()
        
        vector_store = get_vector_store()
        if vector_store is not None:
            rag_tool = create_rag_tool(vector_store)
            tools.append(rag_tool)
        
        return tools
    
    def _build_agent(self):
        """构建 Agent"""
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
            checkpointer=self.memory,
        )
    
    def chat(self, message: str, session_id: str = "default") -> Dict[str, Any]:
        """与晶晶对话"""
        from langchain_core.messages import HumanMessage, ToolMessage
        
        config = {"configurable": {"thread_id": session_id}}
        
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        
        answer = result["messages"][-1].content
        thinking_steps = self._extract_thinking_steps(result["messages"])
        
        return {
            "answer": answer,
            "thinking_steps": thinking_steps,
            "raw_result": result
        }
    
    def chat_stream(self, message: str, session_id: str = "default") -> Generator[Dict[str, Any], None, None]:
        """
        流式对话
        
        生成器返回不同类型的事件：
        - {"event": "tool_start", "name": "...", "args": {...}}
        - {"event": "tool_end", "name": "...", "result": "..."}
        - {"event": "token", "content": "..."}
        - {"event": "done", "answer": "...", "thinking_steps": [...]}
        """
        from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
        
        config = {"configurable": {"thread_id": session_id}}
        
        thinking_steps = []
        current_tool_calls = {}
        final_answer = ""
        
        try:
            for event in self.agent.stream(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                stream_mode="messages"
            ):
                msg, metadata = event
                
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_id = tc.get("id", "")
                        tool_name = tc.get("name", "")
                        tool_args = tc.get("args", {})
                        
                        if tool_id not in current_tool_calls:
                            current_tool_calls[tool_id] = {
                                "name": tool_name,
                                "args": tool_args
                            }
                            yield {
                                "event": "tool_start",
                                "name": tool_name,
                                "args": tool_args
                            }
                
                if isinstance(msg, ToolMessage):
                    tool_id = msg.tool_call_id
                    tool_result = msg.content
                    
                    if tool_id in current_tool_calls:
                        tool_info = current_tool_calls[tool_id]
                        thinking_steps.append({
                            "name": tool_info["name"],
                            "args": tool_info["args"],
                            "result": tool_result
                        })
                        yield {
                            "event": "tool_end",
                            "name": tool_info["name"],
                            "result": tool_result
                        }
                
                if isinstance(msg, AIMessageChunk):
                    if msg.content and not msg.tool_calls:
                        final_answer += msg.content
                        yield {
                            "event": "token",
                            "content": msg.content
                        }
            
            yield {
                "event": "done",
                "answer": final_answer,
                "thinking_steps": thinking_steps,
                "session_id": session_id
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "message": str(e)
            }
    
    def _extract_thinking_steps(self, messages: List) -> List[Dict]:
        """从消息中提取思考过程"""
        from langchain_core.messages import HumanMessage, ToolMessage
        
        thinking_steps = []
        tool_results = {}
        
        last_human_idx = 0
        for i, msg in enumerate(messages):
            if isinstance(msg, HumanMessage):
                last_human_idx = i
        
        for msg in messages[last_human_idx + 1:]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    thinking_steps.append({
                        "type": "tool_call",
                        "name": tc["name"],
                        "args": tc.get("args", {}),
                        "id": tc.get("id", "")
                    })
            
            if isinstance(msg, ToolMessage):
                tool_results[msg.tool_call_id] = msg.content
        
        for step in thinking_steps:
            if step.get("id") in tool_results:
                step["result"] = tool_results[step["id"]]
        
        return thinking_steps
    
    def refresh_tools(self):
        """刷新工具列表"""
        self.tools = self._build_tools()
        self.agent = self._build_agent()
    
    def refresh_llm(self):
        """刷新 LLM 实例（用于切换模型后）"""
        self.llm = get_llm()
        self.agent = self._build_agent()
    
    def get_tool_names(self) -> List[str]:
        """获取当前可用的工具名称列表"""
        return [tool.name for tool in self.tools]
    
    def get_llm_provider(self) -> str:
        """获取当前使用的 LLM 提供者"""
        return get_current_provider().value


def create_jingjing_agent(
    memory: Optional[MemorySaver] = None,
    system_prompt: str = JINGJING_SYSTEM_PROMPT
) -> JingjingAgent:
    """创建晶晶助手实例"""
    return JingjingAgent(memory=memory, system_prompt=system_prompt)


def get_default_agent():
    """获取默认的晶晶助手实例"""
    return create_jingjing_agent()
