#include "urma_0457_urma_cmd_exchange_tp_info_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0457UrmaCmdExchangeTpInfoFunctionFailure> g_urma("urma_0457");

bool Urma0457UrmaCmdExchangeTpInfoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0458"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0457UrmaCmdExchangeTpInfoFunctionFailure::GetName() const
{
    return "urma_cmd_exchange_tp_info 函数故障";
}

std::string Urma0457UrmaCmdExchangeTpInfoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0457UrmaCmdExchangeTpInfoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0457UrmaCmdExchangeTpInfoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0457UrmaCmdExchangeTpInfoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0457UrmaCmdExchangeTpInfoFunctionFailure::GetId() const
{
    return "urma_0457";
}
} // namespace diag
