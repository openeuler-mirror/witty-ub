#include "urma_0668_urma_create_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0668UrmaCreateJfcFunctionFailure> g_urma("urma_0668");

bool Urma0668UrmaCreateJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0669", "urma_0670", "urma_0671"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0668UrmaCreateJfcFunctionFailure::GetName() const
{
    return "urma_create_jfc 函数故障";
}

std::string Urma0668UrmaCreateJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0668UrmaCreateJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0668UrmaCreateJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0668UrmaCreateJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0668UrmaCreateJfcFunctionFailure::GetId() const
{
    return "urma_0668";
}
} // namespace diag
