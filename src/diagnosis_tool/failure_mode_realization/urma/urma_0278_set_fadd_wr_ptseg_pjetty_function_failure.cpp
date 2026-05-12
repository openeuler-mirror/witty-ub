#include "urma_0278_set_fadd_wr_ptseg_pjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0278SetFaddWrPtsegPjettyFunctionFailure> g_urma("urma_0278");

bool Urma0278SetFaddWrPtsegPjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0279", "urma_0280", "urma_0281", "urma_0282", "urma_0283"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0278SetFaddWrPtsegPjettyFunctionFailure::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 函数故障";
}

std::string Urma0278SetFaddWrPtsegPjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0278SetFaddWrPtsegPjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0278SetFaddWrPtsegPjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0278SetFaddWrPtsegPjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0278SetFaddWrPtsegPjettyFunctionFailure::GetId() const
{
    return "urma_0278";
}
} // namespace diag
