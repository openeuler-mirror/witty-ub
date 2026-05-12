#include "urma_0386_urma_cmd_create_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0386UrmaCmdCreateJfcFunctionFailure> g_urma("urma_0386");

bool Urma0386UrmaCmdCreateJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0387", "urma_0388"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0386UrmaCmdCreateJfcFunctionFailure::GetName() const
{
    return "urma_cmd_create_jfc 函数故障";
}

std::string Urma0386UrmaCmdCreateJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0386UrmaCmdCreateJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0386UrmaCmdCreateJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0386UrmaCmdCreateJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0386UrmaCmdCreateJfcFunctionFailure::GetId() const
{
    return "urma_0386";
}
} // namespace diag
