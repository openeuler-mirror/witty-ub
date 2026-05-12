#include "urma_1140_urma_cmd_unimport_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1140UrmaCmdUnimportSegFunctionFailure> g_urma("urma_1140");

bool Urma1140UrmaCmdUnimportSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1141"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1140UrmaCmdUnimportSegFunctionFailure::GetName() const
{
    return "urma_cmd_unimport_seg 函数故障";
}

std::string Urma1140UrmaCmdUnimportSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1140UrmaCmdUnimportSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1140UrmaCmdUnimportSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1140UrmaCmdUnimportSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1140UrmaCmdUnimportSegFunctionFailure::GetId() const
{
    return "urma_1140";
}
} // namespace diag
