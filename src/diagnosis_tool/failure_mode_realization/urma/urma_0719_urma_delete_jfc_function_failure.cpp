#include "urma_0719_urma_delete_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0719UrmaDeleteJfcFunctionFailure> g_urma("urma_0719");

bool Urma0719UrmaDeleteJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0720", "urma_0721", "urma_0722"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0719UrmaDeleteJfcFunctionFailure::GetName() const
{
    return "urma_delete_jfc 函数故障";
}

std::string Urma0719UrmaDeleteJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0719UrmaDeleteJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0719UrmaDeleteJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0719UrmaDeleteJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0719UrmaDeleteJfcFunctionFailure::GetId() const
{
    return "urma_0719";
}
} // namespace diag
