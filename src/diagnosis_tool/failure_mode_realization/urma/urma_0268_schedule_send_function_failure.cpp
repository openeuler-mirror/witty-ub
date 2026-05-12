#include "urma_0268_schedule_send_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0268ScheduleSendFunctionFailure> g_urma("urma_0268");

bool Urma0268ScheduleSendFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0269"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0268ScheduleSendFunctionFailure::GetName() const
{
    return "schedule_send 函数故障";
}

std::string Urma0268ScheduleSendFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0268ScheduleSendFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0268ScheduleSendFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0268ScheduleSendFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0268ScheduleSendFunctionFailure::GetId() const
{
    return "urma_0268";
}
} // namespace diag
