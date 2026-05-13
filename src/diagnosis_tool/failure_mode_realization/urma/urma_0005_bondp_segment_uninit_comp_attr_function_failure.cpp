#include "urma_0005_bondp_segment_uninit_comp_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0005BondpSegmentUninitCompAttrFunctionFailure> g_urma("urma_0005");

bool Urma0005BondpSegmentUninitCompAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0006", "urma_0007"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0005BondpSegmentUninitCompAttrFunctionFailure::GetName() const
{
    return "bondp_segment_uninit_comp_attr 函数故障";
}

std::string Urma0005BondpSegmentUninitCompAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0005BondpSegmentUninitCompAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0005BondpSegmentUninitCompAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0005BondpSegmentUninitCompAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0005BondpSegmentUninitCompAttrFunctionFailure::GetId() const
{
    return "urma_0005";
}
} // namespace diag
