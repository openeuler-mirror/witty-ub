from latency.database.managers.diagnosis_case import DiagnosisCasePGManager
from latency.schemas.diagnosis_case import DiagnosisCaseModel
from latency.schemas.request import CreateDiagnosisCaseRequest, SearchDiagnosisCasesRequest
from latency.schemas.response import (
    CreateDiagnosisCaseMsg,
    GetDiagnosisCaseMsg,
    SearchDiagnosisCasesMsg,
)


class DiagnosisCaseService:
    @staticmethod
    async def create_case(req: CreateDiagnosisCaseRequest) -> CreateDiagnosisCaseMsg:
        case = DiagnosisCaseModel.model_validate(req.model_dump())
        case_id = await DiagnosisCasePGManager.add_case(case)
        return CreateDiagnosisCaseMsg(case_id=case_id or None)

    @staticmethod
    async def get_case(case_id: str) -> GetDiagnosisCaseMsg:
        case = await DiagnosisCasePGManager.get_case(case_id)
        return GetDiagnosisCaseMsg(case=case)

    @staticmethod
    async def search_cases(req: SearchDiagnosisCasesRequest) -> SearchDiagnosisCasesMsg:
        total, matches = await DiagnosisCasePGManager.search_cases(req)
        return SearchDiagnosisCasesMsg(total=total, matches=matches)

    @staticmethod
    async def mark_case_hit(case_id: str) -> GetDiagnosisCaseMsg:
        await DiagnosisCasePGManager.mark_case_hit(case_id)
        case = await DiagnosisCasePGManager.get_case(case_id)
        return GetDiagnosisCaseMsg(case=case)
