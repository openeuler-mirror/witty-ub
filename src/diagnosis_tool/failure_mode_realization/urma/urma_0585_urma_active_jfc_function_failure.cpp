#include "urma_0585_urma_active_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0585UrmaActiveJfcFunctionFailure> g_urma("urma_0585");

bool Urma0585UrmaActiveJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0586", "urma_0587", "urma_0588", "urma_0589"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0585UrmaActiveJfcFunctionFailure::GetName() const
{
    return "urma_active_jfc 函数故障";
}

std::string Urma0585UrmaActiveJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0585UrmaActiveJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0585UrmaActiveJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0585UrmaActiveJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0585UrmaActiveJfcFunctionFailure::GetId() const
{
    return "urma_0585";
}
} // namespace diag
