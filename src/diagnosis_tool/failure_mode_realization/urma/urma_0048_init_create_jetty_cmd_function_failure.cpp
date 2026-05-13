#include "urma_0048_init_create_jetty_cmd_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0048InitCreateJettyCmdFunctionFailure> g_urma("urma_0048");

bool Urma0048InitCreateJettyCmdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0049", "urma_0050"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0048InitCreateJettyCmdFunctionFailure::GetName() const
{
    return "init_create_jetty_cmd 函数故障";
}

std::string Urma0048InitCreateJettyCmdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0048InitCreateJettyCmdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0048InitCreateJettyCmdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0048InitCreateJettyCmdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0048InitCreateJettyCmdFunctionFailure::GetId() const
{
    return "urma_0048";
}
} // namespace diag
