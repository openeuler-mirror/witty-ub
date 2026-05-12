#include "urma_0915_bondp_segment_get_args_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0915BondpSegmentGetArgsListFunctionFailure> g_urma("urma_0915");

bool Urma0915BondpSegmentGetArgsListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0916", "urma_0917"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0915BondpSegmentGetArgsListFunctionFailure::GetName() const
{
    return "bondp_segment_get_args_list 函数故障";
}

std::string Urma0915BondpSegmentGetArgsListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0915BondpSegmentGetArgsListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0915BondpSegmentGetArgsListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0915BondpSegmentGetArgsListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0915BondpSegmentGetArgsListFunctionFailure::GetId() const
{
    return "urma_0915";
}
} // namespace diag
