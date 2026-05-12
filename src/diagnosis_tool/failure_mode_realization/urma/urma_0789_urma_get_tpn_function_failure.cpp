#include "urma_0789_urma_get_tpn_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0789UrmaGetTpnFunctionFailure> g_urma("urma_0789");

bool Urma0789UrmaGetTpnFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0790"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0789UrmaGetTpnFunctionFailure::GetName() const
{
    return "urma_get_tpn 函数故障";
}

std::string Urma0789UrmaGetTpnFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0789UrmaGetTpnFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0789UrmaGetTpnFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0789UrmaGetTpnFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0789UrmaGetTpnFunctionFailure::GetId() const
{
    return "urma_0789";
}
} // namespace diag
