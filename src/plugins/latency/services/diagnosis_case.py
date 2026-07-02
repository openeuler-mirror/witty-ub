from latency.database.managers.diagnosis_case import DiagnosisCaseManager
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
        case_id = await DiagnosisCaseManager.add_case(case)
        return CreateDiagnosisCaseMsg(case_id=case_id or None)

    @staticmethod
    async def get_case(case_id: str) -> GetDiagnosisCaseMsg:
        case = await DiagnosisCaseManager.get_case(case_id)
        return GetDiagnosisCaseMsg(case=case)

    @staticmethod
    async def search_cases(req: SearchDiagnosisCasesRequest) -> SearchDiagnosisCasesMsg:
        total, matches = await DiagnosisCaseManager.search_cases(req)
        return SearchDiagnosisCasesMsg(total=total, matches=matches)

    @staticmethod
    async def mark_case_hit(case_id: str) -> GetDiagnosisCaseMsg:
        await DiagnosisCaseManager.mark_case_hit(case_id)
        case = await DiagnosisCaseManager.get_case(case_id)
        return GetDiagnosisCaseMsg(case=case)
