#include "urma_0864_urma_parse_rsvd_jetty_range_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0864UrmaParseRsvdJettyRangeFunctionFailure> g_urma("urma_0864");

bool Urma0864UrmaParseRsvdJettyRangeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0865", "urma_0866"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0864UrmaParseRsvdJettyRangeFunctionFailure::GetName() const
{
    return "urma_parse_rsvd_jetty_range 函数故障";
}

std::string Urma0864UrmaParseRsvdJettyRangeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0864UrmaParseRsvdJettyRangeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0864UrmaParseRsvdJettyRangeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0864UrmaParseRsvdJettyRangeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0864UrmaParseRsvdJettyRangeFunctionFailure::GetId() const
{
    return "urma_0864";
}
} // namespace diag
