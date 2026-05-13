#include "urma_1025_urma_cmd_register_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1025UrmaCmdRegisterSegFunctionFailure> g_urma("urma_1025");

bool Urma1025UrmaCmdRegisterSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1026", "urma_1027"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1025UrmaCmdRegisterSegFunctionFailure::GetName() const
{
    return "urma_cmd_register_seg 函数故障";
}

std::string Urma1025UrmaCmdRegisterSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1025UrmaCmdRegisterSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1025UrmaCmdRegisterSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1025UrmaCmdRegisterSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1025UrmaCmdRegisterSegFunctionFailure::GetId() const
{
    return "urma_1025";
}
} // namespace diag
