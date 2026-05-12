#include "urma_0818_urma_query_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0818UrmaQueryJfsFunctionFailure> g_urma("urma_0818");

bool Urma0818UrmaQueryJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0819"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0818UrmaQueryJfsFunctionFailure::GetName() const
{
    return "urma_query_jfs 函数故障";
}

std::string Urma0818UrmaQueryJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0818UrmaQueryJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0818UrmaQueryJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0818UrmaQueryJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0818UrmaQueryJfsFunctionFailure::GetId() const
{
    return "urma_0818";
}
} // namespace diag
