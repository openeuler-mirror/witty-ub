#include "urma_0878_urma_post_jfr_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0878UrmaPostJfrWrFunctionFailure> g_urma("urma_0878");

bool Urma0878UrmaPostJfrWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0879"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0878UrmaPostJfrWrFunctionFailure::GetName() const
{
    return "urma_post_jfr_wr 函数故障";
}

std::string Urma0878UrmaPostJfrWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0878UrmaPostJfrWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0878UrmaPostJfrWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0878UrmaPostJfrWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0878UrmaPostJfrWrFunctionFailure::GetId() const
{
    return "urma_0878";
}
} // namespace diag
