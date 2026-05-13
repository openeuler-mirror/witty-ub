#include "urma_1150_urma_free_token_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1150UrmaFreeTokenIdFunctionFailure> g_urma("urma_1150");

bool Urma1150UrmaFreeTokenIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1151", "urma_1152", "urma_1153"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1150UrmaFreeTokenIdFunctionFailure::GetName() const
{
    return "urma_free_token_id 函数故障";
}

std::string Urma1150UrmaFreeTokenIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1150UrmaFreeTokenIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1150UrmaFreeTokenIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1150UrmaFreeTokenIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1150UrmaFreeTokenIdFunctionFailure::GetId() const
{
    return "urma_1150";
}
} // namespace diag
