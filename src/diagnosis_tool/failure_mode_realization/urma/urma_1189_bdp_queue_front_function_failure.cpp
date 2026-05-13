#include "urma_1189_bdp_queue_front_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1189BdpQueueFrontFunctionFailure> g_urma("urma_1189");

bool Urma1189BdpQueueFrontFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1190"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1189BdpQueueFrontFunctionFailure::GetName() const
{
    return "bdp_queue_front 函数故障";
}

std::string Urma1189BdpQueueFrontFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1189BdpQueueFrontFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1189BdpQueueFrontFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1189BdpQueueFrontFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1189BdpQueueFrontFunctionFailure::GetId() const
{
    return "urma_1189";
}
} // namespace diag
