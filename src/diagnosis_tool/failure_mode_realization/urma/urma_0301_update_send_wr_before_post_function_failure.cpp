#include "urma_0301_update_send_wr_before_post_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0301UpdateSendWrBeforePostFunctionFailure> g_urma("urma_0301");

bool Urma0301UpdateSendWrBeforePostFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0302", "urma_0303"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0301UpdateSendWrBeforePostFunctionFailure::GetName() const
{
    return "update_send_wr_before_post 函数故障";
}

std::string Urma0301UpdateSendWrBeforePostFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0301UpdateSendWrBeforePostFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0301UpdateSendWrBeforePostFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0301UpdateSendWrBeforePostFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0301UpdateSendWrBeforePostFunctionFailure::GetId() const
{
    return "urma_0301";
}
} // namespace diag
