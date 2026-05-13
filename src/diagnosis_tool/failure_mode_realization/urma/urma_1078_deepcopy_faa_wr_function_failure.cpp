#include "urma_1078_deepcopy_faa_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1078DeepcopyFaaWrFunctionFailure> g_urma("urma_1078");

bool Urma1078DeepcopyFaaWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1079", "urma_1080", "urma_1081", "urma_1082"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1078DeepcopyFaaWrFunctionFailure::GetName() const
{
    return "deepcopy_faa_wr 函数故障";
}

std::string Urma1078DeepcopyFaaWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1078DeepcopyFaaWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1078DeepcopyFaaWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1078DeepcopyFaaWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1078DeepcopyFaaWrFunctionFailure::GetId() const
{
    return "urma_1078";
}
} // namespace diag
