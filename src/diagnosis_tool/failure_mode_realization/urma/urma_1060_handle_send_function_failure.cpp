#include "urma_1060_handle_send_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1060HandleSendFunctionFailure> g_urma("urma_1060");

bool Urma1060HandleSendFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1061"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1060HandleSendFunctionFailure::GetName() const
{
    return "handle_send 函数故障";
}

std::string Urma1060HandleSendFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1060HandleSendFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1060HandleSendFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1060HandleSendFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1060HandleSendFunctionFailure::GetId() const
{
    return "urma_1060";
}
} // namespace diag
