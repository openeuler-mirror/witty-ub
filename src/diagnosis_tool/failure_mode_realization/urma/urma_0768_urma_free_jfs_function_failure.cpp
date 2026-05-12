#include "urma_0768_urma_free_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0768UrmaFreeJfsFunctionFailure> g_urma("urma_0768");

bool Urma0768UrmaFreeJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0769", "urma_0770", "urma_0771"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0768UrmaFreeJfsFunctionFailure::GetName() const
{
    return "urma_free_jfs 函数故障";
}

std::string Urma0768UrmaFreeJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0768UrmaFreeJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0768UrmaFreeJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0768UrmaFreeJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0768UrmaFreeJfsFunctionFailure::GetId() const
{
    return "urma_0768";
}
} // namespace diag
