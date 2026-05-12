#include "urma_0550_urma_cmd_set_jfs_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0550UrmaCmdSetJfsOptFunctionFailure> g_urma("urma_0550");

bool Urma0550UrmaCmdSetJfsOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0551", "urma_0552", "urma_0553", "urma_0554"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0550UrmaCmdSetJfsOptFunctionFailure::GetName() const
{
    return "urma_cmd_set_jfs_opt 函数故障";
}

std::string Urma0550UrmaCmdSetJfsOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0550UrmaCmdSetJfsOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0550UrmaCmdSetJfsOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0550UrmaCmdSetJfsOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0550UrmaCmdSetJfsOptFunctionFailure::GetId() const
{
    return "urma_0550";
}
} // namespace diag
