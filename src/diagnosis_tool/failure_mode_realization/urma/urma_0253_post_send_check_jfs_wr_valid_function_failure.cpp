#include "urma_0253_post_send_check_jfs_wr_valid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0253PostSendCheckJfsWrValidFunctionFailure> g_urma("urma_0253");

bool Urma0253PostSendCheckJfsWrValidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0254", "urma_0255", "urma_0256"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0253PostSendCheckJfsWrValidFunctionFailure::GetName() const
{
    return "post_send_check_jfs_wr_valid 函数故障";
}

std::string Urma0253PostSendCheckJfsWrValidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0253PostSendCheckJfsWrValidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0253PostSendCheckJfsWrValidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0253PostSendCheckJfsWrValidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0253PostSendCheckJfsWrValidFunctionFailure::GetId() const
{
    return "urma_0253";
}
} // namespace diag
