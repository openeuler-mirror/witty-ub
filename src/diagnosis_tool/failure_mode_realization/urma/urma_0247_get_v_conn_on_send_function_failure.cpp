#include "urma_0247_get_v_conn_on_send_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0247GetVConnOnSendFunctionFailure> g_urma("urma_0247");

bool Urma0247GetVConnOnSendFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0248"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0247GetVConnOnSendFunctionFailure::GetName() const
{
    return "get_v_conn_on_send 函数故障";
}

std::string Urma0247GetVConnOnSendFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0247GetVConnOnSendFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0247GetVConnOnSendFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0247GetVConnOnSendFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0247GetVConnOnSendFunctionFailure::GetId() const
{
    return "urma_0247";
}
} // namespace diag
