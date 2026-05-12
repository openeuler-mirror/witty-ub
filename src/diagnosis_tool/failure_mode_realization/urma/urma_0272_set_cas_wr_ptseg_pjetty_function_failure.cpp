#include "urma_0272_set_cas_wr_ptseg_pjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0272SetCasWrPtsegPjettyFunctionFailure> g_urma("urma_0272");

bool Urma0272SetCasWrPtsegPjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0273", "urma_0274", "urma_0275", "urma_0276", "urma_0277"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0272SetCasWrPtsegPjettyFunctionFailure::GetName() const
{
    return "set_cas_wr_ptseg_pjetty 函数故障";
}

std::string Urma0272SetCasWrPtsegPjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0272SetCasWrPtsegPjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0272SetCasWrPtsegPjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0272SetCasWrPtsegPjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0272SetCasWrPtsegPjettyFunctionFailure::GetId() const
{
    return "urma_0272";
}
} // namespace diag
