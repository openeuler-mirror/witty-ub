#include "urma_1215_urma_check_opt_valid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1215UrmaCheckOptValidFunctionFailure> g_urma("urma_1215");

bool Urma1215UrmaCheckOptValidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1216"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1215UrmaCheckOptValidFunctionFailure::GetName() const
{
    return "urma_check_opt_valid 函数故障";
}

std::string Urma1215UrmaCheckOptValidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1215UrmaCheckOptValidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1215UrmaCheckOptValidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1215UrmaCheckOptValidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1215UrmaCheckOptValidFunctionFailure::GetId() const
{
    return "urma_1215";
}
} // namespace diag
