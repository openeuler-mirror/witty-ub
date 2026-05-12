#include "urma_0389_urma_cmd_create_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0389UrmaCmdCreateJfceFunctionFailure> g_urma("urma_0389");

bool Urma0389UrmaCmdCreateJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0390", "urma_0391"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0389UrmaCmdCreateJfceFunctionFailure::GetName() const
{
    return "urma_cmd_create_jfce 函数故障";
}

std::string Urma0389UrmaCmdCreateJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0389UrmaCmdCreateJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0389UrmaCmdCreateJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0389UrmaCmdCreateJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0389UrmaCmdCreateJfceFunctionFailure::GetId() const
{
    return "urma_0389";
}
} // namespace diag
