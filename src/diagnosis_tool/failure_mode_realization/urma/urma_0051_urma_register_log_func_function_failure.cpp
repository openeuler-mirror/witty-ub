#include "urma_0051_urma_register_log_func_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0051UrmaRegisterLogFuncFunctionFailure> g_urma("urma_0051");

bool Urma0051UrmaRegisterLogFuncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0052"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0051UrmaRegisterLogFuncFunctionFailure::GetName() const
{
    return "urma_register_log_func 函数故障";
}

std::string Urma0051UrmaRegisterLogFuncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0051UrmaRegisterLogFuncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0051UrmaRegisterLogFuncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0051UrmaRegisterLogFuncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0051UrmaRegisterLogFuncFunctionFailure::GetId() const
{
    return "urma_0051";
}
} // namespace diag
