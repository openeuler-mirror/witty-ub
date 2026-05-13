#include "urma_1154_urma_unimport_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1154UrmaUnimportSegFunctionFailure> g_urma("urma_1154");

bool Urma1154UrmaUnimportSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1155"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1154UrmaUnimportSegFunctionFailure::GetName() const
{
    return "urma_unimport_seg 函数故障";
}

std::string Urma1154UrmaUnimportSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1154UrmaUnimportSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1154UrmaUnimportSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1154UrmaUnimportSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1154UrmaUnimportSegFunctionFailure::GetId() const
{
    return "urma_1154";
}
} // namespace diag
