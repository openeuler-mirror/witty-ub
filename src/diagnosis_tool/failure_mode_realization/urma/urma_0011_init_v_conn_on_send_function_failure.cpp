#include "urma_0011_init_v_conn_on_send_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0011InitVConnOnSendFunctionFailure> g_urma("urma_0011");

bool Urma0011InitVConnOnSendFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0012"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0011InitVConnOnSendFunctionFailure::GetName() const
{
    return "init_v_conn_on_send 函数故障";
}

std::string Urma0011InitVConnOnSendFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0011InitVConnOnSendFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0011InitVConnOnSendFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0011InitVConnOnSendFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0011InitVConnOnSendFunctionFailure::GetId() const
{
    return "urma_0011";
}
} // namespace diag
