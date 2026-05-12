#include "urma_0292_set_write_wr_ptseg_ptjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0292SetWriteWrPtsegPtjettyFunctionFailure> g_urma("urma_0292");

bool Urma0292SetWriteWrPtsegPtjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0293", "urma_0294", "urma_0295", "urma_0296",
                                                    "urma_0297", "urma_0298", "urma_0299", "urma_0300"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0292SetWriteWrPtsegPtjettyFunctionFailure::GetName() const
{
    return "set_write_wr_ptseg_ptjetty 函数故障";
}

std::string Urma0292SetWriteWrPtsegPtjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0292SetWriteWrPtsegPtjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0292SetWriteWrPtsegPtjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0292SetWriteWrPtsegPtjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0292SetWriteWrPtsegPtjettyFunctionFailure::GetId() const
{
    return "urma_0292";
}
} // namespace diag
