#include "urma_1073_deepcopy_cas_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1073DeepcopyCasWrFunctionFailure> g_urma("urma_1073");

bool Urma1073DeepcopyCasWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1074", "urma_1075", "urma_1076", "urma_1077"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1073DeepcopyCasWrFunctionFailure::GetName() const
{
    return "deepcopy_cas_wr 函数故障";
}

std::string Urma1073DeepcopyCasWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1073DeepcopyCasWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1073DeepcopyCasWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1073DeepcopyCasWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1073DeepcopyCasWrFunctionFailure::GetId() const
{
    return "urma_1073";
}
} // namespace diag
