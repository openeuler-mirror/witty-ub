#include "urma_0288_set_send_wr_ptseg_ptjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0288SetSendWrPtsegPtjettyFunctionFailure> g_urma("urma_0288");

bool Urma0288SetSendWrPtsegPtjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0289", "urma_0290", "urma_0291"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0288SetSendWrPtsegPtjettyFunctionFailure::GetName() const
{
    return "set_send_wr_ptseg_ptjetty 函数故障";
}

std::string Urma0288SetSendWrPtsegPtjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0288SetSendWrPtsegPtjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0288SetSendWrPtsegPtjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0288SetSendWrPtsegPtjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0288SetSendWrPtsegPtjettyFunctionFailure::GetId() const
{
    return "urma_0288";
}
} // namespace diag
