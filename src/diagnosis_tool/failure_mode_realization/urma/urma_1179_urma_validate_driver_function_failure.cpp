#include "urma_1179_urma_validate_driver_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1179UrmaValidateDriverFunctionFailure> g_urma("urma_1179");

bool Urma1179UrmaValidateDriverFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1180"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1179UrmaValidateDriverFunctionFailure::GetName() const
{
    return "urma_validate_driver 函数故障";
}

std::string Urma1179UrmaValidateDriverFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1179UrmaValidateDriverFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1179UrmaValidateDriverFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1179UrmaValidateDriverFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1179UrmaValidateDriverFunctionFailure::GetId() const
{
    return "urma_1179";
}
} // namespace diag
