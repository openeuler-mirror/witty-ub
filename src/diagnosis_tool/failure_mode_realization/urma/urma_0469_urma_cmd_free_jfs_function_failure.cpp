#include "urma_0469_urma_cmd_free_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0469UrmaCmdFreeJfsFunctionFailure> g_urma("urma_0469");

bool Urma0469UrmaCmdFreeJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0470", "urma_0471"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0469UrmaCmdFreeJfsFunctionFailure::GetName() const
{
    return "urma_cmd_free_jfs 函数故障";
}

std::string Urma0469UrmaCmdFreeJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0469UrmaCmdFreeJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0469UrmaCmdFreeJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0469UrmaCmdFreeJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0469UrmaCmdFreeJfsFunctionFailure::GetId() const
{
    return "urma_0469";
}
} // namespace diag
