#include "urma_0880_urma_post_jfs_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0880UrmaPostJfsWrFunctionFailure> g_urma("urma_0880");

bool Urma0880UrmaPostJfsWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0881"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0880UrmaPostJfsWrFunctionFailure::GetName() const
{
    return "urma_post_jfs_wr 函数故障";
}

std::string Urma0880UrmaPostJfsWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0880UrmaPostJfsWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0880UrmaPostJfsWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0880UrmaPostJfsWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0880UrmaPostJfsWrFunctionFailure::GetId() const
{
    return "urma_0880";
}
} // namespace diag
