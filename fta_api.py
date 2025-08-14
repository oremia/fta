# fta_api.py
"""
故障树分析 (Fault Tree Analysis, FTA) API 模块

本模块负责处理所有与FTA相关的后端逻辑与API接口。
它提供了一个专业的分析工具，用于对复杂系统的故障逻辑进行定性和定量评估。
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Set
import re
import pandas as pd
import io
from pyparsing import infixNotation, opAssoc, Word, alphas, alphanums, ParseException

router = APIRouter()


def setup_parser():
    event = Word(alphas, alphanums + "_-")
    operator = [("and", 2, opAssoc.LEFT), ("or", 2, opAssoc.LEFT)]
    parser = infixNotation(event, operator)
    return parser


boolean_parser = setup_parser()


def convert_parsed_to_dict(parsed_list: list) -> Dict[str, Any]:
    if isinstance(parsed_list, str):
        return {"type": "BASIC", "name": parsed_list}
    if len(parsed_list) >= 3:
        op, op_type = parsed_list[-2], parsed_list[-2].upper()
        right = convert_parsed_to_dict(parsed_list[-1])
        left = convert_parsed_to_dict(parsed_list[:-2])
        if left.get("type") == op_type:
            return {"type": op_type, "children": [*left["children"], right]}
        else:
            return {"type": op_type, "children": [left, right]}
    elif len(parsed_list) == 1:
        return convert_parsed_to_dict(parsed_list[0])
    raise ValueError(f"无效的解析结构: {parsed_list}")


def robust_parse_logic_expression(expr_str: str) -> Dict[str, Any]:
    try:
        parsed_result = boolean_parser.parseString(expr_str, parseAll=True)[0].asList()
        return convert_parsed_to_dict(parsed_result)
    except ParseException as e:
        raise ValueError(f"逻辑表达式语法错误: {e}")
    except Exception as e:
        raise ValueError(f"解析表达式时发生未知错误: {e}")


def calculate_probability(gate: Dict, events: Dict[str, float]) -> float:
    if gate['type'] == 'BASIC':
        return events.get(gate['name'], 0.0)
    elif gate['type'] == 'OR':
        p = 1.0
        for child in gate.get('children', []): p *= (1 - calculate_probability(child, events))
        return 1 - p
    elif gate['type'] == 'AND':
        p = 1.0
        for child in gate.get('children', []): p *= calculate_probability(child, events)
        return p
    return 0.0


def find_minimal_cut_sets(gate: Dict) -> List[Set[str]]:
    def find_sets(sub_gate):
        if sub_gate['type'] == 'BASIC':
            return [[sub_gate['name']]]
        elif sub_gate['type'] == 'OR':
            cut_sets = []
            for child in sub_gate.get('children', []): cut_sets.extend(find_sets(child))
            return cut_sets
        elif sub_gate['type'] == 'AND':
            from itertools import product
            child_cut_sets = [find_sets(child) for child in sub_gate.get('children', [])]
            if not child_cut_sets: return []
            result = [sum(combo, []) for combo in list(product(*child_cut_sets))]
            return result
        return []

    all_cut_sets = [set(cs) for cs in find_sets(gate)]
    all_cut_sets.sort(key=len)
    minimal_sets = []
    for cs in all_cut_sets:
        is_minimal = True
        for existing in minimal_sets:
            if existing.issubset(cs): is_minimal = False; break
        if is_minimal: minimal_sets.append(cs)
    return minimal_sets


def calculate_importance(top_prob: float, gate_structure: Dict, base_events: Dict[str, float]) -> Dict[str, float]:
    if top_prob == 0:
        return {event: 0 for event in base_events}
    minimal_cut_sets = find_minimal_cut_sets(gate_structure)
    importance = {}
    for event, prob in base_events.items():
        cut_sets_with_event = [cs for cs in minimal_cut_sets if event in cs]
        prob_sum_of_cut_sets = 0
        for cs in cut_sets_with_event:
            p_cut_set = 1.0
            for item in cs: p_cut_set *= base_events.get(item, 0)
            prob_sum_of_cut_sets += p_cut_set
        fv_importance = prob_sum_of_cut_sets / top_prob if top_prob > 0 else 0
        importance[event] = fv_importance
    return importance


def generate_graph_json(top_event: str, events: Dict, gate_structure: Dict) -> Dict:
    nodes, edges, node_counter = [], [], {'count': 0}

    def add_node(parent_id, gate):
        node_id = f"node{node_counter['count']}";
        node_counter['count'] += 1
        node_data = {'id': node_id}
        if gate['type'] == 'BASIC':
            prob = events.get(gate['name'], 0.0)
            node_data['label'] = f"{gate['name']}\nP={prob:.4f}";
            node_data['shape'] = 'box';
            node_data['color'] = 'lightcoral'
        else:
            node_data['label'] = "或门 (OR)" if gate['type'] == 'OR' else "与门 (AND)";
            node_data['shape'] = 'ellipse';
            node_data['color'] = 'lightyellow'
        nodes.append(node_data)
        if parent_id: edges.append({'from': parent_id, 'to': node_id})
        if 'children' in gate:
            for child in gate['children']: add_node(node_id, child)
        return node_id

    top_node_id = 'TOP'
    nodes.append({'id': top_node_id, 'label': f'顶事件: {top_event}', 'shape': 'rectangle', 'color': 'lightblue'})
    add_node(top_node_id, gate_structure)
    return {'nodes': nodes, 'edges': edges}


class BaseEvent(BaseModel):
    event: str = Field(..., description="底事件的唯一名称。", example="电源失效")
    probability: float = Field(..., description="该底事件发生的概率。", example=0.001)


class FTAnalysisRequest(BaseModel):
    top_event: str = Field(..., description="顶事件的名称。", example="系统故障")
    logic_expression: str = Field(..., description="描述故障树逻辑关系的完整表达式。",
                                  example="系统故障 = (电源失效 and 控制器失效) or 软件Bug")
    base_events: List[BaseEvent] = Field(..., description="项目中所有底事件及其概率的列表。")


class ImportanceResult(BaseModel):
    event: str
    fv_importance: float = Field(..., description="Fussell-Vesely重要度，值域[0,1]，越高越关键。")


class FTAnalysisResponse(BaseModel):
    top_event_probability: float = Field(..., description="计算出的顶事件总发生概率。")
    minimal_cut_sets: List[List[str]] = Field(..., description="导致顶事件发生的所有最小底事件组合。")
    graph_json: Dict[str, List[Dict]] = Field(..., description="用于前端渲染故障树图形的结构化数据。")
    structure_info: Dict[str, Any] = Field(..., description="故障树的顶层结构信息。")
    importance_analysis: List[ImportanceResult] = Field(...,
                                                        description="所有底事件的关键重要度分析结果，按重要度降序排列。")


@router.post(
    "/fta/import",
    response_model=List[BaseEvent],
    summary="从Excel导入底事件",
    description="""
    通过上传一个标准的Excel(.xlsx)文件，批量导入底事件及其发生概率。
    Excel格式要求:
    - 必须是一个标准的 `.xlsx` 文件。
    - 文件的第一行必须是中文表头，包含 `事件名称` 和 `发生概率` 两列。
    """
)
async def import_fta_events(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="文件格式错误，请上传一个标准的 .xlsx Excel 文件。")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl', header=0)
        required_columns = ['事件名称', '发生概率']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"Excel文件必须包含以下中文表头: {', '.join(required_columns)}")
        events = [BaseEvent(event=str(row['事件名称']), probability=float(row['发生概率'])) for _, row in df.iterrows()]
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@router.post(
    "/fta/analyze",
    response_model=FTAnalysisResponse,
    summary="执行完整的故障树分析",
    description="接收一个完整的故障树定义，并执行所有相关的定性、定量及重要度分析。"
)
def analyze_fault_tree(request: FTAnalysisRequest):
    events_dict = {be.event: be.probability for be in request.base_events}
    try:
        match = re.match(r".*?=\s*(.*)", request.logic_expression)
        if not match:
            raise ValueError("逻辑表达式格式无效，必须包含 '=' 符号。")
        expr_part = match.group(1).strip()

        gate_structure = robust_parse_logic_expression(expr_part)
        p_top = calculate_probability(gate_structure, events_dict)
        min_cut_sets_set = find_minimal_cut_sets(gate_structure)
        min_cut_sets_list = [list(s) for s in min_cut_sets_set]

        importance_dict = calculate_importance(p_top, gate_structure, events_dict)
        importance_list = [ImportanceResult(event=k, fv_importance=v) for k, v in importance_dict.items()]
        importance_list.sort(key=lambda x: x.fv_importance, reverse=True)

        graph_json = generate_graph_json(request.top_event, events_dict, gate_structure)
        structure_info = {"top_event": request.top_event, "gate_type": gate_structure['type'],
                          "children_count": len(gate_structure.get('children', []))}

        return FTAnalysisResponse(
            top_event_probability=p_top,
            minimal_cut_sets=min_cut_sets_list,
            graph_json=graph_json,
            structure_info=structure_info,
            importance_analysis=importance_list
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行分析时发生未知错误: {str(e)}")