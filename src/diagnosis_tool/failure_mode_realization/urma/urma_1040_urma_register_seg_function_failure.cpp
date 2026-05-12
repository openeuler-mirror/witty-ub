#include "urma_1040_urma_register_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1040UrmaRegisterSegFunctionFailure> g_urma("urma_1040");

bool Urma1040UrmaRegisterSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1041", "urma_1042"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1040UrmaRegisterSegFunctionFailure::GetName() const
{
    return "urma_register_seg 函数故障";
}

std::string Urma1040UrmaRegisterSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1040UrmaRegisterSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1040UrmaRegisterSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1040UrmaRegisterSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1040UrmaRegisterSegFunctionFailure::GetId() const
{
    return "urma_1040";
}
} // namespace diag
