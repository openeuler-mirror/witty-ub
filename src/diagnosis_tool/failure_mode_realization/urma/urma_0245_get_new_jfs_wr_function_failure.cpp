#include "urma_0245_get_new_jfs_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0245GetNewJfsWrFunctionFailure> g_urma("urma_0245");

bool Urma0245GetNewJfsWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0246"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0245GetNewJfsWrFunctionFailure::GetName() const
{
    return "get_new_jfs_wr 函数故障";
}

std::string Urma0245GetNewJfsWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0245GetNewJfsWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0245GetNewJfsWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0245GetNewJfsWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0245GetNewJfsWrFunctionFailure::GetId() const
{
    return "urma_0245";
}
} // namespace diag
