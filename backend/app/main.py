"""
FastAPI应用主文件
"""

from contextlib import asynccontextmanager
from io import BytesIO
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

from app.services.patent_search_service import PatentSearchService
from app.services.invention_intent_service import InventionIntentService
from app.services.disclosure_service import DisclosureService
from app.services.patent_drafting_service import PatentDraftingService
from app.services.examination_service import ExaminationService
from app.services.patent_repair_service import PatentRepairService
from app.services.patent_workflow_service import PatentWorkflowService
from shared.db import init_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时确保数据库表已初始化。"""
    init_database()
    logger.info("数据库初始化检查完成")
    yield


# 创建FastAPI应用
app = FastAPI(
    title="Patent Expert System API",
    description="专利专家系统API - 完整的专利辅助服务",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class SearchRequest(BaseModel):
    """检索请求（支持高级检索）"""
    # 简单模式（兼容性）
    query: Optional[str] = None
    
    # 高级模式
    keywords: Optional[List[Dict[str, str]]] = None  # [{"term": "AI", "scope": "CL"}]
    ipc_classes: Optional[List[str]] = None  # ["G06F"]
    cpc_classes: Optional[List[str]] = None  # ["G06F"]
    
    # 通用参数
    country: Optional[str] = None
    ipc_filter: Optional[str] = None  # 废弃，保留兼容性
    max_results: int = 20
    user_id: str = "default_user"
    date_range: Optional[List[str]] = None  # ["2020-01-01", "2026-12-31"]


class SearchHistoryQuery(BaseModel):
    user_id: str = "default_user"
    page: int = 1
    limit: int = 10



# 初始化服务（延迟加载）
search_service = None
intent_service = None
disclosure_service = None
drafting_service = None
examination_service = None
repair_service = None
workflow_service = None


def get_search_service():
    """获取检索服务实例"""
    global search_service
    if search_service is None:
        search_service = PatentSearchService()
    return search_service


def get_intent_service():
    """获取发明意图服务实例"""
    global intent_service
    if intent_service is None:
        intent_service = InventionIntentService()
    return intent_service


def get_disclosure_service():
    """获取技术交底书服务实例"""
    global disclosure_service
    if disclosure_service is None:
        disclosure_service = DisclosureService()
    return disclosure_service


def get_drafting_service():
    """获取专利起草服务实例"""
    global drafting_service
    if drafting_service is None:
        drafting_service = PatentDraftingService()
    return drafting_service


def get_examination_service():
    """获取审查服务实例"""
    global examination_service
    if examination_service is None:
        examination_service = ExaminationService()
    return examination_service


def get_repair_service():
    """获取修复服务实例"""
    global repair_service
    if repair_service is None:
        repair_service = PatentRepairService()
    return repair_service


def get_workflow_service():
    """获取项目工作流服务实例"""
    global workflow_service
    if workflow_service is None:
        workflow_service = PatentWorkflowService()
    return workflow_service



# ========== API端点 ==========

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "Patent Search API"}


@app.post("/api/v1/search")
async def search_patents(request: SearchRequest):
    """
    专利检索
    
    - **query**: 检索关键词
    - **country**: 国家代码（CN, US等）
    - **ipc_filter**: IPC分类号
    """
    logger.info("="*60)
    logger.info(f"收到检索请求:")
    logger.info(f"  - query: {request.query}")
    logger.info(f"  - keywords: {request.keywords}")
    logger.info(f"  - ipc_classes: {request.ipc_classes}")
    logger.info(f"  - cpc_classes: {request.cpc_classes}")
    logger.info(f"  - max_results: {request.max_results}")
    logger.info(f"  - date_range: {request.date_range}")
    logger.info("="*60)
    
    try:
        service = get_search_service()
        results = service.search(
            query=request.query,
            keywords=request.keywords,
            ipc_classes=request.ipc_classes,
            cpc_classes=request.cpc_classes,
            user_id=request.user_id,
            ipc_filter=request.ipc_filter,
            country=request.country,
            max_results=request.max_results,
            date_range=tuple(request.date_range) if request.date_range else None
        )
        
        return {
            "success": True,
            "data": results
        }
    
    except Exception as e:
        logger.error(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/history")
async def get_search_history(request: SearchHistoryQuery):
    """
    获取检索历史
    
    - **user_id**: 用户ID
    - **page**: 页码
    - **limit**: 每页数量
    """
    try:
        service = get_search_service()
        history = service.get_history(
            user_id=request.user_id,
            page=request.page,
            limit=request.limit
        )
        
        return {
            "success": True,
            "data": history
        }
    
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/search/{search_id}/results")
async def get_search_results(search_id: str):
    """
    获取某次检索的结果
    
    - **search_id**: 检索ID
    """
    try:
        service = get_search_service()
        results = service.get_search_results(search_id)
        
        return {
            "success": True,
            "data": results
        }
    
    except Exception as e:
        logger.error(f"获取结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """健康检查（详细）"""
    try:
        # 检查数据库连接
        from shared.db import get_database
        db = get_database()
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "Patent Expert System API v2.0.0",
            "skills": ["invention_intent", "disclosure_writing", "patent_drafting", "examination", "repair", "search"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ========== 项目级工作流 ==========

class CreateProjectRequest(BaseModel):
    user_id: str = "default_user"
    title: Optional[str] = None
    patent_type: str = "发明"
    technical_field: Optional[str] = None
    summary: Optional[str] = None
    initial_notes: Optional[str] = None


class AttachSearchRequest(BaseModel):
    search_id: str


class UpdateDocumentRequest(BaseModel):
    content: str
    change_summary: Optional[str] = None


class RestoreVersionRequest(BaseModel):
    document_key: Optional[str] = None
    change_summary: Optional[str] = None


@app.get("/api/v1/projects")
async def list_projects(user_id: str = "default_user", limit: int = 20):
    """获取项目列表"""
    try:
        service = get_workflow_service()
        result = service.list_projects(user_id=user_id, limit=limit)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/projects")
async def create_project(request: CreateProjectRequest):
    """创建专利项目"""
    try:
        service = get_workflow_service()
        result = service.create_project(
            user_id=request.user_id,
            title=request.title,
            patent_type=request.patent_type,
            technical_field=request.technical_field,
            summary=request.summary,
            initial_notes=request.initial_notes,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{draft_id}")
async def get_project_overview(draft_id: str):
    """获取项目总览"""
    try:
        service = get_workflow_service()
        result = service.get_project_overview(draft_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"获取项目总览参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取项目总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/projects/{draft_id}/documents/{document_key}")
async def update_project_document(draft_id: str, document_key: str, request: UpdateDocumentRequest):
    """手工保存项目文档"""
    try:
        service = get_workflow_service()
        result = service.update_project_document(
            draft_id=draft_id,
            document_key=document_key,
            document_content=request.content,
            change_summary=request.change_summary,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"保存项目文档失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"保存项目文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{draft_id}/versions")
async def list_project_versions(draft_id: str, document_key: Optional[str] = None, limit: int = 20):
    """获取项目版本历史"""
    try:
        service = get_workflow_service()
        result = service.list_project_versions(draft_id=draft_id, document_key=document_key, limit=limit)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"获取版本列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{draft_id}/versions/{version_id}/diff")
async def get_project_version_diff(
    draft_id: str,
    version_id: str,
    document_key: str,
    compare_target: str = "current",
):
    """获取版本差异"""
    try:
        service = get_workflow_service()
        result = service.get_project_version_diff(
            draft_id=draft_id,
            version_id=version_id,
            document_key=document_key,
            compare_target=compare_target,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"获取版本差异失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取版本差异失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/projects/{draft_id}/versions/{version_id}/restore")
async def restore_project_version(draft_id: str, version_id: str, request: RestoreVersionRequest):
    """恢复项目版本"""
    try:
        service = get_workflow_service()
        result = service.restore_project_version(
            draft_id=draft_id,
            version_id=version_id,
            document_key=request.document_key,
            change_summary=request.change_summary,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"恢复项目版本失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"恢复项目版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/projects/{draft_id}/attach-search")
async def attach_search_to_project(draft_id: str, request: AttachSearchRequest):
    """将检索结果挂接到项目"""
    try:
        service = get_workflow_service()
        result = service.attach_search_to_project(draft_id, request.search_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"挂接检索结果参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"挂接检索结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{draft_id}/delivery-package")
async def build_delivery_package(draft_id: str):
    """生成项目交付包"""
    try:
        service = get_workflow_service()
        result = service.build_delivery_package(draft_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成交付包参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成交付包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/{draft_id}/delivery-export")
async def download_delivery_export(draft_id: str):
    """下载项目交付包 ZIP"""
    try:
        service = get_workflow_service()
        export_bundle = service.prepare_delivery_export(draft_id)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in export_bundle["files"].items():
                archive.writestr(name, content)
        buffer.seek(0)

        headers = {
            "Content-Disposition": f'attachment; filename="{export_bundle["filename"]}"'
        }
        return StreamingResponse(buffer, media_type="application/zip", headers=headers)
    except ValueError as e:
        logger.warning(f"下载交付包参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"下载交付包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Skill 1: 发明意图总结 ==========

class StartConversationRequest(BaseModel):
    user_id: str = "default_user"


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str = "default_user"


class GenerateIntentRequest(BaseModel):
    session_id: str
    user_id: str = "default_user"
    draft_id: Optional[str] = None


@app.post("/api/v1/skills/invention-intent/start")
async def start_conversation(request: StartConversationRequest):
    """开始新对话"""
    try:
        service = get_intent_service()
        result = service.start_conversation(user_id=request.user_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"开始对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/invention-intent/chat")
async def chat(request: ChatRequest):
    """对话"""
    try:
        service = get_intent_service()
        result = service.chat(
            session_id=request.session_id,
            message=request.message,
            user_id=request.user_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/invention-intent/generate")
async def generate_intent_document(request: GenerateIntentRequest):
    """生成发明意图文档"""
    try:
        service = get_intent_service()
        result = service.generate_document(
            session_id=request.session_id,
            user_id=request.user_id,
            draft_id=request.draft_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成文档参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Skill 2: 技术交底书撰写 ==========

class GenerateDisclosureRequest(BaseModel):
    draft_id: str


@app.post("/api/v1/skills/disclosure-writing/generate")
async def generate_disclosure(request: GenerateDisclosureRequest):
    """生成技术交底书"""
    try:
        service = get_disclosure_service()
        result = service.generate_from_intent(draft_id=request.draft_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成技术交底书参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成技术交底书失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Skill 3: 专利申请文件起草 ==========

class GeneratePatentFilesRequest(BaseModel):
    draft_id: str


@app.post("/api/v1/skills/patent-drafting/generate")
async def generate_patent_files(request: GeneratePatentFilesRequest):
    """生成专利申请文件"""
    try:
        service = get_drafting_service()
        result = service.generate_patent_files(draft_id=request.draft_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成专利文件参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成专利文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Skill 4: 实质审查模拟 ==========

class ExamineRequest(BaseModel):
    draft_id: str


@app.post("/api/v1/skills/examination/examine")
async def examine_patent(request: ExamineRequest):
    """执行实质审查"""
    try:
        service = get_examination_service()
        result = service.examine(draft_id=request.draft_id)
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"审查参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"审查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Skill 5: 专利修复 ==========

class ParseOpinionRequest(BaseModel):
    opinion_text: str


class GenerateStrategiesRequest(BaseModel):
    issues: List[Dict]
    draft_id: str


class GenerateResponseRequest(BaseModel):
    issues: List[Dict]
    strategies: List[Dict]
    draft_id: str


class ApplyStrategiesRequest(BaseModel):
    draft_id: str
    mode: str = "conservative"


@app.post("/api/v1/skills/repair/parse-opinion")
async def parse_opinion(request: ParseOpinionRequest):
    """解析审查意见"""
    try:
        service = get_repair_service()
        result = service.parse_opinion(opinion_text=request.opinion_text)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"解析审查意见失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/repair/generate-strategies")
async def generate_repair_strategies(request: GenerateStrategiesRequest):
    """生成修改方案"""
    try:
        service = get_repair_service()
        result = service.generate_strategies(
            issues=request.issues,
            draft_id=request.draft_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成修改方案参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成修改方案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/repair/generate-response")
async def generate_repair_response(request: GenerateResponseRequest):
    """生成答复意见书"""
    try:
        service = get_repair_service()
        result = service.generate_response(
            issues=request.issues,
            strategies=request.strategies,
            draft_id=request.draft_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"生成答复意见参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成答复意见失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/repair/apply-strategies")
async def apply_repair_strategies(request: ApplyStrategiesRequest):
    """将修复策略应用到文稿"""
    try:
        service = get_repair_service()
        result = service.apply_strategies(
            draft_id=request.draft_id,
            mode=request.mode,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        logger.warning(f"应用修复策略参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"应用修复策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
