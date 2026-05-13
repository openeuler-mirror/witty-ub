#include "urma_0991_urma_get_eid_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0991UrmaGetEidListFunctionFailure> g_urma("urma_0991");

bool Urma0991UrmaGetEidListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0992"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0991UrmaGetEidListFunctionFailure::GetName() const
{
    return "urma_get_eid_list 函数故障";
}

std::string Urma0991UrmaGetEidListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0991UrmaGetEidListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0991UrmaGetEidListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0991UrmaGetEidListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0991UrmaGetEidListFunctionFailure::GetId() const
{
    return "urma_0991";
}
} // namespace diag
