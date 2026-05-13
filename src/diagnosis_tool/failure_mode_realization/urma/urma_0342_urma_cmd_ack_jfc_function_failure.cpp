#include "urma_0342_urma_cmd_ack_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0342UrmaCmdAckJfcFunctionFailure> g_urma("urma_0342");

bool Urma0342UrmaCmdAckJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0343"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0342UrmaCmdAckJfcFunctionFailure::GetName() const
{
    return "urma_cmd_ack_jfc 函数故障";
}

std::string Urma0342UrmaCmdAckJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0342UrmaCmdAckJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0342UrmaCmdAckJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0342UrmaCmdAckJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0342UrmaCmdAckJfcFunctionFailure::GetId() const
{
    return "urma_0342";
}
} // namespace diag
