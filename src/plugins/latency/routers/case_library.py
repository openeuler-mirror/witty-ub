import os
import json
import uuid
import re
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from latency.services.case_service import CaseServiceManager, CASE_DIR

router = APIRouter(prefix="/case_library", tags=["Case Library"])


@router.post("")
async def create_case(
    data: str = Form(...),
    attachment: UploadFile = File(None),
):
    CaseServiceManager.ensure_case_dir()

    case_data = json.loads(data)

    root_cause_type = case_data.get("root_cause_type", "")
    if not root_cause_type:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "root_cause_type 为必填项", "result": None},
        )

    # 保存附件
    attachment_path = None
    if attachment is not None:
        # 先生成 case_id 用于附件命名
        case_id_prefix = str(uuid.uuid4())
        filename = attachment.filename
        save_name = f"{case_id_prefix}_{filename}"
        save_path = os.path.join(CASE_DIR, save_name)
        with open(save_path, "wb") as f:
            content = await attachment.read()
            f.write(content)
        attachment_path = save_name

    try:
        case_record = await CaseServiceManager.create_case(
            kb_id=case_data.get("kb_id", ""),
            root_cause_type=root_cause_type,
            description=case_data.get("description", ""),
            task_ids=case_data.get("task_ids", []),
            task_names=case_data.get("task_names", []),
            log_file_id=case_data.get("log_file_id", ""),
            log_file_name=case_data.get("log_file_name", ""),
            attachment_path=attachment_path,
            case_category=case_data.get("case_category", ""),
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(e), "result": None},
        )

    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "创建成功", "result": case_record},
    )


@router.get("/list")
async def list_cases():
    cases = CaseServiceManager.list_cases()
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "查询成功", "result": cases},
    )


class CaseUpdateRequest(BaseModel):
    case_category: str | None = None
    root_cause_type: str | None = None


@router.put("/{case_id}")
async def update_case(case_id: str, req: CaseUpdateRequest):
    """更新案例的大类（case_category）和/或小类（root_cause_type）。"""
    updated = CaseServiceManager.update_case(
        case_id=case_id,
        case_category=req.case_category,
        root_cause_type=req.root_cause_type,
    )
    if updated is None:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": f"案例 {case_id} 不存在", "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "更新成功", "result": updated},
    )


@router.delete("/{case_id}")
async def delete_case(case_id: str):
    deleted = CaseServiceManager.delete_case(case_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": f"案例 {case_id} 不存在", "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "删除成功", "result": None},
    )


@router.get("/attachment/{case_id}")
async def download_attachment(case_id: str):
    """下载案例关联的附件文件。"""
    json_path = os.path.join(CASE_DIR, f"{case_id}.json")
    if not os.path.exists(json_path):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": f"案例 {case_id} 不存在"},
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            case_record = json.load(f)
    except (json.JSONDecodeError, OSError):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "案例数据损坏"},
        )

    attachment_path = case_record.get("attachment_path")
    if not attachment_path:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "该案例没有关联附件"},
        )

    att_file = os.path.join(CASE_DIR, attachment_path)
    if not os.path.exists(att_file):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "附件文件不存在"},
        )

    download_name = attachment_path.split("_", 1)[1] if "_" in attachment_path else attachment_path
    return FileResponse(
        path=att_file,
        filename=download_name,
        media_type="application/octet-stream",
    )


@router.get("/log_file/{log_file_id}")
async def download_log_file(log_file_id: str):
    """下载案例关联的原始日志文件。"""
    from latency.ENUM.general import FilePath

    log_upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "file", "file_upload"
    )
    candidates = [
        os.path.join(log_upload_dir, f"{log_file_id}.zip"),
        os.path.join(log_upload_dir, f"{log_file_id}.tar.gz"),
        os.path.join(log_upload_dir, f"{log_file_id}.tgz"),
        os.path.join(log_upload_dir, f"{log_file_id}.rar"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return FileResponse(
                path=candidate,
                filename=os.path.basename(candidate),
                media_type="application/octet-stream",
            )

    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": f"日志文件 {log_file_id} 不存在"},
    )


@router.delete("/type/{root_cause_type}")
async def delete_cases_by_type(root_cause_type: str):
    deleted_count = CaseServiceManager.delete_cases_by_type(root_cause_type)
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": f"已删除 {deleted_count} 条案例", "result": None},
    )


# ------------------------------------------------------------------
# 故障大类 / 故障类型 元数据管理接口
# ------------------------------------------------------------------


class CategoryCreateRequest(BaseModel):
    name: str
    description: str = ""


class CategoryUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class TypeCreateRequest(BaseModel):
    category_id: str
    name: str
    description: str = ""


class TypeUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("/categories")
async def list_categories():
    """返回所有故障大类及其故障类型（含案例数量）。"""
    result = CaseServiceManager.list_categories_with_types()
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "查询成功", "result": result},
    )


@router.post("/categories")
async def create_category(req: CategoryCreateRequest):
    name = req.name.strip()
    if not name:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "分类名称不能为空", "result": None},
        )
    result = CaseServiceManager.create_category(name=name, description=req.description.strip())
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "创建成功", "result": result},
    )


@router.put("/categories/{category_id}")
async def update_category(category_id: str, req: CategoryUpdateRequest):
    result = CaseServiceManager.update_category(
        cat_id=category_id,
        name=req.name.strip() if req.name is not None else None,
        description=req.description.strip() if req.description is not None else None,
    )
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "故障大类不存在", "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "更新成功", "result": result},
    )


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, recursive: bool = Query(False)):
    try:
        CaseServiceManager.delete_category(category_id, recursive=recursive)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(e), "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "删除成功", "result": None},
    )


@router.post("/types")
async def create_type(req: TypeCreateRequest):
    name = req.name.strip()
    if not name:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "故障类型名称不能为空", "result": None},
        )
    try:
        result = CaseServiceManager.create_type(
            category_id=req.category_id,
            name=name,
            description=req.description.strip(),
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(e), "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "创建成功", "result": result},
    )


@router.put("/types/{type_id}")
async def update_type(type_id: str, req: TypeUpdateRequest):
    try:
        result = CaseServiceManager.update_type(
            type_id=type_id,
            name=req.name.strip() if req.name is not None else None,
            description=req.description.strip() if req.description is not None else None,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(e), "result": None},
        )
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "故障类型不存在", "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "更新成功", "result": result},
    )


@router.delete("/types/{type_id}")
async def delete_type(type_id: str, recursive: bool = Query(False)):
    try:
        deleted = CaseServiceManager.delete_type(type_id, recursive=recursive)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(e), "result": None},
        )
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "故障类型不存在", "result": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "删除成功", "result": None},
    )
