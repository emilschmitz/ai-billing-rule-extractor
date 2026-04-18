import os
import json
import operator
from typing import List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncpg

class RuleNodeModel:
    def __init__(self, id, node_type, field, op, value, citation):
        self.id = id
        self.type = node_type
        self.field = field
        self.op = op
        self.value = value
        self.citation = citation
        self.children = []

ast_forest: List[RuleNodeModel] = []

def build_ast(rows):
    global ast_forest
    ast_forest.clear()
    node_cache = {}
    
    for r in rows:
        val = json.loads(r['node_value']) if isinstance(r['node_value'], str) else r['node_value']
        node = RuleNodeModel(
            id=str(r['id']), 
            node_type=r['node_type'], 
            field=r['field_name'], 
            op=r['operator'], 
            value=val,
            citation=r['citation']
        )
        node_cache[str(r['id'])] = node

    for r in rows:
        node = node_cache[str(r['id'])]
        parent_id = str(r['parent_id']) if r['parent_id'] else None
        if parent_id and parent_id in node_cache:
            node_cache[parent_id].children.append(node)
        elif not parent_id:
            ast_forest.append(node)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.getenv("DATABASE_URL", "postgresql://validator:password@localhost:5432/rules_db")
    db_url = db_url.replace("+asyncpg", "") # standard asyncpg wants postgresql://
    try:
        conn = await asyncpg.connect(db_url)
        rows = await conn.fetch("SELECT * FROM rule_nodes")
        build_ast(rows)
        await conn.close()
        print(f"Loaded {len(ast_forest)} root rules into memory.")
    except Exception as e:
        print(f"Error loading AST from DB: {e}")
    yield

app = FastAPI(lifespan=lifespan)

def flatten(lst):
    result = []
    for i in lst:
        if isinstance(i, list):
            result.extend(flatten(i))
        else:
            result.append(i)
    return result

def get_field_values(payload: dict, path: str) -> List[Any]:
    if not path:
        return []
        
    parts = path.split('.')
    current = [payload]
    
    for part in parts:
        next_level = []
        if part.endswith('[]'):
            key = part[:-2]
            for item in current:
                if isinstance(item, dict) and key in item and isinstance(item[key], list):
                    next_level.extend(item[key])
        else:
            for item in current:
                if isinstance(item, dict) and part in item:
                    next_level.append(item[part])
        current = next_level
        
    return current

def evaluate_condition(payload: dict, node: RuleNodeModel) -> bool:
    values = flatten(get_field_values(payload, node.field))
    
    ops = {
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '<': operator.lt,
        'in': lambda a, b: a in b if isinstance(b, list) else False,
        'not in': lambda a, b: a not in b if isinstance(b, list) else True
    }
    
    if not values:
        if node.op in ['!=', 'not in']:
            return True
        return False
        
    op_func = ops.get(node.op)
    if not op_func:
        return False
        
    target = node.value
    if node.op in ['in', 'not in'] and not isinstance(target, list):
        target = [target]
        
    results = []
    for val in values:
        try:
            # Simple string conversion for comparison unless it's an 'in' operator
            v_cmp = str(val) if node.op not in ['in', 'not in'] else val
            
            if node.op in ['in', 'not in']:
                # ensure target elements are same type as v_cmp mostly str
                str_target = [str(t) for t in target]
                res = op_func(str(v_cmp), str_target)
            else:
                res = op_func(str(v_cmp), str(target))
                
            results.append(res)
        except Exception:
            results.append(False)
            
    if node.op in ['!=', 'not in']:
        return all(results)
    else:
        return any(results)

def evaluate_node(payload: dict, node: RuleNodeModel) -> bool:
    if node.type == 'CONDITION':
        return evaluate_condition(payload, node)
    elif node.type == 'AND':
        if not node.children: return True
        return all(evaluate_node(payload, child) for child in node.children)
    elif node.type == 'OR':
        if not node.children: return False
        return any(evaluate_node(payload, child) for child in node.children)
    return False

@app.post("/v1/encounters/validate")
async def validate_encounter(encounter: dict):
    denied_by = []
    for root in ast_forest:
        passes = evaluate_node(encounter, root)
        if not passes:
            denied_by.append({
                "rule_id": root.id,
                "citation": root.citation
            })
            
    return {
        "is_valid": len(denied_by) == 0,
        "denied_by": denied_by
    }
