#include "urma_0680_urma_create_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0680UrmaCreateJfsFunctionFailure> g_urma("urma_0680");

bool Urma0680UrmaCreateJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0681", "urma_0682", "urma_0683", "urma_0684"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0680UrmaCreateJfsFunctionFailure::GetName() const
{
    return "urma_create_jfs 函数故障";
}

std::string Urma0680UrmaCreateJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0680UrmaCreateJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0680UrmaCreateJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0680UrmaCreateJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0680UrmaCreateJfsFunctionFailure::GetId() const
{
    return "urma_0680";
}
} // namespace diag
