#include "urma_1023_urma_cmd_import_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1023UrmaCmdImportSegFunctionFailure> g_urma("urma_1023");

bool Urma1023UrmaCmdImportSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1024"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1023UrmaCmdImportSegFunctionFailure::GetName() const
{
    return "urma_cmd_import_seg 函数故障";
}

std::string Urma1023UrmaCmdImportSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1023UrmaCmdImportSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1023UrmaCmdImportSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1023UrmaCmdImportSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1023UrmaCmdImportSegFunctionFailure::GetId() const
{
    return "urma_1023";
}
} // namespace diag
