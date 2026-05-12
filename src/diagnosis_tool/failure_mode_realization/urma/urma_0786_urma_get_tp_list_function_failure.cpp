#include "urma_0786_urma_get_tp_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0786UrmaGetTpListFunctionFailure> g_urma("urma_0786");

bool Urma0786UrmaGetTpListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0787", "urma_0788"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0786UrmaGetTpListFunctionFailure::GetName() const
{
    return "urma_get_tp_list 函数故障";
}

std::string Urma0786UrmaGetTpListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0786UrmaGetTpListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0786UrmaGetTpListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0786UrmaGetTpListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0786UrmaGetTpListFunctionFailure::GetId() const
{
    return "urma_0786";
}
} // namespace diag
