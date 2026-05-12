#include "urma_0462_urma_cmd_free_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0462UrmaCmdFreeJfcFunctionFailure> g_urma("urma_0462");

bool Urma0462UrmaCmdFreeJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0463", "urma_0464", "urma_0465"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0462UrmaCmdFreeJfcFunctionFailure::GetName() const
{
    return "urma_cmd_free_jfc 函数故障";
}

std::string Urma0462UrmaCmdFreeJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0462UrmaCmdFreeJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0462UrmaCmdFreeJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0462UrmaCmdFreeJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0462UrmaCmdFreeJfcFunctionFailure::GetId() const
{
    return "urma_0462";
}
} // namespace diag
