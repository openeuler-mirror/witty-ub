#include "urma_0040_init_slave_context_fd_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0040InitSlaveContextFdFunctionFailure> g_urma("urma_0040");

bool Urma0040InitSlaveContextFdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0041"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0040InitSlaveContextFdFunctionFailure::GetName() const
{
    return "init_slave_context_fd 函数故障";
}

std::string Urma0040InitSlaveContextFdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0040InitSlaveContextFdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0040InitSlaveContextFdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0040InitSlaveContextFdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0040InitSlaveContextFdFunctionFailure::GetId() const
{
    return "urma_0040";
}
} // namespace diag
