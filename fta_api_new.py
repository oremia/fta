# main.py
from fastapi import FastAPI, Body, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Dict
import uuid
from fastapi.middleware.cors import CORSMiddleware
# ==============================================================================
# 1. 模拟数据库 和 Pydantic 数据模型
# ==============================================================================

# 使用一个全局字典来模拟数据库，用于在内存中存储分析项目
# key 是 analysis_id (str), value 是 Analysis 对象
db: Dict[str, 'Analysis'] = {}

class BaseEvent(BaseModel):
    """单个底事件的数据模型"""
    name: str = Field(..., example="部件A失灵")
    probability: float = Field(..., ge=0.0, le=1.0, example=0.05)

class AnalysisBase(BaseModel):
    """分析项目的基本信息模型"""
    name: str = Field(..., example="发电机系统故障分析")
    logical_expression: str = Field(..., example="发电机系统故障 = (电源模块 and 控制单元) or 传感器")

class AnalysisCreate(AnalysisBase):
    """用于创建分析项目的输入模型"""
    pass

class Analysis(AnalysisBase):
    """分析项目的完整数据模型（包括由服务器生成的ID和事件列表）"""
    id: str = Field(..., example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    events: List[BaseEvent] = []

class CalculationResult(BaseModel):
    """执行计算后返回的结果模型"""
    top_event_name: str = Field(..., example="发电机系统故障分析")
    top_event_probability: float = Field(..., example=0.12345)
    minimal_cut_sets: List[List[str]] = Field(..., example=[["电源模块", "控制单元"], ["传感器"]])


# ==============================================================================
# 2. 创建并配置FastAPI应用
# ==============================================================================

app = FastAPI(
    title="更灵活的故障树分析 (FTA) API",
    description="一个资源导向的、用于故障树分析的模拟API。",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 3. 定义全新、灵活的API接口
# ==============================================================================

# --- A. 管理“故障树分析项目” ---

@app.post("/analyses", response_model=Analysis, status_code=201, summary="1. 创建一个新的故障树分析项目")
async def create_analysis(analysis_in: AnalysisCreate):
    """创建一个分析项目，服务器会为其生成一个唯一的ID。"""
    analysis_id = str(uuid.uuid4())
    new_analysis = Analysis(id=analysis_id, **analysis_in.dict(), events=[])
    db[analysis_id] = new_analysis
    return new_analysis

@app.get("/analyses/{analysis_id}", response_model=Analysis, summary="获取单个分析项目的完整信息")
async def get_analysis(analysis_id: str = Path(..., description="要查询的分析项目ID")):
    """根据ID获取一个分析项目的所有信息，包括其下的所有底事件。"""
    if analysis_id not in db:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return db[analysis_id]

# --- B. 管理单个“底事件” ---

@app.post("/analyses/{analysis_id}/events", response_model=Analysis, summary="2. 为项目添加一个新底事件")
async def add_event_to_analysis(
    analysis_id: str = Path(..., description="要添加事件的项目ID"),
    event_in: BaseEvent = Body(..., description="要添加的新底事件")
):
    """为一个已存在的分析项目添加一个底事件。"""
    if analysis_id not in db:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # 检查事件名是否重复
    for event in db[analysis_id].events:
        if event.name == event_in.name:
            raise HTTPException(status_code=400, detail=f"Event with name '{event_in.name}' already exists")
            
    db[analysis_id].events.append(event_in)
    return db[analysis_id]

@app.put("/analyses/{analysis_id}/events/{event_name}", response_model=BaseEvent, summary="3. 更新一个已存在的底事件")
async def update_event_in_analysis(
    analysis_id: str = Path(..., description="项目ID"),
    event_name: str = Path(..., description="要更新的底事件的名称"),
    event_update: BaseEvent = Body(..., description="更新后的事件数据")
):
    """更新一个特定底事件的属性（主要是概率）。"""
    if analysis_id not in db:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    for i, event in enumerate(db[analysis_id].events):
        if event.name == event_name:
            # 更新事件
            db[analysis_id].events[i] = event_update
            return event_update
            
    raise HTTPException(status_code=404, detail=f"Event with name '{event_name}' not found")

# --- C. 执行计算 ---

@app.post("/analyses/{analysis_id}/calculate", response_model=CalculationResult, summary="4. 对项目执行计算")
async def calculate_analysis(analysis_id: str = Path(..., description="要计算的项目ID")):
    """触发对指定分析项目的计算（模拟）。"""
    if analysis_id not in db:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    analysis = db[analysis_id]
    
    # --- 模拟计算逻辑 ---
    # 在真实应用中，这里会调用核心算法
    # 我们这里只返回一个格式正确的模拟结果
    
    # 提取所有事件名称用于模拟割集
    event_names = [event.name for event in analysis.events]
    mock_cut_sets = [event_names[i:i+2] for i in range(0, len(event_names), 2)] # 简单模拟
    
    return CalculationResult(
        top_event_name=analysis.name,
        top_event_probability=0.42, # 写死的模拟概率
        minimal_cut_sets=mock_cut_sets if mock_cut_sets else [["模拟割集"]]
    )