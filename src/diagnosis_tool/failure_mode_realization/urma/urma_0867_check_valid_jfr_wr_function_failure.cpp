#include "urma_0867_check_valid_jfr_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0867CheckValidJfrWrFunctionFailure> g_urma("urma_0867");

bool Urma0867CheckValidJfrWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0868"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0867CheckValidJfrWrFunctionFailure::GetName() const
{
    return "check_valid_jfr_wr 函数故障";
}

std::string Urma0867CheckValidJfrWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0867CheckValidJfrWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0867CheckValidJfrWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0867CheckValidJfrWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0867CheckValidJfrWrFunctionFailure::GetId() const
{
    return "urma_0867";
}
} // namespace diag
